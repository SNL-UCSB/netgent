import asyncio
import os
from typing import Any, NotRequired

from browser_use import Agent, AgentHistoryList, Browser
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime
from playwright.async_api import Playwright, async_playwright
from pydantic import BaseModel, ConfigDict

from agents.model_factory import get_browser_use_model
from agents.subagents.browser.generate.evolution import (
    BrowserEvolution,
    build_evolutionary_prompt,
    coerce_evolution,
    update_evolution,
)
from agents.subagents.browser.generate.generate import gen_workflow
from agents.subagents.browser.util import (
    build_controller,
    open_browser_session,
    parse_agent_history,
    prune_agenthistorylist,
)

DEFAULT_MAX_STEPS = int(os.getenv("BROWSER_USE_MAX_STEPS", "30"))
EXCLUDED_BROWSER_USE_ACTIONS = [
    "close_tab",
    "search_google",
    "extract_structured_data",
    "read_sheet_contents",
    "read_cell_contents",
    "update_cell_contents",
    "clear_cell_contents",
    "select_cell_or_range",
    "fallback_input_into_single_selected_cell",
    "switch_tab",
    "upload_file",
]

BROWSER_USE_HEADLESS = True


class BrowserGenerateState(MessagesState):
    task: str
    history: NotRequired[list[AgentHistoryList]]
    steps: NotRequired[int]
    workflow: NotRequired[dict[str, Any] | None]
    result: NotRequired[dict[str, Any] | None]
    evolution: NotRequired[BrowserEvolution]
    parameters: NotRequired[dict[str, str]]


class BrowserGenerateContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    playwright: Playwright


def _build_task_with_parameters(task: str, parameters: dict[str, str]) -> str:
    if not parameters:
        return task
    lines = [
        task,
        "",
        "Available runtime parameter placeholders:",
    ]
    for name in parameters:
        lines.append(
            f"  - {name}: use <secret>{name}</secret> when an action needs this value"
        )
    lines.append(
        "Do not hardcode literal parameter values into actions when one of these placeholders applies."
    )
    return "\n".join(lines)


async def execute_task(
    state: BrowserGenerateState, runtime: Runtime[BrowserGenerateContext]
) -> dict[str, Any]:
    playwright = runtime.context.playwright
    parameters = state.get("parameters") or {}
    task = _build_task_with_parameters(state["task"], parameters)
    evolution = coerce_evolution(task, state.get("evolution"))
    history_list: list[AgentHistoryList] = []
    steps = max(1, state.get("steps", 1) or 1)
    for _ in range(steps):
        evolutionary_prompt = build_evolutionary_prompt(task, evolution)
        print("evolutionary_prompt", evolutionary_prompt)
        browser, browser_context, _ = await open_browser_session(playwright)

        try:
            # We don't give it the ability to Change Pages. It can only stay only on one page at a time.
            browser_agent = Agent(
                browser=Browser(
                    browser=browser,
                    browser_context=browser_context,
                    playwright=playwright,
                ),
                controller=build_controller(EXCLUDED_BROWSER_USE_ACTIONS),
                llm=get_browser_use_model(),
                task=evolutionary_prompt,
                sensitive_data=parameters or None,
                headless=BROWSER_USE_HEADLESS,
            )
            history = await browser_agent.run(max_steps=DEFAULT_MAX_STEPS)
            evolution = update_evolution(task, history, evolution)
            history_list.append(history)
        finally:
            await browser.close()
    return {"history": history_list, "evolution": evolution}


async def generate_workflow(state: BrowserGenerateState):
    # top_k = min(max(1, state.get("steps", 3) or 3), 3)
    pruned_history = prune_agenthistorylist(state.get("history", []), top_k=1)
    if not pruned_history or len(pruned_history) == 0:
        return {
            "result": {
                "success": False,
                "message": "Agent could not execute prompted task",
            }
        }
    parsed_history = parse_agent_history(pruned_history[0].model_dump())
    parameter_names = list((state.get("parameters") or {}).keys())
    workflow = gen_workflow(
        parsed_history,
        specification=state["task"],
        parameters=parameter_names,
    )
    print(workflow)
    return {
        "workflow": workflow,
        "result": {
            "success": True,
            "message": "Workflow Generated!",
        },
    }


def create_agent():
    graph = StateGraph(
        state_schema=BrowserGenerateState,
        context_schema=BrowserGenerateContext,
    )
    graph.add_node("execute_task", execute_task)
    graph.add_node("generate_workflow", generate_workflow)
    graph.add_edge(START, "execute_task")
    graph.add_edge("execute_task", "generate_workflow")
    graph.add_edge("generate_workflow", END)
    return graph.compile()
