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
            actions=["Go to https://whereby.com/snlclient1"]
        ),
        StatePrompt(
            name="On Whereby Join Page",
            description="On Whereby Join Page",
            triggers=["If it is on the Whereby Join Page"],
            actions=["First, Join the meeting", "Next, in the meeting, turn on the Camera and Microphone"],
            end_state="Whereby Video Conference Screen"
        ),
    ]

try:
    with open("conference/whereby/results/whereby_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("conference/whereby/results", exist_ok=True)
with open("conference/whereby/results/whereby_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)