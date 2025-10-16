from typing import List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from ...browser.controller.base import BaseController
from ...browser.registry import ActionRegistry
from ...browser.utils import mark_page
from utils.message import Message, format_context, Metadata, ActionOutput
import time
import os
load_dotenv()


class WebAgentState(TypedDict):
    user_query: str
    messages: List[Message]
    global_plan: str
    timestep: int
    actions: List[dict]


class WebAgent():
    def __init__(self, llm: BaseChatModel, controller: BaseController):
        self.llm = llm
        self.controller = controller
        self.driver = controller.driver
        self.action_registry = ActionRegistry(controller)
        self.workflow = self._initalize_workflow()
        self.graph = self.workflow.compile()
        self.wait_period = None

        ## HTML DOM Related ##
        self.elements = None
        self.prompt = None
        self.screenshot = None
        
        ## JSON Output Parser ##
        self.action_parser = JsonOutputParser(pydantic_object=ActionOutput)
        

    def _get_prompt(self, name: str) -> str:
        prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
        prompt_file = os.path.join(prompts_dir, f"{name}.md")
        with open(prompt_file, 'r') as f:
            return f.read()
    
    def _convert_action_to_json(self, action_output: dict) -> dict:
        action_name = action_output.get("action")
        mmid = action_output.get("mmid")
        params = action_output.get("params", {})
        
        # Actions that interact with elements via MMID
        element_actions = {"click", "type", "scroll_to", "move", "scroll"}
        
        # Build the final params dict for the action
        final_params = params.copy()
        
        # If this action uses MMID and we have element data
        if mmid is not None and action_name in element_actions and self.elements:
            element_data = self.elements.get(str(mmid))
            print(self.elements)
            if element_data:
                # Prefer enhanced CSS selector, then CSS selector, then XPath
                selector = (
                    element_data.get('enhanced_css_selector') or 
                    element_data.get('css_selector') or 
                    element_data.get('xpath')
                )
                
                if selector:
                    # Determine the selector type
                    if element_data.get('enhanced_css_selector') or element_data.get('css_selector'):
                        final_params['by'] = 'css selector'
                    else:
                        final_params['by'] = 'xpath'
                    
                    final_params['selector'] = selector
                
                # Get absolute screen coordinates using the controller method
                # This converts element coordinates to actual screen coordinates
                abs_x, abs_y = self.controller.get_element_coordinates(
                    element_data.get('x', 0), 
                    element_data.get('y', 0), 
                    element_data.get('width', 0), 
                    element_data.get('height', 0),
                    percentage=0.5  # Click in the center of the element
                )
                
                # Add absolute screen coordinates as fallback
                final_params['x'] = abs_x
                final_params['y'] = abs_y
        
        return {
            "type": action_name,
            "params": final_params
        }


    def run(self, user_query: str, messages: List[Message] = [], wait_period: float = 0.5):
        self.wait_period = wait_period
        state = WebAgentState(user_query=user_query, messages=messages, global_plan="", timestep=0, actions=[])
        state = self.graph.invoke(state, { "recursion_limit": 100})
        return state
    
    def _annotate(self, state: WebAgentState):
        time.sleep(2 * self.wait_period)
        self.elements, self.prompt, self.screenshot = mark_page(self.driver).with_retry().invoke(None)
        state["messages"] += [Metadata(
            timestamp=state["timestep"], 
            elements=self.elements, 
            element_description=self.prompt, 
            screenshot=self.screenshot, 
            dom="",
            url=self.driver.current_url, 
            title=self.driver.title
        )]
        state["timestep"] += 1
        return { **state }
    

    def _plan(self, state: WebAgentState):
        prompt = self._get_prompt("PLAN_PROMPT")
        if state["global_plan"] != "":
            prompt = self._get_prompt("REPLAN_PROMPT")

        response = self.llm.invoke(input=[
            SystemMessage(content=self._get_prompt("ACTION_SHORT_PROMPT") + "\n\n" + prompt),
            HumanMessage(content=[
                {
                    "type": "text", 
                    "text": f"""## User Query: {state['user_query']}
                    ## Initial HTML State: {self.prompt}
                    You MUST start with the '## Step 1' header and follow the format provided in the examples."""
                },
                {
                    "type": "text",
                    "text": f"""## Previous Action Trajectory:\n{format_context(state['messages'])}\n## Current HTML: {self.prompt}"""
                },
                {
                    "type": "image",
                    "source_type": "base64",
                    "data": self.screenshot,
                    "mime_type": "image/png"
                }
            ])
        ])
        print(self.prompt)
        return { **state, "global_plan": response.content }
    
    def _execute(self, state: WebAgentState):
        # Create the system message with action instructions
        system_content = (
            self._get_prompt("RULES_PROMPT") + "\n\n" +
            self._get_prompt("EXECUTE_PROMPT").format(
                intent=state['user_query'], 
                global_plan=state['global_plan']
            ) + "\n\n" +
            self._get_prompt("ACTION_PROMPT")
        )

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_content),
            HumanMessage(content=f"## Previous Action Trajectory:\n{format_context(state['messages'])}\n## Current HTML: {self.prompt}"),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": f"""Screenshot of the Current Page"""
                },
                {
                    "type": "image",
                    "source_type": "base64",
                    "data": self.screenshot,
                    "mime_type": "image/png"
                }
            ])
        ])



        chain = prompt | self.llm | self.action_parser
        response = chain.invoke({})

        state["messages"] += [ActionOutput(**response)]
        
        replayable_action = self._convert_action_to_json(response)
        print(replayable_action)
        state["actions"] = state["actions"] + [replayable_action]
            
        # Execute the action using the action registry
        action_name = replayable_action["type"]
        action_params = replayable_action["params"]
        
        result = self.action_registry.execute(action_name, action_params)
               
        state["timestep"] += 1
        return { **state }
    
    def _should_continue(self, state: WebAgentState):
        """Check if the agent should continue or terminate."""
        # Check if the last action was terminate
        if state.get("actions"):
            last_action = state["actions"][-1]
            if last_action.get("type") == "terminate":
                return END
        
        # Check if we've exceeded max timesteps (safety check)
        if state.get("timestep", 0) > 50:
            print("WARNING: Max timesteps exceeded, terminating")
            return END
        
        return "annotate"
    
    def _initalize_workflow(self):
        workflow = StateGraph(WebAgentState)
        workflow.add_node("annotate", self._annotate)
        workflow.add_node("plan", self._plan)
        workflow.add_node("execute", self._execute)
        workflow.add_edge(START, "annotate")
        workflow.add_edge("annotate", "plan")
        workflow.add_edge("plan", "execute")
        workflow.add_conditional_edges("execute", self._should_continue)
        return workflow
