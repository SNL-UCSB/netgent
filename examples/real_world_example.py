"""
Real-world example: Using the action decorator system with PyAutoGUIController

This example demonstrates how to extend PyAutoGUIController with new actions
without modifying the StateExecutor.
"""

from seleniumbase import Driver
from netgent.browser.controller import PyAutoGUIController, action
from netgent.components.state_executor.executor import StateExecutor


class ExtendedPyAutoGUIController(PyAutoGUIController):
    """
    Extended controller with additional actions.
    
    Simply add @action() decorators to new methods!
    """
    
    @action()
    def hover(self, by: str, selector: str):
        """Hover over an element using PyAutoGUI"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((by, selector))
        )
        x, y = self.get_element_coordinates(
            element.location['x'], 
            element.location['y'], 
            element.size['width'], 
            element.size['height']
        )
        
        import pyautogui
        from netgent.browser.controller.pyautogui_controller import bezier
        
        bezier_fn = lambda n: bezier(n, (0.25, 0.1), (0.75, 0.9))
        pyautogui.moveTo(x, y, duration=0.5, tween=bezier_fn)
    
    @action()
    def take_screenshot(self, filename: str = "screenshot.png"):
        """Take a screenshot of the current page"""
        self.driver.save_screenshot(filename)
        print(f"Screenshot saved: {filename}")
    
    @action()
    def get_text(self, by: str, selector: str) -> str:
        """Get text content from an element"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((by, selector))
        )
        return element.text
    
    @action()
    def get_attribute(self, by: str, selector: str, attribute: str) -> str:
        """Get an attribute value from an element"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((by, selector))
        )
        return element.get_attribute(attribute)
    
    @action()
    def element_exists(self, by: str, selector: str, timeout: float = 2.0) -> bool:
        """Check if an element exists on the page"""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return True
        except:
            return False
    
    @action()
    def right_click(self, by: str, selector: str):
        """Right-click on an element"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import pyautogui
        from netgent.browser.controller.pyautogui_controller import bezier
        
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((by, selector))
        )
        x, y = self.get_element_coordinates(
            element.location['x'], 
            element.location['y'], 
            element.size['width'], 
            element.size['height']
        )
        
        bezier_fn = lambda n: bezier(n, (0.25, 0.1), (0.75, 0.9))
        pyautogui.click(x, y, duration=0.5, tween=bezier_fn, button='right')


def example_automation_workflow():
    """
    Example: Automating a workflow with extended actions
    """
    print("=" * 70)
    print("Real-World Example: Extended PyAutoGUI Controller")
    print("=" * 70)
    
    # Initialize the driver and extended controller
    # (In production, you'd configure this properly)
    driver = Driver(browser="chrome", headless=False)
    
    try:
        controller = ExtendedPyAutoGUIController(driver)
        executor = StateExecutor(controller)
        
        # Show all available actions (including new ones!)
        print("\n📋 Available Actions:")
        for action_name in sorted(executor.get_available_actions()):
            print(f"  • {action_name}")
        
        # Define a workflow using both built-in and custom actions
        workflow = {
            "actions": [
                # Navigate to a website
                {"type": "navigate", "params": {"url": "https://example.com"}},
                
                # Wait for page to load
                {"type": "wait", "params": {"seconds": 2.0}},
                
                # Take a screenshot
                {"type": "take_screenshot", "params": {"filename": "page_loaded.png"}},
                
                # Check if element exists
                {"type": "element_exists", "params": {"by": "css", "selector": "h1"}},
                
                # Get text from an element
                {"type": "get_text", "params": {"by": "tag name", "selector": "h1"}},
                
                # Hover over an element
                {"type": "hover", "params": {"by": "css", "selector": "a"}},
                
                # Built-in actions still work!
                {"type": "click", "params": {"by": "css", "selector": "a"}},
                {"type": "wait", "params": {"seconds": 1.0}},
                
                # Take final screenshot
                {"type": "take_screenshot", "params": {"filename": "final_state.png"}},
            ]
        }
        
        print("\n🚀 Executing Workflow...")
        print("-" * 70)
        executor.run(workflow)
        print("-" * 70)
        
        print("\n✅ Workflow completed successfully!")
        
    finally:
        # Cleanup
        controller.quit()
        print("\n🔒 Browser closed.")


def main():
    """Main entry point"""
    print("\n💡 This example shows how to extend PyAutoGUIController")
    print("   with new actions without touching StateExecutor!\n")
    
    # Uncomment to run the actual automation
    example_automation_workflow()
    
    print("\nTo run the actual automation, uncomment the line in main()")
    print("and ensure you have seleniumbase installed:\n")
    print("  pip install seleniumbase")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

