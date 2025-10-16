"""
NetGent - Agent-Based Automation of Network Application Workflows

NetGent is an AI-agent framework for automating complex application workflows
to generate realistic network traffic datasets. It combines the flexibility of
language-based agents with the reliability of compiled execution.

Key Features:
    - Deterministic replay of workflows
    - Reduced redundant LLM calls via state caching
    - Fast adaptation to changing application interfaces
    - Natural language workflow definitions

Main Components:
    NetGent: Main orchestrator class
    BrowserSession: Browser session management
    PyAutoGUIController: Browser action controller
    WebAgent: LLM-driven browser interaction
    StateSynthesis: State selection and generation
    ProgramController: State checking and routing
    StateExecutor: Action execution

Usage:
    from netgent import NetGent
    from netgent.components import WebAgent, StateSynthesis
    from utils.message import StatePrompt
    
    # Initialize agent with LLM
    agent = NetGent(llm=your_llm)
    
    # Define workflow
    state_prompts = [
        StatePrompt(
            name="Navigate to Site",
            triggers=["If on homepage"],
            actions=["Navigate to https://example.com"]
        )
    ]
    
    # Run workflow
    result = agent.run(state_prompts=state_prompts)

Reference:
    Research Paper: https://arxiv.org/abs/2406.08392
    "NetGent: Agent-Based Automation of Network Application Workflows"
"""

from .agent import NetGent, NetGentState
from .browser import BrowserSession, PyAutoGUIController, BaseController
from .components import (
    ProgramController,
    StateExecutor,
    StateSynthesis,
    WebAgent,
    WebAgentState,
)

__all__ = [
    # Main agent
    "NetGent",
    "NetGentState",
    # Browser components
    "BrowserSession",
    "PyAutoGUIController",
    "BaseController",
    # Workflow components
    "ProgramController",
    "StateExecutor",
    "StateSynthesis",
    "WebAgent",
    "WebAgentState",
]

__version__ = "0.1.0"
__author__ = "Eugene Vuong"
__email__ = "vuongeugene@gmail.com"