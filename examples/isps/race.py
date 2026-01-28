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
        description="Navigate to Race Communications website",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://race.com word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="BUSINESS_ADDRESS",
        description="Check if it is a business address",
        triggers=["If you see 'Check to see if we're in your area' and 'This looks like a Business Address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="business_address",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE_PLANS2",
        description="Service available with Gigabit/Internet 300 plans",
        triggers=["If you see 'Good news! Race is available at your address'", "If you see 'Gigabit Internet' or 'Internet 300'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE_PLANS1",
        description="Service available with multiple plans",
        triggers=["If you see 'Good news! Race is available at your address'", "If you see 'Gigabit Internet' or '5 Gigabit Internet' or '10 Gigabit Internet' or 'Internet 500'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="EXISTING_SERVICE",
        description="Address already has service or order",
        triggers=["If you see 'Looks like the address you entered has an order in flight or already has service'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="existing_service",
        save_content=True,
    ),
    StatePrompt(
        name="MAYBE_SERVICEABLE",
        description="Service might be available",
        triggers=["If you see 'Our fast fiber internet may be available at your address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="maybe_serviceable",
        save_content=True,
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Check to see if we're in your area'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Close cookie consent popup", "Scroll down to the 'Address' input field", "Click the 'Check your address to get started' button", "Type `%address%` into the input field", "Click the text `%address%` that appears 2nd in the list", "Click the 'My address is not shown' text", "Press enter key to confirm", "TERMINATE AT THIS POINT"],
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Race service area
    rows = db.query("SELECT * FROM bqtplus.race_addresses LIMIT 1000")
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

# LLM enabled set to True as requested
agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), llm_enabled=True)

try:
    with open("examples/isps/results/race_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[5]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code},
    save_content_dir="examples/isps/save/race",
    session="race"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/race_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)