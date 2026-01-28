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
        description="Navigate to Allpoints Broadband signup page",
        triggers=["If the URL is 'data:,' (chrome homescreen)"],
        actions=["Go to https://signup.allpointsbroadband.com word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Tell us where you want your services' text. DO NOT GET THE URL HERE'"],
        actions=[
            "FOLLOW THESE INSTRUCTIONS CLOSELY",
            "Type `%address%` into the input field",
            "Press enter key",
            "Click the 'Check availability' button",
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Choose internet plan - address is serviceable",
        triggers=["If you see 'Choose the internet plan that works best for you.' DO NOT GET THE URL HERE"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Not in service area",
        triggers=["If you see 'We're not in your area just yet' text. DO NOT GET THE URL HERE"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Allpoints Broadband service area
    rows = db.query("SELECT * FROM bqtplus.allpoints_addresses LIMIT 1000")
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

agent = NetGent(
    llm=ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        temperature=0.2, 
        google_api_key=os.getenv("GOOGLE_API_KEY")
    ), 
    llm_enabled=True, 
    config={"allow_multiple_states": True}
)

try:
    with open("examples/isps/results2/allpoints_result.json", "r") as f:
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
    save_content_dir="examples/isps/save/allpoints",
    session="allpoints"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results2", exist_ok=True)
with open("examples/isps/results2/allpoints_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)