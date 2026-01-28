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
        description="Navigate to Onward check availability page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://getonward.com/check-availability/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Check to see if Onward fiber is in your neighborhood.'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'House Number' input field", "Type `%address%` into the input field", "Click the 'Zip Code' input field", "Type `%zip_code%`", "Click the 'LOOKUP' button", "Choose the second option in the list", "Scroll down and press the next button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Select address from list",
        triggers=["If you see 'Please Select Address'"],
        actions=["Click the text `%address%` that appears 2nd in the list", "Click the 'NEXT' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="NO_ADDRESS",
        description="Address not serviceable",
        triggers=["If you see 'Please submit your address here and we will contact you if your location is serviceable!'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Service available",
        triggers=["If you see 'Which type of service are you interested in?'"],
        actions=["TERaINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Onward service area
    rows = db.query("SELECT * FROM bqtplus.inyo_addresses LIMIT 1000")
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
    with open("examples/isps/results/onward_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[3]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code},
    save_content_dir="examples/isps/save/onward",
    session="onward"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/onward_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)