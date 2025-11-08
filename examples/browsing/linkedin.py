"""This example shows NetGent exploring LinkedIn's homepage. It navigates to the login screen, acknowledges protected actions, and scrolls the feed to gather publicly visible content.
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
            actions=["Go to https://www.linkedin.com/login"]
        ),
         StatePrompt(
            name="If on LinkedIn Login Page",
            description="If on LinkedIn Login Page",
            triggers=["If on LinkedIn Login Page"],
            actions=["[1] Type the Email is ", "[2] Type the password '' (MAKE SURE YOU DO THIS BEFORE PRESSING THE BUTTON 'Log In')", "[3] press the button 'Log In'"]
        ),
        StatePrompt(
            name="On LinkedIn Home Page",
            description="On LinkedIn Home Page",
            triggers=["If On LinkedIn Home Page (Find Home Text for the Trigger)"],
            actions=["Browse LinkedIn as a human (scroll down for 6 times with the scroll amount being 20)", "If the 'See more posts' button is on the screen, press it, then you continue the task you are given"],
            end_state="Action Completed"
        ),
    ]


try:
    with open("browsing/linkedin/results/linkedin_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("browsing/linkedin/results", exist_ok=True)
with open("browsing/linkedin/results/linkedin_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)