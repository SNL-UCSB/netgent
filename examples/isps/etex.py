import json
import os
import sys
import uuid
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
        description="Navigate to ETEX CrowdFiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://etex.crowdfiber.com/front_end/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the ETEX page",
        triggers=["If you see 'Please enter your address below'"],
        actions=["Scroll down a little bit", "FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into the input field", "Type `%zip_code%` into the input field", "Click the 'Go' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address location",
        triggers=["If you see 'Verify that the marker below is the correct location for your address'"],
        actions=["Scroll down", "Click the 'Next' button", "TERMINATE AT THIS POINT AND DO NOT DO ANYTHING ELSE"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Build your bundle",
        triggers=["If you see 'Build your bundle'"],
        actions=["TERMINATE AT THIS POINT AND DO NOT DO ANYTHING ELSE"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available - (e.g. 'If you see internet is not available at your address')",
        triggers=["If you see 'Aww shucks! Our service isn't available.'"],
        actions=["TERMINATE AT THIS POINT AND DO NOT DO ANYTHING ELSE"],
        end_state="no_service",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    rows = db.query("SELECT * FROM bqtplus.xfinity_addresses LIMIT 10")
    for row in rows:
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
            
        address_entry = {
            "address": f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}",
            "zip_code": zip_code
        }
        addresses.append(address_entry)

if not addresses:
    print("No addresses found in database.")
    sys.exit(1)

state_repository = []
results = []

# Iterating 15 times with the first 10 addresses repeated
for i in range(15):
    # Cycle through the 10 addresses
    address_data = addresses[i % len(addresses)]
    address = address_data['address']
    zip_code = address_data['zip_code']

    # Generate fake contact info using Faker
    name_f = fake.first_name()
    name_l = fake.last_name()
    phone_num = fake.numerify("##########")
    email = fake.email()

    print(f"Run {i+1}: Address: {address}, Zip: {zip_code}")

    # Initialize a fresh agent for each run
    agent = NetGent(
        llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), 
        # proxy="http://brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335",
        llm_enabled=True
    )
    
    agent.set_state_wait_time(10)
    
    # Load state repository if it exists
    if os.path.exists("examples/isps/results/etex_result.json"):
        with open("examples/isps/results/etex_result.json", "r") as f:
            try:
                data = json.load(f)
                if "state_repository" in data:
                    existing_repo = data["state_repository"]
                    # Merge existing repo into current one
                    state_repository = existing_repo
            except:
                pass

    try:
        result = agent.run(
            state_prompts=prompts, 
            state_repository=state_repository, 
            variables={
                "address": address, 
                "zip_code": zip_code,
                "name_f": name_f,
                "name_l": name_l,
                "phone_num": phone_num,
                "email": email
            },
            session="etex",
            save_content_dir="examples/isps/save/etex",
            close_browser=True
        )
        
        # Persist learned state repository
        state_repository = result.get("state_repository", state_repository)
        results.append({
            "run": i + 1,
            "address": address,
            "end_state": result.get("end_state"),
            "success": True
        })
        
    except Exception as e:
        print(f"Error in run {i+1}: {e}")
        results.append({
            "run": i + 1,
            "address": address,
            "error": str(e),
            "success": False
        })

# Save results
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/etex_robust_results.json", "w") as f:
    json.dump(results, f, indent=2)

# Also update the main result repository
with open("examples/isps/results/etex_result.json", "w") as f:
    json.dump({"state_repository": state_repository}, f, indent=2, default=str)

print("Robustness test completed.")