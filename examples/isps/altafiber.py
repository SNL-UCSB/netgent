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
            description="Navigate to the Altafiber homepage",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://www.altafiber.com/", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="ADDRESS_BAR",
            description="Enter address to check availability",
            triggers=["If you see 'Check Availability' or 'Enter your address' or 'Shop' buttons"],
            actions=[
                "FOLLOW THESE INSTRUCTIONS CLOSELY",
                "Click on 'Check Availability' or find the address input field",
                "Type `%address%` into the address input field",
                "If asked for email, type `%email%`",
                "Press enter to submit",
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
    {"address": "7 Cedar Court Dr, Richmond IN"},
    {"address": "R W 4th St Fl 4, Newport KY"},
    {"address": "D02 County Road 17, Holgate OH"},
    {"address": "C02 Mountainview, Middlesboro KY"},
    {"address": "E015 County Road 8, Hamler OH"}
]

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

try:
    with open("examples/isps/results/altafiber_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[2]
address = row_data['address']
email = fake.email()

print(f"Address: {address}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "email": email}
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/altafiber_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
