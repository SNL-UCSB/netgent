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
        description="Navigate to the Sparklight internet page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.sparklight.com/internet word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR2",
        description="Fill in address and zip code to check availability",
        triggers=["If you see 'Shop plans' and 'Plans for everyone'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Street Address' input field", "Type `%only_address%` into the address input field", "Click the 'Zip Code' input field", "Type `%zip_code%` into the zip code input field", "Click the 'Check Availability' button", "TERMINATE AT THIS POINT"],
    ),
        StatePrompt(
        name="EXISTING_SERVICE",
        description="Address already has service",
        triggers=["If you see 'Street Address or Apartment', 'Available home internet plans', and 'WELCOME BACK'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="existing_service",
        save_content=True,
    ),
    StatePrompt(
        name="ADDRESS_BAR1",
        description="Click Shop plans button",
        triggers=["If you see 'Shop plans'"],
        actions=["Click the 'Shop plans' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="VERIFY_ADDRESS",
        description="Confirm address selection",
        triggers=["If you see 'Shop Plans', 'Retry Address', and 'Confirm'"],
        actions=["Click the 'Confirm' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Serviceable - Select 1 Gig plan",
        triggers=["If you see 'Available Internet plans'"],
        actions=["Click the 'Select 1 Gig Internet plan' button", "TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available in this area",
        triggers=["If you see 'Street Address or Apartment' and 'Our apologies, but currently do not service your area'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE1",
        description="Optimum Fiber offer - likely no Sparklight service",
        triggers=["If you see 'Optimum Fiber'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="UNKNOWN_STATUS",
        description="Serviceable area but address not in system",
        triggers=["If you see 'It looks like you're ina serviceable area, but we currently don't have your specific address in our system'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="maybe_serviceable",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Sparklight service area
    rows = db.query("SELECT * FROM bqtplus.sparklight_addresses LIMIT 1000")
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
    with open("examples/isps/results/sparklight_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[1]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code},
    save_content_dir="examples/isps/save/sparklight",
    session="sparklight"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/sparklight_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)