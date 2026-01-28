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
        description="Navigate to Brightspeed shop page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://shop.brightspeed.com/uas word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Enter your address'"],
        actions=[
            "FOLLOW THESE INSTRUCTIONS CLOSELY",
            "Type `%address%` into the input field",
            "Press tab key once and press enter key once",
            "Click the 'Check availability' button",
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="RES_BUS_ADDRESS",
        description="Residential or business address",
        triggers=["If you see 'Is this a business address'"],
        actions=["Click the 'Home address' option", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="PLANS_STEP1",
        description="Learn about ultrafast fiber plans",
        triggers=["If you see 'Learn about our ultrafast fiber plans'"],
        actions=["Click the 'Continue to view pricing' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE_NO_PLANS",
        description="Brightspeed available at home",
        triggers=["If you see 'great news Brightspeed Internet is available at your home'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="EXISTING_SERVICE",
        description="Brightspeed now available",
        triggers=["If you see 'Brightspeed Internet is nowavailableat yourhome'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="ALREADY_CONNECTED",
        description="Already has Brightspeed service",
        triggers=["If you see 'The address you entered already has Brightspeed service'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="existing_service",
        save_content=True,
    ),
    StatePrompt(
        name="CALL_TO_VERIFY",
        description="IT SAYS GREAT NEWS, Brightspeed may be available - call to verify or 'Brightspeed may be available at your address. Call us to learn more about the best promotions for you.'",
        triggers=["If you see 'Brightspeed may be available at your address Call us at ' or 'Brightspeed may be available at your address. Call us to learn more about the best promotions for you.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="maybe_serviceable",
        save_content=True,
    ),
    StatePrompt(
        name="UNKNOWN_ADDRESS",
        description="Could not find address",
        triggers=["If you see 'We're sorry: We could not find that address. Did you mean'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="unknown_address",
        save_content=True,
    ),
    StatePrompt(
        name="UNKNOWN_ERROR",
        description="Unable to process request",
        triggers=["If you see 'Sorry, we're not able to process your request at the moment'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="access_error",
        save_content=True,
    ),
    StatePrompt(
        name="ACCESS_ERROR",
        description="403 Error",
        triggers=["If you see 'This is 403'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="access_error",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Brightspeed service area
    rows = db.query("SELECT * FROM bqtplus.brightspeed_addresses LIMIT 1000")
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
    with open("examples/isps/results/brightspeed_result.json", "r") as f:
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
    save_content_dir="examples/isps/save/brightspeed",
    session="brightspeed"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/brightspeed_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)