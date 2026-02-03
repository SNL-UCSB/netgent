import json
import os
import sys
from netgent.errors import NetGentError
from bqtdb.main import BQTDatabase
from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from faker import Faker

load_dotenv()
fake = Faker()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to Team Midwest CrowdFiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://internet.teammidwest.com/front_end/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the Team Midwest page",
        triggers=["If you see 'HELLO, BETTER INTERNET'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Accept cookies first if there is the option to remove it", "Type `%address%` into the input field", "Type `%zip_code%` into the input field", "Click the 'Go' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address location",
        triggers=["If you see 'Verify that the marker below is the correct location for your address'"],
        actions=["Scroll down the whole page", "Click the 'Next' button", "TERMINATE AT THIS POINT AND DO NOT NOTHING"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Build your bundle",
        triggers=["If you see 'Build your bundle'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available - (e.g. 'Maybe In The Future')",
        triggers=["Check if there is the text 'Maybe In The Future' or 'We are not in your area. However, we are actively expanding and evaluating new places to extend service.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    rows = db.query("SELECT * FROM bqtplus.xfinity_addresses LIMIT 1000")
    for row in rows:
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
            
        address_entry = {
            "address": f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}",
            "zip_code": zip_code
        }
        addresses.append(address_entry)


results = []
state_repository = []

# Initialize agent once if possible, or inside loop. 
# Assuming NetGent can be reused or is lightweight. PROXY and LLM are passed in init.
for i in range(100):
    agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)
    agent.set_state_wait_time(5)
    agent.set_action_wait_time(5)
    address_data = addresses[1] # Using same address for robustness testing?
    address = address_data['address']
    zip_code = address_data['zip_code']


    print(f"Run {i+1}: Address: {address}, Zip: {zip_code}")


    try:
        result = agent.run(
            state_prompts=prompts, 
            state_repository=state_repository, 
            variables={
                "address": address, 
                "zip_code": zip_code,
            },
            session=f"teammidwest_robust",
            save_content_dir=f"examples/isps/experiments/robustness/teammidwest",
            close_browser=True
        )
        state_repository = result['state_repository']
    except Exception as e:
        print(f"Error in run {i+1}: {e}")

# Write result to file
os.makedirs("examples/isps/experiments/robustness/teammidwest", exist_ok=True)
with open("examples/isps/experiments/robustness/teammidwest_result.json", "w") as f:
    json.dump(results, f, indent=2, default=str)