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
from netgent.utils.message import Message, format_context, Metadata, ActionOutput
import time
import os
import re
import json
load_dotenv()


class WebAgentState(TypedDict):
    user_query: str
    messages: List[Message]
    global_plan: str
    timestep: int
    actions: List[dict]


class WebAgent():
    def __init__(self, llm: BaseChatModel, controller: BaseController, domain: str = "web"):
        self.llm = llm
        self.controller = controller
        # Desktop controllers have no Selenium driver; perception goes through
        # the controller's snapshot()/get_context() instead.
        self.driver = getattr(controller, "driver", None)
        self.domain = domain
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
        # Prefer a domain-specific variant (e.g. prompts/desktop/ACTION_PROMPT.md)
        # and fall back to the shared browser prompt when none exists.
        if self.domain and self.domain != "web":
            domain_file = os.path.join(prompts_dir, self.domain, f"{name}.md")
            if os.path.isfile(domain_file):
                with open(domain_file, 'r') as f:
                    return f.read()
        prompt_file = os.path.join(prompts_dir, f"{name}.md")
        with open(prompt_file, 'r') as f:
            return f.read()
    
    def _convert_action_to_json(self, action_output: dict) -> dict:
        # Delegate mmid -> replayable action mapping to the controller, so the
        # browser (CSS/xpath) and desktop (AX locator) domains each attach the
        # right durable locator plus fallback coordinates.
        return self.controller.resolve_element_action(action_output, self.elements)


    def run(self, user_query: str, messages: List[Message] = [], wait_period: float = 0.5):
        self.wait_period = wait_period
        state = WebAgentState(user_query=user_query, messages=messages, global_plan="", timestep=0, actions=[])
        state = self.graph.invoke(state, { "recursion_limit": 100})
        return state
    
    def _annotate(self, state: WebAgentState):
        time.sleep(2 * self.wait_period)
        # Controller-agnostic perception: DOM snapshot for browsers, AX-tree
        # snapshot (via the host bridge) for desktop apps.
        self.elements, self.prompt, self.screenshot = self.controller.snapshot()
        context = self.controller.get_context()
        state["messages"] += [Metadata(
            timestamp=state["timestep"],
            elements=self.elements,
            element_description=self.prompt,
            screenshot=self.screenshot,
            dom="",
            url=context.get("url", ""),
            title=context.get("title", "")
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



        response = self._invoke_action(prompt)

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
    
    def _invoke_action(self, prompt, max_attempts: int = 2) -> dict:
        """Get the next action from the LLM, robust to malformed output.

        Occasionally the model returns prose or not-quite-JSON (a common
        LLM failure), which would otherwise raise an OutputParserException and
        crash the whole run. We: (1) try the strict JSON parser a couple of
        times, (2) fall back to salvaging a JSON object from the raw text, and
        (3) as a last resort emit a `terminate` action so the state ends
        gracefully instead of aborting the workflow.
        """
        last_err = None
        for attempt in range(max_attempts):
            try:
                return (prompt | self.llm | self.action_parser).invoke({})
            except Exception as e:
                last_err = e
                print(f"Action parse attempt {attempt + 1}/{max_attempts} failed: {e}")

        # Salvage: pull a JSON object out of the raw model text ourselves.
        try:
            raw = (prompt | self.llm).invoke({})
            text = getattr(raw, "content", None) or str(raw)
            if isinstance(text, list):  # some providers return content parts
                text = " ".join(str(p) for p in text)
            parsed = self._extract_json_object(text)
            if parsed is not None:
                print("Salvaged action from raw model output.")
                return parsed
        except Exception as e:
            print(f"Raw action salvage failed: {e}")

        print("Could not parse a valid action from the model; terminating this state gracefully.")
        return {
            "action": "terminate",
            "mmid": None,
            "params": {"reason": f"Unable to parse a valid action from model output ({last_err})."},
            "reasoning": "",
        }

    @staticmethod
    def _extract_json_object(text: str) -> Optional[dict]:
        """Best-effort extraction of an action JSON object from raw text."""
        if not text:
            return None
        # Prefer a fenced ```json { ... } ``` block if present.
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        candidate = fenced.group(1) if fenced else None
        if candidate is None:
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = text[start:end + 1]
        if candidate is None:
            return None
        try:
            obj = json.loads(candidate)
        except Exception:
            return None
        return obj if isinstance(obj, dict) and "action" in obj else None

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
