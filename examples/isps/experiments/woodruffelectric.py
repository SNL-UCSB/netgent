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
        description="Navigate to Woodruff Electric page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://woodruffelectric.vetro.io/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the Woodruff Electric page",
        triggers=["If you see 'Check Internet Availability'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into the input field", "Press enter key", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Available for Service - (e.g. 'Broadband service is available at your address!')",
        triggers=["If you see 'Broadband service is available at your address!'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available - (e.g. 'Currently Unavailable')",
        triggers=["If you see 'Currently Unavailable'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

# addresses = []
# with BQTDatabase() as db:
#     rows = db.query("SELECT * FROM bqtplus.xfinity_addresses LIMIT 1000")
#     for row in rows:
#         zip_code = str(row['PropertyZip'])
#         if zip_code.endswith('.0'):
#             zip_code = zip_code[:-2]
            
#         address_entry = {
#             "address": f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}",
#             "zip_code": zip_code
#         }
#         addresses.append(address_entry)




results = []
state_repository = []

# Initialize agent once if possible, or inside loop. 
# Assuming NetGent can be reused or is lightweight. PROXY and LLM are passed in init.
for i in range(100):
    agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)
    agent.set_state_wait_time(5)
    agent.set_action_wait_time(5)

    full_address = "1304 E Broadway St, Forrest City, AR"
    address = full_address
    zip_code = "72335"


    print(f"Run {i+1}: Address: {address}, Zip: {zip_code}")


    try:
        result = agent.run(
            state_prompts=prompts, 
            state_repository=state_repository, 
            variables={
                "address": address, 
                "zip_code": zip_code,
            },
            session=f"woodruffelectric_robust",
            save_content_dir=f"examples/isps/experiments/robustness/woodruffelectric",
            close_browser=True
        )
        state_repository = result['state_repository']
    except Exception as e:
        print(f"Error in run {i+1}: {e}")

# Write result to file
os.makedirs("examples/isps/experiments/robustness/woodruffelectric", exist_ok=True)
with open("examples/isps/experiments/robustness/woodruffelectric_result.json", "w") as f:
    json.dump(state_repository, f, indent=2, default=str)