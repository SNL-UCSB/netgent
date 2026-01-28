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
        description="Navigate to Optimum Check Availability page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.optimum.com/check-availability word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="POPUP",
        description="Close promotional popup",
        triggers=["If you see 'Sign up today and receive' and 'Broadband Consumer Disclosure'"],
        actions=["Click the 'Not interested' text", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'See if Optimum is available'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Enter your address*' input field", "Type `%only_address%` into the input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click the 'Check availability' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="VERIFY_ADDRESS",
        description="Verify address selection",
        triggers=["If you see 'Verify Your Address'"],
        actions=["Click the 'KEEP WHAT I ENTERED' text", "Click the 'Continue' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="EXISTING_SERVICE",
        description="Address has existing service",
        triggers=["If you see 'This address has an active Optimum account'"],
        actions=["Click the 'Start shopping' button", "TERMINATE AT THIS POINT"],
        end_state="existing_service",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE_PLANS",
        description="Service available with plans",
        triggers=["If you see 'Pick your Internet speed'"],
        actions=["Click the 'Broadband Facts' text", "Click the '%arrow%' button", "Click the 'Broadband Facts' text", "Click the 'Broadband Facts' text", "TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="BB_FACTS",
        description="Broadband facts disclosure",
        triggers=["If you see 'Broadband Consumer Disclosure'"],
        actions=["Click the 'Pick your Internet speed' text", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see 'Unfortunately Optimum interent is unavailable at this address.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="MAYBE_SERVICEABLE",
        description="Service might be available but online order not supported",
        triggers=["If you see 'We do not currently support ordering service online at this address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="maybe_serviceable",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE_COX",
        description="Redirected to Cox or caught Cox keyword",
        triggers=["If you see 'Cox'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Optimum service area
    rows = db.query("SELECT * FROM bqtplus.optimum_addresses LIMIT 1000")
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
    with open("examples/isps/results/optimum_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[0]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code, "arrow": "->"},
    save_content_dir="examples/isps/save/optimum",
    session="optimum"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/optimum_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)