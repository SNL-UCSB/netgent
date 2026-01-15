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
            name="Navigate To Xfinity",
            description="Navigated to the Xfinity Website",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://www.xfinity.com/national", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Enter Address on Xfinity Homepage",
            description="Enter the address to check service availability",
            triggers=["If on the Xfinity homepage with an address input field"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click the address input field", "Type `%address%` into the address input field", "Wait for address suggestions to appear", "Press down key to select the first suggestion", "You must press the submit button to confirm", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Handle Existing Customer Question",
            description="Handle the question about existing Xfinity customer",
            triggers=["If asked 'Are you an existing Xfinity customer?' or similar"],
            actions=["Click 'No' or 'New Customer' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="If it is one of these options",
            description="If it is asking if it is one of these options, click the first option",
            triggers=["If it is asking if it is one of these options"],
            actions=["Click the first option and check availability", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Internet Available at Address on Xfinity",
            description="Internet service is available at this address",
            triggers=["If you see internet plans, pricing, or 'Shop plans' or 'View plans' options"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Service Available"
        ),
        StatePrompt(
            name="Internet Not Available at Address on Xfinity",
            description="Internet service is not available at this address",
            triggers=["If you see 'service not available', 'not in your area', or 'we don't offer service'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Service Not Available"
        ),
    ]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Xfinity service area
    rows = db.query("SELECT * FROM bqtplus.xfinity_addresses LIMIT 1000")
    for row in rows:
        # Construct address string
        # Clean up Zip code (remove .0 if present)
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
            
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}, {zip_code}"
        addresses.append(full_address)

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

state_repository = []

    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": addresses[7]}
)

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/xfinity_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)

agent.set_state_wait_time(5)


try:
    with open("examples/isps/results/xfinity_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompts, state_repository=result)

input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/xfinity_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)




