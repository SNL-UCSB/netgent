import json
import os
import sys
from netgent.errors import NetGentError


from netgent import NetGent, StatePrompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()
from faker import Faker
fake = Faker()
prompts = [
        StatePrompt(
        name="START",
        description="Navigate to Fastwyre CrowdFiber page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://fastwyre.crowdfiber.com/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the fastwyre page",
        triggers=["If you see 'Please enter your address below'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into the input field", "Type `%zip_code%` into the input field", "Press enter to confirm selection", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="CONFIRM_ADDRESS",
        description="Confirm address location",
        triggers=["If you see 'Verify that the marker below is the correct location for your address'"],
        actions=["Scroll down", "press tab and enter", "Click the 'Next' button", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="INTERNET_AVAILABLE",
        description="Service available - enter contact info",
        triggers=["If you see 'Fastwyre is in your neighborhood. Order now!'"],
        actions=[
            "Scroll to put this contact information in the form",
            "Type `%email%`",
            "Type `%name_f%`",
            "Type `%name_l%`",
            "Type `%phone_num%`",
            "Click the 'Next' button",
            "TERMINATE AT THIS POINT"
        ],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Build your bundle",
        triggers=["If you see 'Build your bundle'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans",
        save_content=True,
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available",
        triggers=["If you see 'Aww shucks! Our service isn't available.'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service",
        save_content=True,
    ),
]

addresses = [
    {"address": "682 Adagio Way", "zip_code": "95111"},
    {"address": "8 Birch Ln", "zip_code": "95127"},
    {"address": "7 Cedar Ln", "zip_code": "95127"},
    {"address": "E Berry Dr", "zip_code": "94043"},
    {"address": "H Berry Dr", "zip_code": "94043"}
]

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), llm_enabled=True)

try:
    with open("examples/isps/results/fastwyre_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']
zip_code = row_data['zip_code']

# Generate fake contact info using Faker
name_f = fake.first_name()
name_l = fake.last_name()
phone_num = fake.numerify("##########")
email = fake.email()

print(f"Address: {address}, Zip: {zip_code}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address, 
        "zip_code": zip_code,
        "name_f": name_f,
        "name_l": name_l,
        "phone_num": phone_num,
        "email": email
    },
    save_content_dir="examples/isps/save/bluepeak2",
    session="bluepeak2"
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/fastwyre_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)