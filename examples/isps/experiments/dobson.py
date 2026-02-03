import json
import os
from bqtdb.main import BQTDatabase
from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to Dobson shop page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://shop.dobson.net/#/order/1 word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Check for Fiber Fast Internet Availability and Pricing'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Enter your address' input field", "Type `%address%` into the input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click the 'NEXT' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see 'We are not serving your area at this time'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Service available",
        triggers=["If you see 'We are serving your area at this time'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable",
        save_content=True,
    ),
    StatePrompt(
        name="UNKNOWN_ERROR",
        description="Unknown error",
        triggers=["If you see 'We apologize something went wrong with your search'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="not_found",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    rows = db.query("SELECT * FROM bqtplus.dobson_addresses LIMIT 10")
    for row in rows:
        prop_zip = str(row.get('PropertyZip',''))
        if prop_zip.endswith('.0'):
            prop_zip = prop_zip[:-2]
        full_address = f"{row.get('PropertyFullStreetAddress','')}, {row.get('PropertyCity','')}, {row.get('PropertyState','')}, {prop_zip}"
        addresses.append({
            'address': full_address,
            'only_address': row.get('PropertyFullStreetAddress',''),
            'city': row.get('PropertyCity',''),
            'state': row.get('PropertyState',''),
            'zip_code': prop_zip,
        })

if not addresses:
    raise SystemExit("No addresses available for dobson experiment")

os.makedirs("examples/isps/experiments/robustness/dobson", exist_ok=True)

state_repository = []

PROXY = os.getenv("GFIBER_PROXY") or "brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335"

for i in range(100):
    addr = addresses[i % len(addresses)]
    address = addr['address']
    zip_code = addr['zip_code']

    agent = NetGent(
        llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")),
        proxy=PROXY,
        llm_enabled=True,
    )
    agent.set_state_wait_time(5)
    agent.set_action_wait_time(5)

    print(f"Run {i+1}: Address: {address}")

    try:
        result = agent.run(
            state_prompts=prompts,
            state_repository=state_repository,
            variables={"address": address, "zip_code": zip_code},
            session="dobson_robust",
            save_content_dir="examples/isps/experiments/robustness/dobson",
            close_browser=True,
        )
        if isinstance(result, dict) and 'state_repository' in result:
            state_repository = result['state_repository']
    except Exception as e:
        print(f"Error in run {i+1}: {e}")

with open("examples/isps/experiments/robustness/dobson_result.json", "w") as f:
    json.dump(state_repository, f, indent=2, default=str)
