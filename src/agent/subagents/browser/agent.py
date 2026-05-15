import asyncio
import json
import os
import re
import tempfile
from typing import Any, NotRequired

from langgraph.graph import END, START, MessagesState
from langgraph.graph.state import StateGraph
from playwright.async_api import async_playwright

from clients.netgent.src.agent.subagents.browser.execute.agent import (
    create_agent as create_execute_agent,
)
from clients.netgent.src.agent.subagents.browser.generate.agent import (
    create_agent as create_browser_generate_agent,
)
from clients.netgent.src.agent.subagents.browser.util import open_browser_session
from clients.netgent.src.engine.controller import ProgramController
from clients.netgent.src.engine.executor import StateExecutor
from clients.netgent.src.engine.runner import WorkflowRunner
from clients.netgent.src.registry.actions.playwright import PLAYWRIGHT_ACTIONS
from clients.netgent.src.registry.triggers.base import always_true
from clients.netgent.src.registry.triggers.playwright import PLAYWRIGHT_TRIGGERS


class BrowserState(MessagesState):
    task: str
    workflow: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    generate_result: dict[str, Any] | None = None
    steps: NotRequired[int]
    parameters: NotRequired[dict[str, str]]


def _browser_parameter_placeholder(name: str) -> str:
    return "{{" + name + "}}"


_SECRET_TAG_RE = re.compile(r"<secret>\s*(\w+)\s*</secret>")


def _substitute_embedded_secrets(value: str, parameters: dict[str, str]) -> str | None:
    """Replace every ``<secret>name</secret>`` tag inside *value* with
    ``{{name}}`` — but only for names that exist in *parameters*.

    Returns the substituted string if at least one tag was replaced, or
    ``None`` if no known-parameter tag was present (so callers can fall
    back to their existing whole-value matching logic)."""
    if "<secret>" not in value:
        return None

    made_change = False

    def _sub(match: re.Match[str]) -> str:
        nonlocal made_change
        name = match.group(1)
        if name in parameters:
            made_change = True
            return _browser_parameter_placeholder(name)
        return match.group(0)

    new_value = _SECRET_TAG_RE.sub(_sub, value)
    return new_value if made_change else None


def _infer_browser_parameter_name(
    *,
    action_type: str,
    param_name: str,
    parameters: dict[str, str],
) -> str | None:
    if action_type == "go_to_url" and param_name == "url":
        candidates = [
            name
            for name in parameters
            if any(token in name.lower() for token in ("url", "link", "href"))
        ]
        if len(candidates) == 1:
            return candidates[0]

    if action_type == "wait" and param_name == "seconds":
        candidates = [
            name
            for name in parameters
            if any(
                token in name.lower()
                for token in ("wait", "time", "seconds", "duration")
            )
        ]
        if len(candidates) == 1:
            return candidates[0]

    return None


def _parameterize_browser_workflow(
    workflow: dict[str, Any],
    parameters: dict[str, str],
) -> dict[str, Any]:
    value_to_key = {value: key for key, value in parameters.items()}

    for wf_state in workflow.get("states") or []:
        for action in wf_state.get("actions") or []:
            action_type = action.get("type")
            params = action.get("params") or {}
            if not isinstance(action_type, str) or not isinstance(params, dict):
                continue

            for param_name, param_value in list(params.items()):
                # First: rewrite any embedded <secret>name</secret> tags into
                # {{name}} placeholders. Handles both full-value matches and
                # values where the secret is inside a larger string (e.g. a
                # URL like ``https://whereby.com/<secret>code</secret>``).
                if isinstance(param_value, str):
                    substituted = _substitute_embedded_secrets(param_value, parameters)
                    if substituted is not None:
                        params[param_name] = substituted
                        continue

                replacement_name: str | None = None

                if isinstance(param_value, str) and param_value in value_to_key:
                    replacement_name = value_to_key[param_value]
                elif isinstance(param_value, (int, float)):
                    replacement_name = value_to_key.get(str(param_value))

                if replacement_name is None:
                    replacement_name = _infer_browser_parameter_name(
                        action_type=action_type,
                        param_name=param_name,
                        parameters=parameters,
                    )

                if replacement_name is not None:
                    params[param_name] = _browser_parameter_placeholder(
                        replacement_name
                    )

    workflow["parameters"] = list(parameters.keys())
    return workflow


def route_run_workflow(state: BrowserState):
    if state.get("workflow"):
        return "run_workflow"
    return "generate_workflow"


async def generate_workflow(state: BrowserState) -> dict[str, Any]:
    playwright = await async_playwright().start()
    generate_agent = create_browser_generate_agent()
    parameters = state.get("parameters") or {}
    try:
        response = await generate_agent.ainvoke(
            {
                "task": state["task"],
                "messages": [],
                "steps": state.get("steps"),
                "parameters": parameters,
            },
            context={"playwright": playwright},
        )

        workflow = response.get("workflow")
        if isinstance(workflow, dict) and parameters:
            workflow = _parameterize_browser_workflow(workflow, parameters)

        return {
            "generate_result": response.get("result"),
            "workflow": workflow,
        }
    finally:
        await playwright.stop()


def route_run_generated_workflow(state: BrowserState):
    result = state.get("generate_result")
    workflow = state.get("workflow")
    if isinstance(result, dict) and result.get("success", False):
        if isinstance(workflow, dict):
            return "run_workflow"
    return END


async def run_workflow(state: BrowserState) -> dict[str, Any]:
    workflow = state.get("workflow")
    if not isinstance(workflow, dict):
        return {
            "result": {
                "success": False,
                "error": "Workflow must be generated before running it",
            }
        }
    agent = create_execute_agent()
    playwright = await async_playwright().start()
    har_file = tempfile.NamedTemporaryFile(suffix=".har", delete=False)
    har_file.close()
    har_path = har_file.name
    browser_instance, browser_context, page = await open_browser_session(
        playwright, record_har_path=har_path
    )
    runner = WorkflowRunner(
        controller=ProgramController(
            triggers=(always_true, *PLAYWRIGHT_TRIGGERS),
            context={"page": page},
        ),
        executor=StateExecutor(
            actions=PLAYWRIGHT_ACTIONS,
            context={"page": page},
            parameters=state.get("parameters"),
        ),
        config={},
    )
    response: dict[str, Any] | None = None
    try:
        response = await agent.ainvoke(
            {
                "task": state["task"],
                "messages": state["messages"],
                "workflow": workflow,
            },
            context={
                "playwright": playwright,
                "browser": browser_instance,
                "browser_context": browser_context,
                "page": page,
                "runner": runner,
            },
        )
    except Exception as exc:
        response = {
            "result": {
                "success": False,
                "error": str(exc),
            }
        }
    finally:
        await browser_context.close()
        await browser_instance.close()
        await playwright.stop()

    har_result: dict[str, Any] | None = None
    if os.path.exists(har_path):
        try:
            har_result = json.loads(open(har_path, encoding="utf-8").read())
        except Exception:
            har_result = None
        finally:
            try:
                os.unlink(har_path)
            except OSError:
                pass
    response_result = response.get("result") if isinstance(response, dict) else None
    if isinstance(response_result, dict):
        final_result = dict(response_result)
        final_result["har"] = har_result
    else:
        final_result = {
            "data": response_result,
            "har": har_result,
        }
    return {
        "result": final_result,
        "workflow": (
            response.get("workflow", workflow)
            if isinstance(response, dict)
            else workflow
        ),
    }


def create_agent():
    graph = StateGraph(state_schema=BrowserState)
    graph.add_node("generate_workflow", generate_workflow)
    graph.add_node("run_workflow", run_workflow)
    graph.add_conditional_edges(
        START,
        route_run_workflow,
        {
            "generate_workflow": "generate_workflow",
            "run_workflow": "run_workflow",
        },
    )
    graph.add_conditional_edges(
        "generate_workflow",
        route_run_generated_workflow,
        {
            "run_workflow": "run_workflow",
            END: END,
        },
    )
    graph.add_edge("run_workflow", END)
    return graph.compile()


async def main():
    task = (
        "Run a simple browser workflow. "
        "First navigate to a test page. "
        "Second wait for 5 seconds."
    )
    workflow = {
        "specification": (
            "Run a simple browser workflow. "
            "First navigate to a test page. "
            "Second wait for 5 seconds."
        ),
        "states": [
            {
                "checks": [{"type": "always_true", "params": {}}],
                "actions": [
                    {
                        "type": "go_to_url",
                        "params": {
                            "url": "data:text/html,<html><body><h1>Workflow Runner Test</h1></body></html>",
                            "new_tab": False,
                        },
                    },
                    {
                        "type": "wait",
                        "params": {"seconds": 5},
                    },
                ],
                "end_state": "Workflow Completed",
            }
        ],
    }
    browser_agent = create_agent()
    response = await browser_agent.ainvoke(
        {
            "task": os.getenv("BROWSER_USE_TASK", task),
            "messages": [],
            "workflow": workflow,
        },
    )
    print(response)
    return response


if __name__ == "__main__":
    asyncio.run(main())
