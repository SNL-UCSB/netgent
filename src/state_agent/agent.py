from state_agent.actions.state_executor import StateExecutor
from state_agent.actions.browser_manager import BrowserManager
from langgraph.graph import StateGraph, START, END
from pydantic import Field
from typing import TypedDict, Optional
from state_agent.state_agent.browser_agent.agent import BrowserAgent
from state_agent.state_agent.judge_agent.agent import JudgeAgent
from dotenv import load_dotenv
from .message import StatePrompt, Code, Message
from langchain_core.language_models.chat_models import BaseChatModel
load_dotenv()


class StateAgentState(TypedDict):
    prompt: list[StatePrompt] = Field(description="Prompt of the State the User Wants to Implement")
    states: list[dict] = Field(description="Current States")
    parameters: dict = Field(description="Parameters of the State")
    use_llm: bool = Field(description="Whether to use the LLM to execute the state")

    # Executed State
    executed: list[dict] = Field(description="States Executed")
    success: bool = Field(description="Whether the State was Successful")
    error: Optional[str] = Field(description="Error Message of the Error State (Used for LLM Debugging)")
    message: Optional[str] = Field(description="Message of the State")

# State Agent Initialization
class StateAgent:
    def __init__(self, judge_llm: BaseChatModel, browser_llm: BaseChatModel, browser_manager: BrowserManager, config: dict = {"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 10, "action_period": 2}):
        self.graph = self._initalize_workflow()
        self.judge_agent = JudgeAgent(judge_llm, browser_manager)
        self.browser_agent = BrowserAgent(browser_llm, browser_manager)
        self.browser_manager = browser_manager
        self.executor = StateExecutor(self.browser_manager)

        # Config for the State Machine
        self.config = config
        
    def run(self, prompt: list[StatePrompt], states: list[dict] = [], parameters: dict = {}, use_llm: bool = False):
        state = StateAgentState(prompt=prompt, states=states, parameters=parameters, use_llm=use_llm, executed=[], success=False, error=None, message=None)
        result = self.graph.invoke(state, {"recursion_limit": 100})
        self.browser_manager.close_browser()
        return result
    
    def _execute(self, state: StateAgentState):
        result = self.executor.execute(state["states"], parameters=state["parameters"], config=self.config)

        return { **state,
            "executed": state["executed"] + result["executed"],
            "success": result["success"],
            "error": result["error"],
            "message": result["message"]
        }
    
    def _continue(self, state: StateAgentState):
        # If the State is Successful or the LLM is not used, End the State
        if not state["use_llm"] or state["success"]:
            return END
        if state["error"] is not None and state["error"].get("message", "") == "No states provided" or "No states have been passed" in state["error"].get("message", ""):
            print("No states provided, generating new state")
            return "generate_state"

        # If the State has an Error, End the State
        if state["error"] is not None:
            print(state["error"])
            return END
        # If the current state has an end_state, End the State
        if state["states"] and state["states"][0].get("end_state") and state["states"][0]["end_state"].strip() != "":
            print("State has end_state, terminating")
            return END
        # If the State is not Successful and the LLM is used, Generate a New State
        print("Generating New State")
        return "generate_state"
    
    def _generate_actions(self, messages: list[Message]):
        actions = []
        for message in messages:
            if isinstance(message, Code) and message.name != "terminate":
                actions.append(message.to_code())
        return actions

    
    def _generate_state(self, state: StateAgentState):
        # Run Judging Agent
        judge_state = self.judge_agent.run(prompts=state["prompt"], executed=state["executed"], parameters=state["parameters"])
        
        # Run Browser Agent
        browser_state = self.browser_agent.run("ONLY FOLLOW THE FOLLOWING INSTRUCTION(S):" + "\n" + judge_state["prompt"] + "\n" + "ONCE YOU COMPLETE THE TASK, YOU TERMINATE INMEDIATLY. DO NOT DO ANYTHING ELSE NO MATTER THE RESULT OF THE TASK. THERE WILL BE OTHER STATES TO HANDLE THE RESULT OF THE TASK.", messages=[], parameters=state["parameters"])
        # Extract only Code objects from messages
        code_messages = self._generate_actions(browser_state["messages"])

        new_state = {
            "name": judge_state["choice"].name,
            "description": judge_state["choice"].description,
            "checks": judge_state["triggers"],
            "actions": code_messages,
            "end_state": judge_state["choice"].end_state
        }

        # Add the New State to the States List
        state["states"] = [new_state] + state["states"]
        state["executed"] += [new_state]

        # If the State is an End State, Set the State to Successful
        if state["states"][0].get("end_state") and state["states"][0]["end_state"].strip() != "":
            state["success"] = True
            state["message"] = judge_state["choice"].end_state
            state["error"] = None

        return state
    
    def _end_state(self, state: StateAgentState):
        if state["states"][0].get("end_state") and state["states"][0]["end_state"].strip() != "":
            return END
        return "execute"
    
    
    
    def _initalize_workflow(self):
        workflow = StateGraph(StateAgentState)
        workflow.add_node("execute", self._execute)
        workflow.add_node("generate_state", self._generate_state)
        workflow.add_edge(START, "execute")
        workflow.add_conditional_edges("execute", self._continue)
        workflow.add_conditional_edges("generate_state", self._end_state)
        return workflow.compile()
    


