import json
import os
import sys
from netgent.errors import NetGentError


from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
load_dotenv()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to VNET Fiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.vnetfiber.com/residential/check-availability/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the VNET Fiber page",
        triggers=["If you see 'Please enter your address below'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Press 'Check Address' button", "Type `%address%` into the input field", "Type `%zip_code%` into the input field", "Press down and enter to select the first option", "Click 'Lets Go' to confirm selection", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address location",
        triggers=["If you see 'Verify that the marker below is the correct location for your address'"],
        actions=["Scroll down", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Build your bundle",
        triggers=["If you see 'Build your bundle'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans"
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available - (e.g. Make It Possible!)",
        triggers=["Get the Text from the page like 'Make It Possible!' and 'While your address is not in an area that we have plans to serve at this time, if we receive enough expressions of interest in your neighborhood, we may be able to provide our services to you in the future."],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
    ),
]

addresses = [
    {"address": "15802 N 62ND ST, SCOTTSDALE, AZ", "zip_code": "85254"},
    {"address": "4 1/2 12TH ST NW, ROCHESTER, MN", "zip_code": "55901"},
    {"address": "B ST, COLORADO SPRINGS, CO", "zip_code": "80906"},
    {"address": "3 Lake Front Dr", "zip_code": "16507"},
    {"address": "J 5TH ST, COVINGTON, LA", "zip_code": "70433"}
]

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), llm_enabled=True)

try:
    with open("examples/isps/results/vnetfiber_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
zip_code = row_data['zip_code']
address = row_data['address']

print(f"Address: {address}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address,
        "zip_code": zip_code
    }
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/vnetfiber_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
