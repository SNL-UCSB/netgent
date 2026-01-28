import json
import os
import sys
from netgent.errors import NetGentError
from bqtdb.main import BQTDatabase
from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from faker import Faker

load_dotenv()
fake = Faker()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to MyCentral new connection page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://mycentral.smarthub.coop/ui/#/marketing/serviceLocation word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Please enter your service address below'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into the input field and press enter", "Press Up and Down arrow keys to select the correct address", "Scroll down to press the 'Continue' button", "Click the 'Continue' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available in area",
        triggers=["If you see 'Please enter your service address below' and 'We are still working to build out our network in your area'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Fiber services available",
        triggers=["If you see 'Please enter your service address below' and 'Fiber services are now available'"],
        actions=["Scroll down to the 'Continue' button", "Click the 'Continue' button", "TERMINATE AT THIS POINT"],
    ),
]

addresses = []
with BQTDatabase() as db:
    rows = db.query("SELECT * FROM bqtplus.xfinity_addresses LIMIT 1000")
    for row in rows:
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
            
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}, {zip_code}"
        only_address = row['PropertyFullStreetAddress']
        city = row['PropertyCity']
        state = row['PropertyState']
        addresses.append({
            'address': full_address,
            'only_address': only_address,
            'city': city,
            'state': state,
            'zip_code': zip_code
        })

# Pick an address
address_data = addresses[4] 
address = address_data['address']
only_address = address_data['only_address']
city = address_data['city']
zip_code = address_data['zip_code']

# Generate fake contact info using Faker
name_f = fake.first_name()
name_l = fake.last_name()
phone_num = fake.numerify("##########")
email = fake.email()

print(f"Address: {address}, City: {city}, Zip: {zip_code}")

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

state_repository = []

if os.path.exists("examples/isps/results/mycentral_result.json"):
    with open("examples/isps/results/mycentral_result.json", "r") as f:
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
        "only_address": only_address, 
        "city": city, 
        "state": address_data['state'], 
        "zip_code": zip_code,
        "email": email
    },
    session="mycentral",
    save_content_dir="examples/isps/save/mycentral"
)

input("Press Enter to continue...")

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/mycentral_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)