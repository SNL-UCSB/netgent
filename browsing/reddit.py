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
            actions=["Go to https://reddit.com"]
        ),
        StatePrompt(
            name="On Reddit Home Page",
            description="On Reddit Home Page",
            triggers=["If On Reddit Home Page (Find Home Text for the Trigger)"],
            actions=["Browse Reddit as a human (scroll down for around 6 times with the scroll amount being 20."],
            end_state="Action Completed"
        ),
    ]

try:
    with open("browsing/reddit/results/reddit_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("browsing/reddit/results", exist_ok=True)
with open("browsing/reddit/results/reddit_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)