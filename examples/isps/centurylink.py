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
        description="Navigate to CenturyLink shop page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://shop.centurylink.com/uas/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Please enter your address so we can show you the newest deals.'"],
        actions=[
            "FOLLOW THESE INSTRUCTIONS CLOSELY",
            "Click the 'Accept Cookies' button if visible",
            "Type `%address%` into the input field",
            "Press down key to select the first suggestion",
            "Press enter key to confirm selection",
            "Click the 'Start Now' button",
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="HUMAN_CHECK",
        description="Human verification required",
        triggers=["If you see 'Please verify you are a human'"],
        actions=["TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Service available - multiple plans",
        triggers=["If you see 'Before you make your selection, we want to show you the options available to you.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable"
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="No service - CenturyLink",
        triggers=["If you see 'CenturyLink may not be able to provide internet service at your address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
    ),
    StatePrompt(
        name="NO_SERVICE_Brightspeed",
        description="No service - Brightspeed area",
        triggers=["If you see 'Brightspeed is the new internet provider for your neighborhood.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
    ),
    StatePrompt(
        name="UNKNOWN_ADDRESS",
        description="Unknown address",
        triggers=["If you see 'We're having trouble finding your address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="unknown_address"
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for CenturyLink service area
    rows = db.query("SELECT * FROM bqtplus.centurylink_addresses LIMIT 1000")
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

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), llm_enabled=True)

try:
    with open("examples/isps/results/centurylink_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[2]
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
with open("examples/isps/results/centurylink_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
