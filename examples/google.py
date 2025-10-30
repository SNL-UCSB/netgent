import json
from netgent import NetGent, StatePrompt
from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import ChatGoogleGenerativeAI
agent = NetGent(llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.2, api_key="AIzaSyDN-JBFHXwJsZLgXwQxW_0j5IFcleUUzZM"), llm_enabled=False)
prompt = [
        StatePrompt(
            name="On Browser Home Page",
            description="Start the Process",
            triggers=["If it is on the current condition of the page! (Create trigger based on current page)."],
            actions=["[1] Navigate to https://www.google.com/"]
        ),
        StatePrompt(
            name="Search for SeleniumBase Python",
            description="On Search Page",
            triggers=["If On Search Page (Find Search Text for the Trigger / Don't Use the URL as a Trigger)"],
            actions=["[1] Type the 'SeleniumBase Python' into the search box", "[2] Press Enter to search"],
        ),
        StatePrompt(
            name="Click on the first result",
            description="On First Result Page",
            triggers=["If On First Result Page (Find First Result Text for the Trigger)"],
            actions=["[1] Click on the first result"],
            end_state="Action Completed"
        ),
    ]

try:
    with open("examples/states/google_result.json", "r") as f:
        result_json = json.load(f)
except FileNotFoundError:
    result_json = []

result = agent.run(state_prompts=prompt, state_repository=result_json)

input("Press Enter to continue...")
with open("examples/states/google_result.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)