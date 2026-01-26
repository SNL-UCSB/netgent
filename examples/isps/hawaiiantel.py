import json
import os
import sys
from netgent.errors import NetGentError



from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
load_dotenv()
prompts = [
        StatePrompt(
            name="START",
            description="Navigate to the TrueStream Fiber availability page",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://shop.hawaiiantel.com/cart/addressVerification/Residential", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="ADDRESS_BAR",
            description="Enter address to check availability",
            triggers=["If you see 'AVAILABILITY AND STATUS'"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into the address input field", "Press down key to select the first suggestion", "Press enter key to confirm selection", "Click on the 'Check Address' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="An account already exists at this address",
            description="Service is available - Burnips 2 Installation",
            triggers=["If you see 'An account already exists at this address'"],
            actions=["Click I am a new customer at this address"],
        ),
        StatePrompt(
            name="CONFIRM_ADDRESS",
            description="Confirm address",
            triggers=["If you see 'Confirm your address'"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Click on the 'Confirm Address' button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="SERVICEABLE",
            description="Service is available - Burnips 2 Installation",
            triggers=["If you see 'Burnips 2: Installation &'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans"
        ),
        StatePrompt(
            name="NO_SERVICE",
            description="Services not available in your area",
            triggers=["If you see 'AVAILABILITY AND STATUS' and 'Services are not available in your area'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="no_service"
        ),
        StatePrompt(
            name="403_FORBIDDEN",
            description="403 Forbidden access error",
            triggers=["If you see '403 Forbidden'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="access_error"
        ),
    ]

addresses = [
    {"address": "682 AHUKINI ST HONOLULU 96825", "zip_code": "96825"},
    {"address": "710 AHUKINI ST HONOLULU 96825", "zip_code": "96825"},
    {"address": "801 AHUKINI ST HONOLULU 96825", "zip_code": "96825"},
    {"address": "202 AIOKOA ST KAILUA 96734", "zip_code": "96825"},
    {"address": "909 AHUKINI ST HONOLULU 96825", "zip_code": "96825"}
]

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

try:
    with open("examples/isps/results/hawaiiantel_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']
zip_code = row_data['zip_code']

print(f"Address: {address}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "zip_code": zip_code}
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/hawaiiantel_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
