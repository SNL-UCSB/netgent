import json
import os
import sys
from netgent.errors import NetGentError


from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to SECOM page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://secom.crowdfiber.com/front_end word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the SECOM page",
        triggers=["If you see 'Search For Your Address'"],
        actions=[
            "FOLLOW THESE INSTRUCTIONS CLOSELY", 
            "Type `%address%` into the 'Search For Your Address' input field", 
            "Type `%zip_code%` into the 'Zip Code' input field",
            "Press on Service Type dropdown",
            "Down arrow key 1 time and press enter",
            "Click the 'GO' button", 
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address location",
        triggers=["If you see 'Verify that the marker below is the correct location for your address'"],
        actions=["Scroll down", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="INTERNET_AVAILABLE",
        description="Service available - enter contact info",
        triggers=["If you see 'SECOM is in your neighborhood. Order now!'"],
        actions=[
            "Scroll to put this contact information in the form",
            "Click the 'Next' button",
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Build your bundle",
        triggers=["If you see 'Build your bundle'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available (e.g. 'Make It Possible!')",
        triggers=["Get the Text from the page like 'Make It Possible!' and 'At this time, your home is not in a fiber area.   We may be able to provide wireless services until we receive more fiber interest.  By expressing interest and providing your information below, you will be helping us to determine where to go next.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

addresses = [
    {"address": "15802 N 62ND ST, SCOTTSDALE, AZ", "zip_code": "85254"},
    {"address": "4 1/2 12TH ST NW, ROCHESTER, MN", "zip_code": "55901"},
    {"address": "B ST, COLORADO SPRINGS, CO", "zip_code": "80906"},
    {"address": "J 5TH ST, COVINGTON, LA", "zip_code": "70433"},
    {"address": "3282 Scottsville Rd, Charlottesvle, VA", "zip_code": "22902"}
]

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), llm_enabled=True)

try:
    with open("examples/isps/results/secom_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']
zip_code = row_data['zip_code']

print(f"Address: {address}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address,
        "zip_code": zip_code
    },
    save_content_dir="examples/isps/save/secom",
    session="secom"
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/secom_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)