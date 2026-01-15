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
            description="Navigate to the Ting website",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://www.ting.com/# word for word", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="NO_SERVICE",
            description="Ting isn't in your area yet on the screen, run this",
            triggers=["If you see 'Ting isn’t in your area yet' on the screen, run this"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="no_service"
        ),
        StatePrompt(
            name="ADDRESS_BAR",
            description="Enter address to check availability",
            triggers=["If you see 'Life moves better at fiber speed'"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click on the 'e.g: 123 Ting Street; Anytown CA; 01234' input field", "Type `%address%` into the address input field", "Click on the address suggestion that matches `%address%` (second occurrence)", "Click the 'Check availability' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="INTERNET_AVAILABLE",
            description="Ting Internet is in your area",
            triggers=["If you see 'Ting Internet is in your area'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans"
        ),
        StatePrompt(
            name="ACCESS_DENIED",
            description="Access error - we apologize for the inconvenience",
            triggers=["If you see 'We apologize for the inconvenience'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="access_error"
        ),
    ]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Ting service area
    rows = db.query("SELECT * FROM bqtplus.ting_addresses LIMIT 1000")
    for row in rows:
        # Construct address string
        # Clean up Zip code (remove .0 if present)
        prop_zip = str(row['PropertyZip'])
        if prop_zip.endswith('.0'):
            prop_zip = prop_zip[:-2]
            
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}, {prop_zip}"
        city = row['PropertyCity']
        state = row['PropertyState']
        addresses.append({
            'address': full_address,
            'city': city,
            'state': state,
            'zip_code': prop_zip
        })

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy="brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335", llm_enabled=True)

try:
    with open("examples/isps/results/ting_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "city": city, "state": row_data['state'], "zip_code": zip_code}
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/ting_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
