"""This example guides NetGent through the X (Twitter) login flow and home timeline. It documents the credential prompt and then scrolls and interacts with posts as an anonymized user.
"""
import json
from netgent import NetGent, StatePrompt
from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
load_dotenv()
agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2), llm_enabled=True)

prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["Go to https://x.com/login"]
        ),
         StatePrompt(
            name="If on X Login Page",
            description="If on X Login Page",
            triggers=["If on X Login Page"],
            actions=["[1] Type the Email is ", "[2] Type the password '' (MAKE SURE YOU DO THIS BEFORE PRESSING THE BUTTON 'Log In')", "[3] press the button 'Log In'"]
        ),
        StatePrompt(
            name="On X Home Page",
            description="On X Home Page",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["Browse X as a human (scroll down for around 6 times with the scroll amount being 20. press on the like button which is the heart icon)"],
            end_state="Action Completed"
        ),
    ]

try:
    with open("examples/web_browsing/X/results/X_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

# Clear state repository to start fresh each time (comment out if you want to keep previous states)
result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("examples/web_browsing/X/results", exist_ok=True)
with open("examples/web_browsing/X/results/X_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)