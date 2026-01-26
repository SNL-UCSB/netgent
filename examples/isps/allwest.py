import json
import os
import sys
from netgent.errors import NetGentError
from bqtdb.main import BQTDatabase
from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
from faker import Faker

load_dotenv()
fake = Faker()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to All West page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://shop.allwest.com/order/1 word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the All West page",
        triggers=["If you see 'Please enter your address below'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into the input field", "Click submit to confirm selection", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address location",
        triggers=["If you see 'Verify that the marker below is the correct location for your address'"],
        actions=["Scroll down", "press tab and enter", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="INTERNET_AVAILABLE",
        description="Service available - enter contact info",
        triggers=["If you see 'All West is in your neighborhood. Order now!'"],
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
        end_state="serviceable_with_plans"
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available (e.g. 'Contact Us')",
        triggers=["Get the Text from the page like 'Contact Us'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
    ),
]

addresses = []
with BQTDatabase() as db:
    rows = db.query("SELECT * FROM bqtplus.xfinity_addresses LIMIT 1000")
    for row in rows:
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
            
        address_entry = {
            "address": f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}",
            "zip_code": zip_code
        }
        addresses.append(address_entry)

# Pick an address
address_data = addresses[0] 
address = address_data['address']
zip_code = address_data['zip_code']

# Generate fake contact info using Faker
name_f = fake.first_name()
name_l = fake.last_name()
phone_num = fake.numerify("##########")
email = fake.email()

print(f"Address: {address}, Zip: {zip_code}")

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

state_repository = []

if os.path.exists("examples/isps/results/allwest_result.json"):
    with open("examples/isps/results/allwest_result.json", "r") as f:
        try:
            data = json.load(f)
            if "state_repository" in data:
                state_repository = data["state_repository"]
                print(f"Loaded {len(state_repository)} states from previous session")
        except:
            pass

result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address,
        "zip_code": zip_code,
    },
    session="allwest"
)

agent.set_state_wait_time(5)

input("Press Enter to continue...")

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/allwest_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
