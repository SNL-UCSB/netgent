from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from typing import List, TypedDict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from netgent.browser.controller.base import BaseController
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
    def __init__(self, llm: BaseChatModel, controller: BaseController, domain: str = "web"):
        self.llm = llm
        self.controller = controller
        self.domain = domain
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
        context = self.controller.get_context()

        # On desktop, get_context() falls back to the *frontmost* app when the
        # target app isn't running yet (so the agent can still see the screen
        # to open it) -- but that fallback is misleading here: it can make an
        # unrelated frontmost app (e.g. the terminal) look like "the current
        # app", causing the LLM to skip the "open the app" state entirely. Ask
        # the ground-truth "is it running" question directly and state it
        # plainly so the state choice can't be fooled by whatever happens to
        # be frontmost.
        app_status_line = ""
        target_app = getattr(self.controller, "target_app", None)
        if self.domain == "desktop" and target_app:
            try:
                running = self.controller.check_app(name=target_app)
            except Exception:
                running = None
            if running is not None:
                app_status_line = f"Target application '{target_app}' is currently running: {running}\n    "

        messages = [
            SystemMessage(content=get_prompt("CHOOSE_STATE_PROMPT", self.domain).format(
                STATES='\n'.join(str(prompt) for prompt in state['prompts']) + '\n'
            )),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": f"""
    ## History of Action
    {self._prompt_execution(state.get('executed', [])) if state.get('executed') else 'No History of Actions'}
    ## Current Application State
    {app_status_line}Context: {context.get('url', '')}
    Title: {context.get('title', '')}
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
        # Define the Trigger for the State.
        # The controller supplies the concrete candidate triggers for its domain
        # (URL/text/CSS for browsers; app/window/text/AX-element for desktop).
        available_trigger_types = list(self.trigger_registry.get_all_triggers().keys())
        print("AVAILABLE_TRIGGER_TYPES: ", available_trigger_types)

        triggers_dict = self.controller.build_trigger_candidates()

        # Format Triggers for Prompt
        formatted_triggers = []
        for key, trigger in triggers_dict.items():
            params_str = ", ".join(f"{k}={v}" for k, v in trigger['params'].items())
            formatted_triggers.append(f"{key} <{trigger['type']}/>: {params_str}")
        
        # Prompt the LLM with the Available Triggers
        triggers_prompt = "\n".join(formatted_triggers)
        print("TRIGGERS_PROMPT: ", triggers_prompt)
        messages = [
            SystemMessage(content=get_prompt("DEFINE_TRIGGER_PROMPT", self.domain).format(
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
        context = self.controller.get_context()
        # Append TERMINATE as a properly numbered final instruction (not a bare
        # trailing line) so the planning LLM can't mistake it for a competing
        # directive that overrides/replaces the preceding action(s) -- that
        # ambiguity previously caused single-action states (e.g. just "open the
        # app") to be planned as an immediate termination, skipping the action.
        numbered_instructions = list(state['choice'].actions) + ["TERMINATE"]
        instruction_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(numbered_instructions))
        messages = [
            SystemMessage(content=get_prompt("PROMPT_ACTION_PROMPT", self.domain)),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": f"""## User Instruction
    {instruction_text}
    ## History of Action
    {self._prompt_execution(state.get('executed', [])) if state.get('executed') else 'No History of Actions'}
    ## Current Application State
    Context: {context.get('url', '')}
    Title: {context.get('title', '')}
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



