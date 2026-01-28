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
        description="Navigate to Archtop Fiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://shopwvt.archtopfiber.com/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the Archtop Fiber page",
        triggers=["If you see 'Please enter your address below'"],
        actions=[
            "FOLLOW THESE INSTRUCTIONS CLOSELY", 
            "Scroll down",
            "Type `%address%` into the input field", 
            "Type `%zip_code%` into the zip code", 
            "Type `%state%` into the state field", 
            "Type `%city%` into the city field",
            "Choose RESIDENTIAL",
            "Click submit to confirm selection", 
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address location",
        triggers=["If you see 'Verify that the marker below is the correct location for your address'"],
        actions=["Scroll down", "press tab and enter", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
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
        description="Service not available (e.g Hmm... looks like we had trouble recognizing your address. Give us a quick call at 844-832-7823)",
        triggers=["If you see 'Hmm... looks like we had trouble recognizing your address. Give us a quick call at 844-832-7823'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

addresses = [
    {"address": "15802 N 62ND ST", "city": "SCOTTSDALE", "state": "AZ", "zip_code": "85254"},
    {"address": "4 1/2 12TH ST NW", "city": "ROCHESTER", "state": "MN", "zip_code": "55901"},
    {"address": "G1027 W HEMPHILL RD", "city": "FLINT", "state": "MI", "zip_code": "48507"},
    {"address": "B ST", "city": "COLORADO SPRINGS", "state": "CO", "zip_code": "80906"},
    {"address": "J 5TH ST", "city": "COVINGTON", "state": "LA", "zip_code": "70433"}
]

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), llm_enabled=True)

try:
    with open("examples/isps/results/archtopfiber_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']
zip_code = row_data['zip_code']
state = row_data['state']
city = row_data['city']

print(f"Address: {address}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address,
        "zip_code": zip_code,
        "state": state,
        "city": city
    },
    save_content_dir="examples/isps/save/archtopfiber",
    session="archtopfiber"
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/archtopfiber_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)