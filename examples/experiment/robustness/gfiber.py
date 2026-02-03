import json
import os
import sys
from netgent.errors import NetGentError

from bqtdb.main import BQTDatabase

from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()
# Proxy string to pass directly to NetGent. Override with GFIBER_PROXY env var.
PROXY = os.getenv("GFIBER_PROXY") or "brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335"

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to Google Fiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://fiber.google.com word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Fast is just the beginning'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Enter your address' input field", "Type `%address%` into the input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click the 'Check availability' button which appears 2nd", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ENTER_EMAIL",
        description="Not available - enter email for updates",
        triggers=["If you see 'Enter your email address to receive updates'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE_PLANS",
        description="Service available with plans",
        triggers=["If you see 'Choose your internet'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="SELECT_INTERNET",
        description="Eligible for service",
        triggers=["If you see 'Nice! You\\'re eligible'"],
        actions=["Click the 'Get started' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="EXISTING_SERVICE",
        description="Address has existing service",
        triggers=["If you see 'This address has a Google Fiber account'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="existing_service",
        save_content=True,
    ),
    StatePrompt(
        name="VERIFY_UNIT",
        description="MDU - verify unit",
        triggers=["If you see 'Check your address:'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="MDU",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Google Fiber service area
    rows = db.query("SELECT * FROM bqtplus.gfiber_addresses LIMIT 1000")
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

    # Create LLM instance once, but reinitialize NetGent for each run to avoid cross-run state
    LLM_INSTANCE = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.2,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )

try:
    with open("examples/experiment/robustness/results/googlefiber_robustness_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

if not addresses:
    raise SystemExit("No addresses loaded from database.")

# Ensure directories exist and set wait time
os.makedirs("examples/experiment/robustness/results", exist_ok=True)
os.makedirs("examples/experiment/robustness/save/googlefiber_robustness", exist_ok=True)


# Run the agent N times, cycling through addresses if needed
RUN_COUNT = 100
for i in range(RUN_COUNT):
    row_data = addresses[0]
    address = row_data['address']
    only_address = row_data['only_address']
    city = row_data['city']
    zip_code = row_data['zip_code']

    print(f"Run {i+1}/{RUN_COUNT} - Address: {address}, City: {city}, Zip: {zip_code}")
    # Initialize a fresh NetGent agent for this iteration
    agent = NetGent(
        llm=LLM_INSTANCE,
        proxy=PROXY,
        llm_enabled=True,
        config={"allow_multiple_states": True},
    )
    agent.set_state_wait_time(10)

    try:
        result = agent.run(
            state_prompts=prompts,
            state_repository=state_repository,
            variables={
                "address": address,
                "only_address": only_address,
                "city": city,
                "state": row_data['state'],
                "zip_code": zip_code,
            },
            save_content_dir="examples/experiment/robustness/save/googlefiber_robustness",
            session=f"googlefiber_robustness",
        )

        state_repository = result["state_repository"]
    except Exception as e:
        print(f"Run {i+1} raised an exception: {e}")
    finally:
        try:
            if hasattr(agent, 'controller') and getattr(agent, 'controller') and getattr(agent.controller, 'driver', None):
                agent.controller.quit()
        except Exception:
            pass

# Write aggregated results
with open("examples/experiment/robustness/results/googlefiber_robustness_result.json", "w") as f:
    json.dump(state_repository, f, indent=2)