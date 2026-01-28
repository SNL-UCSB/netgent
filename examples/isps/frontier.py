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
        description="Navigate to Frontier buy page",
        triggers=["If it is on the chrome homescreen. Check for link for this page."],
        actions=["Go to https://frontier.com/buy/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see 'Were sorry, Frontier Internet is not available at that address' or 'We're Here to Help You Get Connected!'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check availability",
        triggers=["If you see 'Enter your address to view plans and exclusive offers.'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the 'Enter your address' input field which appears 2nd", "Type `%address%` into the input field", "Press enter key", "Click the 'CHECK AVAILABILITY' button which appears 2nd", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="CONFIRM_MOVING",
        description="Confirm moving to address",
        triggers=["If you see 'Are you moving to this address?' and 'Enter your address to view plans and exclusive offers.'"],
        actions=["Click the 'YES,IMMOVING' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="MULTIPLE_PLANS_POPUP",
        description="Multiple plans popup",
        triggers=["If you see 'Find your way to better internet'"],
        actions=["Click the 'SHOP ALL PLANS' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE_PLANS",
        description="Service available - fiber area",
        triggers=["If you see 'Your home is in a fiber-optic service area'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="EXISTING_SERVICE",
        description="Existing service at address",
        triggers=["If you see 'Looks like this address currently has'"],
        actions=["Click the 'VIEW PLANS' button which appears 1st", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_NOT_AVAILABLE",
        description="Address not available",
        triggers=["If you see 'Frontier is not available at this address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="AREA_NOT_AVAILABLE",
        description="Area not available",
        triggers=["If you see 'Frontier Fiber is not available in your area.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="UNKNOWN_ADDRESS",
        description="Unknown address",
        triggers=["If you see 'We\\'re having trouble finding your selected address.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="unknown_address",
        save_content=True,
    ),
    StatePrompt(
        name="ZIPLY_ACQUIRED",
        description="Ziply acquired area",
        triggers=["If you see 'Ziply Fiber acquired Frontier in your area'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="unknown_address",
        save_content=True,
    ),
    StatePrompt(
        name="CLINK_CHECK",
        description="CenturyLink check",
        triggers=["If you see 'Check to see if CenturyLink services are available at your address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="ATT",
        description="AT&T redirect",
        triggers=["If you see 'AT&T'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="ALLCONNECT_NOT_AVAILABLE",
        description="Allconnect redirect",
        triggers=["If you see 'If you are interested in finding an internet provider in your area, search for providers through Allconnect below'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="VERIZON_INTERNET",
        description="Verizon redirect",
        triggers=["If you see 'Check if Verizon Home Internet is available'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="TECHNICAL_DIFFICULTIES",
        description="Technical difficulties",
        triggers=["If you see 'Sorry, we\\'re having some technical difficulties.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="access_error",
        save_content=True,
    ),
    StatePrompt(
        name="FORBIDDEN",
        description="403 Forbidden",
        triggers=["If you see '403 Forbidden'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="access_error",
        save_content=True,
    )
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Frontier service area
    rows = db.query("SELECT * FROM bqtplus.frontier_addresses LIMIT 1000")
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

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), llm_enabled=True)

try:
    with open("examples/isps/results/frontier_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code},
    save_content_dir="examples/isps/save/frontier",
    session="frontier"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/frontier_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)