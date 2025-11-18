"""This example captures the Google Meet join experience using NetGent. It documents the join form fields, notes credential placeholders, and walks through the steps leading to the waiting room.
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
            actions=["Go to https://workspace.google.com/products/meet/"]
        ),
        StatePrompt(
            name="On Google Meet Home Page",
            description="On Google Meet Home Page",
            triggers=["If 'Google Meet' is on the page"],
            actions=["Press 'Join a Meeting' and then type the Meeting ID '', then press 'tab' key and 'enter' key, the name is '' and press 'Join'", "Wait for Host to Approve You to Join the Meeting"],
        ),
        StatePrompt(
            name="Error",
            description="Error",
            triggers=["If 'Error' is on the page"],
            actions=["Terminate"],
            end_state="Error"
        ),
        StatePrompt(
            name="On Google Meet Meeting Conference Screen",
            description="On the Google Meet Meeting Conference Screen",
            triggers=["If it is on the Google Meet Meeting Conference Screen"],
            actions=["Turn on the Camera and Microphone"],
            end_state="Google Meet Meeting Conference Screen"
        )
    ]

try:
    with open("examples/video_conference/google-meet/results/google-meet_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("examples/video_conference/google-meet/results", exist_ok=True)
with open("examples/video_conference/google-meet/results/google-meet_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)