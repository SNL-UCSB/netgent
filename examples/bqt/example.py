
# """
# Example usage of the BQT Database.

# This demonstrates connecting to the BQT+ PostgreSQL database and querying data.
# """

# from bqtdb import BQTDatabase


# def example_usage():
#     """Example usage of the BQT Database connection."""
#     try:
#         with BQTDatabase() as db:
#             # Query information_schema.tables to get table information
#             query = """
#                 SELECT table_schema, table_name, table_type
#                 FROM information_schema.tables
#                 WHERE table_schema = %s
#                 ORDER BY table_name;
#             """
#             tables = db.execute_query(query, (db.schema,))
            
#             print(f"\nTables in schema '{db.schema}':")
#             print("-" * 60)
#             for table in tables:
#                 print(f"Schema: {table['table_schema']}, Table: {table['table_name']}, Type: {table['table_type']}")
            
#             return tables
            
#     except Exception as e:
#         print(f"Error: {e}")


# if __name__ == "__main__":
#     example_usage()

import json
from netgent import NetGent, StatePrompt
from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()
agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2, vertexai=True, api_key="AQ.Ab8RN6LLLUAcOK2HebZTMs8cmjK9FI11GyC2QDjog0SN236yVA"), llm_enabled=True)
prompts = [
        StatePrompt(
            name="Navigate To 123net",
            description="Navigated to the 123net Website",
            triggers=["If it is on the chrome incognito mode"],
            actions=["Go to https://www.123.net/home-fiber-internet/sign-up/", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Search for Address in 123net Website",
            description="Searched for the address on the 123net Website",
            triggers=["If 'See Pricing In Your Area' is visible (CHECK THE TEXT AND ELEMENT)", "If on the 123net Website"],
            actions=["Type `%address%` into input field", "press down key", "press enter key", "TERMINATE AT THIS POINT"],
        ),
        StatePrompt(
            name="Internet Avaliable in Address on the 123net Website",
            description="Internet is avaliable for this address",
            triggers=["If it shows that the address is avaliable"],
            actions=["TERMINATE AT THIS POINT"],
            save_html_dom="internet_avaliable_in_address.html",
            terminate="Address is Avaliable"
        ),
        StatePrompt(
            name="Internet Is Not Avaliable in Address on the 123net Website",
            description="Internet is not avaliable for this address",
            triggers=["If it shows that the address is not avaliable"],
            actions=["TERMINATE AT THIS POINT"],
            terminate="Address is Not Avaliable"
        ),
    ]
try:
    with open("examples/bqt/results/123net_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompts, state_repository=result, variables={"address": "123 Main St, Anytown, USA"})

input("Press Enter to continue...")
with open("examples/bqt/results/123net_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)
