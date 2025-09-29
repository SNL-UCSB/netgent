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
        with open("conference/states/ring-central.json", "r") as f:
            states = json.load(f)
    except:
        states = []
    prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["Go to https://video.ringcentral.com/join"]
        ),
        StatePrompt(
            name="On RingCentral Join Page",
            description="On RingCentral Join Page",
            triggers=["If it is on the RingCentral Join Page"],
            actions=["[1] Type '114715853207' for the meeting code and press 'Join'", 'Then, set the name to "SNL Client" to join the meeting'],
        ),
        StatePrompt(
            name="On RingCentral Video Conference Screen",
            description="On RingCentral Video Conference Screen",
            triggers=["If it is on the RingCentral Video Conference Screen"],
            actions=["[1] Press 'Join by Computer Audio' button and then close any popups", "[2] Press the microphone and camera icon to toggle them on or off"],
            end_state="RingCentral Video Conference Screen"
        ),
    ]

    parameters = {
        
    }
    start_time = time.perf_counter()
    result = state_agent.run(prompt, states, parameters, use_llm=True)
    elapsed_secs = time.perf_counter() - start_time
    print(f"State machine build time: {elapsed_secs:.2f} seconds")

    if input("Save the states? (y/n): ") == "y":
        with open("conference/states/ring-central.json", "w") as f:
            json.dump(result["states"], f)

    print("Executed:", result["executed"])
    print("Success:", result["success"])
    print("Error:", result["error"])
    print("Message:", result["message"])
    print("States:", result["states"])