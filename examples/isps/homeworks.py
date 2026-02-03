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
        description="Navigate to Homeworks new connection page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://homeworks.smarthub.coop/ui/#/newConnect word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="On Initial Page of Homeworks",
        description="Address not found or needs verification - (e.g. 'Shop for new service')",
        triggers=["If you see 'Enter your street address, including city ...'"],
        actions=["Scroll down", "Type `%address%` into the input field", "Press 'enter' to submit the form", "Press up and down arrow keys to verify address", "Scroll down and press 'Continue' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available in area",
        triggers=["If you see 'We're not currently offering services in your area, but we are gathering information from those who are interested. If there’s enough demand, we may consider expanding. We’ll keep your information on file and reach out if service becomes available in your area.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Fiber services available - (e.g. 'Contact Us')",
        triggers=["If you see 'Contact Us'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
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
            
        # SmartHub usually works well with "Address, City, State, Zip"
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}, {zip_code}"
        
        address_entry = {
            "address": full_address,
            "city": row['PropertyCity'],
            "state": row['PropertyState'],
            "zip_code": zip_code
        }
        addresses.append(address_entry)

if not addresses:
    print("No addresses found in database.")
    sys.exit(1)

state_repository = []
results = []

# Iterating 100 times with the first 10 addresses repeated
for i in range(15):
    # Cycle through the 10 addresses
    address_data = addresses[i % len(addresses)]
    address = f"{address_data['address']}" # Full address is already constructed

    # Generate fake contact info using Faker
    name_f = fake.first_name()
    name_l = fake.last_name()
    phone_num = fake.numerify("##########")
    email = fake.email()

    print(f"Run {i+1}: Address: {address}")

    # Initialize a fresh agent for each run
    agent = NetGent(
        llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), 
        # proxy="http://brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335",
        llm_enabled=True
    )
    
    agent.set_state_wait_time(10)

    try:
        result = agent.run(
            state_prompts=prompts, 
            state_repository=state_repository, 
            variables={
                "address": address, 
                "email": email,
            },
            session="homeworks",
            save_content_dir="examples/isps/save/homeworks",
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
with open("examples/isps/results/homeworks_robust_results.json", "w") as f:
    json.dump(results, f, indent=2)

# Also update the main result repository
with open("examples/isps/results/homeworks_result.json", "w") as f:
    json.dump({"state_repository": state_repository}, f, indent=2, default=str)

print("Robustness test completed.")