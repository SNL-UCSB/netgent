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
        description="Navigate to MTE Communications page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.mtecom.net/check-availability word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the MTE Communications page",
        triggers=["If you see 'Please enter your address below'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Close Pop Up", "Type `%address%` into the input field", "Click the 'Go' button", "DON'T DO ANYTHING ELSE AND TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Build your bundle",
        triggers=["If you see 'Build your bundle'"],
        actions=["DON'T DO ANYTHING ELSE AND TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available - (e.g. 'If you see internet is not available at your address' or 'Sorry, we can't provide service to this address.')",
        triggers=["Check the 'Sorry, we can't provide service to this address.'"],
        actions=["DON'T DO ANYTHING ELSE AND TERMINATE AT THIS POINT"],
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
            "address": f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}",
        }
        addresses.append(address_entry)

# Pick an address
state_repository = []
results = []

# Load state repository if it exists
if os.path.exists("examples/isps/results/mte_result.json"):
    with open("examples/isps/results/mte_result.json", "r") as f:
        try:
            data = json.load(f)
            if "state_repository" in data:
                state_repository = data["state_repository"]
                print(f"Loaded {len(state_repository)} states from previous session")
        except:
            pass

for i in range(15):
    try:
        address_data = addresses[i % len(addresses)] 
        address = address_data['address']
        
        # Generate fake contact info
        name_f = fake.first_name()
        name_l = fake.last_name()
        phone_num = fake.numerify("##########")
        email = fake.email()

        print(f"Run {i+1}/15: Address: {address}")

        agent = NetGent(
            llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), 
            # proxy="http://brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335",
            proxy=os.getenv("PROXY_URL"), 
            llm_enabled=True
        )
        
        agent.set_state_wait_time(5)

        result = agent.run(
            state_prompts=prompts, 
            state_repository=state_repository, 
            variables={
                "address": address, 
                "name_f": name_f,
                "name_l": name_l,
                "phone_num": phone_num,
                "email": email
            },
            session="mte",
            save_content_dir="examples/isps/save/mte",
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
        
        print(f"Run {i+1} completed. End State: {result.get('end_state')}")

    except Exception as e:
        print(f"Error in run {i+1}: {e}")
        results.append({
            "run": i + 1,
            "address": address if 'address' in locals() else "Unknown",
            "error": str(e),
            "success": False
        })

# Save cumulative results
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/mte_robust_results.json", "w") as f:
    json.dump(results, f, indent=2)

# Update the main result repository
with open("examples/isps/results/mte_result.json", "w") as f:
    json.dump({"state_repository": state_repository}, f, indent=2, default=str)

print("Robustness test completed.")