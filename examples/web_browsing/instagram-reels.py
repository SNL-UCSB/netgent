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
    browser_manager = BrowserManager(human_movement=True, shake=False)
    judge_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2, thinking_budget=0, cache=False)
    browser_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2, thinking_budget=0, cache=False)
    state_agent = StateAgent(judge_llm, browser_llm, browser_manager, {"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 10, "action_period": 2})
    try:
        with open("browsing/states/instagram-reels.json", "r") as f:
            states = json.load(f)
    except:
        states = []
    
    prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["Go to https://www.instagram.com/"]
        ),
        StatePrompt(
            name="Login to Account",
            description="On Login",
            triggers=["If On Login Page (Find Login Text for the Trigger)"],
            actions=["[1] Type the Email is snlclient1@gmail.com", "[2] Type the password 'SNL.12345' (MAKE SURE YOU DO THIS BEFORE PRESSING THE BUTTON 'Log In')", "[3] press the button 'Log In'"],
        ),
        StatePrompt(
            name="Save Information",
            description="On Save Information Page",
            triggers=["If On Save Information Page (Find Save Information Text for the Trigger)"],
            actions=["[1] press the button 'No Right Now'"],
        ),
        StatePrompt(
            name="On Instagram Home Page",
            description="On Instagram Home Page",
            triggers=["If On Instagram Home Page (Find Home Text for the Trigger)"],
            actions=["Navigate to https://www.instagram.com/reels/", "On Instagram Reels, CAN YOU DO THESE ACTIONS FOR EXACTLY 4 TIMES: Go the Next Video (BY PRESSING THE DOWN ARROW BUTTON). YOU MUST DO THIS FOR EXACTLY 4 TIMES REPEATLY AND IF YOU ARE NOT ON THE REEL PAGE ANYMORE, TERMINATE THE TASK"],
            end_state="Action Completed"
        ),
    ]

    parameters = {
        
    }
    result = state_agent.run(prompt, states, parameters, use_llm=True)

    if input("Save the states? (y/n): ") == "y":
        with open("browsing/states/instagram-reels.json", "w") as f:
            json.dump(result["states"], f)

    print("Executed:", result["executed"])
    print("Success:", result["success"])
    print("Error:", result["error"])
    print("Message:", result["message"])
    print("States:", result["states"])