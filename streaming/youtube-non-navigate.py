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
            actions=["Go to https://www.youtube.com/watch?v=3BFUm3m3kyE"]
        ),
        StatePrompt(
            name="On the Video Player",
            description="Press the Play Button on the Video Player",
            triggers=["Only use URL as a Trigger"],
            actions=["Go to 20% of the Video Slider", "Wait 5 Seconds", "Go to 40% of the Video Slider", "Wait 5 Seconds", "Go to 60% of the Video Slider"],
            end_state="Action Completed"
        ),
    ]


try:
    with open("streaming/youtube-non-navigate/results/youtube-non-navigate_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("streaming/youtube-non-navigate/results", exist_ok=True)
with open("streaming/youtube-non-navigate/results/youtube-non-navigate_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)