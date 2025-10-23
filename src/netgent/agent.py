from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from seleniumbase import Driver
from netgent.components.program_controller.controller import ProgramController
from netgent.components.state_executor.executor import StateExecutor
from netgent.browser.session import BrowserSession
from netgent.browser.controller import PyAutoGUIController, BaseController
from typing import Any, Optional, TypedDict
from langchain_core.language_models.chat_models import BaseChatModel
from netgent.components.state_synthesis import StateSynthesis
import time
from netgent.components.web_agent import WebAgent
from utils.message import StatePrompt
load_dotenv()

class NetGentState(TypedDict):
    state_repository: Optional[list[dict[str, Any]]]
    state_prompts: list[StatePrompt]
    passed_states: Optional[list[dict[str, Any]]]
    recursion_count: Optional[int]
    last_passed_state_name: Optional[str]
    state_timeout_start: Optional[float]

    synthesis_prompt: Optional[str]
    synthesis_choice: Optional[StatePrompt]
    synthesis_triggers: Optional[list[str]]
    executed_states: Optional[list[dict[str, Any]]]

class NetGent():
    def __init__(self, driver: Driver = None, controller: BaseController = None, llm: BaseChatModel = None, config: Optional[dict] = None, llm_enabled: bool = True, user_data_dir: Optional[str] = None):
        self.llm = llm
        self.llm_enabled = llm_enabled
        self.driver = driver
        if self.driver is None:
            self.driver = BrowserSession(user_data_dir=user_data_dir).driver
        self.controller = controller
        if self.controller is None:
            self.controller = PyAutoGUIController(self.driver)

        
        default_config = {
            "action_period": 1,
            "transition_period": 3,
            "recursion_limit": 100,
            "allow_multiple_states": False,
            "state_timeout": 30,
        }
        self.config = {**default_config, **(config or {})}
        
        self.program_controller = ProgramController(self.controller, self.config)
        self.state_executor = StateExecutor(self.controller, self.config)
        self.web_agent = WebAgent(self.llm, self.controller)
        self.state_synthesis = StateSynthesis(self.llm, self.controller)
        self.workflow = StateGraph(NetGentState)
        self.graph = self.compile()
    
    def compile(self):
        self.workflow.add_node("program_controller", self._program_controller)
        self.workflow.add_node("state_executor", self._state_executor)
        self.workflow.add_node("state_synthesis", self._state_synthesis)
        self.workflow.add_node("web_agent", self._web_agent)
        self.workflow.add_edge(START, "program_controller")
        self.workflow.add_edge("state_synthesis", "web_agent")
        self.workflow.add_conditional_edges(
            "program_controller",
            self._route_after_controller
        )
        self.workflow.add_conditional_edges(
            "state_executor",
            self._continue_run
        )
        self.workflow.add_conditional_edges(
            "web_agent",
            self._check_web_agent_end_state
        )
        graph = self.workflow.compile()
        return graph

    def _check_web_agent_end_state(self, state: NetGentState):
        """Check if the web agent generated state has an end_state"""
        # Safety check: if LLM is disabled, this method shouldn't be called
        if not self.llm_enabled:
            print("LLM is disabled but web agent end state check was called - ending execution")
            return END
            
        synthesis_choice = state.get('synthesis_choice')
        
        # Check if synthesis choice has an end_state
        if synthesis_choice and synthesis_choice.end_state and synthesis_choice.end_state != "":
            print(f"Web agent generated state with end_state: {synthesis_choice.end_state}")
            return END
        
        # Otherwise continue to program_controller
        return "program_controller"

    def _route_after_controller(self, state: NetGentState):
        """Route after program_controller based on whether states were passed"""
        # Check recursion limit first
        recursion_count = state.get('recursion_count', 0)
        if recursion_count >= self.config["recursion_limit"]:
            print(f"Recursion limit of {self.config['recursion_limit']} reached")
            return END
        
        passed_states = state.get('passed_states', [])
        
        # If no states passed, check LLM flag before routing
        if len(passed_states) == 0:
            if self.llm_enabled:
                print("No states passed - routing to state synthesis agent")
                return "state_synthesis"
            else:
                print("No states passed and LLM disabled - ending execution")
                return END
        
        # If states passed, route to state executor
        return "state_executor"

    def _continue_run(self, state: NetGentState):
        """Determine next step after state_executor (only called when states exist)"""
        passed_states = state.get('passed_states', [])
        
        # Check if end state reached
        if passed_states[0].get('end_state') is not None and passed_states[0].get('end_state') != "":
            return END
        
        # Check state timeout for non-continuous states
        last_passed_state_name = state.get('last_passed_state_name')
        state_timeout_start = state.get('state_timeout_start')
        current_state = passed_states[0]
        
        if last_passed_state_name == current_state.get('name'):
            is_continuous = current_state.get('config', {}).get('continuous', False)
            if not is_continuous and self.config["state_timeout"]:
                if state_timeout_start is not None:
                    elapsed_time = time.time() - state_timeout_start
                    if elapsed_time > self.config["state_timeout"]:
                        print(f"State '{current_state.get('name')}' timeout of {self.config['state_timeout']} seconds exceeded")
                        return END
                    print(f"State '{current_state.get('name')}' repeated - timer running: {elapsed_time:.2f}s")
        
        return "program_controller"

    def _program_controller(self, state: NetGentState):
        # Wait transition period between checks
        time.sleep(self.config["transition_period"])
        
        passed_states = self.program_controller.check(state.get('state_repository'))
        
        # Update recursion count
        recursion_count = state.get('recursion_count', 0) + 1
        
        # Update timeout tracking
        last_passed_state_name = state.get('last_passed_state_name')
        state_timeout_start = state.get('state_timeout_start')
        
        if len(passed_states) == 0:
            # Reset state timeout when no states pass
            state_timeout_start = None
            last_passed_state_name = None
        else:
            # Track state timeout
            current_state_name = passed_states[0].get('name')
            if last_passed_state_name == current_state_name:
                is_continuous = passed_states[0].get('config', {}).get('continuous', False)
                if not is_continuous:
                    if state_timeout_start is None:
                        state_timeout_start = time.time()
                        print(f"Timer started for state '{current_state_name}' - will timeout after {self.config['state_timeout']} seconds")
            else:
                state_timeout_start = None
                last_passed_state_name = current_state_name
        
        return {
            **state,
            "passed_states": passed_states,
            "recursion_count": recursion_count,
            "last_passed_state_name": last_passed_state_name,
            "state_timeout_start": state_timeout_start,
        }
        
    def _state_executor(self, state: NetGentState):
        passed_states = state.get('passed_states', [])
        self.state_executor.run(passed_states[0])
        return {**state}

    def _state_synthesis(self, state: NetGentState):
        # Pass executed states to state synthesis for tracking
        state_synthesis_state = self.state_synthesis.run(
            state.get('state_prompts', []), 
            state.get('executed_states', [])
        )
        print(state_synthesis_state)
        return {**state,"synthesis_prompt": state_synthesis_state.get('prompt'), "synthesis_choice": state_synthesis_state.get('choice'), "synthesis_triggers": state_synthesis_state.get('triggers')}
    
    def _web_agent(self, state: NetGentState):
        synthesis_state = {"prompt": state.get('synthesis_prompt', '')}
        web_agent_state = self.web_agent.run(user_query="ONLY FOLLOW THE FOLLOWING INSTRUCTION(S):\n"
            + synthesis_state["prompt"]
            + "\nONCE YOU COMPLETE THE TASK, YOU TERMINATE INMEDIATLY. DO NOT DO ANYTHING ELSE NO MATTER THE RESULT OF THE TASK. THERE WILL BE OTHER STATES TO HANDLE THE RESULT OF THE TASK.")
        print(web_agent_state)
        
        # Extract actions from web agent output
        actions = web_agent_state.get('actions', [])
        synthesis_choice = state.get('synthesis_choice')
        synthesis_triggers = state.get('synthesis_triggers', [])
        
        # Create new state from synthesis and web agent output
        new_state = {
            "name": synthesis_choice.name if synthesis_choice else "generated_state",
            "description": synthesis_choice.description if synthesis_choice else "",
            "checks": synthesis_triggers,
            "actions": actions,
            "end_state": synthesis_choice.end_state if synthesis_choice else "",
            "executed": []
        }
        
        # Update state repository
        state_repository = state.get('state_repository', []).copy()
        
        # Find matching state in repository and update its executed field
        if synthesis_choice:
            for repo_state in state_repository:
                if repo_state.get('name') == synthesis_choice.name:
                    # Initialize executed field if not present
                    if "executed" not in repo_state:
                        repo_state["executed"] = []
                    # Add new state to the parent state's executed list
                    repo_state["executed"] = repo_state["executed"] + [new_state]
                    matching_state_found = True
                    break
        
        # Add new state to state repository
        updated_state_repository = state_repository + [new_state]
        
        # Track executed states for state synthesis
        executed_states = state.get('executed_states', [])
        updated_executed_states = executed_states + [new_state]
        
        return {
            **state,
            "state_repository": updated_state_repository,
            "executed_states": updated_executed_states,
            "messages": web_agent_state.get('messages')
        }

    def run(self, state_prompts: list[StatePrompt] = [], state_repository: list[dict[str, Any]] = []):
        for state_item in state_repository:
            if "executed" not in state_item:
                state_item["executed"] = []
        
        state: NetGentState = {
            "state_repository": state_repository,
            "state_prompts": state_prompts,
            "passed_states": [],
            "recursion_count": 0,
            "last_passed_state_name": None,
            "state_timeout_start": None,
            "synthesis_prompt": None,
            "synthesis_choice": None,
            "synthesis_triggers": None,
            "executed_states": [],
        }
        return self.graph.invoke(state, {"recursion_limit": 100000})
    

