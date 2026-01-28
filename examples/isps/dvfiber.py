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
        description="Navigate to DV Fiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://order.mydvfiber.net/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the DV Fiber page",
        triggers=["If you see 'Please enter your address below'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into the input field", "Press enter to confirm selection", "Click 'Check Availability' to confirm selection", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="VERIFY_ADDRESS",
        description="Verify address location",
        triggers=["If you see 'Verify address location'"],
        actions=["Press 'Confirm location' to confirm selection", "TERMINATE AT THIS POINT"],
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
        description="Service not available (e.g. 'Stay tuned! We’re not in your area just yet — but we can’t wait to get there!')",
        triggers=["If you see 'Stay tuned! We’re not in your area just yet — but we can’t wait to get there!'"],
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
            "address": f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']} {zip_code}",
            "zip_code": zip_code
        }
        addresses.append(address_entry)

# Pick an address
address_data = addresses[4] 
address = address_data['address']
zip_code = address_data['zip_code']

# Generate fake contact info using Faker
name_f = fake.first_name()
name_l = fake.last_name()
phone_num = fake.numerify("##########")
email = fake.email()

print(f"Address: {address}, Zip: {zip_code}")

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

state_repository = []

if os.path.exists("examples/isps/results/dvfiber_result.json"):
    with open("examples/isps/results/dvfiber_result.json", "r") as f:
        try:
            data = json.load(f)
            if "state_repository" in data:
                state_repository = data["state_repository"]
                print(f"Loaded {len(state_repository)} states from previous session")
        except:
            pass

result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address,
    },
    session="dvfiber",
    save_content_dir="examples/isps/save/dvfiber"
)

agent.set_state_wait_time(5)

input("Press Enter to continue...")

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/dvfiber_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)