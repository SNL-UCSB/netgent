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
        with open("streaming/states/tubi.json", "r") as f:
            states = json.load(f)
    except:
        states = []
    
    prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["Go to https://tubitv.com/?"]
        ),
        StatePrompt(
            name="On Tubi Home Page",
            description="On Tubi Home Page",
            triggers=["If on the home page"],
            actions=["Search for 'Lego' in the search bar and press on the first result"],
        ),
        StatePrompt(
            name="On the Movie/Show Page",
            description="Press the Play Button on the Movie Page",
            triggers=["If it is on the Movie/Show Page", "ONLY USE THE ELEMENTS AS A TRIGGER", "Don't use URL as a Trigger"],
            actions=["wait for the video to load and then click on the play button", "Click on 0.2 of the Slider", "Wait 5 Seconds", "Click on 0.4 of the Slider", "Wait 5 Seconds", "Click on 0.6 of the Slider", "Wait 5 Seconds"],
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
        with open("streaming/states/tubi.json", "w") as f:
            json.dump(result["states"], f)

    print("Executed:", result["executed"])
    print("Success:", result["success"])
    print("Error:", result["error"])
    print("Message:", result["message"])
    print("States:", result["states"])