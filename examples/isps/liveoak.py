import json
import os
import sys
from netgent.errors import NetGentError
from faker import Faker

from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
load_dotenv()

fake = Faker()

prompts = [
        StatePrompt(
            name="START",
            description="Navigate to the LiveOak Fiber availability page",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://loforder.liveoakfiber.com/", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="ADDRESS_BAR",
            description="Enter address to check availability",
            triggers=["If you see 'Check Availability' or 'Enter your address'"],
            actions=[
                "FOLLOW THESE INSTRUCTIONS CLOSELY",
                "Type `%address%` into the address input field",
                "Press down key and enter key if suggestions appear",
                "Type `%first_name%` into the First Name input field",
                "Type `%last_name%` into the Last Name input field",
                "Type `%email%` into the Email input field",
                "Type `%phone_number%` into the Mobile Phone input field",
                "Click on the 'Check Availability' button",
                "TERMINATE AT THIS POINT"
            ],
        ),
        StatePrompt(
            name="CONFIRM_ADDRESS",
            description="Confirm address",
            triggers=["If you see 'Confirm your address' or select address form list"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Select the correct address from the dropdown list", "Click confirm/next", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="SERVICEABLE",
            description="Service is available",
            triggers=["If you see 'Great news!' or 'Service Available' or 'Select a plan'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="serviceable_with_plans"
        ),
        StatePrompt(
            name="NO_SERVICE",
            description="Services not available in your area",
            triggers=["If you see 'Services are not available' or 'we are not in your area' or 'Sign up for updates'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="no_service"
        ),
    ]

addresses = [
    {"address": "682 Adagio Way, San Jose, CA 95111", "zip_code": "95111"},
    {"address": "8 Birch Ln, San Jose, CA 95127", "zip_code": "95127"},
    {"address": "7 Cedar Ln, San Jose, CA 95127", "zip_code": "95127"},
    {"address": "E Berry Dr, Mountain View, CA 94043", "zip_code": "94043"},
    {"address": "H Berry Dr, Mountain View, CA 94043", "zip_code": "94043"}
]

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), llm_enabled=True)

try:
    with open("examples/isps/results/liveoak_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']
zip_code = row_data['zip_code']
first_name = fake.first_name()
last_name = fake.last_name()
email = fake.email()
phone_number = fake.phone_number()

print(f"Address: {address}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address, 
        "zip_code": zip_code,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone_number": phone_number
    }
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/liveoak_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
