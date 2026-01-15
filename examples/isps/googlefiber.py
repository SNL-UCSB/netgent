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
        description="Navigate to Google Fiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://fiber.google.com word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Fast is just the beginning'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Enter your address' input field", "Type `%address%` into the input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click the 'Check availability' button which appears 2nd", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ENTER_EMAIL",
        description="Not available - enter email for updates",
        triggers=["If you see 'Enter your email address to receive updates'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
    ),
    StatePrompt(
        name="SERVICEABLE_PLANS",
        description="Service available with plans",
        triggers=["If you see 'Choose your internet'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans"
    ),
    StatePrompt(
        name="SELECT_INTERNET",
        description="Eligible for service",
        triggers=["If you see 'Nice! You\\'re eligible'"],
        actions=["Click the 'Get started' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="EXISTING_SERVICE",
        description="Address has existing service",
        triggers=["If you see 'This address has a Google Fiber account'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="existing_service"
    ),
    StatePrompt(
        name="VERIFY_UNIT",
        description="MDU - verify unit",
        triggers=["If you see 'Check your address:'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="MDU"
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Google Fiber service area
    rows = db.query("SELECT * FROM bqtplus.gfiber_addresses LIMIT 1000")
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
    with open("examples/isps/results/googlefiber_result.json", "r") as f:
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
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code}
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/googlefiber_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
