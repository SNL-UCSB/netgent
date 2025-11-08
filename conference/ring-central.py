"""This example demonstrates joining a RingCentral video session with NetGent. It visits the join page, points out the meeting code and name fields, and documents actions once the conference loads.
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
            actions=["Go to https://video.ringcentral.com/join"]
        ),
        StatePrompt(
            name="On RingCentral Join Page",
            description="On RingCentral Join Page",
            triggers=["If it is on the RingCentral Join Page"],
            actions=["[1] Type '' for the meeting code and press 'Join'", 'Then, set the name to "" to join the meeting'],
        ),
        StatePrompt(
            name="On RingCentral Video Conference Screen",
            description="On RingCentral Video Conference Screen",
            triggers=["If it is on the RingCentral Video Conference Screen"],
            actions=["[1] Press 'Join by Computer Audio' button and then close any popups", "[2] Press the microphone and camera icon to toggle them on or off"],
            end_state="RingCentral Video Conference Screen"
        ),
    ]

try:
    with open("conference/ring-central/results/ring-central_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("conference/ring-central/results", exist_ok=True)
with open("conference/ring-central/results/ring-central_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)