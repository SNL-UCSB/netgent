import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state_agent.state_agent.agent import StateAgent
from state_agent.state_agent.agent import StatePrompt
from langchain_google_vertexai import ChatVertexAI
from state_agent.actions.browser_manager import BrowserManager
import json
import time
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__": 
    browser_manager = BrowserManager(human_movement=True, shake=True)
    judge_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2, thinking_budget=0, cache=False)
    browser_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2, thinking_budget=0, cache=False)
    state_agent = StateAgent(judge_llm, browser_llm, browser_manager, {"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 10, "action_period": 2})
    try:
        with open("conference/states/microsoft-teams.json", "r") as f:
            states = json.load(f)
    except:
        states = []
    prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["Go to https://teams.microsoft.com/v2/"]
        ),
        StatePrompt(
            name="On Microsoft Login",
            description="Login to Microsoft",
            triggers=["If it is on the Microsoft Login Page. Get elements and text from the page"],
            actions=["Type 'snlclient1@gmail.com' in the email field and password is 'SNL.12345'. Transverse to find these information and make sure it is on the stay sign in option"],
        ),
        StatePrompt(
            name="On Microsoft Teams Home Page",
            description="On Microsoft Teams Home Page",
            triggers=["If 'Microsoft Teams' is on the page"],
            actions=["Press 'Meet' on the Sidebar, 'Join a Meeting ID' and then type the Meeting ID '9362664981417' and password is 'kGRIkO3HhILAigRFwG', and press 'Join meeting'"],
        ),
        StatePrompt(
            name="Error",
            description="Error",
            triggers=["If 'Error' is on the page"],
            actions=["Terminate"],
            end_state="Error"
        ),
        StatePrompt(
            name="On Teams Waiting Room",
            description="On the Teams Waiting Room",
            triggers=["If it is on the Teams Waiting Room"],
            actions=["wait for 5 seconds"],
        ),
        StatePrompt(
            name="On Teams Meeting Conference Screen",
            description="On the Teams Meeting Conference Screen",
            triggers=["If it is on the Teams Meeting Conference Screen"],
            actions=["Turn on the Camera and Microphone"],
            end_state="Teams Meeting Conference Screen"
        )
    ]

    parameters = {
        
    }
    start_time = time.perf_counter()
    result = state_agent.run(prompt, states, parameters, use_llm=True)
    elapsed_secs = time.perf_counter() - start_time
    print(f"State machine build time: {elapsed_secs:.2f} seconds")

    if input("Save the states? (y/n): ") == "y":
        with open("conference/states/microsoft-teams.json", "w") as f:
            json.dump(result["states"], f)

    print("Executed:", result["executed"])
    print("Success:", result["success"])
    print("Error:", result["error"])
    print("Message:", result["message"])
    print("States:", result["states"])