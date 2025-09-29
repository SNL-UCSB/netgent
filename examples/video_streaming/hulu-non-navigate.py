import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state_agent.state_agent.agent import StateAgent
from state_agent.state_agent.agent import StatePrompt
from langchain_google_vertexai import ChatVertexAI
from state_agent.actions.browser_manager import BrowserManager
import vertexai
import json
from dotenv import load_dotenv
load_dotenv()

# vertexai.init(project="crypto-hallway-464121-j6", location="us-central1")

# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../google_creds.json"


if __name__ == "__main__": 
    browser_manager = BrowserManager(human_movement=True, shake=True)
    judge_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0, thinking_budget=0, cache=False)
    browser_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0, thinking_budget=0, cache=False)
    state_agent = StateAgent(judge_llm, browser_llm, browser_manager, {"allow_multiple_states": False, "transition_period": 10, "no_states_timeout": 20, "action_period": 2})
    try:
        with open("streaming/states/hulu-non-navigate.json", "r") as f:
            raise Exception("Test")
            states = json.load(f)
    except:
        states = []
    
    prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition and there is no actions that are already executed, run the action"],
            actions=["Go to https://www.hulu.com", "TERMINATE"]
        ),
        StatePrompt(
            name="On the Welcome Page",
            description="On the Welcome Page",
            triggers=["If 'Welcome to Hulu' is on the page. (GET THE TEXT: 'Get Hulu, Disney+, and ESPN+, all with ads, for $16.99/mo.')"],
            actions=["Press Tab and Press Enter to Go in the Login Page", "TERMINATE"],
        ),
        StatePrompt(
            name="Login to Account",
            description="On Login",
            triggers=["If On Login Page (Find Login Text for the Trigger)"],
            actions=["[1] Type the Email is snlclient1@gmail.com", "[2] Pressing the button 'Continue'", "[3] Type the password 'SNL.12345' (MAKE SURE YOU DO THIS BEFORE PRESSING THE BUTTON 'Log In')", "[4] press the button 'Log In'", "TERMINATE"],
        ),
        StatePrompt(
            name="On Select Profile",
            description="On Select Profile",
            triggers=["If 'Who's watching?' is on the page"],
            actions=["Select the Profile 'snlclient' (Ex: 'snlclient')", "TERMINATE"],
        ),
        StatePrompt(
            name="On the Hulu Home Page (When Logged In)",
            description="Go to the Show After Logging In In the Home Page",
            triggers=["If it is on the Home Page (Showing Recommended For You) And On 'https://www.hulu.com/hub/home'"],
            actions=["Go to https://www.hulu.com/series/91de62df-0394-4e17-85a8-e843bd730ede", "TERMINATE"],
        ),
        StatePrompt(
            name="On the Movie/Show Page",
            description="Press the Play Button on the Movie Page",
            triggers=["If it is on the Movie/Show Page (See If There is the Key Word 'Suggested' and 'Details' as a Trigger)", "Don't use URL as a Trigger"],
            actions=["Press Tab THREE Times and Press Enter to Go in the Video Player", "WAIT FOR THE ADS TO END", "Click on 0.2 of the Slider", "Wait 5 Seconds", "Click on 0.4 of the Slider", "Wait 5 Seconds", "Click on 0.6 of the Slider", "Wait 5 Seconds", "TERMINATE"],
            end_state="Action Completed"
        ),
    ]

    parameters = {
        
    }
    import time
    start_time = time.time()
    result = state_agent.run(prompt, states, parameters, use_llm=True)
    end_time = time.time()
    print(f"Execution time: {end_time - start_time:.2f} seconds")

    if input("Save the states? (y/n): ") == "y":
        with open("streaming/states/hulu-non-navigate.json", "w") as f:
            json.dump(result["states"], f)

    print("Executed:", result["executed"])
    print("Success:", result["success"])
    print("Error:", result["error"])
    print("Message:", result["message"])
    print("States:", result["states"])