"""
Test script for StateSynthesis component.

This demonstrates:
1. How to initialize StateSynthesis with an LLM and controller
2. How to define state prompts for different scenarios
3. How the state synthesis workflow selects states, defines triggers, and generates action prompts
4. Integration with the existing trigger registry system
"""

from netgent.browser import BrowserSession, PyAutoGUIController
from netgent.components.state_synthesis.state_synthesis import StateSynthesis
from utils.message import StatePrompt
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Setup browser and controller
print("Setting up browser and controller...")
session = BrowserSession()
controller = PyAutoGUIController(session.driver)

# Initialize LLM (using Google Gemini as specified in pyproject.toml)
print("Initializing LLM...")
llm = ChatVertexAI(
    model="gemini-2.0-flash-exp",
    temperature=0.2,
)

# Initialize StateSynthesis
print("Initializing StateSynthesis...")
state_synthesis = StateSynthesis(llm=llm, controller=controller)

# Define some example states for a Google search workflow
states = [
    StatePrompt(
        name="search_state",
        description="Search for a query on Google",
        triggers=[
            "The search box is visible on the page",
            "The URL is the Google homepage"
        ],
        actions=[
            "Type the search query into the search box",
            "Press Enter to search"
        ],
        end_state="Search results page is loaded"
    ),
    StatePrompt(
        name="results_state",
        description="View search results and click on the first result",
        triggers=[
            "Search results are visible on the page",
            "The URL contains 'search?q=' parameter"
        ],
        actions=[
            "Scroll through the search results",
            "Click on the first search result"
        ],
        end_state="First result page is loaded"
    ),
    StatePrompt(
        name="completion_state",
        description="Task completed successfully",
        triggers=[
            "The page has loaded completely",
            "URL has changed from Google search"
        ],
        actions=[
            "Terminate the task"
        ],
        end_state="Task finished"
    )
]

# Navigate to Google
print("\n--- Navigating to Google ---")
controller.navigate("https://www.google.com")
controller.wait(3)

# Test 1: State selection on Google homepage
print("\n--- Test 1: State Selection on Google Homepage ---")
executed_history = []
parameters = {"query": "SeleniumBase Python"}

try:
    result = state_synthesis.run(
        prompts=states,
        executed=executed_history,
        parameters=parameters
    )
    
    print(f"Selected State: {result['choice'].name if result['choice'] else 'None'}")
    print(f"State Description: {result['choice'].description if result['choice'] else 'N/A'}")
    print(f"\nDefined Triggers ({len(result['triggers'])} triggers):")
    for i, trigger in enumerate(result['triggers'], 1):
        print(f"  {i}. Type: {trigger['type']}")
        print(f"     Params: {trigger['params']}")
    
    print(f"\nGenerated Prompt Preview:")
    print("=" * 80)
    print(result['prompt'][:500] + "..." if len(result['prompt']) > 500 else result['prompt'])
    print("=" * 80)
    
except Exception as e:
    print(f"Error during state synthesis: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Perform search and test state selection on results page
print("\n--- Test 2: Performing Search ---")
try:
    controller.type_text("css selector", "textarea[name='q']", "SeleniumBase Python")
    controller.press_key("enter")
    controller.wait(3)
    
    print("\n--- Test 3: State Selection on Results Page ---")
    executed_history = [
        {
            "name": "search_state",
            "description": "Searched for 'SeleniumBase Python' on Google"
        }
    ]
    
    result = state_synthesis.run(
        prompts=states,
        executed=executed_history,
        parameters=parameters
    )
    
    print(f"Selected State: {result['choice'].name if result['choice'] else 'None'}")
    print(f"State Description: {result['choice'].description if result['choice'] else 'N/A'}")
    print(f"\nDefined Triggers ({len(result['triggers'])} triggers):")
    for i, trigger in enumerate(result['triggers'], 1):
        print(f"  {i}. Type: {trigger['type']}")
        print(f"     Params: {trigger['params']}")
    
    print(f"\nGenerated Prompt Preview:")
    print("=" * 80)
    print(result['prompt'][:500] + "..." if len(result['prompt']) > 500 else result['prompt'])
    print("=" * 80)
    
except Exception as e:
    print(f"Error during test: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Demonstrate trigger validation with ProgramController
print("\n--- Test 4: Validating Generated Triggers ---")
from netgent.components.program_controller.controller import ProgramController

try:
    # Create a state with the generated triggers
    if result['triggers']:
        test_state = {
            "name": result['choice'].name,
            "checks": result['triggers']
        }
        
        program = ProgramController(controller)
        matching_states = program.check([test_state])
        
        print(f"Trigger validation result: {len(matching_states) > 0}")
        if matching_states:
            print(f"  State '{matching_states[0]['name']}' triggers passed!")
        else:
            print("  No matching states found")
            
except Exception as e:
    print(f"Error during trigger validation: {e}")
    import traceback
    traceback.print_exc()

# Show available trigger types from the registry
print("\n--- Available Trigger Types in Registry ---")
from netgent.browser.registry import TriggerRegistry
trigger_registry = TriggerRegistry(controller)
print(f"Trigger types: {list(trigger_registry.get_all_triggers().keys())}")

# Cleanup
print("\n--- Cleaning up ---")
controller.quit()
print("Test completed!")

