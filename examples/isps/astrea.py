import json
import os
import sys
from netgent.errors import NetGentError

from bqtdb.main import BQTDatabase
from faker import Faker

from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()

fake = Faker()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to Astrea CrowdFiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://astrea.crowdfiber.com word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="EXISTING_SEARCH",
        description="Existing search found",
        triggers=["If you see 'A service search already exists'"],
        actions=["Click the 'Start From the Beginning' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to verify service",
        triggers=["If you see 'Enter your full address to verify service'"],
        actions=[
            "FOLLOW THESE INSTRUCTIONS CLOSELY",
            "Click the 'Search For Your Address' input field",
            "Type `%address%` into the input field",
            "Press down key",
            "Press enter key",
            "Click the 'Select Market' dropdown",
            "Press down key",
            "Press enter key",
            "Click the 'Go' button",
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="VERIFY_ADDRESS",
        description="Verify address location",
        triggers=["If you see 'please verify that the blue pin'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Scroll down to bottom of the page", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE_PLANS1",
        description="Serviceable - enter contact info",
        triggers=["If you see 'We are excited to be able to service you'"],
        actions=[
            "FOLLOW THESE INSTRUCTIONS CLOSELY",
            "Scroll down to bottom of the page (basically end of the page)",
            "Type `%email%`",
            "Type `%name_f%`",
            "Type `%name_l%`",
            "Type `%phone_num%`",
            "Click the 'Next' button",
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="SERVICEABLE_PLANS2",
        description="Services available in area",
        triggers=["If you see 'The following services are available in your area'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Outside service area",
        triggers=["If you see 'Looks like you're outside of our service area'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Astrea service area
    rows = db.query("SELECT * FROM bqtplus.astrea_addresses LIMIT 1000")
    for row in rows:
        # Construct address string
        # Clean up Zip code (remove .0 if present)
        prop_zip = str(row['PropertyZip'])
        if prop_zip.endswith('.0'):
            prop_zip = prop_zip[:-2]
            
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}, {prop_zip}"
        only_address = row['PropertyFullStreetAddress']
        city = row['PropertyCity']
        state = row['PropertyState']
        addresses.append({
            'address': full_address,
            'only_address': only_address,
            'city': city,
            'state': state,
            'zip_code': prop_zip
        })

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy="brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335", llm_enabled=True)

try:
    with open("examples/isps/results/astrea_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[0]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

# Generate fake contact info using Faker
name_f = fake.first_name()
name_l = fake.last_name()
phone_num = fake.numerify("##########")
email = fake.email()

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address, 
        "only_address": only_address, 
        "city": city, 
        "state": row_data['state'], 
        "zip_code": zip_code,
        "name_f": name_f,
        "name_l": name_l,
        "phone_num": phone_num,
        "email": email
    },
    save_content_dir="examples/isps/save/astrea",
    session="astrea"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/astrea_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)