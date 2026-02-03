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

PROXY = "brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335"

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to Nuvera shop page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://shop.nuvera.net/#/order/1 word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Check for Fiber Fast Internet Availability and Pricing'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Enter your address' input field", "Type `%address%` into the input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click the 'NEXT' button", "JUST DONT DO ANYTHING AT THIS POINT AND TERMINATE"],
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see URL is 'https://nuvera.net/future-service/' and 'We’re not in your neighborhood yet…'"],
        actions=["JUST DONT DO ANYTHING AT THIS POINT AND TERMINATE"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Service available",
        triggers=["If you see 'We are serving your area at this time'"],
        actions=["JUST DONT DO ANYTHING AT THIS POINT AND TERMINATE"],
        end_state="serviceable",
        save_content=True,
    )
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

# Use first 10 addresses (or fewer if not available) and cycle through them over 100 runs
seed_addresses = addresses[:10] if len(addresses) >= 10 else addresses
if not seed_addresses:
    raise SystemExit("No addresses loaded from database to run nuvera experiment.")

for i in range(100):
    address_data = seed_addresses[i % len(seed_addresses)]
    address = address_data['address']
    zip_code = address_data['zip_code']

    agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=PROXY, llm_enabled=True)
    agent.set_state_wait_time(5)
    agent.set_action_wait_time(5)

    print(f"Run {i+1}: seed_idx={i % len(seed_addresses)} Address: {address}, Zip: {zip_code}")

    try:
        result = agent.run(
            state_prompts=prompts,
            state_repository=state_repository,
            variables={
                "address": address,
                "zip_code": zip_code,
            },
            session=f"nuvera_robust",
            save_content_dir=f"examples/isps/experiments/robustness/nuvera",
            close_browser=True,
        )
        if isinstance(result, dict) and 'state_repository' in result:
            state_repository = result['state_repository']
    except Exception as e:
        print(f"Error in run {i+1}: {e}")

# Write result to file
os.makedirs("examples/isps/experiments/robustness/nuvera", exist_ok=True)
with open("examples/isps/experiments/robustness/nuvera_result.json", "w") as f:
    json.dump(state_repository, f, indent=2, default=str)