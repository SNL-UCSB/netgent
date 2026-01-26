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
        description="Navigate to Joink page",
        triggers=["If it is on the chrome homescreen"],
        actions=["Go to https://www.joink.com/service-availability/ word for word", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="ADDRESS_BAR",
        description="If on the Joink page",
        triggers=["If you see 'Please enter your address below'"],
        actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into the input field", "Click submit to confirm selection", "TERMINATE AT THIS POINT"],
    ),
    StatePrompt(
        name="SERVICEABLE",
        description="Build your bundle",
        triggers=["If you see 'Build your bundle'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="serviceable_with_plans"
    ),
    StatePrompt(
        name="NO_SERVICE",
        description="Service not available (e.g. 'Thank you for your interest!')",
        triggers=["Check this text 'Thank you for your interest!'"],
        actions=["TERMINATE AT THIS POINT"],
        end_state="no_service"
    ),
]

addresses = [
    {"address": "15802 N 62ND ST, SCOTTSDALE, AZ 85254"},
    {"address": "4 1/2 12TH ST NW, ROCHESTER, MN 55901"},
    {"address": "G1027 W HEMPHILL RD, FLINT, MI 48507"},
    {"address": "B ST, COLORADO SPRINGS, CO 80906"},
    {"address": "J 5TH ST, COVINGTON, LA 70433"}
]

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY"), project=os.getenv("GOOGLE_CLOUD_PROJECT")), llm_enabled=True)

try:
    with open("examples/isps/results/joink_result.json", "r") as f:
        state_repository = json.load(f)
except FileNotFoundError:
    state_repository = []

row_data = addresses[4]
address = row_data['address']

print(f"Address: {address}")
    
result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={
        "address": address
    }
)

agent.set_state_wait_time(5)


input("Press Enter to continue...")
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/joink_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
