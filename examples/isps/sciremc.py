import json
import os
import sys
from netgent.errors import NetGentError

# from bqtdb.main import BQTDatabase # Commented out as we don't have specific BQT table for SCI REMC
from faker import Faker

from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()

fake = Faker()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to SCI REMC CrowdFiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://join.sciremc.com/front_end/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Please enter your address below'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into the input field", "Type `%zip_code%` into the input field", "press 'select market' button", "press down and enter to confirm selection", "Click the 'Go' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address location - 'if you see 'Verify that the marker below is the correct location for your address'",
        triggers=["If you see 'Verify that the marker below is the correct location for your address'"],
        actions=["Scroll down", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="INTERNET_AVAILABLE",
        description="Service available - enter contact info",
        triggers=["If you see 'SCI REMC is in your neighborhood. Order now!'"],
        actions=[
            "Scroll to put this contact information in the form",
            "Type `%email%`",
            "Type `%name_f%`",
            "Type `%name_l%`",
            "Type `%phone_num%`",
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
        description="Service not available",
        triggers=["If you see 'Aww shucks! Our service isn't available.'"],
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

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

try:
    with open("examples/isps/results/sciremc_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']
zip_code = row_data['zip_code']

# Generate fake contact info using Faker
name_f = fake.first_name()
name_l = fake.last_name()
phone_num = fake.numerify("##########")
email = fake.email()

print(f"Address: {address}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address, 
        "zip_code": zip_code,
        "name_f": name_f,
        "name_l": name_l,
        "phone_num": phone_num,
        "email": email
    },
    session="sciremc",
    save_content_dir="examples/isps/save/sciremc"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/sciremc_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)