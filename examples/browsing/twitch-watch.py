"""This example directs NetGent to Twitch's homepage and featured streams. It illustrates navigating to live content, pausing briefly, and resuming playback to mimic a viewer session.
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
            actions=["Go to https://www.twitch.tv/"]
        ),
        StatePrompt(
            name="On Twitch Home Page",
            description="On Twitch Home Page",
            triggers=["If The Text is 'Live on Twitch', use that as a trigger"],
            actions=["Press on the First Stream on Live on Twitch", "Watch the Stream for 10 Seconds"],
            end_state="Action Completed"
        ),
    ]



try:
    with open("browsing/twitch-watch/results/twitch-watch_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("browsing/twitch-watch/results", exist_ok=True)
with open("browsing/twitch-watch/results/twitch-watch_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)