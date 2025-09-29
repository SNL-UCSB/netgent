import sys
import os
import json
# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from state_agent.state_agent.agent import StateAgent
from state_agent.state_agent.message import StatePrompt
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":

    prompts = [
        StatePrompt(
            name="Navigate To Googlesea",
            description="Navigated to the Google Website",
            triggers=["If it is on the chrome incognito mode"],
            actions=["Go to https://www.google.com/", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Search on Google",
            description="Searched for the address on the Google Website",
            triggers=["If on the Google Website"],
            actions=["Type parameters[SEARCH] into input field", "press enter key", "TERMINATE AT THIS POINT AND DO NOTHING ELSE"],
            terminate="If the search results are displayed"
        ),
    ]


    state_agent = StateAgent()

    with open(os.path.join(os.path.dirname(__file__), 'basic-example-workflow.json'), 'r') as f:
        states = json.load(f)

    result = state_agent.run(prompts, states, parameters={"SEARCH": "Hello World"}, transition_period=5)
    
      