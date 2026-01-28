import json
import os
import sys
from netgent.errors import NetGentError
from bqtdb.main import BQTDatabase
from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

prompts = [
    StatePrompt(
        name="START",
        description="Navigate to Ezee Fiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://shop.ezeefiber.com/#/order/1 word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the Ezee Fiber page",
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
        triggers=["If you see 'Ezee Fiber is in your neighborhood. Order now!'"],
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
        description="Service not available (e.g. 'Ezee Fiber is working hard to expand our services. Lets keep in touch and you will be the first to know when we get to your area.')",
        triggers=["Get the Text from the page like 'Ezee Fiber is working hard to expand our services. Lets keep in touch and you will be the first to know when we get to your area.'"],
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
            "address": f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}",
            "zip_code": zip_code
        }
        addresses.append(address_entry)

# Pick an address (using same index as usually requested or 0)
address_data = addresses[4] 
address = address_data['address']
zip_code = address_data['zip_code']

print(f"Address: {address}, Zip: {zip_code}")

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

state_repository = []

result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address,
        "zip_code": zip_code
    },
    session="ezeefiber",
    save_content_dir="examples/isps/save/ezeefiber"
)

input("Press Enter to continue...")

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/ezeefiber_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)