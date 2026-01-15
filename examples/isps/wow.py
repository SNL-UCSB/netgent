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
            description="Navigate to the WOW website",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://www.wowway.com/ word for word", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="ADDRESS_BAR",
            description="Enter address to check availability",
            triggers=["If you see an address input field or 'Enter your address' or 'Check availability'"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Scroll down", "Click on the address input field", "Type `%address%` into the address input field", "Type `%city%` into the city input field if available", "Type `%zip_code%` into the zip code input field if available", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click the submit or continue button if available", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Internet Available at Address on WOW",
            description="Internet service is available at this address",
            triggers=["If you see internet plans, pricing, or 'Shop plans' or 'View plans' options"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Service Available"
        ),
        StatePrompt(
            name="Internet Not Available at Address on WOW",
            description="Internet service is not available at this address",
            triggers=["If you see 'service not available', 'not in your area', or 'we don't offer service'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Service Not Available"
        ),
    ]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for WOW service area
    rows = db.query("SELECT * FROM bqtplus.wow_addresses LIMIT 1000")
    for row in rows:
        # Construct address string
        # Clean up Zip code (remove .0 if present)
        prop_zip = str(row['PropertyZip'])
        if prop_zip.endswith('.0'):
            prop_zip = prop_zip[:-2]
            
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}"
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
    with open("examples/isps/results/wow_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[1]
address = row_data['address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "city": city, "zip_code": zip_code}
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/wow_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
