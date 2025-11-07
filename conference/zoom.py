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
            actions=["Go to https://app.zoom.us/wc"]
        ),
        StatePrompt(
            name="On Zoom Home Page",
            description="On Zoom Home Page",
            triggers=["If 'Zoom' is on the page"],
            actions=["Press 'Join a Meeting' and then type the Meeting ID '964 911 6513' and password is '1nUkh1', name is 'SNL' and press 'Join'"],
        ),
        StatePrompt(
            name="Error",
            description="Error",
            triggers=["If 'Error' is on the page"],
            actions=["Terminate"],
            end_state="Error"
        ),
        StatePrompt(
            name="On Zoom Meeting Conference Screen",
            description="On the Zoom Meeting Conference Screen",
            triggers=["If it is on the Zoom Meeting Conference Screen"],
            actions=["Turn on the Camera and Microphone"],
            end_state="Zoom Meeting Conference Screen"
        )
    ]

try:
    with open("conference/zoom/results/zoom_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("conference/zoom/results", exist_ok=True)
with open("conference/zoom/results/zoom_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)