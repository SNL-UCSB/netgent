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
            description="Navigate to the TDS address entry page",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://tdstelecom.com/visitor/address-entry.html word for word", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="ADDRESS_BAR",
            description="Enter address to view available services",
            triggers=["If you see 'Enter your address to view services available to you today'"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Accept' button if visible", "Click on the 'Address' input field", "Type `%only_address%` into the address input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click the 'Submit' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="EXISTING_SERVICE",
            description="Existing service found at this address",
            triggers=["If you see 'Existing Service Found at This Address'"],
            actions=["Click the 'Continue' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="HELLO_TDS",
            description="Address is served by HelloTDS.com",
            triggers=["If you see 'Your address is served by HelloTDS.com. Let's get you over there!'"],
            actions=["Click 'Visit hellotds.com' button", "Click 'Accept' button if visible", "TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans",
            save_content=True,
        ),
        StatePrompt(
            name="HELLO_TDS_RES_BUS",
            description="Select residential or business service type",
            triggers=["If you see 'Please select the type of service you're shopping for to proceed'"],
            actions=["Click 'Residential Services' button", "Click 'Accept' button if visible", "TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans",
            save_content=True,
        ),
        StatePrompt(
            name="SERVICE_AVAILABLE_PLANS",
            description="Choose a package - service is available",
            triggers=["If you see 'Choose a package and customize options to suit your needs.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans",
            save_content=True,
        ),
        StatePrompt(
            name="SERVICE_AVAILABLE_PLANS2",
            description="Inflation-Proof Internet available",
            triggers=["If you see 'Welcome to Inflation-Proof Internet' and 'Enjoy fiber Internet that moves fast. With a price that won't budge.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans",
            save_content=True,
        ),
        StatePrompt(
            name="INTERNET_ONLY",
            description="Internet-Only plan available",
            triggers=["If you see 'Internet-Only' and 'Pay the same low rate for 1 year!'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans",
            save_content=True,
        ),
        StatePrompt(
            name="INTERNET_SECURITY_LINE",
            description="Internet & FREE Security Phone Line available",
            triggers=["If you see 'Internet & FREE Security Phone Line' and 'Reliable High-Speed Internet with a free security phone line.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans",
            save_content=True,
        ),
        StatePrompt(
            name="DISH_TV",
            description="DISH TV & Phone available",
            triggers=["If you see 'DISH TV & Phone' and 'More TV. Less Money.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans",
            save_content=True,
        ),
        StatePrompt(
            name="NO_SERVICE",
            description="Service not available - future fiber build",
            triggers=["If you see 'Service is not available today, but this address is part of a future fiber build'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="no_service",
            save_content=True,
        ),
        StatePrompt(
            name="NO_SERVICE2",
            description="Address not found in systems",
            triggers=["If you see 'We're sorry, but your address was not found in our systems'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="no_service",
            save_content=True,
        ),
        StatePrompt(
            name="TDS_FIBER",
            description="Address is near fiber network build area",
            triggers=["If you see 'The address entered is near our fiber network build area!'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="no_service",
            save_content=True,
        ),
        StatePrompt(
            name="FIBER_SPEEDS_COMING",
            description="Fiber speeds coming to your area",
            triggers=["If you see 'Fiber speeds are coming to your area!' and 'TDS is bringing the future of Internet, TV and phone service to your neighborhood.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="unknown_address",
            save_content=True,
        ),
        StatePrompt(
            name="VERIFY_ADDRESS",
            description="Verify address prompt",
            triggers=["If you see 'Are you sure that's the right address?'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="unknown_address",
            save_content=True,
        ),
        StatePrompt(
            name="SECURE_LOGIN",
            description="TDS Secure Login page",
            triggers=["If you see 'TDS Secure Login'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="unknown_address",
            save_content=True,
        ),
        StatePrompt(
            name="BUSINESS_ADDRESS",
            description="Business address detected",
            triggers=["If you see 'Visit tdsbusiness.com'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="business_address",
            save_content=True,
        ),
        StatePrompt(
            name="SITE_ERROR",
            description="Site has encountered an error",
            triggers=["If you see 'We're sorry. This site has encountered an error.'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="access_error",
            save_content=True,
        ),
    ]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for TDS service area
    rows = db.query("SELECT * FROM bqtplus.tds_addresses LIMIT 1000")
    for row in rows:
        # Construct address string
        # Clean up Zip code (remove .0 if present)
        prop_zip = str(row['PropertyZip'])
        if prop_zip.endswith('.0'):
            prop_zip = prop_zip[:-2]
            
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}, {prop_zip}"
        only_address = row['PropertyFullStreetAddress']
        city = row['PropertyCity']
        state = row['PropertyState']
        addresses.append({
            'address': full_address,
            'only_address': only_address,
            'city': city,
            'state': state,
            'zip_code': prop_zip
        })

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy="brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335", llm_enabled=True)

try:
    with open("examples/isps/results/tds_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[6]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code},
    save_content_dir="examples/isps/save/tds",
    session="tds"
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/tds_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)