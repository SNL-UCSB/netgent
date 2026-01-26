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
        description="Navigate to Nuvera shop page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://shop.nuvera.net/#/order/1 word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Check for Fiber Fast Internet Availability and Pricing'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Enter your address' input field", "Type `%address%` into the input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click the 'NEXT' button", "JUST DONT DO ANYTHING AT THIS POINT AND TERMINATE"],
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see URL is 'https://nuvera.net/future-service/' and 'We’re not in your neighborhood yet…'"],
        actions=["JUST DONT DO ANYTHING AT THIS POINT AND TERMINATE"],
        end_state="no_service"
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Service available",
        triggers=["If you see 'We are serving your area at this time'"],
        actions=["JUST DONT DO ANYTHING AT THIS POINT AND TERMINATE"],
        end_state="serviceable"
    )
]

addresses = []
with BQTDatabase() as db:
    rows = db.query("SELECT * FROM bqtplus.xfinity_addresses LIMIT 1000")
    for row in rows:
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
            
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}, {zip_code}"
        only_address = row['PropertyFullStreetAddress']
        city = row['PropertyCity']
        state = row['PropertyState']
        
        addresses.append({
            'address': full_address,
            'only_address': only_address,
            'city': city,
            'state': state,
            'zip_code': zip_code
        })

# Pick an address
address_data = addresses[0] 
address = address_data['address']
only_address = address_data['only_address']
city = address_data['city']
state = address_data['state']
zip_code = address_data['zip_code']

# Generate fake contact info using Faker
name_f = fake.first_name()
name_l = fake.last_name()
phone_num = fake.numerify("##########")
email = fake.email()

print(f"Address: {address}, City: {city}, Zip: {zip_code}")

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

state_repository = []

if os.path.exists("examples/isps/results/nuvera_result.json"):
    with open("examples/isps/results/nuvera_result.json", "r") as f:
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
        "only_address": only_address, 
        "city": city, 
        "state": state, 
        "zip_code": zip_code,
        "email": email
    },
    session="nuvera"
)

input("Press Enter to continue...")

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/nuvera_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
