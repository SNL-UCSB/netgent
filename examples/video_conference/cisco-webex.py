"""This example models joining a Cisco Webex conference with NetGent. It opens the join portal, records where meeting details belong, and shows the minimal interaction required to wait for host admission.
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
            triggers=["ONLY CHOSE THE TRIGGER URL"],
            actions=["Go to https://web.webex.com/dashboard"]
        ),
        StatePrompt(
            name="On Cisco Webex Sign In Page",
            description="On Webex Sign In Page",
            triggers=["If 'Webex Sign In' is on the page"],
            actions=['Accept the cookies', "Press 'Join a Meeting' and then type the Meeting ID '', name '' and press 'Join'", "And wait for the meeting to start"],
        ),
        StatePrompt(
            name="Error",
            description="Error",
            triggers=["If 'Error' is on the page"],
            actions=["Terminate"],
            end_state="Error"
        ),
        StatePrompt(
            name="On Cisco Webex Meeting Conference Screen",
            description="On the Cisco Webex Meeting Conference Screen",
            triggers=["If it is on the Cisco Webex Meeting Conference Screen"],
            actions=["TERMINATE AS SOON AS ACTION IS DONE"],
            end_state="Cisco Webex Meeting Conference Screen"
        )
    ]

try:
    with open("examples/video_conference/cisco-webex/results/cisco-webex_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("examples/video_conference/cisco-webex/results", exist_ok=True)
with open("examples/video_conference/cisco-webex/results/cisco-webex_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)