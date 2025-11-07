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
            actions=["Go to https://www.disneyplus.com/"]
        ),
        StatePrompt(
            name="On Disney Plus Home Page",
            description="On Disney Plus Home Page",
            triggers=["If 'Endless entertainment for all.' is on the page"],
            actions=["Press the Login Button"],
        ),
        StatePrompt(
            name="Login to Account",
            description="On Login",
            triggers=["If On Login Page (Find Login Text for the Trigger)"],
            actions=["[1] Type the Email is snlclient1@gmail.com", "[2] Pressing the button 'Continue'", "[3] Type the password 'password' (MAKE SURE YOU DO THIS BEFORE PRESSING THE BUTTON 'Log In')", "[4] press the button 'Log In'"],
        ),
        StatePrompt(
            name="On Select Profile",
            description="On Select Profile",
            triggers=["If 'Who's watching?' is on the page"],
            actions=["Select the Profile 'snlclient'"],
        ),
        StatePrompt(
            name="On the Disney Plus Home Page (When Logged In)",
            description="Go to the National Geographic Channel After Logging In In the Home Page",
            triggers=["If it is on the Home Page ONLY CHECK BY URL"],
            actions=["Press on the National Geographic Channel"],
        ),
        StatePrompt(
            name="On National Geographic Channel",
            description="On National Geographic Channel, Go to the First Movie/Show",
            triggers=["If it is has 'Featured' in the page"],
            actions=["Press on First Movie/Show"],
        ),
        StatePrompt(
            name="On the Movie/Show Page",
            description="Press the Play Button on the Movie Page",
            triggers=["If it is on the Movie/Show Page (See If There is the Key Word 'Suggested' and 'Details' as a Trigger)", "Don't use URL as a Trigger"],
            actions=["Press Tab, Press Enter And Enter Again to Go in the Video Player", "Click on 0.2 of the Slider", "Wait 5 Seconds", "Click on 0.4 of the Slider", "Wait 5 Seconds", "Click on 0.6 of the Slider", "Wait 5 Seconds"],
            end_state="Action Completed"
        ),
    ]
try:
    with open("streaming/disney-plus-national-geo/results/disney-plus-national-geo_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("streaming/disney-plus-national-geo/results", exist_ok=True)
with open("streaming/disney-plus-national-geo/results/disney-plus-national-geo_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)