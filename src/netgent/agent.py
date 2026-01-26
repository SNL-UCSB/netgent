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
from netgent.utils.message import StatePrompt
from netgent.errors import NetGentError, NetGentExecutionError
import json
from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation import using_metadata
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
import contextlib
load_dotenv()

# Setup tracing
tracer_provider = register(
    project_name="netgent-default",
    batch=True,
)
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
tracer = trace.get_tracer(__name__)



class NetGentState(TypedDict):
    state_repository: Optional[list[dict[str, Any]]]
    state_prompts: list[StatePrompt]
    passed_states: Optional[list[dict[str, Any]]]
    recursion_count: Optional[int]
    last_passed_state_name: Optional[str]
    consecutive_state_count: Optional[int]
    state_timeout_start: Optional[float]
    variables: Optional[dict[str, Any]]
    synthesis_prompt: Optional[str]
    synthesis_choice: Optional[dict[str, Any]]
    synthesis_triggers: Optional[list[str]]
    executed_states: Optional[list[dict[str, Any]]]
    metadata: Optional[dict[str, Any]]

class NetGent():
    def __init__(self, driver: Driver = None, controller: BaseController = None, llm: BaseChatModel = None, config: Optional[dict] = None, llm_enabled: bool = True, user_data_dir: Optional[str] = None, proxy: Optional[str] = None):
        
        self.llm = llm
        self.llm_enabled = llm_enabled
        self.driver = driver
        if self.driver is None:
            self.driver = BrowserSession(user_data_dir=user_data_dir, proxy=proxy).driver
        self.controller = controller
        if self.controller is None:
            self.controller = PyAutoGUIController(self.driver)

        
        default_config = {
            "action_period": 1,
            "transition_period": 3,
            "recursion_limit": 100,
            "allow_multiple_states": False,
            "state_timeout": 30,
            "max_consecutive_repeats": 3,
        }
        self.config = {**default_config, **(config or {})}
        
        self.program_controller = ProgramController(self.controller, self.config)
        self.state_executor = StateExecutor(self.controller, self.config)
        self.web_agent = WebAgent(self.llm, self.controller)
        self.state_synthesis = StateSynthesis(self.llm, self.controller)
        self.workflow = StateGraph(NetGentState)
        self.graph = self.compile()

    def set_action_wait_time(self, seconds: float):
        """
        Set the wait time between actions in seconds.
        
        Args:
            seconds (float): The time to wait between actions.
        """
        self.config["action_period"] = seconds
        if hasattr(self, "state_executor"):
            self.state_executor.config["action_period"] = seconds

    def set_state_wait_time(self, seconds: float):
        """
        Set the wait time between state checks (transition period) in seconds.
        
        Args:
            seconds (float): The time to wait between state checks.
        """
        self.config["transition_period"] = seconds
    
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
        if synthesis_choice and synthesis_choice.get('end_state') and synthesis_choice.get('end_state') != "":
            print(f"Web agent generated state with end_state: {synthesis_choice.get('end_state')}")
            return END
        
        # Otherwise continue to program_controller
        return "program_controller"

    def _route_after_controller(self, state: NetGentState):
        """Route after program_controller based on whether states were passed"""
        # Check recursion limit first
        recursion_count = state.get('recursion_count', 0)
        if recursion_count >= self.config["recursion_limit"]:
            print(f"Recursion limit of {self.config['recursion_limit']} reached")
            raise NetGentExecutionError("RecursionLimitExceeded", f"Recursion limit of {self.config['recursion_limit']} reached")
            
        # Check consecutive repeats limit
        consecutive_state_count = state.get('consecutive_state_count', 0)
        max_repeats = self.config.get("max_consecutive_repeats")
        if max_repeats and consecutive_state_count > max_repeats:
            print(f"Max consecutive repeats of {max_repeats} reached for state '{state.get('last_passed_state_name')}'")
            raise NetGentExecutionError("MaxConsecutiveRepeatsExceeded", f"Max consecutive repeats of {max_repeats} reached for state '{state.get('last_passed_state_name')}'")
        
        passed_states = state.get('passed_states', [])
        
        # If no states passed, check LLM flag before routing
        if len(passed_states) == 0:
            if self.llm_enabled:
                print("No states passed - routing to state synthesis agent")
                return "state_synthesis"
            else:
                print("No states passed and LLM disabled - ending execution")
                raise NetGentExecutionError("NoStatesPassed", "No states passed and LLM disabled")
        
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
                        raise NetGentExecutionError("StateTimeoutExceeded", f"State '{current_state.get('name')}' timeout of {self.config['state_timeout']} seconds exceeded")
                    print(f"State '{current_state.get('name')}' repeated - timer running: {elapsed_time:.2f}s")
        
        return "program_controller"

    def _program_controller(self, state: NetGentState):
        # Wait transition period between checks
        time.sleep(self.config["transition_period"])
        
        passed_states = self.program_controller.check(state.get('state_repository'))
        
        # Update recursion count
        recursion_count = state.get('recursion_count', 0) + 1
        
        # Update timeout tracking and consecutive count
        last_passed_state_name = state.get('last_passed_state_name')
        state_timeout_start = state.get('state_timeout_start')
        consecutive_state_count = state.get('consecutive_state_count', 0)
        
        if len(passed_states) == 0:
            # Reset state timeout when no states pass
            state_timeout_start = None
            last_passed_state_name = None
            consecutive_state_count = 0
        else:
            # Track state timeout
            current_state_name = passed_states[0].get('name')
            if last_passed_state_name == current_state_name:
                consecutive_state_count += 1
                is_continuous = passed_states[0].get('config', {}).get('continuous', False)
                if not is_continuous:
                    if state_timeout_start is None:
                        state_timeout_start = time.time()
                        print(f"Timer started for state '{current_state_name}' - will timeout after {self.config['state_timeout']} seconds")
            else:
                state_timeout_start = None
                last_passed_state_name = current_state_name
                consecutive_state_count = 1
        
        return {
            **state,
            "passed_states": passed_states,
            "recursion_count": recursion_count,
            "last_passed_state_name": last_passed_state_name,
            "state_timeout_start": state_timeout_start,
            "consecutive_state_count": consecutive_state_count,
        }
        
    def _state_executor(self, state: NetGentState):
        passed_states = state.get('passed_states', [])
        self.state_executor.run(passed_states[0], state.get('variables', {}))
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
            + "\nONCE YOU COMPLETE THE TASK, YOU TERMINATE INMEDIATLY. DO NOT DO ANYTHING ELSE NO MATTER THE RESULT OF THE TASK. THERE WILL BE OTHER STATES TO HANDLE THE RESULT OF THE TASK.", variables=state.get('variables', {}))
        print(web_agent_state)
        
        # Extract actions from web agent output
        actions = web_agent_state.get('actions', [])
        synthesis_choice = state.get('synthesis_choice')
        synthesis_triggers = state.get('synthesis_triggers', [])
        
        # Create new state from synthesis and web agent output
        new_state = {
            "name": synthesis_choice.get('name') if synthesis_choice else "generated_state",
            "description": synthesis_choice.get('description') if synthesis_choice else "",
            "checks": synthesis_triggers,
            "actions": actions,
            "end_state": synthesis_choice.get('end_state') if synthesis_choice else "",
            "executed": []
        }
        
        # Update state repository
        state_repository = state.get('state_repository', []).copy()
        
        # Find matching state in repository and update its executed field
        if synthesis_choice:
            for repo_state in state_repository:
                if repo_state.get('name') == synthesis_choice.get('name'):
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

    def run(self, state_prompts: list[StatePrompt] = [], state_repository: list[dict[str, Any]] = [], variables: dict[str, Any] = {}, end_state_files: str = "", session: Optional[str] = None):
        # Accept either a list of state dicts or a dict containing "state_repository"
        if isinstance(state_repository, dict):
            repo_list = state_repository.get("state_repository", [])
        elif isinstance(state_repository, list):
            repo_list = state_repository
        else:
            repo_list = []

        for state_item in repo_list:
            if isinstance(state_item, dict) and "executed" not in state_item:
                state_item["executed"] = []

        state: NetGentState = {
            "state_repository": repo_list,
            "state_prompts": state_prompts,
            "passed_states": [],
            "recursion_count": 0,
            "last_passed_state_name": None,
            "state_timeout_start": None,
            "synthesis_prompt": None,
            "synthesis_choice": None,
            "synthesis_triggers": None,
            "executed_states": [],
            "variables": variables,
        }
        
        with tracer.start_as_current_span("NetGent") as span:
            try:
                result = self.graph.invoke(state, config={"recursion_limit": 100000})
                
                metadata = {"session": session, "variables": variables}
                span.set_attribute("metadata", json.dumps(metadata))
                
                if end_state_files:
                    html = self.driver.page_source
                    with open(end_state_files, "w") as f:
                        f.write(html)
                
                print(f"DEBUG: Setting span status to OK for {span}")
                span.set_status(Status(StatusCode.OK))

                return result
            except NetGentExecutionError as e:
                span.set_status(Status(StatusCode.ERROR, description=e.message))
                span.record_exception(e)
                raise NetGentError(name=e.name, message=e.message) from e
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
                span.record_exception(e)
                raise e
