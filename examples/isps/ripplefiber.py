import json
import os
import sys
from netgent.errors import NetGentError


from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()
prompts = [
        StatePrompt(
            name="START",
            description="Navigate to the Ripple Fiber availability page",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://ripplefiber.com/availability-checker word for word", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="ADDRESS_BAR",
            description="Enter address to check availability",
            triggers=["If you see 'Check Availability' or 'Enter your address'"],
            actions=[
                "FOLLOW THESE INSTRUCTIONS CLOSELY",
                "Type `%address%` into the address input field",
                "Press down key and enter key if suggestions appear",
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
            end_state="serviceable_with_plans",
            save_content=True,
        ),
        StatePrompt(
            name="NO_SERVICE",
            description="Services not available in your area",
            triggers=["If you see 'Services are not available' or 'we are not in your area' or 'Sign up for updates'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="no_service",
            save_content=True,
        ),
    ]

addresses = [
    {"address": "682 Adagio Way, San Jose, CA 95111", "zip_code": "95111"},
    {"address": "8 Birch Ln, San Jose, CA 95127", "zip_code": "95127"},
    {"address": "7 Cedar Ln, San Jose, CA 95127", "zip_code": "95127"},
    {"address": "E Berry Dr, Mountain View, CA 94043", "zip_code": "94043"},
    {"address": "H Berry Dr, Mountain View, CA 94043", "zip_code": "94043"}
]

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

try:
    with open("examples/isps/results/ripplefiber_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[0]
address = row_data['address']
zip_code = row_data['zip_code']

print(f"Address: {address}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address, "zip_code": zip_code},
    save_content_dir="examples/isps/save/ripplefiber",
    session="ripplefiber"
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/ripplefiber_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)