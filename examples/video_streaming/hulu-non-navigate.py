"""This example showcases NetGent visiting Hulu's web experience. It covers the welcome screen, login transition, and the playback flow while flagging credential-protected actions.
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
            actions=["Go to https://www.hulu.com", "TERMINATE"]
        ),
        StatePrompt(
            name="On the Welcome Page",
            description="On the Welcome Page",
            triggers=["If 'Welcome to Hulu' is on the page. (GET THE TEXT: 'Get Hulu, Disney+, and ESPN+, all with ads, for $16.99/mo.')"],
            actions=["[1] If there is a pop-up or modal visible, search for a button with text 'Close', 'X', or aria-label containing 'close' or 'dismiss'", "[2] Find the close button element using CSS selector like button[aria-label*='close'], button[aria-label*='dismiss'], or button with class containing 'close'", "[3] Click on that specific close button element - do NOT click on random coordinates, click on the actual button element", "[4] If no close button is found by selector, press Escape key", "[5] Wait 3 seconds after attempting to close", "[6] Press Tab and Press Enter to Go in the Login Page", "TERMINATE"],
        ),
        StatePrompt(
            name="Login to Account",
            description="On Login",
            triggers=["If On Login Page (Find Login Text for the Trigger)"],
            actions=["[1] Type the Email is ", "[2] Pressing the button 'Continue'", "[3] Type the password '' (MAKE SURE YOU DO THIS BEFORE PRESSING THE BUTTON 'Log In')", "[4] press the button 'Log In'", "TERMINATE"],
        ),
        StatePrompt(
            name="On Select Profile",
            description="On Select Profile",
            triggers=["If 'Who's watching?' is on the page"],
            actions=["Select the Profile ''", "TERMINATE"],
        ),
        StatePrompt(
            name="On the Hulu Home Page (When Logged In)",
            description="Go to the Show After Logging In In the Home Page",
            triggers=["If it is on the Home Page (Showing Recommended For You) And On 'https://www.hulu.com/hub/home'"],
            actions=["[1] If there is a pop-up or modal visible, search for a button with text 'Close', 'X', or aria-label containing 'close' or 'dismiss'", "[2] Find the close button element using CSS selector like button[aria-label*='close'], button[aria-label*='dismiss'], or button with class containing 'close'", "[3] Click on that specific close button element - do NOT click on random coordinates, click on the actual button element", "[4] If no close button is found by selector, press Escape key", "[5] Wait 3 seconds after attempting to close", "[6] Go to https://www.hulu.com/series/91de62df-0394-4e17-85a8-e843bd730ede", "TERMINATE"],
        ),
        StatePrompt(
            name="On the Movie/Show Page",
            description="Press the Play Button on the Movie Page",
            triggers=["If it is on the Movie/Show Page (See If There is the Key Word 'Suggested' and 'Details' as a Trigger)", "Don't use URL as a Trigger"],
            actions=["[1] If there is a pop-up or modal visible, search for a button with text 'Close', 'X', or aria-label containing 'close' or 'dismiss'", "[2] Find the close button element using CSS selector like button[aria-label*='close'], button[aria-label*='dismiss'], or button with class containing 'close'", "[3] Click on that specific close button element - do NOT click on random coordinates, click on the actual button element", "[4] If no close button is found by selector, press Escape key", "[5] Wait 3 seconds after attempting to close", "[6] Press Tab THREE Times and Press Enter to Go in the Video Player", "[7] WAIT FOR THE ADS TO END", "[8] Click on 0.2 of the Slider", "[9] Wait 5 Seconds", "[10] Click on 0.4 of the Slider", "[11] Wait 5 Seconds", "[12] Click on 0.6 of the Slider", "[13] Wait 5 Seconds", "TERMINATE"],
            end_state="Action Completed"
        ),
    ]


try:
    with open("examples/video_streaming/hulu-non-navigate/results/hulu-non-navigate_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("examples/video_streaming/hulu-non-navigate/results", exist_ok=True)
with open("examples/video_streaming/hulu-non-navigate/results/hulu-non-navigate_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)