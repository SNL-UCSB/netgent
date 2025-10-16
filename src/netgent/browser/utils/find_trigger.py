import os
import json
from typing import Any

with open(os.path.join(os.path.dirname(__file__), 'avaliable_trigger.js'), 'r') as f:
    AVAILABLE_TRIGGER_SCRIPT = f.read()

def find_trigger(driver) -> list[dict[str, Any]]:
    """
    Finds potential trigger elements in the DOM.
    
    This function executes the available_trigger.js script which finds visible elements
    on the page that can potentially be interacted with (triggers).
    
    Args:
        driver: The Selenium WebDriver instance
        
    Returns:
        A list of dictionaries containing information about each visible trigger element.
        Each dict contains: tagName, id, text, cssSelector, enhancedCssSelector, 
        xpath, ariaRole, accessibleName
    """
    try:
        # First check if the function is already loaded
        check_script = "typeof window.highlightVisibleElements !== 'undefined';"
        is_loaded = driver.execute_cdp_cmd("Runtime.evaluate", {
            "expression": check_script, 
            "returnByValue": True
        })["result"]["value"]
        
        # If not loaded, inject the script
        if not is_loaded:
            driver.execute_cdp_cmd("Runtime.evaluate", {
                "expression": AVAILABLE_TRIGGER_SCRIPT
            })
        
        # Execute the script and get results
        result = driver.execute_cdp_cmd("Runtime.evaluate", {
            "expression": AVAILABLE_TRIGGER_SCRIPT,
            "returnByValue": True
        })
        
        # Handle the CDP response structure properly
        if "result" in result and "value" in result["result"]:
            triggers = result["result"]["value"]
        elif "result" in result and "result" in result["result"]:
            triggers = result["result"]["result"]
        else:
            # Fallback: try to get the value directly
            triggers = result.get("result", result)
            
        return triggers if isinstance(triggers, list) else []
        
    except Exception as e:
        raise Exception(f"Failed to find triggers: {str(e)}")