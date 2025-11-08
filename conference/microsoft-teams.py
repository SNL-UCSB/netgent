"""This example guides NetGent through Microsoft Teams on the web. It shows the login prompt, identifies where meeting credentials would be supplied, and navigates to the Teams home interface.
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
            actions=["Go to https://teams.microsoft.com/v2/"]
        ),
        StatePrompt(
            name="On Microsoft Login",
            description="Login to Microsoft",
            triggers=["If it is on the Microsoft Login Page. Get elements and text from the page"],
            actions=["Type '' in the email field and password is ''. Transverse to find these information and make sure it is on the stay sign in option"],
        ),
        StatePrompt(
            name="On Microsoft Teams Home Page",
            description="On Microsoft Teams Home Page",
            triggers=["If 'Microsoft Teams' is on the page"],
            actions=["Press 'Meet' on the Sidebar, 'Join a Meeting ID' and then type the Meeting ID '' and password '', and press 'Join meeting'"],
        ),
        StatePrompt(
            name="Error",
            description="Error",
            triggers=["If 'Error' is on the page"],
            actions=["Terminate"],
            end_state="Error"
        ),
        StatePrompt(
            name="On Teams Waiting Room",
            description="On the Teams Waiting Room",
            triggers=["If it is on the Teams Waiting Room"],
            actions=["wait for 5 seconds"],
        ),
        StatePrompt(
            name="On Teams Meeting Conference Screen",
            description="On the Teams Meeting Conference Screen",
            triggers=["If it is on the Teams Meeting Conference Screen"],
            actions=["Turn on the Camera and Microphone"],
            end_state="Teams Meeting Conference Screen"
        )
    ]

try:
    with open("conference/microsoft-teams/results/microsoft-teams_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("conference/microsoft-teams/results", exist_ok=True)
with open("conference/microsoft-teams/results/microsoft-teams_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)