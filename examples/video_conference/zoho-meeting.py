"""This example demonstrates joining a Zoho Meeting session with NetGent. It highlights the meeting URL and attendee name fields, then walks through the waiting room and conference stages.
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
            actions=["Go to https://www.zoho.com/meeting/join/"]
        ),
        StatePrompt(
            name="On Webex Join Page",
            description="On Webex Join Page",
            triggers=["If it is on the Webex Join Page"],
            actions=["Type Put the meeting link in the '' field and '' in the 'Name' field, and press 'Join'. Tranverse the UI as a proper human"],
        ),
        StatePrompt(
            name="Error",
            description="Error",
            triggers=["If 'Error' is on the page"],
            actions=["Terminate"],
            end_state="Error"
        ),
        StatePrompt(
            name="On Zoho Waiting Room",
            description="On the Zoho Waiting Room",
            triggers=["If it is on the Zoho Waiting Room"],
            actions=["wait for 5 seconds"],
        ),
        StatePrompt(
            name="On Zoho Meeting Conference Screen",
            description="On the Zoho Meeting Conference Screen",
            triggers=["If it is on the Zoho Meeting Conference Screen"],
            actions=["Turn on the Camera and Microphone"],
            end_state="Zoho Meeting Conference Screen"
        )
    ]

try:
    with open("examples/video_conference/zoho-meeting/results/zoho-meeting_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("examples/video_conference/zoho-meeting/results", exist_ok=True)
with open("examples/video_conference/zoho-meeting/results/zoho-meeting_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)