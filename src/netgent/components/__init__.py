"""
NetGent Components

Core components implementing the NetGent workflow logic.

This module provides the four main subsystems of NetGent:

Components:
    ProgramController: Checks state trigger conditions and routes workflow execution
    StateExecutor: Executes actions defined in matched states
    StateSynthesis: Uses LLM to select and generate state definitions
    WebAgent: Intelligent browser interaction using vision-language models

Typical Workflow:
    1. NetGent Agent initializes with state_prompts and state_repository
    2. ProgramController checks if any states match current page
       - If match found: → StateExecutor → back to ProgramController
       - If no match: → StateSynthesis
    3. StateSynthesis selects appropriate state and generates triggers
    4. WebAgent generates and executes actions for the state
    5. NetGent Agent adds generated state to repository
    6. Loop back to ProgramController

Usage:
    from netgent.components import ProgramController, StateExecutor
    from netgent.components import StateSynthesis, WebAgent
    
    # Initialize components
    program_controller = ProgramController(controller, config)
    state_executor = StateExecutor(controller, config)
    state_synthesis = StateSynthesis(llm, controller)
    web_agent = WebAgent(llm, controller)
"""

from .program_controller import ProgramController
from .state_executor import StateExecutor
from .state_synthesis import StateSynthesis
from .web_agent import WebAgent, WebAgentState

__all__ = [
    "ProgramController",
    "StateExecutor",
    "StateSynthesis",
    "WebAgent",
    "WebAgentState",
]

