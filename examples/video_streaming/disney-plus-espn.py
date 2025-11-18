"""This example demonstrates a Disney+ (ESPN hub) session captured by NetGent. It highlights the login flow, profile selection, and the actions that would occur when authenticated playback is available.
"""
import json
import os
from netgent import NetGent, StatePrompt
from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()
agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2), llm_enabled=True)


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
            actions=["Close Modal If There Is One", "Press the Login Button"],
        ),
        StatePrompt(
            name="Login to Account",
            description="On Login",
            triggers=["If On Login Page (Find Login Text for the Trigger)"],
            actions=["[1] Type the Email is ", "[2] Pressing the button 'Continue'", "[3] Type the password '' (MAKE SURE YOU DO THIS BEFORE PRESSING THE BUTTON 'Log In')", "[4] press the button 'Log In'"]
        ),
        StatePrompt(
            name="On Select Profile",
            description="On Select Profile",
            triggers=["If 'Who's watching?' is on the page"],
            actions=["Select the Profile ''"]
        ),
        StatePrompt(
            name="On the One Time Code Page",
            description="On the One Time Code Page After Logging In",
            triggers=["If it is on the One Time Code Page", "Don't use URL as a Trigger"],
            actions=["Do Nothing. JUST Terminate"],
            end_state="One Time Code Needed"
        ),
        StatePrompt(
            name="On the Profile PIN Page",
            description="On the Profile PIN Page",
            triggers=["If it is on the Profile PIN Page", "Don't use URL as a Trigger"],
            actions=["Type the PIN '' and press 'Enter'"]
        ),
        StatePrompt(
            name="On the Disney Plus Home Page (When Logged In)",
            description="Go to the Show After Logging In In the Home Page",
            triggers=["If it is on the Home Page ONLY CHECK BY URL"],
            actions=["[1] Navigate to https://www.disneyplus.com/brand/espn", "[2] Wait 5 seconds for the ESPN hub to finish loading"]
        ),
        StatePrompt(    
            name="On ESPN Channel",
            description="On ESPN Channel, Go to the First Movie/Show on the 'Studio Show' Section",
            triggers=["If it is has 'ESPN' in the page"],
            actions=["Scroll down to find the 'Studio Show' section", "Click on the First 'Studio Show' Video"],
        ),
        StatePrompt(
            name="On the Movie/Show Page",
            description="Press the Play Button on the Movie Page",
            triggers=["If it is on the Movie/Show Page (See If There is the Key Word 'Suggested' and 'Details' as a Trigger)", "Don't use URL as a Trigger"],
            actions=["Press Tab, Press Enter And Enter Again to Go in the Video Player", "Press Space", "Click on 0.2 of the Slider", "Wait 5 Seconds", "Click on 0.4 of the Slider", "Wait 5 Seconds", "Click on 0.6 of the Slider", "Wait 5 Seconds"],
            end_state="Action Completed"
        ),
    ]

try:
    with open("examples/video_streaming/disney-plus-espn/results/disney-plus-espn_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("examples/video_streaming/disney-plus-espn/results", exist_ok=True)
with open("examples/video_streaming/disney-plus-espn/results/disney-plus-espn_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)