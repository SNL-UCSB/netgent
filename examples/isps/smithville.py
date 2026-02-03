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
        description="Navigate to Smithville page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://join.smithville.com/front_end word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the Smithville page",
        triggers=["If you see 'Enter your address below to get started:'"],
        actions=[
            "FOLLOW THESE INSTRUCTIONS CLOSELY", 
            "Type `%address%` into the 'Search For Your Address' input field", 
            "Type `%zip_code%` into the 'Zip Code' input field",
            "Click the 'GO' button", 
            "TERMINATE AT THIS POINT AND DON'T DO ANYTHING ELSE"
        ],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address location",
        triggers=["If you see 'To provide you with the best service possible, please verify that the blue pin on the map below is at the exact location of your service address.'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Scroll down", "Click the 'Next' button", "TERMINATE AT THIS POINT AND DON'T DO ANYTHING ELSE"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Build your bundle",
        triggers=["If you see 'Build your bundle'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "TERMINATE AT THIS POINT AND DON'T DO ANYTHING ELSE"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available (e.g. 'Well, shoot!')",
        triggers=["Get the Text from the page like 'Well, shoot!'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "TERMINATE AT THIS POINT AND DON'T DO ANYTHING ELSE"],
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

# Iterating 100 times with the first 10 addresses repeated
for i in range(10):
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
        # proxy="brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335",
        llm_enabled=True
    )
    
    agent.set_state_wait_time(10)

    try:
        result = agent.run(
            state_prompts=prompts, 
            state_repository=state_repository, 
            variables={
                "address": address, 
                "zip_code": zip_code,
            },
            session="smithville",
            save_content_dir="examples/isps/save/smithville",
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
with open("examples/isps/results/smithville_robust_results.json", "w") as f:
    json.dump(results, f, indent=2)

# Also update the main result repository
with open("examples/isps/results/smithville_result.json", "w") as f:
    json.dump({"state_repository": state_repository}, f, indent=2, default=str)

print("Robustness test completed.")