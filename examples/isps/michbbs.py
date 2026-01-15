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
        description="Navigate to Michigan Broadband Services home page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://michbbs.com word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Search address bar",
        triggers=["If you see 'Search Your Address'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "close mailing list popup", "Scroll down pixels to the search for address", "Type `%only_address%`", "Type `%zip_code%`", "Press on service type, press down key and press enter key", "Click the 'Go' text or button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address selection",
        triggers=["If you see 'Click the Next button to see if services are available'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY","Scroll down to the bottom of the page", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see 'Service is not currently available in your area.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
    ),
    StatePrompt(
        name="EXISTING_SERVICE",
        description="Registration already exists",
        triggers=["If you see 'A Registration Already Exists For Your Address'"],
        actions=["Click the 'No One at My Location' text or button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Service available",
        triggers=["If you see 'Your home is in an area where Michigan Broadband provides services!'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans"
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for MichBBS service area
    rows = db.query("SELECT * FROM bqtplus.michigan_addresses LIMIT 1000")
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
    with open("examples/isps/results/michbbs_result.json", "r") as f:
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
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code}
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/michbbs_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
