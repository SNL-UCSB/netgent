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


# Pick an address
state_repository = []
results = []

# Load state repository if it exists
if os.path.exists("examples/isps/results/buckeyebroadband_result.json"):
    with open("examples/isps/results/buckeyebroadband_result.json", "r") as f:
        try:
            data = json.load(f)
            if "state_repository" in data:
                state_repository = data["state_repository"]
                print(f"Loaded {len(state_repository)} states from previous session")
        except:
            pass

for i in range(15):
    try:
        address_data = addresses[i % len(addresses)] 
        address = address_data['address']
        
        print(f"Run {i+1}/15: Address: {address}")

        agent = NetGent(
            llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.getenv("GOOGLE_API_KEY")), 
            # proxy="http://brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335",
            proxy=os.getenv("PROXY_URL"), 
            llm_enabled=True
        )
        
        agent.set_state_wait_time(5)

        result = agent.run(
            state_prompts=prompts, 
            state_repository=state_repository, 
            variables={
                "address": address, 
            },
            session="buckeyebroadband",
            save_content_dir="examples/isps/save/buckeyebroadband",
            close_browser=True
        )
        
        # Persist learned state repository
        state_repository = result.get("state_repository", state_repository)
        results.append({
            "run": i + 1,
            "address": address,
            "end_state": result.get("end_state"),
            "success": True
        })
        
        print(f"Run {i+1} completed. End State: {result.get('end_state')}")

    except Exception as e:
        print(f"Error in run {i+1}: {e}")
        results.append({
            "run": i + 1,
            "address": address if 'address' in locals() else "Unknown",
            "error": str(e),
            "success": False
        })

# Save cumulative results
os.makedirs("examples/isps/results", exist_ok=True)
with open("examples/isps/results/buckeyebroadband_robust_results.json", "w") as f:
    json.dump(results, f, indent=2)

# Update the main result repository
with open("examples/isps/results/buckeyebroadband_result.json", "w") as f:
    json.dump({"state_repository": state_repository}, f, indent=2, default=str)

print("Robustness test completed.")