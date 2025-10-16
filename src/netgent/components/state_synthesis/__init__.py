"""
State Synthesis Component

The State Synthesis component uses LLMs to select appropriate states and generate
trigger conditions when no existing state matches.

This component:
    - Selects appropriate state from user-defined prompts
    - Generates trigger conditions for states
    - Creates action prompts for Web Agent
    - Tracks execution history

Classes:
    StateSynthesis: Main synthesis class

Workflow:
    select_state → define_trigger → prompt_action → END

Usage:
    from netgent.components.state_synthesis import StateSynthesis
    from utils.message import StatePrompt
    
    synthesis = StateSynthesis(llm, browser_controller)
    result = synthesis.run(
        prompts=[StatePrompt(...)],
        executed=executed_states
    )
    
Output Format:
    {
        "choice": StatePrompt,      # Selected state
        "triggers": [...]            # Generated trigger definitions
        "prompt": "..."             # Action prompt for Web Agent
    }
"""

from .state_synthesis import StateSynthesis

__all__ = ['StateSynthesis']
