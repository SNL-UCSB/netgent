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
            name="Navigate To Astound",
            description="Navigated to the Astound Broadband Website",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://astound.com/", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Enter Address on Astound Homepage",
            description="Enter the address to check service availability",
            triggers=["If on the Astound homepage with an address input field"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the address input field", "Type `%address%` into the address input field and the `%zip_code%` into the zip code input field", "You must press `Check for Service` button to confirm", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Handle Existing Customer Question",
            description="Handle the question about existing Astound customer",
            triggers=["If asked 'Are you an existing Astound customer?' or similar"],
            actions=["Click 'No' or 'New Customer' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="If it is one of these options",
            description="If it is asking if it is one of these options, click the first option",
            triggers=["If it is asking if it is one of these options"],
            actions=["Click the first option and check availability", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Internet Available at Address on Astound",
            description="Internet service is available at this address",
            triggers=["If you see internet plans, pricing, or 'Shop plans' or 'View plans' options"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Service Available"
        ),
        StatePrompt(
            name="Internet Not Available at Address on Astound or They Say Internet is Coming Soon or Technical Issue",
            description="Internet service is not available at this address",
            triggers=["If you see 'service not available', 'not in your area', or 'we don't offer service' or 'coming soon (in the link or on the website)' or 'technical issue'"],
            actions=["TERMINATE AT THIS POINT AND DON'T PERFORM ANY ACTIONS"],
            end_state="Service Not Available"
        ),
        StatePrompt(
            name="Technical Issue",
            description="Technical issue at this address",
            triggers=["If you see 'technical issue'"],
            actions=["TERMINATE AT THIS POINT. Don't perform any actions. just quit."],
            end_state="Technical Issue"
        ),
    ]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Astound service area
    rows = db.query("SELECT * FROM bqtplus.astound_addresses LIMIT 1000")
    for row in rows:
        # Clean up Zip code (remove .0 if present)
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
        
        # Store address and zip code separately
        address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}"
        addresses.append({
            "address": address,
            "zip_code": zip_code
        })

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

try:
    with open("examples/isps/results/astound_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

address = addresses[4]["address"]
zip_code = addresses[4]["zip_code"]

    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "zip_code": zip_code}
)

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/astound_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)

agent.set_state_wait_time(5)


try:
    with open("examples/isps/results/astound_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompts, state_repository=result)

input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/astound_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
