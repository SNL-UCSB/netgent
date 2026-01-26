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
        description="Navigate to GVTC new connection page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://gvtctx.smarthub.coop/Shop.html word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="On Initial Page of GVTC",
        description="Address not found or needs verification - (e.g. 'Shop for new service')",
        triggers=["If you see 'Shop for new service'"],
        actions=["Type `%email%` into the input field", "Press 'tab' to focus on the address field", "Type `%address%` into the input field", "Click the Submit' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available in area",
        triggers=["If you see 'Please enter your service address below' and 'We are still working to build out our network in your area'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Fiber services available - (e.g. 'Contact Us')",
        triggers=["If you see 'Contact Us'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans"
    ),
]

addresses = []
with BQTDatabase() as db:
    rows = db.query("SELECT * FROM bqtplus.xfinity_addresses LIMIT 1000")
    for row in rows:
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
            
        # SmartHub usually works well with "Address, City, State, Zip"
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}, {zip_code}"
        
        address_entry = {
            "address": full_address,
            "zip_code": zip_code
        }
        addresses.append(address_entry)

# Pick an address
address_data = addresses[3] 
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

if os.path.exists("examples/isps/results/gvtc_result.json"):
    with open("examples/isps/results/gvtc_result.json", "r") as f:
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
        "email": email,
    },
    session="gvtc"
)

input("Press Enter to continue...")

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/gvtc_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
