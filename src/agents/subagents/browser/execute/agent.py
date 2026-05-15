import asyncio
import json
import os
from typing import Any, NotRequired

from browser_use import Agent, Browser
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime
from playwright.async_api import (
    Browser as PlaywrightBrowser,
)
from playwright.async_api import (
    BrowserContext as PlaywrightBrowserContext,
)
from playwright.async_api import (
    Page,
    Playwright,
)
from pydantic import BaseModel, ConfigDict

from agents.model_factory import get_browser_use_model
from agents.subagents.browser.generate.generate import gen_workflow
from agents.subagents.browser.util import (
    build_controller,
    parse_agent_history,
)
from engine.runner import WorkflowRunner

DEFAULT_MAX_STEPS = int(os.getenv("BROWSER_USE_MAX_STEPS", "30"))
DEFAULT_MAX_REPAIR_ATTEMPTS = int(os.getenv("BROWSER_USE_MAX_REPAIR_ATTEMPTS", "2"))
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


class BrowserExecuteState(MessagesState):
    task: str
    debug: NotRequired[bool]
    error: NotRequired[str]
    failed_action: NotRequired[dict[str, Any] | None]
    completed_actions: NotRequired[list[dict[str, Any]]]
    remaining_actions: NotRequired[list[dict[str, Any]]]
    result: NotRequired[dict[str, Any] | None]
    workflow: NotRequired[dict[str, Any] | None]


class BrowserExecuteContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    playwright: Playwright
    browser: PlaywrightBrowser
    browser_context: PlaywrightBrowserContext
    page: Page
    runner: WorkflowRunner


class WorkflowExecutionError(Exception):
    def __init__(
        self,
        *,
        state: dict[str, Any],
        action: dict[str, Any],
        action_index: int,
        completed_results: list[Any],
        original_error: Exception,
    ) -> None:
        super().__init__(str(original_error))
        self.state = state
        self.action = action
        self.action_index = action_index
        self.completed_results = completed_results
        self.original_error = original_error


def route_workflow(state: BrowserExecuteState, runtime: Runtime[BrowserExecuteContext]):
    runner = runtime.context.runner
    workflow = state.get("workflow")
    if isinstance(workflow, dict) and runner.validate(workflow):
        return "execute_workflow"
    state["result"] = {
        "result": {
            "success": False,
            "message": "Workflow validation failed",
        }
    }
    return END


def _patched_workflow_actions(patched_workflow: dict[str, Any]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for patched_state in patched_workflow.get("states") or []:
        if not isinstance(patched_state, dict):
            continue
        for action in patched_state.get("actions") or []:
            if isinstance(action, dict):
                merged.append(action)
    return merged


def _build_final_workflow(
    original_workflow: dict[str, Any],
    completed_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a copy of the original workflow whose first state holds the
    flat list of actions that were actually executed (pre-failure originals
    plus any patched continuation). All other top-level metadata — spec,
    parameters, extra states — is preserved from the original workflow."""
    original_states = original_workflow.get("states") or []
    if not original_states:
        return {**original_workflow, "states": original_states}

    merged_first_state = {
        **original_states[0],
        "actions": list(completed_actions),
        "executed": [],
    }
    return {
        **original_workflow,
        "states": [merged_first_state, *original_states[1:]],
    }


async def execute_workflow(state: BrowserExecuteState, runtime: Runtime[BrowserExecuteContext]):
    runner = runtime.context.runner
    workflow = state.get("workflow")
    if not isinstance(workflow, dict):
        return {
            "result": {
                "success": False,
                "message": "Workflow validation failed",
            }
        }

    result: list[Any] = []
    current_workflow = workflow
    # Flat record of every action that ran successfully across all repair
    # attempts — original pre-failure actions plus recovered continuations.
    completed_actions: list[dict[str, Any]] = []

    for repair_attempt in range(DEFAULT_MAX_REPAIR_ATTEMPTS + 1):
        validated_workflow = runner.validate(current_workflow)
        passed_states = await runner.controller.check(validated_workflow["states"])
        if not passed_states:
            return {
                "result": result,
                "workflow": _build_final_workflow(workflow, completed_actions),
            }

        try:
            for workflow_state in passed_states:
                state_results = await _execute_state_actions(workflow_state, runner)
                result.append(state_results)
                completed_actions.extend(workflow_state.get("actions") or [])
            return {
                "result": result,
                "workflow": _build_final_workflow(workflow, completed_actions),
            }
        except WorkflowExecutionError as exc:
            if exc.completed_results:
                result.append(exc.completed_results)
            # The actions before the failing index ran successfully this round.
            completed_actions.extend(workflow_state["actions"][: exc.action_index])

            if repair_attempt >= DEFAULT_MAX_REPAIR_ATTEMPTS:
                return {
                    "result": {
                        "success": False,
                        "error": str(exc.original_error),
                        "failed_action": exc.action,
                        "completed_results": exc.completed_results,
                        "repair_attempts": repair_attempt,
                    },
                    "workflow": _build_final_workflow(workflow, completed_actions),
                }

            debug_response = await debug_workflow(
                BrowserExecuteState(
                    task=state["task"],
                    messages=state["messages"],
                    workflow=current_workflow,
                    error=str(exc.original_error),
                    failed_action=exc.action,
                    completed_actions=workflow_state["actions"][: exc.action_index],
                    remaining_actions=workflow_state["actions"][exc.action_index :],
                ),
                runtime,
            )

            patched_workflow = debug_response.get("workflow")
            if not isinstance(patched_workflow, dict):
                return {
                    "result": {
                        "success": False,
                        "error": str(exc.original_error),
                        "message": "Workflow repair failed to produce a patched workflow",
                    },
                    "workflow": _build_final_workflow(workflow, completed_actions),
                }

            # Execute only the patched continuation — we're already past the
            # completed actions in the live browser and don't want to re-run
            # them. The merged final workflow is assembled separately.
            current_workflow = patched_workflow

    return {
        "result": result,
        "workflow": _build_final_workflow(workflow, completed_actions),
    }


async def _execute_state_actions(state: dict[str, Any], runner: WorkflowRunner) -> list[Any]:
    actions = state.get("actions")
    if not isinstance(actions, list):
        raise ValueError("State 'actions' must be a list")

    results: list[Any] = []
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValueError("Each action must be a dictionary")
        try:
            results.append(await runner.executor.execute(action))
        except Exception as exc:
            raise WorkflowExecutionError(
                state=state,
                action=action,
                action_index=index,
                completed_results=results,
                original_error=exc,
            ) from exc

        if index < len(actions) - 1:
            await asyncio.sleep(runner.executor.config["action_period"])

    return results


def _build_debug_task(state: BrowserExecuteState, runtime: Runtime[BrowserExecuteContext]) -> str:
    page = runtime.context.runner.executor.registry.context.get("page", runtime.context.page)
    current_url = page.url
    error = state.get("error") or "Unknown workflow execution error"
    failed_action = state.get("failed_action")
    completed_actions = state.get("completed_actions", [])
    remaining_actions = state.get("remaining_actions", [])

    lines = [
        "Recover a failed browser workflow from the current live page state.",
        f"Original task: {state['task']}",
        f"Current URL: {current_url}",
        f"Failure: {error}",
        "",
        "Actions already completed successfully in this run:",
        json.dumps(completed_actions, indent=2),
        "",
        "Action that failed or next actions that still need to be adapted:",
        json.dumps(failed_action or remaining_actions, indent=2),
        "",
        "Remaining original actions from the failure point:",
        json.dumps(remaining_actions, indent=2),
        "",
        "You are already on the page reached after the successful actions above.",
        "Do not restart from the beginning unless it is absolutely necessary.",
        "Interact with the current page to determine a reliable continuation path.",
        "When you are done, stop after completing the remaining task.",
    ]
    return "\n".join(lines)


async def debug_workflow(state: BrowserExecuteState, runtime: Runtime[BrowserExecuteContext]):
    page = runtime.context.runner.executor.registry.context.get("page", runtime.context.page)
    debug_task = _build_debug_task(state, runtime)
    browser_agent = Agent(
        page=page,
        browser=Browser(
            browser=runtime.context.browser,
            browser_context=runtime.context.browser_context,
            playwright=runtime.context.playwright,
            agent_current_page=page,
            human_current_page=page,
        ),
        controller=build_controller(EXCLUDED_BROWSER_USE_ACTIONS),
        llm=get_browser_use_model(),
        task=debug_task,
        headless=BROWSER_USE_HEADLESS,
    )
    history = await browser_agent.run(max_steps=DEFAULT_MAX_STEPS)
    parsed_history = parse_agent_history(history.model_dump())
    patched_workflow = gen_workflow(
        parsed_history,
        specification=f"Recovered continuation for: {state['task']}",
    )
    return {
        "result": history.model_dump(),
        "workflow": patched_workflow,
    }


def create_agent():
    graph = StateGraph(
        state_schema=BrowserExecuteState,
        context_schema=BrowserExecuteContext,
    )
    graph.add_node("execute_workflow", execute_workflow)
    graph.add_conditional_edges(
        START,
        route_workflow,
        path_map={
            "execute_workflow": "execute_workflow",
            END: END,
        },
    )
    graph.add_edge("execute_workflow", END)
    return graph.compile()
