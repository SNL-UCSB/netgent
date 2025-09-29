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
    browser_manager = BrowserManager(human_movement=True, shake=True, user_data_dir="./streaming/hulu-non-navigate-profile/")
    judge_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0, thinking_budget=0, cache=False)
    browser_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0, thinking_budget=0, cache=False)
    state_agent = StateAgent(judge_llm, browser_llm, browser_manager, {"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 20, "action_period": 2})
    with open("streaming/states/disney-plus-national-geo.json", "r") as f:
        states = json.load(f)
    
    # states = []
    prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["Go to https://www.disneyplus.com/"]
        ),
        StatePrompt(
            name="On Disney Plus Home Page",
            description="On Disney Plus Home Page",
            triggers=["If 'Endless entertainment for all.' is on the page"],
            actions=["Press the Login Button"],
        ),
        StatePrompt(
            name="Login to Account",
            description="On Login",
            triggers=["If On Login Page (Find Login Text for the Trigger)"],
            actions=["[1] Type the Email is snlclient1@gmail.com", "[2] Pressing the button 'Continue'", "[3] Type the password 'password' (MAKE SURE YOU DO THIS BEFORE PRESSING THE BUTTON 'Log In')", "[4] press the button 'Log In'"],
        ),
        StatePrompt(
            name="On Select Profile",
            description="On Select Profile",
            triggers=["If 'Who's watching?' is on the page"],
            actions=["Select the Profile 'snlclient'"],
        ),
        StatePrompt(
            name="On the Disney Plus Home Page (When Logged In)",
            description="Go to the National Geographic Channel After Logging In In the Home Page",
            triggers=["If it is on the Home Page ONLY CHECK BY URL"],
            actions=["Press on the National Geographic Channel"],
        ),
        StatePrompt(
            name="On National Geographic Channel",
            description="On National Geographic Channel, Go to the First Movie/Show",
            triggers=["If it is has 'Featured' in the page"],
            actions=["Press on First Movie/Show"],
        ),
        StatePrompt(
            name="On the Movie/Show Page",
            description="Press the Play Button on the Movie Page",
            triggers=["If it is on the Movie/Show Page (See If There is the Key Word 'Suggested' and 'Details' as a Trigger)", "Don't use URL as a Trigger"],
            actions=["Press Tab, Press Enter And Enter Again to Go in the Video Player", "Click on 0.2 of the Slider", "Wait 5 Seconds", "Click on 0.4 of the Slider", "Wait 5 Seconds", "Click on 0.6 of the Slider", "Wait 5 Seconds"],
            end_state="Action Completed"
        ),
    ]

    parameters = {
        
    }
    result = state_agent.run(prompt, states, parameters, use_llm=True)

    if input("Save the states? (y/n): ") == "y":
        with open("streaming/states/disney-plus-national-geo.json", "w") as f:
            json.dump(result["states"], f)

    print("Executed:", result["executed"])
    print("Success:", result["success"])
    print("Error:", result["error"])
    print("Message:", result["message"])
    print("States:", result["states"])