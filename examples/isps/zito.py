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
            description="Navigate to the Zito Media service contact page",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://www.zitomedia.net/service-contact/ word for word", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="MAYBE_SERVICE",
            description="Zito may provide service at your address",
            triggers=["If you see 'WE MAY PROVIDE SERVICE AT YOUR ADDRESS'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="maybe_serviceable"
        ),
        StatePrompt(
            name="ADDRESS_BAR",
            description="Enter address to check availability",
            triggers=["If you see 'CHECK AVAILABILITY'"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click on the 'STREET ADDRESS' input field", "Type `%address%` into the address input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click the 'CONTINUE' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Handle Existing Customer Question",
            description="Handle the question about existing Zito customer",
            triggers=["If asked 'Are you an existing Zito customer?' or similar"],
            actions=["Click 'No' or 'New Customer' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="If it is one of these options",
            description="If it is asking if it is one of these options, click the first option",
            triggers=["If it is asking if it is one of these options"],
            actions=["Click the first option and check availability", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Internet Available at Address on Zito",
            description="Internet service is available at this address",
            triggers=["If you see internet plans, pricing, or 'Shop plans' or 'View plans' options"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Service Available"
        ),
        StatePrompt(
            name="Internet Not Available at Address on Zito",
            description="Internet service is not available at this address",
            triggers=["If you see 'service not available', 'not in your area', or 'we don't offer service'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Service Not Available"
        ),
    ]

addresses = []
with BQTDatabase() as db:
    # Fetching addresses for Zito service area
    rows = db.query("SELECT * FROM bqtplus.zito_addresses LIMIT 1000")
    for row in rows:
        # Construct address string
        # Clean up Zip code (remove .0 if present)
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
            
        full_address = f"{row['PropertyFullStreetAddress']}, {row['PropertyCity']}, {row['PropertyState']}, {zip_code}"
        addresses.append(full_address)

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

try:
    with open("examples/isps/results/zito_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

address = addresses[9]

print(address)
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address}
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/zito_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
