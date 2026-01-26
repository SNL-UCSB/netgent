import json
import os
import sys
from netgent.errors import NetGentError
from bqtdb.main import BQTDatabase
from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
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
        end_state="no_service"
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Fiber services available - (e.g. 'Contact Us')",
        triggers=["If you see 'Contact Us'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans"
    ),
]

addresses = []
with BQTDatabase() as db:
    rows = db.query("SELECT * FROM bqtplus.xfinity_addresses LIMIT 1000")
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

# Pick an address
address_data = addresses[4] 
address = f"{address_data['address']}, {address_data['city']}, {address_data['state']}, {address_data['zip_code']}"

# Generate fake contact info using Faker
name_f = fake.first_name()
name_l = fake.last_name()
phone_num = fake.numerify("##########")
email = fake.email()

print(f"Address: {address}")

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

state_repository = []

if os.path.exists("examples/isps/results/homeworks_result.json"):
    with open("examples/isps/results/homeworks_result.json", "r") as f:
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
        "email": email,
    },
    session="homeworks"
)

input("Press Enter to continue...")

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/homeworks_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
