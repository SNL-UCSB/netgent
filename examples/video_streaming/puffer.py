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
    browser_manager = BrowserManager(human_movement=True, shake=True)
    judge_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2, thinking_budget=0, cache=False)
    browser_llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2, thinking_budget=0, cache=False)
    state_agent = StateAgent(judge_llm, browser_llm, browser_manager, {"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 8, "action_period": 2})
    try:
        with open("streaming/states/puffer.json", "r") as f:
            states = json.load(f)
    except:
        states = []
    
    prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["Go to https://puffer.stanford.edu/accounts/login"]
        ),
        StatePrompt(
            name="On Puffer Login Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["On login page, Username: 'snlclient1' and Password: 'SNL.12345', click the checkbox and press 'Login'"]
        ),
        StatePrompt(
            name="On Puffer Channel Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["[0] Click 'Watch TV' button", "[1] Wait for 5 seconds", "[2] Click on the 'Fox' channel", "[3] Wait for 5 seconds", "[4] Terminate"],
            end_state="Puffer Channel Page"
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
        with open("streaming/states/puffer.json", "w") as f:
            json.dump(result["states"], f)

    print("Executed:", result["executed"])
    print("Success:", result["success"])
    print("Error:", result["error"])
    print("Message:", result["message"])
    print("States:", result["states"])