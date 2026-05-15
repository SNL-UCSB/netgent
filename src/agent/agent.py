import asyncio
import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from langgraph.graph import END, START, MessagesState
from langgraph.graph.state import StateGraph
from playwright.async_api import async_playwright

from clients.netgent.src.agent.subagents.browser.agent import (
    create_agent as create_browser_agent,
)
from clients.netgent.src.agent.subagents.browser.util import open_browser_session
from clients.netgent.src.agent.subagents.shell.agent import (
    create_agent as create_shell_agent,
)
from clients.netgent.src.engine.controller import ProgramController
from clients.netgent.src.engine.executor import StateExecutor
from clients.netgent.src.engine.runner import WorkflowRunner
from clients.netgent.src.registry.actions.network import NETWORK_ACTIONS
from clients.netgent.src.registry.actions.playwright import PLAYWRIGHT_ACTIONS
from clients.netgent.src.registry.triggers.base import always_true
from clients.netgent.src.registry.triggers.playwright import PLAYWRIGHT_TRIGGERS

WorkflowType = Literal["browser", "shell", "hybrid"]


class NetGentState(MessagesState):
    task: str
    type: WorkflowType = "browser"
    workflow: dict = {}
    result: list = []
    config: dict = {}
    parameters: dict[str, str] = {}


def _iter_result_screenshots(value: object, path: tuple[object, ...] = ()):
    if isinstance(value, dict):
        screenshot = value.get("screenshot")
        if isinstance(screenshot, dict):
            b64 = screenshot.get("b64")
            image_format = screenshot.get("format")
            if isinstance(b64, str) and b64 and isinstance(image_format, str):
                yield path, b64, image_format

        for key, nested_value in value.items():
            yield from _iter_result_screenshots(nested_value, (*path, key))
        return

    if isinstance(value, list):
        for index, nested_value in enumerate(value):
            yield from _iter_result_screenshots(nested_value, (*path, index))


def _write_result_screenshot_artifacts(
    result: object,
    artifact_dir: Path,
) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    artifact_dir.mkdir(parents=True, exist_ok=True)

    for index, (path_parts, b64, image_format) in enumerate(
        _iter_result_screenshots(result),
        start=1,
    ):
        safe_format = image_format.lower().strip(".") or "png"
        filename = f"screenshot_{index:03d}.{safe_format}"
        file_path = artifact_dir / filename
        file_path.write_bytes(base64.b64decode(b64))
        artifacts.append(
            {
                "path": str(file_path),
                "format": safe_format,
                "source": " -> ".join(str(part) for part in path_parts),
            }
        )

    return artifacts


def _write_workflow_artifact(
    result: object,
    artifact_dir: Path,
) -> str | None:
    if not isinstance(result, dict):
        return None

    workflow = result.get("workflow")
    if not isinstance(workflow, dict):
        return None

    artifact_dir.mkdir(parents=True, exist_ok=True)

    workflow_json_path = artifact_dir / "generated_workflow.json"
    workflow_json_path.write_text(json.dumps(workflow, indent=2), encoding="utf-8")
    return str(workflow_json_path)


# Routes the Type
def route_type(state: NetGentState):
    if state["type"] == "browser":
        return "browser"
    if state["type"] == "shell":
        return "shell"
    if state["type"] == "hybrid":
        return "hybrid"
    return END


def _build_shell_runner(*, parameters: dict[str, Any] | None = None) -> WorkflowRunner:
    return WorkflowRunner(
        controller=ProgramController(triggers=(always_true,)),
        executor=StateExecutor(actions=NETWORK_ACTIONS, parameters=parameters),
        config={},
    )


def _build_hybrid_runner(
    *, page: Any, parameters: dict[str, Any] | None = None
) -> WorkflowRunner:
    return WorkflowRunner(
        controller=ProgramController(
            triggers=(always_true, *PLAYWRIGHT_TRIGGERS),
            context={"page": page},
        ),
        executor=StateExecutor(
            actions=(*PLAYWRIGHT_ACTIONS, *NETWORK_ACTIONS),
            context={"page": page},
            parameters=parameters,
        ),
        config={},
    )


def _load_har_result(har_path: str) -> dict[str, Any] | None:
    if not os.path.exists(har_path):
        return None

    try:
        with open(har_path, encoding="utf-8") as har_file:
            return json.load(har_file)
    except Exception:
        return None
    finally:
        try:
            os.unlink(har_path)
        except OSError:
            pass


def _coerce_workflow(response: object) -> dict[str, Any] | None:
    if not isinstance(response, dict):
        return None

    workflow = response.get("workflow")
    if isinstance(workflow, dict):
        return workflow
    return None


def _coerce_result(response: object) -> Any:
    if isinstance(response, dict) and "result" in response:
        return response["result"]
    return response


def _merge_workflows(
    *,
    task: str,
    browser_workflow: dict[str, Any] | None,
    shell_workflow: dict[str, Any] | None,
) -> dict[str, Any]:
    states: list[dict[str, Any]] = []
    if isinstance(browser_workflow, dict):
        browser_states = browser_workflow.get("states")
        if isinstance(browser_states, list):
            states.extend(browser_states)
    if isinstance(shell_workflow, dict):
        shell_states = shell_workflow.get("states")
        if isinstance(shell_states, list):
            states.extend(shell_states)

    return {
        "specification": task,
        "states": states,
    }


async def browser(state: NetGentState):
    browser_agent = create_browser_agent()
    return await browser_agent.ainvoke(
        {
            "task": state["task"],
            "messages": state["messages"],
            "workflow": state.get("workflow", None),
            "parameters": state.get("parameters", {}),
        },
    )


async def shell(state: NetGentState):
    shell_agent = create_shell_agent()
    runner = _build_shell_runner(parameters=state.get("parameters"))
    return await shell_agent.ainvoke(
        {
            "task": state["task"],
            "messages": [],
            "workflow": state.get("workflow", None),
            "parameters": state.get("parameters", {}),
        },
        context={"runner": runner},
    )


async def hybrid(state: NetGentState):
    workflow = state.get("workflow")
    if isinstance(workflow, dict) and workflow:
        return await _run_hybrid_workflow(
            task=state["task"],
            workflow=workflow,
            parameters=state.get("parameters"),
        )

    browser_agent = create_browser_agent()
    browser_response = await browser_agent.ainvoke(
        {
            "task": state["task"],
            "messages": state["messages"],
            "workflow": None,
            "parameters": state.get("parameters", {}),
        },
    )

    shell_agent = create_shell_agent()
    shell_runner = _build_shell_runner(parameters=state.get("parameters"))
    shell_response = await shell_agent.ainvoke(
        {
            "task": state["task"],
            "messages": [],
            "workflow": None,
            "parameters": state.get("parameters", {}),
        },
        context={"runner": shell_runner},
    )

    merged_workflow = _merge_workflows(
        task=state["task"],
        browser_workflow=_coerce_workflow(browser_response),
        shell_workflow=_coerce_workflow(shell_response),
    )
    if not merged_workflow["states"]:
        return {
            "result": {
                "success": False,
                "error": "Hybrid workflow generation did not produce any workflow states",
            },
            "workflow": {},
        }

    return {
        "result": {
            "browser": _coerce_result(browser_response),
            "shell": _coerce_result(shell_response),
        },
        "workflow": merged_workflow,
    }


async def _run_hybrid_workflow(
    *,
    task: str,
    workflow: dict[str, Any],
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    playwright = await async_playwright().start()
    har_file = tempfile.NamedTemporaryFile(suffix=".har", delete=False)
    har_file.close()
    har_path = har_file.name
    browser_instance, browser_context, page = await open_browser_session(
        playwright,
        record_har_path=har_path,
    )
    runner = _build_hybrid_runner(page=page, parameters=parameters)
    response: dict[str, Any]
    try:
        output = await runner.run(workflow)
        response = {
            "result": {
                "success": True,
                "output": output,
            },
            "workflow": workflow,
        }
    except Exception as exc:
        response = {
            "result": {
                "success": False,
                "error": str(exc),
            },
            "workflow": workflow,
        }
    finally:
        await browser_context.close()
        await browser_instance.close()
        await playwright.stop()

    har_result = _load_har_result(har_path)
    result_payload = response.get("result")
    if isinstance(result_payload, dict):
        result_payload = dict(result_payload)
        result_payload["har"] = har_result
    else:
        result_payload = {"data": result_payload, "har": har_result}

    return {
        "result": result_payload,
        "workflow": workflow,
    }


def create_agent():
    graph = StateGraph(state_schema=NetGentState)
    graph.add_node("browser", browser)
    graph.add_node("shell", shell)
    graph.add_node("hybrid", hybrid)
    graph.add_conditional_edges(
        START,
        route_type,
        {
            "browser": "browser",
            "shell": "shell",
            "hybrid": "hybrid",
            END: END,
        },
    )
    graph.add_edge("browser", END)
    graph.add_edge("shell", END)
    graph.add_edge("hybrid", END)
    return graph.compile()


async def main():
    wf = {
        "specification": "1. Watch a YouTube video (https://www.youtube.com/watch?v=RKBi_ouZPP8) for 30 seconds",
        "workflow": {
            "specification": "1. Go to YouTube, 2. Search for Silent and Quiet Video, 3. Click a Video and Wait/Watch it 30 Seconds",
            "states": [
                {
                    "checks": [{"type": "always_true", "params": {}}],
                    "actions": [
                        {
                            "type": "go_to_url",
                            "params": {
                                "url": "https://www.youtube.com",
                                "new_tab": False,
                            },
                        },
                        {
                            "type": "input_text",
                            "params": {
                                "selector": 'input[name="search_query"]',
                                "text": "Silent and Quiet Video",
                            },
                        },
                        {
                            "type": "click_element",
                            "params": {
                                "selector": 'button.ytSearchboxComponentSearchButton[aria-label="Search"]'
                            },
                        },
                        {
                            "type": "click_element",
                            "params": {"selector": 'div[id="searchbox-suggestion:19"]'},
                        },
                        {
                            "type": "click_element",
                            "params": {
                                "selector": 'button.ytSearchboxComponentSearchButton[aria-label="Search"]'
                            },
                        },
                        {
                            "type": "click_element",
                            "params": {"selector": 'a[id="thumbnail"]'},
                        },
                        {"type": "wait", "params": {"seconds": 30}},
                        {"type": "wait", "params": {"seconds": 10}},
                    ],
                    "end_state": "Workflow Completed",
                    "executed": [],
                }
            ],
        },
    }

    agent = create_agent()
    result = await agent.ainvoke(
        {
            "messages": [],
            "task": wf["specification"],
            "workflow": {},
            "type": "browser",
        },
    )
    artifacts = _write_result_screenshot_artifacts(
        result,
        Path("artifacts") / "browser",
    )
    if isinstance(result, dict):
        result["artifacts"] = artifacts
        workflow_artifact = _write_workflow_artifact(
            result,
            Path("artifacts") / "browser",
        )
        if workflow_artifact is not None:
            result["workflow_json_path"] = workflow_artifact
    result_json_path = Path("artifacts") / "browser" / "result.json"
    result_json_path.parent.mkdir(parents=True, exist_ok=True)
    result_json_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    if isinstance(result, dict):
        result["result_json_path"] = str(result_json_path)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
