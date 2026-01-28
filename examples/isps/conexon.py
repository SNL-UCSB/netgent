import json
import os
import sys
from netgent.errors import NetGentError

from bqtdb.main import BQTDatabase

from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to Conexon Connect signup page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.connectsignup.com word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Is service from Conexon Connect available to me'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Street Address' input field", "Type `%address%` into the input field", "Press enter key", "Click the 'Check availability' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="CHECK_SERVICEABLE",
        description="Provide information - serviceable",
        triggers=["If you see 'Please provide the information below'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="EXISTING_SERVICE",
        description="Existing service at address",
        triggers=["If you see 'There is an existing account registered to this address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="existing_service",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Service available - select services",
        triggers=["If you see 'Select services below to sign-up for world-class, affordable reliable internet'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE_PLANS",
        description="Future service - building network",
        triggers=["If you see 'We are building out as network as quickly as we can'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="future_service",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Conexon Connect service area
    rows = db.query("SELECT * FROM bqtplus.conexon_addresses LIMIT 1000")
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
    with open("examples/isps/results/conexon_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code},
    save_content_dir="examples/isps/save/conexon",
    session="conexon"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/conexon_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)