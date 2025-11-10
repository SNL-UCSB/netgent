"""This example instructs NetGent on starting a Talky room. It opens the service, provides a placeholder room name, and describes how to join and manage audio/video controls.
"""
import json
import os
from netgent import NetGent, StatePrompt
from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()
agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2), llm_enabled=True, user_data_dir="examples/user_data")


prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["Go to https://talky.io/"]
        ),
        StatePrompt(
            name="On Talky Home Page",
            description="On Talky Home Page",
            triggers=["If it is on the Talky Home Page"],
            actions=["[1] Type '' for the meeting code and press 'Start Meeting'"],
        ),
        StatePrompt(
            name="On Talky Video Conference Screen",
            description="On Talky Video Conference Screen",
            triggers=["If it is on the Talky Video Conference Screen"],
            actions=["[1] Scroll down ONLY ONCE and press the 'Join' button", "[2] Scroll down up ONLY ONCE and press the microphone and camera icon to toggle them on or off"],
            end_state="Talky Video Conference Screen"
        ),
    ]

try:
    with open("conference/talkly/results/talkly_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("conference/talkly/results", exist_ok=True)
with open("conference/talkly/results/talkly_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)