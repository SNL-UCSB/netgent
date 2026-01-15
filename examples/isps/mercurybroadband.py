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
        description="Navigate to Mercury Broadband sign up page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://mercurybroadband.com word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'See if Mercury Fiber or Wireless Internet is available for your address'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Scroll down to the 'Enter your address' input field", "Click the 'Enter your address' input field", "Type `%only_address%` into the input field", "Click the text `%address%` that appears 2nd in the list", "Click the 'Check Availability' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="FIBER_SERVICE",
        description="Fiber Internet available, fill contact info",
        triggers=["If you see 'Fiber Internet Is Available at Your Address'"],
        actions=[
            "Click the 'First Name' input field",
            "Type `%name_f%`",
            "Click the 'Last Name' input field",
            "Type `%name_l%`",
            "Click the 'Phone Number' input field",
            "Type `%phone_num%`",
            "Click the 'Email Address' input field",
            "Type `%email%`",
            "Click the 'I consent' text or checkbox",
            "Click the 'View Plans' button",
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service currently unavailable",
        triggers=["If you see 'Service is currently unavailable'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
    ),
    StatePrompt(
        name="PLANS",
        description="Select Fiber Plan",
        triggers=["If you see 'Select Your Fiber Plan'"],
        actions=["Click the 'View 100 500 Mbps Plans' text or button", "Take a screenshot", "TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans"
    ),
    StatePrompt(
        name="UNKNOWN_SERVICE",
        description="Service may be available",
        triggers=["If you see 'Service may be available'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="unknown_address"
    ),
    StatePrompt(
        name="EXISTING_CUSTOMER",
        description="Existing customer record found",
        triggers=["If you see 'Our records show that Mercury account already associated with this address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="existing_service"
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Mercury Broadband service area
    rows = db.query("SELECT * FROM bqtplus.mercury_addresses LIMIT 1000")
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
    with open("examples/isps/results/mercurybroadband_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

# Dummy contact info for flow
name_f = "John"
name_l = "Doe"
phone_num = "5555555555"
email = "john.doe@example.com"

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address, 
        "only_address": only_address, 
        "city": city, 
        "state": row_data['state'], 
        "zip_code": zip_code,
        "name_f": name_f,
        "name_l": name_l,
        "phone_num": phone_num,
        "email": email
    }
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/mercurybroadband_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
