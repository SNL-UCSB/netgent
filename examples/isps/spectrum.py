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
        description="Navigate to the Spectrum address localization page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.spectrum.com/phx/address/localization word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="Enter address to check Spectrum service availability",
        triggers=["If you see 'Apt/Unit (optional)' or 'Specific location data is necessary to determine what you may already have and other services you can get with Spectrum'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click on the 'Street address' input field", "Type `%address%` into the address input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click the 'FIND OFFERS' button", "Wait for 20 seconds", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="VERIFY_APARTMENT",
        description="Apartment or unit number selection required",
        triggers=["If you see 'Please select your apartment or unit number'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="MDU",
        save_content=True,
    ),
    StatePrompt(
        name="CALL_TO_VERIFY",
        description="Call required to verify Spectrum services",
        triggers=["If you see 'Please call to verify if Spectrum services are available at this address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="unknown_address",
        save_content=True,
    ),
    StatePrompt(
        name="EXISTING_SERVICE",
        description="Address already has a Spectrum account",
        triggers=["If you see 'The address you provided already has a Spectrum account associated with it'"],
        actions=["Click 'I'm a new customer at this address'", "Click 'Continue' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="COX_NO_SERVICE",
        description="Cox services offer shown - no Spectrum service",
        triggers=["If you see 'I'm interested in Cox services'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="COX_NO_SERVICE_2",
        description="Cox popular services shown - no Spectrum service",
        triggers=["If you see 'Start by choosing from these popular services'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="EXISTING_SERVICE_SPEEDS",
        description="Existing service with available speeds",
        triggers=["If you see 'Get in touch now to start your services'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="SPEAK_TO_VERIFY",
        description="Verification call required before ordering",
        triggers=["If you see 'We need to speak with you to verify a few details before you can place an order'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="unknown_address",
        save_content=True,
    ),
    StatePrompt(
        name="SPECIAL_OFFERS",
        description="Special offers available at this address",
        triggers=["If you see 'Good news! Special offers are avilable at this address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="SERVICEABLE_PLANS",
        description="Compare Internet plans page",
        triggers=["If you see 'Compare Internet plans'"],
        actions=["Click 'View Broadband Plans'", "TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="BUSINESS_ADDRESS",
        description="Business address detected",
        triggers=["If you see 'Call now for our best offers on business solutions'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="unknown_address",
        save_content=True,
    ),
    StatePrompt(
        name="UNKNOWN_ADDRESS",
        description="Address could not be validated",
        triggers=["If you see 'We could not validate this address'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="unknown_address",
        save_content=True,
    ),
    StatePrompt(
        name="ACCESS_DENIED",
        description="Access denied error",
        triggers=["If you see 'Access Denied'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="access_error",
        save_content=True,
    ),
    StatePrompt(
        name="ERROR_OCCURED",
        description="An error occurred on the site",
        triggers=["If you see 'We're sorry, an error occured'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="access_error",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE_2",
        description="Address not in Spectrum service area",
        triggers=["If you see 'This address is not part of the Spectrum services area'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE_XFIN",
        description="May be serviceable by Xfinity instead",
        triggers=["If you see 'YOU MAY BE SERVICEABLE BY XFINITY'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE_HUGHES_2",
        description="HughesNet satellite service offered",
        triggers=["If you see 'hughesnet'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE_HUGHES",
        description="Satellite internet offered instead",
        triggers=["If you see 'Connect, stream and play wherever you live with satellite internet!'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE_RDOF",
        description="RDOF expansion area - no current service",
        triggers=["If you see 'Spectrum is expanding Internet service across America'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Spectrum service area
    rows = db.query("SELECT * FROM bqtplus.spectrum_addresses LIMIT 1000")
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
    with open("examples/isps/results/spectrum_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[0]
address = row_data['address']
only_address = row_data['only_address']
city = row_data['city']
zip_code = row_data['zip_code']

print(f"Address: {address}, City: {city}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "only_address": only_address, "city": city, "state": row_data['state'], "zip_code": zip_code},
    save_content_dir="examples/isps/save/spectrum",
    session="spectrum"
)

agent.set_state_wait_time(10)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/spectrum_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)