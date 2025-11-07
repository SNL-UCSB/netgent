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
            actions=["Go to https://www.aparat.com/aparat"]
        ),
        StatePrompt(
            name="On Aparat Home Page",
            description="On Aparat Home Page",
            triggers=["If 'Aparat' is on the page"],
            actions=["Search for 'Seal' in the search bar and press Enter, and click on the first result"],
        ),
        StatePrompt(
            name="On the Movie/Show Page",
            description="Press the Play Button on the Movie Page",
            triggers=["If it is on the Movie/Show Page", "ONLY USE THE ELEMENTS AS A TRIGGER", "Don't use URL or text as a Trigger"],
            actions=["Wait for the ad to finish and the video to load", "Click on 0.2 of the Slider", "Wait 5 Seconds", "Click on 0.4 of the Slider", "Wait 5 Seconds", "Click on 0.6 of the Slider", "Wait 5 Seconds", "ONLY DO THESE ACTIONS"],
            end_state="Action Completed"
        ),
    ]


try:
    with open("streaming/aparat/results/aparat_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("streaming/aparat/results", exist_ok=True)
with open("streaming/aparat/results/aparat_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)