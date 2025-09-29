from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from ..message import StatePrompt, Message
from pydantic import BaseModel
from state_agent.state_agent.judge_agent.prompt import CHOSE_STATE_PROMPT, DEFINE_TRIGGER_PROMPT, PROMPT_ACTION_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage
from typing import List, TypedDict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from state_agent.actions.browser_manager import BrowserManager
import re
load_dotenv()

class JudgeAgentState(TypedDict):
    executed: list[dict[str, Any]] # History of Action
    prompts: list[StatePrompt] # Available States
    choice: StatePrompt | None # State Choice
    triggers: list[str] # Triggers
    parameters: dict[str, Any] # Parameters
    prompt: Optional[str] # Generated prompt for browser agent

class JudgeAgent():
    def __init__(self, llm: BaseChatModel, browser_manager: BrowserManager):
        self.llm = llm
        self.workflow = self._initalize_workflow()
        self.graph = self.workflow.compile()
        
        self.browser_manager = browser_manager


    def run(self, prompts: list[StatePrompt], executed: list[dict[str, Any]], parameters: dict[str, Any] = {}):
        state = JudgeAgentState(prompts=prompts, choice=None, executed=executed, triggers=[], parameters=parameters)
        state = self.graph.invoke(state, { "recursion_limit": 100})
        return state
    
    def _prompt_execution(self, executed: list[dict[str, Any]]):
        prompt = []
        for i, execute in enumerate(executed):
            prompt.append(f"Step {i+1} - {execute['name']}: {execute['description']}")
        return "\n".join(prompt)
    
    def _select_state(self, state: JudgeAgentState):
        # _, _, self.screenshot = self.browser_manager.mark_page.with_retry().invoke(None)

        # Define the Messages for the LLM
        """
        Include the History of Action, Current Website State, and the Available States
        """
        messages = [
            SystemMessage(content=CHOSE_STATE_PROMPT.format(
                STATES='\n'.join(str(prompt) for prompt in state['prompts']) + '\n'
            )),
            HumanMessage(content=[
                {
                    "type": "text", 
                    "text": f"""
    ## History of Action
    {self._prompt_execution(state.get('executed', [])) if state.get('executed') else 'No History of Actions'}
    ## Current Website State
    URL: {self.browser_manager.driver.current_url}
    Title: {self.browser_manager.driver.title}
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
    
    def _define_trigger(self, state: JudgeAgentState):
        # Define the Trigger for the State
        triggers = self.browser_manager.find_trigger()
        
        triggers_dict = {}
        # Add URL as Trigger 0
        triggers_dict["URL"] = {
            "type": "url",
            "value": self.browser_manager.driver.current_url
        }
        # Process other Triggers Starting from Index 1
        for i, trigger in enumerate(triggers):
            if trigger.get("text", "") != "":
                triggers_dict[f"TEXT_{i}"] = {
                    "type": "text",
                    "value": trigger.get("text", "")
                }
            if trigger.get("enhancedCssSelector", "") != "":
                triggers_dict[f"CSS_{i}"] = {
                    "type": "element",
                    "value": trigger.get("enhancedCssSelector", "")
                }

        # Format Triggers for Prompt
        formatted_triggers = []
        for key, trigger in triggers_dict.items():
            formatted_triggers.append(f"{key} <{trigger['type']}/>: {trigger['value']}")
        
        # Prompt the LLM with the Available Triggers
        triggers_prompt = "\n".join(formatted_triggers)
        messages = [
            SystemMessage(content=DEFINE_TRIGGER_PROMPT.format(
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
    
    def _prompt_action(self, state: JudgeAgentState):
        messages = [
            SystemMessage(content=PROMPT_ACTION_PROMPT),
            HumanMessage(content=[
                {
                    "type": "text", 
                    "text": f"""## User Instruction
    {chr(10).join(f"{i+1}. {action}" for i, action in enumerate(state['choice'].actions)) + chr(10) + "TERMINATE ACTION"}
    ## History of Action
    {self._prompt_execution(state.get('executed', [])) if state.get('executed') else 'No History of Actions'}
    ## Current Website State
    URL: {self.browser_manager.driver.current_url}
    Title: {self.browser_manager.driver.title}
    ## Parameters
    {chr(10).join(f"- {key}: %{key}%" for key in state.get('parameters', {}).keys()) if state.get('parameters') else 'No Parameters'}
    """
                },
            ])
        ]

        response = self.llm.invoke(messages)        
        return { **state, "prompt": response.content }
    
    def _initalize_workflow(self):
        workflow = StateGraph(JudgeAgentState)
        workflow.add_node("select_state", self._select_state)
        workflow.add_node("define_trigger", self._define_trigger)
        workflow.add_node("prompt_action", self._prompt_action)
        workflow.add_edge(START, "select_state")
        workflow.add_edge("select_state", "define_trigger")
        workflow.add_edge("define_trigger", "prompt_action")
        workflow.add_edge("prompt_action", END)
        return workflow



