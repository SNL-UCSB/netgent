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
        description="Navigate to T-Mobile Fiber check address page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://fiber.t-mobile.com/check-address word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address",
        triggers=["If you see 'Enter your address to find out if T-Mobile Fiber is available where you'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Reject' text", "Click the 'Address' input field", "Type `%address%` into the input field", "Click the text `%address%` that appears 2nd in the list", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="HOME_SCREEN",
        description="Home screen availability check",
        triggers=["If you see 'Supercharge your home internet with gigabit'"],
        actions=["Click the 'Check availability' button which appears 2nd", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="MDU",
        description="Multiple Dwelling Unit selection",
        triggers=["If you see 'Enter your address to find out if T-Mobile Fiber is available where you' and 'Unitno'"],
        actions=["Click the 'Unitno' text", "Press down key", "Press enter key", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE_BB",
        description="Service available, broadband facts",
        triggers=["If you see 'Great News' and 'T-Mobile Fiber is available'"],
        actions=["Click the 'Broadband Facts' text which appears 1st", "Click the 'Broadband Facts' text which appears 2nd", "Click the 'Broadband Facts' text which appears 3rd", "TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE_5G",
        description="5G Home Internet available",
        triggers=["If you see '5G Home Internet Plans'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="TMOBILE_5G",
        description="Fiber not available, suggest 5G",
        triggers=["If you see 'T-Mobile Fiber isn\\'t currently available at your'"],
        actions=["Click the 'View Available Plans' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="EXISTING_SERVICE2",
        description="Existing service login required",
        triggers=["If you see 'Please log in'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="existing_service",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available, waitlist",
        triggers=["If you see 'Join our waitlist.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="ACCESS_DENIED",
        description="Access denied",
        triggers=["If you see 'Access Denied'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="access_error",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for T-Mobile Fiber service area
    rows = db.query("SELECT * FROM bqtplus.lumos_addresses LIMIT 1000")
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
    with open("examples/isps/results/tmobile_fiber_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[6]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code},
    save_content_dir="examples/isps/save/tmobile_fiber",
    session="tmobile_fiber"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/tmobile_fiber_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)