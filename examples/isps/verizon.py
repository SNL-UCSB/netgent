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
            description="Navigate to the Verizon check availability page",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://www.verizon.com/inhome/checkavailability word for word", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="ADDRESS_BAR",
            description="Enter address to check availability",
            triggers=["If you see 'Let's see what's available.'"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click on 'Type your address (without unit #)' input field", "Type `%address%` into the address input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click the 'Continue' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="ENTER_UNIT",
            description="Handle apartment/unit number selection",
            triggers=["If you see 'Apartment/Unit number'"],
            actions=["Click on 'Type your address (without unit #)' input field", "Press down key to select the first option", "Press enter key to confirm", "Click the 'Continue' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="INTERNET_AVAILABLE",
            description="Fios Home Internet is available",
            triggers=["If you see 'Good news, Fios Home Internet is available at your address.'"],
            actions=["Click the 'Order now' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="EXPLORE_OPTIONS2",
            description="Explore options with Order now button",
            triggers=["If you see 'Explore your options' and 'Order now'"],
            actions=["Click the 'Order now' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="EXPLORE_OPTIONS1",
            description="Explore options with Continue button",
            triggers=["If you see 'Explore your options'"],
            actions=["Click the 'Continue' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="SERVICEABLE",
            description="Verizon Home Internet is available (Choose your plan / LTE / 5G)",
            triggers=[
                "If you see 'Choose your plan'",
                "If you see 'Good news, LTE Home Internet is available at your address.'",
                "If you see 'Good news, 5G Home Internet is available at your address.'"
            ],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans",
            save_content=True,
        ),
        StatePrompt(
            name="NO_SERVICE",
            description="Verizon Home Internet isn't available / Be among the first to know",
            triggers=[
                "If you see 'Be among the first to know'",
                "If you see 'Verizon Home Internet isn't available at your address'"
            ],
            actions=["TERMINATE AT THIS POINT"],
            end_state="no_service",
            save_content=True,
        ),
        StatePrompt(
            name="EXISTING_ORDER",
            description="Address has a pending order",
            triggers=["If you see 'Looks like this address has a pending order.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="existing_service",
            save_content=True,
        ),
        StatePrompt(
            name="NO_DROPDOWN",
            description="Enter address and select from dropdown error",
            triggers=["If you see 'Enter address and select from dropdown.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="access_error",
            save_content=True,
        ),
        StatePrompt(
            name="PLEASE_CONTACT",
            description="Contact customer service required",
            triggers=["If you see 'Please contact the National Customer Service Center.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="unknown_address",
            save_content=True,
        ),
        StatePrompt(
            name="BUSINESS_ADDRESS",
            description="Business address detected",
            triggers=["If you see 'Looks like you entered a business address.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="business_address",
            save_content=True,
        ),
        StatePrompt(
            name="ERROR",
            description="Unable to process request",
            triggers=["If you see 'We're sorry. We are unable to process your request at this time.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="access_error",
            save_content=True,
        ),
        StatePrompt(
            name="ORDER_ERROR",
            description="Unable to continue order",
            triggers=["If you see 'We're unable to continue your order at this time.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="unknown_address",
            save_content=True,
        ),
    ]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Verizon service area
    rows = db.query("SELECT * FROM bqtplus.verizon_addresses LIMIT 1000")
    for row in rows:
        # Construct address string
        # Clean up Zip code (remove .0 if present)
        prop_zip = str(row['PropertyZip'])
        if prop_zip.endswith('.0'):
            prop_zip = prop_zip[:-2]
            
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}, {prop_zip}"
        city = row['PropertyCity']
        state = row['PropertyState']
        addresses.append({
            'address': full_address,
            'city': city,
            'state': state,
            'zip_code': prop_zip
        })

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

try:
    with open("examples/isps/results/verizon_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "city": city, "state": row_data['state'], "zip_code": zip_code},
    save_content_dir="examples/isps/save/verizon",
    session="verizon"
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/verizon_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)