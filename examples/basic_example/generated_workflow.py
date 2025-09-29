import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from state_agent.state_agent.agent import StateAgent
from state_agent.state_agent.message import StatePrompt
from langchain_google_vertexai import ChatVertexAI
from state_agent.actions.browser_manager import BrowserManager
from dotenv import load_dotenv
import json
load_dotenv()


if __name__ == "__main__":
    browser_manager = BrowserManager(human_movement=True, shake=False)
    prompts = [
        StatePrompt(
            name="Navigate To Googlesea",
            description="Navigated to the Google Website",
            triggers=["If it is on the chrome incognito mode"],
            actions=["ONLY FOLLOW THESE INSTRUCTIONS", "Go to https://www.google.com/", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Search on Google",
            description="Searched for the address on the Google Website",
            triggers=["If on the Google Website"],
            actions=["Type [SEARCH] into input field", "press enter key", "TERMINATE AT THIS POINT AND DO NOTHING ELSE"],
            terminate="If the search results are displayed"
        ),
    ]

    judge_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0, thinking_budget=0, cache=False)
    browser_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0, thinking_budget=0, cache=False)
    state_agent = StateAgent(judge_llm, browser_llm, browser_manager, {"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 10, "action_period": 2})

    states = []

    result = state_agent.run(prompts, states, transition_period=5, parameters={"SEARCH": "Python Tutorial"})

    with open(os.path.join(os.path.dirname(__file__), 'basic-example-workflow.json'), 'w') as f:
        json.dump(result["states"], f, indent=2)
