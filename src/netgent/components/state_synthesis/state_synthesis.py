from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from typing import List, TypedDict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from netgent.browser.controller.base import BaseController
from netgent.browser.utils import find_trigger
from netgent.browser.registry import TriggerRegistry
from netgent.utils.message import StatePrompt
from .prompt import get_prompt
import re
load_dotenv()

class StateSynthesisState(TypedDict):
    executed: list[dict[str, Any]] # History of Action
    prompts: list[StatePrompt] # Available States
    choice: StatePrompt | None # State Choice
    triggers: list[str] # Triggers
    prompt: Optional[str] # Generated prompt for browser agent

class StateSynthesis():
    def __init__(self, llm: BaseChatModel, controller: BaseController):
        self.llm = llm
        self.controller = controller
        self.trigger_registry = TriggerRegistry(controller)
        self.workflow = self._initalize_workflow()
        self.graph = self.workflow.compile()


    def run(self, prompts: list[StatePrompt], executed: list[dict[str, Any]]):
        state = StateSynthesisState(prompts=prompts, choice=None, executed=executed, triggers=[])
        state = self.graph.invoke(state, { "recursion_limit": 100})
        return state
    
    def _prompt_execution(self, executed: list[dict[str, Any]]):
        prompt = []
        for i, execute in enumerate(executed):
            prompt.append(f"Step {i+1} - {execute['name']}: {execute['description']}")
        return "\n".join(prompt)
    
    def _select_state(self, state: StateSynthesisState):
        # Define the Messages for the LLM
        """
        Include the History of Action, Current Website State, and the Available States
        """
        messages = [
            SystemMessage(content=get_prompt("CHOOSE_STATE_PROMPT").format(
                STATES='\n'.join(str(prompt) for prompt in state['prompts']) + '\n'
            )),
            HumanMessage(content=[
                {
                    "type": "text", 
                    "text": f"""
    ## History of Action
    {self._prompt_execution(state.get('executed', [])) if state.get('executed') else 'No History of Actions'}
    ## Current Website State
    URL: {self.controller.driver.current_url}
    Title: {self.controller.driver.title}
    """
                }
            ])
        ]
        
        # Selecting the State to Run
        response = self.llm.invoke(messages)
        
        # Finding the State Prompt
        # Use Regex to Find "State:"
        state_match = re.search(r'State:\s*(.+)', response.content, re.IGNORECASE)
        state_name = state_match.group(1).strip() if state_match else None
        
        # Fallback: Find First Matching State Name in Response Content
        if not state_name:
            for prompt in state["prompts"]:
                if prompt.name in response.content:
                    state_name = prompt.name
                    break
        
        # Selected Prompt
        choice = next(
            (prompt for prompt in state["prompts"] if prompt.name == state_name),
            None
        )

        print("CHOICE: ", choice)

        # Return the Selected Prompt
        return { **state, "choice": choice }
    
    def _define_trigger(self, state: StateSynthesisState):
        # Define the Trigger for the State
        # Get available triggers from the page
        page_triggers = find_trigger(self.controller.driver)
        
        # Get all available trigger types from the registry
        available_trigger_types = list(self.trigger_registry.get_all_triggers().keys())
        print("AVAILABLE_TRIGGER_TYPES: ", available_trigger_types)
        
        #--- TODO: Current Hardcoded Triggers But Should be Dynamic (We Will Be Changed in the Future) ---#
        triggers_dict = {}
        # Add URL as Trigger 0
        triggers_dict["URL"] = {
            "type": "url",
            "params": {"url": self.controller.driver.current_url}
        }
        # Process other Triggers Starting from Index 1
        for i, trigger in enumerate(page_triggers):
            if trigger.get("text", "") != "":
                triggers_dict[f"TEXT_{i}"] = {
                    "type": "text",
                    "params": {"text": trigger.get("text", "")}
                }
            if trigger.get("enhancedCssSelector", "") != "":
                triggers_dict[f"CSS_{i}"] = {
                    "type": "element",
                    "params": {
                        "by": "css selector",
                        "selector": trigger.get("enhancedCssSelector", "")
                    }
                }
        #--- Current Hardcoded Triggers But Should be Dynamic (We Will Be Changed in the Future) ---#

        # Format Triggers for Prompt
        formatted_triggers = []
        for key, trigger in triggers_dict.items():
            params_str = ", ".join(f"{k}={v}" for k, v in trigger['params'].items())
            formatted_triggers.append(f"{key} <{trigger['type']}/>: {params_str}")
        
        # Prompt the LLM with the Available Triggers
        triggers_prompt = "\n".join(formatted_triggers)
        print("TRIGGERS_PROMPT: ", triggers_prompt)
        messages = [
            SystemMessage(content=get_prompt("DEFINE_TRIGGER_PROMPT").format(
                AVAILABLE_TRIGGERS=triggers_prompt
            )),
            HumanMessage(content=[
                {
                    "type": "text", 
                    "text": f"""## State Triggers
    {chr(10).join(f"- {trigger}" for trigger in state['choice'].triggers)}
                    """
                },
            ])
        ]

        # Return the Triggers
        class LLMTriggerOutput(BaseModel):
            triggers: List[str]
        response = self.llm.with_structured_output(LLMTriggerOutput).invoke(messages)
        triggers = [triggers_dict[key] for key in response.triggers if key in triggers_dict]

        print("TRIGGERS: ", triggers)

        return { **state, "triggers": triggers }
    
    def _prompt_action(self, state: StateSynthesisState):
        messages = [
            SystemMessage(content=get_prompt("PROMPT_ACTION_PROMPT")),
            HumanMessage(content=[
                {
                    "type": "text", 
                    "text": f"""## User Instruction
    {chr(10).join(f"{i+1}. {action}" for i, action in enumerate(state['choice'].actions)) + chr(10) + "TERMINATE ACTION"}
    ## History of Action
    {self._prompt_execution(state.get('executed', [])) if state.get('executed') else 'No History of Actions'}
    ## Current Website State
    URL: {self.controller.driver.current_url}
    Title: {self.controller.driver.title}
    """
                },
            ])
        ]

        response = self.llm.invoke(messages)        
        return { **state, "prompt": response.content }
    
    def _initalize_workflow(self):
        workflow = StateGraph(StateSynthesisState)
        workflow.add_node("select_state", self._select_state)
        workflow.add_node("define_trigger", self._define_trigger)
        workflow.add_node("prompt_action", self._prompt_action)
        workflow.add_edge(START, "select_state")
        workflow.add_edge("select_state", "define_trigger")
        workflow.add_edge("define_trigger", "prompt_action")
        workflow.add_edge("prompt_action", END)
        return workflow



