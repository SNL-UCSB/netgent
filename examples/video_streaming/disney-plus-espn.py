import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state_agent.state_agent.agent import StateAgent
from state_agent.state_agent.agent import StatePrompt
from langchain_google_vertexai import ChatVertexAI
from state_agent.actions.browser_manager import BrowserManager
import vertexai
import json
import time
from dotenv import load_dotenv
load_dotenv()

# vertexai.init(project="crypto-hallway-464121-j6", location="us-central1")

# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../google_creds.json"


if __name__ == "__main__": 
    browser_manager = BrowserManager(human_movement=True, shake=True)
    judge_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2, thinking_budget=0, cache=False)
    browser_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2, thinking_budget=0, cache=False)
    state_agent = StateAgent(judge_llm, browser_llm, browser_manager, {"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 10, "action_period": 2})
    try:
        with open("streaming/states/6-disney-plus-espn.json", "r") as f:
            states = json.load(f)
    except:
        states = []
    
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
            actions=["Close Modal If There Is One", "Press the Login Button"],
        ),
        StatePrompt(
            name="Login to Account",
            description="On Login",
            triggers=["If On Login Page (Find Login Text for the Trigger)"],
            actions=["[1] Type the Email is snlclient1@gmail.com", "[2] Pressing the button 'Continue'", "[3] Type the password 'SNL.12345' (MAKE SURE YOU DO THIS BEFORE PRESSING THE BUTTON 'Log In')", "[4] press the button 'Log In'"],
        ),
        StatePrompt(
            name="On Select Profile",
            description="On Select Profile",
            triggers=["If 'Who's watching?' is on the page"],
            actions=["Select the Profile 'snlclient'"],
        ),
        StatePrompt(
            name="On the One Time Code Page",
            description="On the One Time Code Page After Logging In",
            triggers=["If it is on the One Time Code Page", "Don't use URL as a Trigger"],
            actions=["Do Nothing. JUST Terminate"],
            end_state="One Time Code Needed"
        ),
        StatePrompt(
            name="On the Profile PIN Page",
            description="On the Profile PIN Page",
            triggers=["If it is on the Profile PIN Page", "Don't use URL as a Trigger"],
            actions=["Type the PIN '1234' and press 'Enter'"],
        ),
        StatePrompt(
            name="On the Disney Plus Home Page (When Logged In)",
            description="Go to the ESPN Channel After Logging In In the Home Page",
            triggers=["If it is on the Home Page ONLY CHECK BY URL"],
            actions=["Press on the ESPN Channel"],
        ),
        StatePrompt(    
            name="On ESPN Channel",
            description="On ESPN Channel, Go to the First Movie/Show on the 'Studio Show' Section",
            triggers=["If it is has 'ESPN' in the page"],
            actions=["Scroll down to and click on the First 'Studio Show' Video and Terminate"],
        ),
        StatePrompt(
            name="On the Movie/Show Page",
            description="Press the Play Button on the Movie Page",
            triggers=["If it is on the Movie/Show Page (See If There is the Key Word 'Suggested' and 'Details' as a Trigger)", "Don't use URL as a Trigger"],
            actions=["Press Tab, Press Enter And Enter Again to Go in the Video Player", "Press Space", "Click on 0.2 of the Slider", "Wait 5 Seconds", "Click on 0.4 of the Slider", "Wait 5 Seconds", "Click on 0.6 of the Slider", "Wait 5 Seconds"],
            end_state="Action Completed"
        ),
    ]

    parameters = {
        
    }
    start_time = time.perf_counter()
    result = state_agent.run(prompt, states, parameters, use_llm=True)
    elapsed_secs = time.perf_counter() - start_time
    print(f"State machine build time: {elapsed_secs:.2f} seconds")

    if input("Save the states? (y/n): ") == "y":
        with open("streaming/states/6-disney-plus-espn.json", "w") as f:
            json.dump(result["states"], f)

    print("Executed:", result["executed"])
    print("Success:", result["success"])
    print("Error:", result["error"])
    print("Message:", result["message"])
    print("States:", result["states"])