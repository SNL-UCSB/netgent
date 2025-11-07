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
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["[1] Press 'Live on Twitch' link", "[2] Click on the First Video in the List", "[3] Pause and wait for 5 seconds ONLY ONCE", "[4] Unpause only once", "[5] Terminate the process as soon as the task is done"],
            end_state="Twitch Home Page"
        ),
    ]
try:
    with open("streaming/twitch/results/twitch_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("streaming/twitch/results", exist_ok=True)
with open("streaming/twitch/results/twitch_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)