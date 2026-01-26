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
        description="Navigate to Foothills page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://foothills.net/get-service/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the Foothills page",
        triggers=["If you see 'To check for service availability in your area, please enter your physical address below.' and URL is `https://foothills.net/get-service/#NoServicesAvailable`"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Scroll down", "Type `%address%` into the input field", "Type `%zip_code%` into the input field", "Click the 'Continue' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Build your bundle",
        triggers=["If you see 'Build your bundle'"],
        actions=["DON'T DO ANYTHING, JUST TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans"
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available - (e.g. 'We don't recognize that address.')",
        triggers=["If you see 'We don't recognize that address.'"],
        actions=["DON'T DO ANYTHING, JUST TERMINATE AT THIS POINT"],
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
address_data = addresses[4] 
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

if os.path.exists("examples/isps/results/foothills_result.json"):
    with open("examples/isps/results/foothills_result.json", "r") as f:
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
    session="foothills"
)

input("Press Enter to continue...")

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/foothills_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
