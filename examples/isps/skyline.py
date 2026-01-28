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
        description="Navigate to the SkyBest internet page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.skybest.com/residential/services/internet word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Enter your address in the search bar below to discover the speeds available in your area'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Find address or place' input field", "Type `%address%` into the address input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE_NO_PLANS",
        description="Fiber Optic Network available",
        triggers=["If you see 'Fiber Optic Network'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable",
        save_content=True,
    ),
    StatePrompt(
        name="WEBGL_ERROR",
        description="WebGL2 support required for map",
        triggers=["If you see 'Unable to display map. WebGL2 support is required.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="access_error",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="SkyLine/SkyBest does not currently serve your location",
        triggers=["If you see 'SkyLine/SkyBest does not currently serve your location'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Skyline service area
    rows = db.query("SELECT * FROM bqtplus.skyline_addresses LIMIT 1000")
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
    with open("examples/isps/results/skybest_result.json", "r") as f:
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
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code},
    save_content_dir="examples/isps/save/skyline",
    session="skyline"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/skyline_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)