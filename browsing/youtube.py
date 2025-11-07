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
            actions=["Go to https://www.tiktok.com/login/phone-or-email/email"]
        ),
         StatePrompt(
            name="If on TikTok Login Page",
            description="If on TikTok Login Page",
            triggers=["If on TikTok Login Page"],
            actions=["[1] Type the Email is snlclient1@gmail.com", "[2] Type the password 'SNL.12345' (MAKE SURE YOU DO THIS BEFORE PRESSING THE BUTTON 'Log In')", "[3] press the button 'Log In'"]
        ),
        StatePrompt(
            name="If on TikTok Interest Page",
            description="If on TikTok Interest Page",
            triggers=["Anything on the TikTok Interest Pop Up. Don't use URL as a trigger"],
            actions=["Press the Skip Button"],
        ),
        StatePrompt(
            name="On TikTok For You Page",
            description="On TikTok For You Page",
            triggers=["If on TikTok For You Page"],
            actions=["Press the Down Arrow 6 Times", "Press the Like Button on the First Video"],
            end_state="Action Completed"
        ),
    ]


try:
    with open("browsing/youtube/results/youtube_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("browsing/youtube/results", exist_ok=True)
with open("browsing/youtube/results/youtube_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)