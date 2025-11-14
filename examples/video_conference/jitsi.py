"""This example illustrates accessing a Jitsi Meet room via NetGent. It highlights entering the meeting name, toggling media controls, and observing the conference interface.
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
            actions=["Go to https://meet.jit.si/"]
        ),
        StatePrompt(
            name="On Jitsi Join Page",
            description="On Jitsi Join Page",
            triggers=["If it is on the Jitsi Join Page"],
            actions=["First, Join the meeting as ", "Next, in the meeting, click the Camera and Microphone icon"],
            end_state="Jitsi Video Conference Screen"
        ),
    ]

try:
    with open("examples/video_conference/jitsi/results/jitsi_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("examples/video_conference/jitsi/results", exist_ok=True)
with open("examples/video_conference/jitsi/results/jitsi_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)