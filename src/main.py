"""NetGent client.

Two entry points:

* :meth:`NetGent.run_workflow` — deterministic engine replay of a
  pre-built workflow. ``type="shell"`` runs subprocess actions;
  ``type="browser"`` runs Playwright actions.

* :meth:`NetGent.generate` — drives the LLM subagent matching ``type``
  to turn a natural-language spec into a workflow and execute it.

Routing is inlined (no LangGraph wrapper).
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Literal

from engine.controller import ProgramController
from engine.executor import StateExecutor
from engine.runner import WorkflowRunner
from registry.actions.network import NETWORK_ACTIONS
from registry.triggers.base import always_true

WorkflowType = Literal["shell", "browser"]


class NetGent:
    def __init__(
        self,
        *,
        cdp_url: str | None = None,
        headless: bool = True,
    ) -> None:
        self._cdp_url = cdp_url
        self._headless = headless

    # ── deterministic replay ─────────────────────────────────────────
    def run_workflow(
        self,
        workflow: dict[str, Any],
        *,
        parameters: dict[str, str] | None = None,
        type: WorkflowType = "shell",
    ) -> dict[str, Any]:
        return asyncio.run(
            self.arun_workflow(workflow, parameters=parameters, type=type)
        )

    async def arun_workflow(
        self,
        workflow: dict[str, Any],
        *,
        parameters: dict[str, str] | None = None,
        type: WorkflowType = "shell",
    ) -> dict[str, Any]:
        if type == "shell":
            runner = self._shell_runner(parameters=parameters)
            try:
                output = await runner.run(workflow)
            except Exception as exc:
                return {"result": {"success": False, "error": str(exc)}}
            return {"result": {"success": True, "output": output}}

        if type == "browser":
            async with self._playwright_page() as page:
                runner = self._browser_runner(page=page, parameters=parameters)
                try:
                    output = await runner.run(workflow)
                except Exception as exc:
                    return {"result": {"success": False, "error": str(exc)}}
                return {"result": {"success": True, "output": output}}

        raise ValueError(f"unsupported workflow type: {type!r}")

    # ── LLM generate ─────────────────────────────────────────────────
    async def generate(
        self,
        spec: str,
        *,
        type: WorkflowType = "browser",
        parameters: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Drive the appropriate LLM subagent to produce + run a workflow."""
        params = dict(parameters or {})

        if type == "browser":
            from agents.subagents.browser.agent import (
                create_agent as create_browser_agent,
            )

            agent = create_browser_agent()
            return await agent.ainvoke(
                {
                    "task": spec,
                    "messages": [],
                    "workflow": None,
                    "parameters": params,
                },
            )

        if type == "shell":
            from agents.subagents.shell.agent import (
                create_agent as create_shell_agent,
            )

            agent = create_shell_agent()
            runner = self._shell_runner(parameters=params)
            return await agent.ainvoke(
                {
                    "task": spec,
                    "messages": [],
                    "workflow": None,
                    "parameters": params,
                },
                context={"runner": runner},
            )

        raise ValueError(f"unsupported workflow type: {type!r}")

    # ── runner builders (shell + browser) ────────────────────────────
    @staticmethod
    def _shell_runner(
        *, parameters: dict[str, str] | None = None
    ) -> WorkflowRunner:
        return WorkflowRunner(
            controller=ProgramController(triggers=(always_true,)),
            executor=StateExecutor(actions=NETWORK_ACTIONS, parameters=parameters),
            config={},
        )

    @staticmethod
    def _browser_runner(
        *, page: Any, parameters: dict[str, str] | None = None
    ) -> WorkflowRunner:
        # Imported lazily so the shell path doesn't pull in Playwright
        # transitively.
        from registry.actions.playwright import PLAYWRIGHT_ACTIONS

        return WorkflowRunner(
            controller=ProgramController(
                triggers=(always_true,),
                context={"page": page},
            ),
            executor=StateExecutor(
                actions=PLAYWRIGHT_ACTIONS,
                context={"page": page},
                parameters=parameters,
            ),
            config={},
        )

    # ── playwright lifecycle (browser engine path only) ──────────────
    @asynccontextmanager
    async def _playwright_page(self):
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        try:
            if self._cdp_url:
                browser = await playwright.chromium.connect_over_cdp(self._cdp_url)
                context = browser.contexts[0] if browser.contexts else (
                    await browser.new_context()
                )
            else:
                browser = await playwright.chromium.launch(headless=self._headless)
                context = await browser.new_context()

            page = await context.new_page()
            try:
                yield page
            finally:
                await context.close()
                await browser.close()
        finally:
            await playwright.stop()


__all__ = ["NetGent", "WorkflowType"]
