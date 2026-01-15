import json
import os
import sys
from netgent.errors import NetGentError

from bqtdb.main import BQTDatabase

from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
load_dotenv()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to Consolidated check availability page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.consolidated.com/residential/check-availability word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Please provide your complete service address, starting with street number'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the '123 Main St, Mattoon, IL' input field", "Type `%address%` into the input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICE_NO_PLANS",
        description="Service available without plans",
        triggers=["If you see 'Internet service is available at your address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable"
    ),
    StatePrompt(
        name="SERVICEABLE_PLANS",
        description="Service available - redirect to Fidium",
        triggers=["If you see 'We'll take you to Fidium's website to get started'"],
        actions=["Click the 'Let's Go' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="FIDIUM_FIBER",
        description="Fidium fiber plans page",
        triggers=["If you see 'Choose your fiber internet plan'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans"
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see 'Go to our Fidium pre-order page to get on our list'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
    ),
    StatePrompt(
        name="ADDRESS_NOT_FOUND",
        description="Address not found",
        triggers=["If you see 'We weren't able to find your address, but it could be us and not you'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="unknown_address"
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Consolidated service area
    rows = db.query("SELECT * FROM bqtplus.consolidated_addresses LIMIT 1000")
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

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy="brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335", llm_enabled=True)

try:
    with open("examples/isps/results/consolidated_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[9]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code}
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/consolidated_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
