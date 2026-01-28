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
        description="Navigate to ECOEC registration page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://register.ecoec.com word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Taking high-speed fiber services where'"],
        actions=[
            "FOLLOW THESE INSTRUCTIONS CLOSELY",
            "Type `%only_address%` into the input field",
            "Press down key to select the first suggestion",
            "Press enter key to confirm selection",
            "Click the 'Select Type' dropdown",
            "Press down key",
            "Press enter key",
            "Click the 'Go' button",
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="VERIFY_ADDRESS",
        description="Verify address location",
        triggers=["If you see 'Verify that the marker below is the correct location for your address'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Scroll down to the next button", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="EXISTING_SERVICE",
        description="Service already registered",
        triggers=["If you see 'A registration already exists for this address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="existing_service",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see 'Unfortunately, your address is not in an area'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="QUESTIONNAIRE_PHASE1",
        description="Questionnaire - serviceable",
        triggers=["If you see 'Please answer the questions below'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for ECOEC service area
    rows = db.query("SELECT * FROM bqtplus.ecolink_addresses LIMIT 1000")
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

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), llm_enabled=True)

try:
    with open("examples/isps/results/ecoec_result.json", "r") as f:
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
    save_content_dir="examples/isps/save/ecoec",
    session="ecoec"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/ecoec_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)