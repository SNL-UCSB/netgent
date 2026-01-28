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
        description="Navigate to Fidium Fiber internet page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.fidiumfiber.com/fiber-internet word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Life's too short for slow and unreliable internet'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the cookie pop up button", "Type `%address%` into the input field", "Click the text `%address%` that appears 1st in the list", "Click the 'Check availability' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see 'Life's too short for slow and unreliable internet' and 'Fidium Fiber isn't available at your location'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="UNKNOWN_ADDR",
        description="Unknown address",
        triggers=["If you see 'We weren't able to find your address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="unknown_address",
        save_content=True,
    ),
    StatePrompt(
        name="AVAILABLE_INTERNET",
        description="Service available",
        triggers=["If you see 'Good News! Fidium Fiber is available to you'"],
        actions=["Click the 'Order for home' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="FIBER_PLANS",
        description="Fiber plans page",
        triggers=["If you see 'Choose your fiber internet plan'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Fidium Fiber service area
    rows = db.query("SELECT * FROM bqtplus.fidium_addresses LIMIT 1000")
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

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), llm_enabled=True)

try:
    with open("examples/isps/results/fidium_result.json", "r") as f:
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
    save_content_dir="examples/isps/save/fidium",
    session="fidium"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/fidium_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)