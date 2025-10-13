"""
Example usage of the WebAgent with the current codebase structure.
"""

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from netgent.browser.session import BrowserSession
from netgent.browser.controller import PyAutoGUIController
from netgent.components.web_agent import WebAgent

load_dotenv()

def main():
    # Initialize browser session
    browser_session = BrowserSession()
    driver = browser_session.driver
    
    # Initialize controller (PyAutoGUI or any other controller)
    controller = PyAutoGUIController(driver)
    
    # Initialize LLM
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0
    )
    
    # Initialize WebAgent with controller
    web_agent = WebAgent(
        llm=llm,
        controller=controller,
        wait_period=0.5
    )
    
    # Navigate to a starting URL
    driver.get("https://www.google.com")
    
    # Define the task
    user_query = "Search for 'Python programming' and click on the first result"
    
    # Run the web agent
    result = web_agent.run(
        user_query=user_query,
        messages=[],  # Previous message history if resuming
        parameters={}  # Any parameters to pass to the agent
    )
    
    print("Task completed!")
    print(f"Final state: {result}")
    
    # Clean up
    input("Press Enter to close the browser...")
    browser_session.quit()

if __name__ == "__main__":
    main()


