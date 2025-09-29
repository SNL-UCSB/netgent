import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state_agent.state_agent.agent import StateAgent
from state_agent.state_agent.agent import StatePrompt
from langchain_google_vertexai import ChatVertexAI
from state_agent.actions.browser_manager import BrowserManager
import json
from dotenv import load_dotenv
load_dotenv()


if __name__ == "__main__": 
    browser_manager = BrowserManager(human_movement=True, shake=True, user_data_dir="./streaming/hulu-non-navigate-profile/")
    judge_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2, thinking_budget=0, cache=False)
    browser_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2, thinking_budget=0, cache=False)
    state_agent = StateAgent(judge_llm, browser_llm, browser_manager, {"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 8, "action_period": 2})
    try:
        with open("streaming/states/youtube.json", "r") as f:
            raise Exception("Test")
            states = json.load(f)
    except:
        states = []
    
    prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["Go to https://www.youtube.com/watch?v=3BFUm3m3kyE"]
        ),
        StatePrompt(
            name="On the Video Player",
            description="Press the Play Button on the Video Player",
            triggers=["Only use URL as a Trigger"],
            actions=["Go to 20% of the Video Slider", "Wait 5 Seconds", "Go to 40% of the Video Slider", "Wait 5 Seconds", "Go to 60% of the Video Slider"],
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
        with open("streaming/states/youtube.json", "w") as f:
            json.dump(result["states"], f)

    print("Executed:", result["executed"])
    print("Success:", result["success"])
    print("Error:", result["error"])
    print("Message:", result["message"])
    print("States:", result["states"])