import json
import os
from netgent.errors import NetGentError
from bqtdb.main import BQTDatabase
from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

# Proxy string to use for outbound requests
PROXY = "brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335"

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to Nsight Telservices page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.nsighttel.com/services/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the Nsight Telservices page",
        triggers=["If you see 'Please enter your address below'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into the input field", "Click submit to confirm selection", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address location",
        triggers=["If you see 'Verify that the marker below is the correct location for your address'"],
        actions=["Scroll down", "press tab and enter", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="INTERNET_AVAILABLE",
        description="Service available - enter contact info",
        triggers=["If you see 'Nsight Telservices is in your neighborhood. Order now!'"],
        actions=[
            "Scroll to put this contact information in the form",
            "Click the 'Next' button",
            "TERMINATE AT THIS POINT"
        ],
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
        description="Service not available",
        triggers=["If you see 'We could not find you in our system!'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

# Try to load addresses from DB table; fallback to embedded list
addresses = []
try:
    with BQTDatabase() as db:
        rows = db.query("SELECT * FROM bqtplus.xfinity_addresses LIMIT 10")
        for row in rows:
            prop_zip = str(row.get('PropertyZip', ''))
            if prop_zip.endswith('.0'):
                prop_zip = prop_zip[:-2]
            full = f"{row.get('PropertyFullStreetAddress','')}, {row.get('PropertyCity','')}, {row.get('PropertyState','')}, {prop_zip}"
            addresses.append({
                'address': full,
                'zip_code': prop_zip,
                'city': row.get('PropertyCity',''),
                'state': row.get('PropertyState',''),
                'only_address': row.get('PropertyFullStreetAddress',''),
            })
except Exception:
    # DB table may not exist or connection failed; fall back
    addresses = [
        {"address": "15802 N 62ND ST, SCOTTSDALE, AZ 85254"},
        {"address": "4 1/2 12TH ST NW, ROCHESTER, MN 55901"},
        {"address": "G1027 W HEMPHILL RD, FLINT, MI 48507"},
        {"address": "B ST, COLORADO SPRINGS, CO 80906"},
        {"address": "J 5TH ST, COVINGTON, LA 70433"},
    ]

seed_addresses = addresses[:10] if len(addresses) >= 10 else addresses
if not seed_addresses:
    raise SystemExit("No addresses available for nsighttel experiment.")

os.makedirs("examples/isps/experiments/robustness/nsighttel", exist_ok=True)

state_repository = []

for i in range(100):
    addr = seed_addresses[i % len(seed_addresses)]
    address = addr.get('address')
    zip_code = addr.get('zip_code', '')

    agent = NetGent(
        llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")),
        proxy=PROXY,
        llm_enabled=True,
    )
    agent.set_state_wait_time(5)
    agent.set_action_wait_time(5)

    print(f"Run {i+1}: seed_idx={i % len(seed_addresses)} Address: {address}")

    try:
        result = agent.run(
            state_prompts=prompts,
            state_repository=state_repository,
            variables={"address": address, "zip_code": zip_code},
            session="nsighttel_robust",
            save_content_dir="examples/isps/experiments/robustness/nsighttel",
            close_browser=True,
        )
        if isinstance(result, dict) and 'state_repository' in result:
            state_repository = result['state_repository']
    except Exception as e:
        print(f"Error in run {i+1}: {e}")

with open("examples/isps/experiments/robustness/nsighttel_result.json", "w") as f:
    json.dump(state_repository, f, indent=2, default=str)
