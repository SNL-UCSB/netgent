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
        description="Navigate to the Sonic availability page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.sonic.com/availability word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address and zip code to check availability",
        triggers=["If you see 'Check Your Internet Availability by Address'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Street Address' input field", "Type `%address%` into the address input field", "Click the text '%address%'", "Click the text 'Check Your Internet Availability by Address'", "Click the 'Zip Code' input field", "Type `%zip_code%` into the zip code input field", "Click the 'Home' button", "Click the 'CHECK AVAILABILITY' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE_NO_PLANS",
        description="Business eligible for internet - business address",
        triggers=["If you see 'Your business is eligible for America’s fastest internet.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="business_address",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="No service available yet",
        triggers=["If you see 'We're Sorry, No Service is Available - Yet!'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICABLE",
        description="Service options available",
        triggers=["If you see 'Choose from service options below'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Sonic service area
    rows = db.query("SELECT * FROM bqtplus.sonic_addresses LIMIT 1000")
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
    with open("examples/isps/results/sonic_result.json", "r") as f:
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
    save_content_dir="examples/isps/save/sonic",
    session="sonic"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/sonic_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)