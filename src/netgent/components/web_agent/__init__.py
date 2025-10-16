"""
Web Agent Component

The Web Agent uses vision-language models to understand web pages and generate
appropriate browser actions.

This component:
    - Understands web pages using vision (screenshots + DOM)
    - Plans action sequences to achieve goals
    - Generates executable browser actions
    - Adapts to changing page states

Classes:
    WebAgent: Main agent class for LLM-driven browser interaction
    WebAgentState: TypedDict defining web agent state

Workflow:
    START → annotate → plan → execute → check_continue
              ↑                           |
              └───────────────────────────┘

Usage:
    from netgent.components.web_agent import WebAgent
    
    web_agent = WebAgent(llm, browser_controller)
    result = web_agent.run(
        user_query="Type 'hello' into the search box and press Enter",
        wait_period=0.5
    )
    
Output Format:
    {
        "actions": [                # List of executed actions
            {"type": "click", "params": {...}},
            {"type": "type", "params": {...}},
            {"type": "terminate", "params": {...}}
        ],
        "messages": [...]           # Full interaction history
    }
"""

from .web_agent import WebAgent, WebAgentState

__all__ = ["WebAgent", "WebAgentState"]
