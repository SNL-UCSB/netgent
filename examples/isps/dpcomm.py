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
        description="Navigate to D-P Communications page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.d-pcomm.com word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'GIG Internet' and 'Get our best deal ever.'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Enter your address to view available plans' input field", "Type `%address%` into the input field", "Click the 'CHECK AVAILABILITY' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="INTERNET",
        description="Build your bundle - select Internet",
        triggers=["If you see 'Internet' and 'Build your bundle'"],
        actions=["Click the 'Internet' option", "Click the 'SELECT' button which appears 1st", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="INTERNET_RURAL",
        description="Build your bundle - Rural Internet",
        triggers=["If you see 'Internet' and 'Build your bundle' and 'Rural Internet'"],
        actions=["TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="INTERNET_BB_FACTS",
        description="Broadband Facts page",
        triggers=["If you see 'Broadband Facts'"],
        actions=[
            "TERMINATE AT THIS POINT"
        ],
        end_state="serviceable_with_plans"
    ),
    StatePrompt(
        name="INTERNET_BB_FACTS_RURAL_INT",
        description="Broadband Facts with Rural Internet",
        triggers=["If you see 'Broadband Facts' and 'Rural Internet'"],
        actions=[
            "TERMINATE AT THIS POINT"
        ],
        end_state="serviceable_with_plans"
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see 'Unfortunately, we currently do not offer services to that address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for D-P Communications service area
    rows = db.query("SELECT * FROM bqtplus.dpcomm_addresses LIMIT 1000")
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
    with open("examples/isps/results/dpcomm_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
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
with open("examples/isps/results/dpcomm_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
