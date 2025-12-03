import json
import os

from bqtdb.main import BQTDatabase

from netgent import NetGent, StatePrompt
from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()
prompts = [
        StatePrompt(
            name="Navigate To Dobson",
            description="Navigated to the Dobson Website",
            triggers=["If it is on the chrome incognito mode"],
            actions=["Go to https://shop.dobson.net/#/order/1", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Asking fo Residental Address or Business Address",
            description="Asking for the residental address or business address",
            triggers=["Asking for the residental address or business address"],
            actions=["Choose the residental address", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Search for Address in Dobson Website",
            description="Searched for the address on the Dobson Website",
            triggers=["If on the website"],
            actions=["FOLLOW THESE INSTRUCTIONS CLOSELY", "Type `%address%` into input field", "press down key", "press enter key", "press the Next Button", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Internet Avaliable in Address on the Dobson Website",
            description="Internet is avaliable for this address",
            triggers=["If it shows that the address is avaliable"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Address is Avaliable"
        ),
        StatePrompt(
            name="Internet Is Not Avaliable in Address on the Dobson Website",
            description="Internet is not avaliable for this address",
            triggers=["ONLY GET THE BUMMER... TEXT ONLY"],
            actions=["TERMINATE AT THIS POINT"],
            end_state="Address is Not Avaliable"
        ),
    ]


# Connect to DB and fetch addresses
print("Fetching addresses from database...")
addresses = []
with BQTDatabase() as db:
    # Fetching 5 addresses for demonstration
    rows = db.query("SELECT * FROM bqtplus.dobson_addresses LIMIT 1000")
    for row in rows:
        # Construct address string
        # Clean up Zip code (remove .0 if present)
        zip_code = str(row['PropertyZip'])
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
            
        full_address = f"{row['PropertyFullStreetAddress']} {row['PropertyCity']} {row['PropertyState']} {zip_code} USA"
        addresses.append(full_address)

print(f"Found {len(addresses)} addresses to process.")

for i, address in enumerate(addresses):
    print(f"\nProcessing address {i+1}/{len(addresses)}: {address}")
    
    try:
        with open("examples/bqt/results/dobson_result.json", "r") as f:
            existing_data = json.load(f)
            # Ensure it's a list
            if isinstance(existing_data, dict):
                 state_repository = existing_data.get("state_repository", [])
            else:
                state_repository = existing_data
    except (FileNotFoundError, json.JSONDecodeError):
        state_repository = []
    
    # Initialize the agent
    agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2, vertexai=True, api_key=os.getenv("GOOGLE_API_KEY")), llm_enabled=True)
    
    # Run the agent
    result = agent.run(
        state_prompts=prompts, 
        state_repository=state_repository, 
        variables={"address": address}
    )

    # Close the browser
    agent.driver.quit()
    
    # Update repository for next iteration
    state_repository = result["state_repository"]
    
    # Save intermediate results
    with open("examples/bqt/results/dobson_result.json", "w") as f:
        json.dump(state_repository, f, indent=2)

print("\nAll addresses processed.")
input("Press Enter to continue...")
