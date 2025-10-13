from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from seleniumbase import Driver
from netgent.components.program_controller.controller import ProgramController
from netgent.components.state_executor.executor import StateExecutor
from netgent.browser.session import BrowserSession
from netgent.browser.controller import PyAutoGUIController, BaseController
from typing import Any, Optional, TypedDict
import time
load_dotenv()

class NetGentState(TypedDict):
    state_repository: Optional[list[dict[str, Any]]]
    passed_states: Optional[list[dict[str, Any]]]
    recursion_count: Optional[int]
    last_passed_state_name: Optional[str]
    state_timeout_start: Optional[float]
    no_states_timeout_start: Optional[float]

class NetGent():
    def __init__(self, driver: Driver = None, controller: BaseController = None, config: Optional[dict] = None):
        self.driver = driver
        if self.driver is None:
            self.driver = BrowserSession().driver
        self.controller = controller
        if self.controller is None:
            self.controller = PyAutoGUIController(self.driver)
        
        default_config = {
            "action_period": 1,
            "transition_period": 3,
            "recursion_limit": 10,
            "allow_multiple_states": False,
            "state_timeout": 30,
            "no_states_timeout": 60,
        }
        self.config = {**default_config, **(config or {})}
        
        self.program_controller = ProgramController(self.controller, self.config)
        self.state_executor = StateExecutor(self.controller, self.config)
        self.workflow = StateGraph(NetGentState)
        self.graph = self.compile()
    
    def compile(self):
        self.workflow.add_node("program_controller", self._program_controller)
        self.workflow.add_node("state_executor", self._state_executor)
        self.workflow.add_edge(START, "program_controller")
        self.workflow.add_edge("program_controller", "state_executor")
        self.workflow.add_conditional_edges(
            "state_executor",
            self._continue_run
        )
        graph = self.workflow.compile()
        return graph

    def _continue_run(self, state: NetGentState):
        # Check recursion limit
        recursion_count = state.get('recursion_count', 0)
        if recursion_count >= self.config["recursion_limit"]:
            print(f"Recursion limit of {self.config['recursion_limit']} reached")
            return END
        
        passed_states = state.get('passed_states', [])
        
        # Check if no states passed
        if len(passed_states) == 0:
            no_states_timeout_start = state.get('no_states_timeout_start')
            if self.config["no_states_timeout"]:
                if no_states_timeout_start is None:
                    # First time no states passed, continue to track
                    return "program_controller"
                else:
                    elapsed_time = time.time() - no_states_timeout_start
                    if elapsed_time > self.config["no_states_timeout"]:
                        print(f"No states passed timeout of {self.config['no_states_timeout']} seconds exceeded")
                        return END
                    print(f"No states passed - timer running: {elapsed_time:.2f}s")
                    return "program_controller"
            return END
        
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
        no_states_timeout_start = state.get('no_states_timeout_start')
        
        if len(passed_states) == 0:
            # Track no states timeout
            if no_states_timeout_start is None and self.config["no_states_timeout"]:
                no_states_timeout_start = time.time()
                print(f"No states passed - starting no states timeout timer: {self.config['no_states_timeout']} seconds")
            # Reset state timeout
            state_timeout_start = None
            last_passed_state_name = None
        else:
            # Reset no states timeout
            no_states_timeout_start = None
            
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
            "no_states_timeout_start": no_states_timeout_start,
        }
        
    def _state_executor(self, state: NetGentState):
        passed_states = state.get('passed_states', [])
        for passed_state in passed_states:
            self.state_executor.run(passed_state)
        return {**state}

    def run(self, state_repository: list[dict[str, Any]]):
        state: NetGentState = {
            "state_repository": state_repository,
            "passed_states": [],
            "recursion_count": 0,
            "last_passed_state_name": None,
            "state_timeout_start": None,
            "no_states_timeout_start": None,
        }
        return self.graph.invoke(state)
    

