"""This example demonstrates NetGent performing a simple Instagram scroll session. It navigates to the homepage, passes the login gate, and scrolls the feed to mimic lightweight engagement.
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
            actions=["Go to https://www.instagram.com/"]
        ),
        StatePrompt(
            name="Login to Account",
            description="On Login",
            triggers=["If On Login Page (Find Login Text for the Trigger)"],
            actions=["[1] Type the Email is ", "[2] Type the password '' (MAKE SURE YOU DO THIS BEFORE PRESSING THE BUTTON 'Log In')", "[3] press the button 'Log In'"]
        ),
        StatePrompt(
            name="Save Information",
            description="On Save Information Page",
            triggers=["If On Save Information Page (Find Save Information Text for the Trigger)"],
            actions=["[1] press the button 'No Right Now'"],
        ),
        StatePrompt(
            name="On Instagram Home Page",
            description="On Instagram Home Page",
            triggers=["If On Instagram Home Page (Find Home Text for the Trigger)"],
            actions=["Browse Instagram as a human (scroll down for around 6 times with the scroll amount being 20. press on the like button which is the heart icon)"],
            end_state="Action Completed"
        ),
    ]

try:
    with open("examples/web_browsing/instagram-scroll/results/instagram-scroll_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("examples/web_browsing/instagram-scroll/results", exist_ok=True)
with open("examples/web_browsing/instagram-scroll/results/instagram-scroll_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)