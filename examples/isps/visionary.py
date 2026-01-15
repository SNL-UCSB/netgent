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
            description="Navigate to the Visionary order page",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://order.vcn.com/ word for word", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="ADDRESS_BAR",
            description="Enter address to check service availability",
            triggers=["If you see 'Enter your address to check service availability.'"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click on the 'Street Address' input field", "Type `%address%` into the address input field", "Click on the 'Zip' input field", "Type `%zip_code%` into the zip code input field", "Click the 'Go' button", "Click the 'Continue' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="INTERNET_AVAILABLE",
            description="Enter contact information to view available plans",
            triggers=["If you see 'Enter your contact information below to view all available plans and pricing.'"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Scroll down to the 'Enter your contact information' section", "Click on 'First Name' input field", "Type `%name_f%` into the first name field", "Click on 'Last Name' input field", "Type `%name_l%` into the last name field", "Click on 'Email' input field", "Type `%email%` into the email field", "Click on 'Phone' input field", "Type `%phone_num%` into the phone field", "Click 'Own' option", "Click 'How did you hear about us?' dropdown and press 'D' to select 'Direct Mail'", "Click the 'Continue' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="SERVICEABLE",
            description="Service plans are available at this address",
            triggers=["If you see 'Please select from the below service plans that are available at your address.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans"
        ),
        StatePrompt(
            name="EXISTING_SERVICE",
            description="Address already has service with Visionary",
            triggers=["If you see 'Your address already has service with Visionary'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans"
        ),
        StatePrompt(
            name="NO_SERVICE",
            description="Visionary is not available in this area",
            triggers=["If you see 'We are not in your area... yet!'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="no_service"
        ),
    ]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Visionary service area
    rows = db.query("SELECT * FROM bqtplus.visionary_addresses LIMIT 1000")
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

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

try:
    with open("examples/isps/results/visionary_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[1]
address = row_data['address']
city = row_data['city']
zip_code = row_data['zip_code']

# Contact information variables
name_f = "John"
name_l = "Doe"
email = "test@example.com"
phone_num = "5551234567"

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address, 
        "city": city, 
        "state": row_data['state'], 
        "zip_code": zip_code,
        "name_f": name_f,
        "name_l": name_l,
        "email": email,
        "phone_num": phone_num
    }
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/visionary_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
