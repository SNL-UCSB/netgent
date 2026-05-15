from __future__ import annotations

from typing import Any

from agents.subagents.shell.prompts import (
    DECIDE_PROMPT,
    TASK_PROMPT,
    build_parameters_prompt,
)
from agents.subagents.shell.schema import (
    RunIPerf3Tool,
    RunNDT7Tool,
    RunPingTool,
    SendMessage,
)
from agents.subagents.shell.tool_nodes import (
    bad_tool_name,
    run_iperf3,
    run_ndt7,
    run_ping,
    send_message,
)

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency

    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False


from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, ConfigDict

from agents.model_factory import get_langchain_model
from engine.controller import ProgramController
from engine.executor import StateExecutor
from engine.runner import WorkflowRunner
from engine.schema import (
    WorkflowAction,
    WorkflowCheck,
    WorkflowSchema,
    WorkflowState,
)
from registry.actions.network import NETWORK_ACTIONS
from registry.triggers.base import always_true

load_dotenv()


class ShellRunAgentState(MessagesState):
    task: str
    workflow: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    parameters: dict[str, str] = {}


class ShellAgentContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    runner: WorkflowRunner


EXECUTION_TOOL_ROUTES = {
    "RunIPerf3Tool": "run_iperf3",
    "RunNDT7Tool": "run_ndt7",
    "RunPingTool": "run_ping",
}

TOOL_ROUTES = {
    **EXECUTION_TOOL_ROUTES,
    "SendMessage": "send_message",
}

WORKFLOW_ACTION_TYPES = {
    "RunIPerf3Tool": "iperf",
    "RunNDT7Tool": "ndt",
    "RunPingTool": "ping",
}


def add_task_message(state: ShellRunAgentState) -> dict[str, list]:
    for message in state["messages"]:
        if isinstance(message, (HumanMessage, AIMessage, ToolMessage)):
            return {}
    task = state["task"]
    parameters = state.get("parameters") or {}
    param_suffix = build_parameters_prompt(parameters)
    if param_suffix:
        task = f"{task}\n\n{param_suffix}"
    return {"messages": TASK_PROMPT.invoke({"task": task}).messages}


def route_run_workflow(state: ShellRunAgentState):
    if state.get("workflow"):
        return "run_workflow"
    return "decide"


async def decide(state: ShellRunAgentState) -> ShellRunAgentState:
    tools = [RunIPerf3Tool, RunNDT7Tool, RunPingTool, SendMessage]

    model = get_langchain_model()
    decision_model = model.bind_tools(tools)
    prompt_value = await DECIDE_PROMPT.ainvoke({"messages": state["messages"]})
    decision = await decision_model.ainvoke(prompt_value.messages)
    return {"messages": [decision]}


def route_decision(state: ShellRunAgentState) -> str:
    tool_calls = state["messages"][-1].tool_calls
    if not tool_calls:
        return "generate_workflow"

    tool_call = tool_calls[0]
    tool_name = tool_call["name"]
    if tool_name == "SendMessage":
        return "send_message"
    return TOOL_ROUTES.get(tool_name, "bad_tool_name")


def extract_tool_runs(messages: list[Any]) -> list[dict[str, Any]]:
    tool_responses: dict[str, ToolMessage] = {}
    for message in messages:
        if isinstance(message, ToolMessage):
            tool_responses[message.tool_call_id] = message

    tool_runs: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, AIMessage):
            continue

        for tool_call in message.tool_calls:
            tool_name = tool_call["name"]
            if tool_name not in EXECUTION_TOOL_ROUTES:
                continue

            tool_runs.append(
                {
                    "tool_name": tool_name,
                    "node_name": EXECUTION_TOOL_ROUTES[tool_name],
                    "tool_call": tool_call,
                    "tool_message": tool_responses.get(tool_call["id"]),
                }
            )

    return tool_runs


def workflow_conversion(tool_run: dict[str, Any]) -> WorkflowAction:
    tool_call = tool_run["tool_call"]
    tool_name = tool_call["name"]
    tool_args = tool_call.get("args", {})
    if not isinstance(tool_args, dict):
        raise ValueError(f"Tool call args must be a dictionary for '{tool_name}'")

    action_type = WORKFLOW_ACTION_TYPES[tool_name]
    params = {
        key: value
        for key, value in tool_args.items()
        if key != "reasoning" and value is not None
    }
    return WorkflowAction(type=action_type, params=params)


def generate_workflow(state: ShellRunAgentState) -> dict[str, Any]:
    tool_runs = extract_tool_runs(state["messages"])
    parameters = state.get("parameters") or {}
    actions = [workflow_conversion(tool_run) for tool_run in tool_runs]

    # Replace literal parameter values with {{placeholder}} in action params
    if parameters:
        value_to_key = {v: k for k, v in parameters.items()}
        for action in actions:
            for param_name, param_value in list(action.params.items()):
                if isinstance(param_value, str) and param_value in value_to_key:
                    action.params[param_name] = "{{" + value_to_key[param_value] + "}}"
                elif isinstance(param_value, (int, float)):
                    str_value = str(param_value)
                    if str_value in value_to_key:
                        action.params[param_name] = (
                            "{{" + value_to_key[str_value] + "}}"
                        )

    workflow = WorkflowSchema(
        specification=state["task"],
        states=[
            WorkflowState(
                checks=[WorkflowCheck(type="always_true")],
                actions=actions,
                end_state="Workflow Completed",
            )
        ],
        parameters=list(parameters.keys()),
    )
    return {
        "workflow": workflow.model_dump(mode="json"),
    }


async def run_workflow(
    state: ShellRunAgentState, runtime: Runtime[ShellAgentContext]
) -> dict[str, Any]:
    workflow = state.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError("Workflow must be generated before running it")

    try:
        return {
            "result": {
                "success": True,
                "output": await runtime.context.runner.run(workflow),
            }
        }
    except Exception as exc:
        return {
            "result": {
                "success": False,
                "error": str(exc),
            }
        }


def create_agent():
    graph = StateGraph(
        state_schema=ShellRunAgentState, context_schema=ShellAgentContext
    )
    graph.add_node("add_task_message", add_task_message)
    graph.add_node("decide", decide)
    graph.add_node("run_iperf3", run_iperf3)
    graph.add_node("run_ndt7", run_ndt7)
    graph.add_node("run_ping", run_ping)
    graph.add_node("send_message", send_message)
    graph.add_node("bad_tool_name", bad_tool_name)
    graph.add_node("generate_workflow", generate_workflow)
    graph.add_node("run_workflow", run_workflow)
    graph.add_edge(START, "add_task_message")
    graph.add_conditional_edges(
        "add_task_message",
        route_run_workflow,
        {
            "run_workflow": "run_workflow",
            "decide": "decide",
        },
    )
    graph.add_conditional_edges(
        "decide",
        route_decision,
        {
            "run_iperf3": "run_iperf3",
            "run_ndt7": "run_ndt7",
            "run_ping": "run_ping",
            "send_message": "send_message",
            "bad_tool_name": "bad_tool_name",
            "generate_workflow": "generate_workflow",
        },
    )
    graph.add_edge("run_iperf3", "decide")
    graph.add_edge("run_ndt7", "decide")
    graph.add_edge("run_ping", "decide")
    graph.add_edge("send_message", "generate_workflow")
    graph.add_edge("bad_tool_name", "decide")
    graph.add_edge("generate_workflow", "run_workflow")
    graph.add_edge("run_workflow", END)

    return graph.compile()


async def main():
    task = (
        "Run all three tools one by one in a single workflow. "
        "First run ping against google.com. "
        "Second run iperf3 against host speedtest.sfo12.us.leaseweb.net on port 5201. "
        "Third run ndt7 with default settings. "
        "After all three tool calls complete, summarize the results."
    )

    workflow = {
        "specification": "Run all three tools one by one in a single workflow. First run ping against google.com. Second run iperf3 against host speedtest.sfo12.us.leaseweb.net on port 5201. Third run ndt7 with default settings. After all three tool calls complete, summarize the results.",
        "states": [
            {
                "checks": [{"type": "always_true", "params": {}}],
                "actions": [
                    {"type": "ping", "params": {"host": "google.com"}},
                    {
                        "type": "iperf",
                        "params": {
                            "host": "speedtest.sfo12.us.leaseweb.net",
                            "port": 5201,
                        },
                    },
                    {"type": "ndt", "params": {}},
                ],
                "end_state": "Workflow Completed",
            }
        ],
    }

    agent = create_agent()
    runner = WorkflowRunner(
        controller=ProgramController(triggers=(always_true,)),
        executor=StateExecutor(actions=NETWORK_ACTIONS),
        config={},
    )
    result = await agent.ainvoke(
        {"task": task, "messages": [], "workflow": workflow},
        context={"runner": runner},
    )
    print(result)
