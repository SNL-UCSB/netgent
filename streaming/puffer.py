import json
import os
from netgent import NetGent, StatePrompt
from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()
agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2), llm_enabled=True, user_data_dir="examples/user_data")


prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["Go to https://puffer.stanford.edu/accounts/login"]
        ),
        StatePrompt(
            name="On Puffer Login Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["On login page, Username: 'snlclient1' and Password: 'SNL.12345', click the checkbox and press 'Login'"]
        ),
        StatePrompt(
            name="On Puffer Channel Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)"],
            actions=["[0] Click 'Watch TV' button", "[1] Wait for 5 seconds", "[2] Click on the 'Fox' channel", "[3] Wait for 5 seconds", "[4] Terminate"],
            end_state="Puffer Channel Page"
        ),
    ]


try:
    with open("streaming/puffer/results/puffer_result.json", "r") as f:
        result = json.load(f)
except FileNotFoundError:
    result = []

result = agent.run(state_prompts=prompt, state_repository=result)

input("Press Enter to continue...")
# Create directory if it doesn't exist
os.makedirs("streaming/puffer/results", exist_ok=True)
with open("streaming/puffer/results/puffer_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)