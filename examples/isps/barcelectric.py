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
        description="Navigate to Barc Electric SmartHub page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://barcelectric.smarthub.coop/ui/#/newConnect/serviceLocation word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'What is the address of your new service location'"],
        actions=[
            "FOLLOW THESE INSTRUCTIONS CLOSELY",
            "Type `%address%` into the input field",
            "Press down key",
            "Press enter key",
            "Press down key",
            "Press up key",
            "Scroll down to bottom of the page"
            "Click the 'Continue' button",
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="If you see 'What is the address of your new service location' and 'We are currently providing services in your area'",
        description="Service available in area",
        triggers=["If you see 'What is the address of your new service location' and 'We are currently providing services in your area'"],
        actions=["Click the 'Continue' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Select service plans",
        triggers=["If you see 'Select the service plans that are right for your home'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available in area or if there it says failure or the it say that we are not currently providing services in your area",
        triggers=["If you see 'What is the address of your new service location' and 'Sorry, we are not currently providing services in your area'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="FAILURE",
        description="Failure page - address lookup failed",
        triggers=["If you see 'WE'RE SORRY'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Barc Electric service area
    rows = db.query("SELECT * FROM bqtplus.barc_addresses LIMIT 1000")
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
    with open("examples/isps/results/barcelectric_result.json", "r") as f:
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
    save_content_dir="examples/isps/save/barcelectric",
    session="barcelectric"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/barcelectric_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)