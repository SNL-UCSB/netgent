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
            name="Navigate To Ozark Fiber",
            description="Navigated to the Ozark Fiber Website",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://myozarkfiber.camvio.cloud/guest-order word for word", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Enter Address on Ozark Fiber Homepage",
            description="Enter the address to check service availability",
            triggers=["If on the Ozark Fiber page with an address input field"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Scroll down to see the address input field", "Type `%address%` and `%zip_code%` into the address input field", "Press down and enter to confirm", "Press Check Availability button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Internet Available at Address on Ozark Fiber",
            description="Internet service is available at this address",
            triggers=["If you see 'service available'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Service Available",
            save_content=True,
        ),
        StatePrompt(
            name="Internet Not Available at Address on Ozark Fiber",
            description="Internet service is not available at this address (e.g - 'Your address is in survey phase, show your interest below')",
            triggers=["If you see 'service not available' or 'Your address is in survey phase, show your interest below'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Service Not Available",
            save_content=True,
        ),
    ]

# addresses = [
#     {"address": "15802 N 62ND ST, SCOTTSDALE, AZ", "zip_code": "85254"},
#     {"address": "4 1/2 12TH ST NW, ROCHESTER, MN", "zip_code": "55901"},
#     {"address": "G1027 W HEMPHILL RD, FLINT, MI", "zip_code": "48507"},
#     {"address": "B ST, COLORADO SPRINGS, CO", "zip_code": "80906"},
#     {"address": "J 5TH ST, COVINGTON, LA", "zip_code": "70433"}
# ]

addresses = []
with BQTDatabase() as db:
    rows = db.query("SELECT * FROM bqtplus.xfinity_addresses LIMIT 1000")
    for row in rows:
        # Construct address string
        # Clean up Zip code (remove .0 if present)
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
            
        address_entry = {
            "address": f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}",
            "zip_code": zip_code
        }
        addresses.append(address_entry)

address = addresses[5]

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

state_repository = []

result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address["address"], "zip_code": address["zip_code"]},
    session="ozarkfiber",
    save_content_dir="examples/isps/save/ozarkfiber"
)

input("Press Enter to continue...")

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/ozarkfiber_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)