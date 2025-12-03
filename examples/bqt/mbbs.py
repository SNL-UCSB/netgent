import json
import os
import sys
import pandas as pd
from netgent.errors import NetGentError

from bqtdb.main import BQTDatabase

from netgent import NetGent, StatePrompt
from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()
prompts = [
        StatePrompt(
            name="Navigate To Michigan Broadband Service Website",
            description="Navigated to the Michigan Broadband Service Website",
            triggers=["If it is on the chrome incognito mode"],
            actions=["Go to https://michbbs.com/internet#block-bfe9ac9d035e8cd1ff08", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Asking fo Residental Address or Business Address",
            description="Asking for the residental address or business address",
            triggers=["Asking for the residental address or business address"],
            actions=["Choose the residental address", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Search for Address in Michigan Broadband Service Website",
            description="Searched for the address on the Michigan Broadband Service Website",
            triggers=["ONLY GET THE TEXT 'Search Your Address' ONLY. NOTHING ELSE"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into address field", "Type the `%zip_code%` into zip code field", "press tab key and press the r key", "press enter key", "Press the 'Go' Button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="If it has `*If you would like to update the location of your address please drag and drop the blue pin to the rooftop of your service address.`",
            description="If it has `If you would like to update the location of your address please drag and drop the blue pin to the rooftop of your service address.`",
            triggers=["Get the text `+` text ONLY. NOTHING ELSE"],
            actions=["Scroll to the bottom of the page", "and press next button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Internet Avaliable in Address on the Michigan Broadband Service Website",
            description="Internet is avaliable for this address",
            triggers=["ONLY GET THE TEXT 'Great News!' ONLY. NOTHING ELSE"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Address is Avaliable"
        ),
        StatePrompt(
            name="Internet Is Not Avaliable in Address on the Michigan Broadband Service Website",
            description="Internet is not avaliable for this address",
            triggers=["ONLY GET THE TEXT 'Service is not currently available in your area.' ONLY. NOTHING ELSE"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Address is Not Avaliable"
        ),
        StatePrompt(
            name="Popup",
            description="Internet is not avaliable for this address",
            triggers=["Get the text `Join MBS mailing list.` ONLY. NOTHING ELSE"],
            actions=["Close Popup ONLY", "TERMINATE AT THIS POINT"],
        ),
    ]


# Connect to DB and fetch addresses
print("Fetching addresses from database...")
addresses = []
with BQTDatabase() as db:
    # Fetching 5 addresses for demonstration
    rows = db.query("SELECT * FROM bqtplus.michigan_addresses LIMIT 1000")
    for row in rows:
        # Construct address dictionary
        # Clean up Zip code (remove .0 if present)
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
            
        address_data = {
            "address": row['PropertyFullStreetAddress'],
            "zip_code": zip_code
        }
        addresses.append(address_data)

print(f"Found {len(addresses)} addresses to process.")

# Initialize CSV file
evals_dir = "examples/bqt/evals"
os.makedirs(evals_dir, exist_ok=True)
csv_path = os.path.join(evals_dir, "mbbs_results.csv")

if not os.path.exists(csv_path):
    df = pd.DataFrame(columns=['address', 'zip_code', 'error', 'service_available'])
    df.to_csv(csv_path, index=False)

for i, address_data in enumerate(addresses):
    print(f"\nProcessing address {i+1}/{len(addresses)}: {address_data}")
    
    try:
        with open("examples/bqt/results/mbbs_result.json", "r") as f:
            existing_data = json.load(f)
            # Ensure it's a list
            if isinstance(existing_data, dict):
                 state_repository = existing_data.get("state_repository", [])
            else:
                state_repository = existing_data
    except (FileNotFoundError, json.JSONDecodeError):
        state_repository = []
    
    # Initialize the agent
    agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY")), llm_enabled=False, proxy=os.getenv("PROXY_URL"))
    agent.set_state_wait_time(5)
    
    # Initialize variables for logging
    error_msg = None
    service_available = "Unknown"

    try:
        # Run the agent
        result = agent.run(
            state_prompts=prompts, 
            state_repository=state_repository, 
            variables=address_data
        )
        
        # Update repository for next iteration
        state_repository = result["state_repository"]
        
        # Extract end state
        passed_states = result.get("passed_states", [])
        if passed_states and passed_states[0].get("end_state"):
            service_available = passed_states[0].get("end_state")
        
    except NetGentError as e:
        print(f"Error processing address: {e}")
        error_msg = str(e)
        # Save screenshot on error
        if agent and agent.driver:
            try:
                errors_dir = "examples/bqt/evals/errors/mbbs"
                os.makedirs(errors_dir, exist_ok=True)
                safe_address = address_data['address'].replace(" ", "_")
                screenshot_path = os.path.join(errors_dir, f"{safe_address}.png")
                agent.driver.save_screenshot(screenshot_path)
                print(f"Saved screenshot to {screenshot_path}")
            except Exception as screenshot_err:
                print(f"Failed to save screenshot: {screenshot_err}")
        pass
    except Exception as e:
        print(f"Unexpected error: {e}")
        error_msg = str(e)
        # Save screenshot on error
        if agent and agent.driver:
            try:
                errors_dir = "examples/bqt/evals/errors/mbbs"
                os.makedirs(errors_dir, exist_ok=True)
                safe_address = address_data['address'].replace(" ", "_")
                screenshot_path = os.path.join(errors_dir, f"{safe_address}.png")
                agent.driver.save_screenshot(screenshot_path)
                print(f"Saved screenshot to {screenshot_path}")
            except Exception as screenshot_err:
                print(f"Failed to save screenshot: {screenshot_err}")
    finally:
        # Close the browser
        if agent and agent.driver:
            agent.driver.quit()
        
        # Log to CSV
        new_row = {
            'address': address_data['address'],
            'zip_code': address_data['zip_code'],
            'error': error_msg,
            'service_available': service_available
        }
        df_row = pd.DataFrame([new_row])
        df_row.to_csv(csv_path, mode='a', header=False, index=False)
        print(f"Logged result for {address_data['address']}")
    
    # Save intermediate results
    # with open("examples/bqt/results/mbbs_result.json", "w") as f:
    #    json.dump(state_repository, f, indent=2)

print("\nAll addresses processed.")
input("Press Enter to continue...")
