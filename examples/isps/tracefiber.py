import json
import os
import sys
from netgent.errors import NetGentError
from bqtdb.main import BQTDatabase
from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv

load_dotenv()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to Trace Fiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://connect.tracefiber.com/front_end word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the Trace Fiber page",
        triggers=["If you see 'Search by Address'"],
        actions=[
            "FOLLOW THESE INSTRUCTIONS CLOSELY", 
            "Type `%address%` into the 'Search For Your Address' input field", 
            "Type `%zip_code%` into the 'Zip Code' input field",
            "Press the Service Type Dropdown Menu",
            "Down arrow key 1 time and press enter",
            "Click the 'Search' button", 
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address location - (e.g. *If you would like to update the location of your address please drag and drop the blue pin to the rooftop of your service address.)",
        triggers=["If you see '*If you would like to update the location of your address please drag and drop the blue pin to the rooftop of your service address."],
        actions=["Scroll down", "Click the 'Confirm Location' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="If serviceable",
        triggers=["If you see 'Great news!'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable"
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available - (e.g. 'Make It Possible!' or similar)",
        triggers=["If you see 'Make It Possible!' or similar"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
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
            "zip_code": zip_code
        }
        addresses.append(address_entry)

# Pick an address
address_data = addresses[4] 
address = address_data['address']
zip_code = address_data['zip_code']

print(f"Address: {address}, Zip: {zip_code}")

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

state_repository = []

if os.path.exists("examples/isps/results/tracefiber_result.json"):
    with open("examples/isps/results/tracefiber_result.json", "r") as f:
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
        "zip_code": zip_code,
    },
    session="tracefiber"
)

input("Press Enter to continue...")

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/tracefiber_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
