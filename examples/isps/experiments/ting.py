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
            description="Navigate to the Ting website",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://www.ting.com/# word for word", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="NO_SERVICE",
            description="Ting isn't in your area yet on the screen, run this",
            triggers=["If you see 'Ting isn’t in your area yet' on the screen"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="no_service",
            save_content=True,
        ),
        StatePrompt(
            name="ADDRESS_BAR",
            description="Enter address to check availability",
            triggers=["If you see 'Life moves better at fiber speed'"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click on the 'e.g: 123 Ting Street; Anytown CA; 01234' input field", "Type `%address%` into the address input field", "Click on the address suggestion that matches `%address%` (second occurrence)", "Click the 'Check availability' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="INTERNET_AVAILABLE",
            description="Ting Internet is in your area",
            triggers=["If you see 'Ting Internet is in your area'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans",
            save_content=True,
        ),
        StatePrompt(
            name="ACCESS_DENIED",
            description="Access error - we apologize for the inconvenience",
            triggers=["If you see 'We apologize for the inconvenience'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="access_error",
            save_content=True,
        ),
    ]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Ting service area (limit seeds to 10)
    rows = db.query("SELECT * FROM bqtplus.ting_addresses LIMIT 10")
    for row in rows:
        # Construct address string
        # Clean up Zip code (remove .0 if present)
        prop_zip = str(row['PropertyZip'])
        if prop_zip.endswith('.0'):
            prop_zip = prop_zip[:-2]
            
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}, {prop_zip}"
        city = row['PropertyCity']
        state = row['PropertyState']
        addresses.append({
            'address': full_address,
            'city': city,
            'state': state,
            'zip_code': prop_zip
        })

results = []
state_repository = []

# Use the first 10 addresses (or fewer if not available) and cycle through them over 100 runs
seed_addresses = addresses[:10] if len(addresses) >= 10 else addresses
if not seed_addresses:
    raise SystemExit("No addresses available to run tests.")

for i in range(100):
    # pick one of the first 10 addresses, cycling through 0..9
    address_data = seed_addresses[i % len(seed_addresses)]
    address = address_data['address']
    zip_code = address_data['zip_code']

    agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=PROXY, llm_enabled=True)
    agent.set_state_wait_time(5)
    agent.set_action_wait_time(5)

    print(f"Run {i+1}: Address idx={i % len(seed_addresses)} Address: {address}, Zip: {zip_code}")

    try:
        result = agent.run(
            state_prompts=prompts,
            state_repository=state_repository,
            variables={
                "address": address,
                "zip_code": zip_code,
            },
            session=f"ting_robust2",
            save_content_dir=f"examples/isps/experiments/robustness/ting",
            close_browser=True,
        )
        if isinstance(result, dict) and 'state_repository' in result:
            state_repository = result['state_repository']
    except Exception as e:
        print(f"Error in run {i+1}: {e}")

# Write result to file
os.makedirs("examples/isps/experiments/robustness/ting", exist_ok=True)
with open("examples/isps/experiments/robustness/ting_result.json", "w") as f:
    json.dump(state_repository, f, indent=2, default=str)