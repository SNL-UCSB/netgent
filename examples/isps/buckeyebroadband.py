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
            name="Navigate To Buckeye Broadband",
            description="Navigated to the Buckeye Broadband Website",
            triggers=["If it is on the chrome homescreen"],
            actions=["Go to https://www.buckeyebroadband.com/packages word for word", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Enter Address on Buckeye Broadband Homepage",
            description="Enter the address to check service availability",
            triggers=["If on the Buckeye Broadband page with an address input field"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Scroll down to see the address input field", "Type `%address%` into the address input field", "Press down and enter to confirm", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Internet Available at Address on Buckeye Broadband",
            description="Internet service is available at this address - 'Showing available offers for'",
            triggers=["If you see 'Showing available offers for'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Service Available",
            save_content=True,
        ),
        StatePrompt(
            name="Internet Not Available at Address on Buckeye Broadband",
            description="Internet service is not available at this address (e.g - 'Your address is in survey phase, show your interest below')",
            triggers=["If you see 'service not available' or 'Your address is in survey phase, show your interest below'"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Service Not Available",
            save_content=True,
        ),
    ]

addresses = [
    {"address": "3698 RIDGEDALE LN , LAMBERTVILLE, MI, 48144"},
    {"address": "9683 MILLCROFT RD, PERRYSBURG, OH, 43551"},
    {"address": "7847 BRAEBURN RD, HOLLAND, OH, 43528"},
    {"address": "5937 BARKWOOD LN, SYLVANIA, OH, 43560"},
    {"address": "8967 SUMMERFIELD RD, LAMBERTVILLE, MI, 48144"}
]


address = addresses[4]

agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), proxy=os.getenv("PROXY_URL"), llm_enabled=True)

state_repository = []

result = agent.run(
    state_prompts=prompts, 
    state_repository=state_repository, 
    variables={"address": address["address"]},
    session="buckeyebroadband",
    save_content_dir="examples/isps/save/buckeyebroadband"
)

input("Press Enter to continue...")

# Write result to file
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/buckeyebroadband_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)