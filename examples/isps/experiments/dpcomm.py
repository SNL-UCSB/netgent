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
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see 'Unfortunately, we currently do not offer services to that address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    rows = db.query("SELECT * FROM bqtplus.dpcomm_addresses LIMIT 1000")
    for row in rows:
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

results = []
state_repository = []

# select first 10 addresses (or fewer) as seeds
seed_addresses = addresses[:10] if len(addresses) >= 10 else addresses
if not seed_addresses:
    raise SystemExit("No addresses found in bqtplus.dpcomm_addresses")

os.makedirs("examples/isps/experiments/robustness/dpcomm", exist_ok=True)

for i in range(100):
    addr = seed_addresses[i % len(seed_addresses)]
    address = addr['address']
    zip_code = addr['zip_code']

    agent = NetGent(
        llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")),
        proxy=os.getenv("PROXY_URL"),
        llm_enabled=True,
    )
    agent.set_state_wait_time(5)
    agent.set_action_wait_time(5)

    print(f"Run {i+1}: seed_idx={i % len(seed_addresses)} Address: {address}, Zip: {zip_code}")

    try:
        result = agent.run(
            state_prompts=prompts,
            state_repository=state_repository,
            variables={
                "address": address,
                "only_address": addr['only_address'],
                "city": addr['city'],
                "state": addr['state'],
                "zip_code": zip_code,
            },
            session=f"dpcomm_robust",
            save_content_dir="examples/isps/experiments/robustness/dpcomm",
            close_browser=True,
        )
        if isinstance(result, dict) and 'state_repository' in result:
            state_repository = result['state_repository']
    except Exception as e:
        print(f"Error in run {i+1}: {e}")

# write results
with open("examples/isps/experiments/robustness/dpcomm_result.json", "w") as f:
    json.dump(state_repository, f, indent=2, default=str)
