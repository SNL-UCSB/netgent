import time
import os
from seleniumbase import Driver
from selenium.webdriver.support.ui import WebDriverWait
import json
import base64

with open(os.path.join(os.path.dirname(__file__), 'build_dom.js'), 'r') as f:
    WEBMARKER_SCRIPT = f.read()

def mark_dom(driver, args: dict = None) -> tuple[dict, str, str]:
    args = args or {
            "doHighlightElements": True,
            "focusHighlightIndex": -1,
            "viewportExpansion": 0,
            "debugMode": False,
            "filterEmptyElements": False,
        }
    
    """
    Loads the webmarker script (if not already present) and executes DOM marking.
    The script will highlight all interactable elements.
    """
    try:
        # Prepare arguments for the getDomSnapshot function

        
        if not driver.execute_cdp_cmd("Runtime.evaluate", {"expression": "typeof window.getDomSnapshot !== 'undefined';", "returnByValue": True})["result"]["value"]:
            driver.execute_cdp_cmd("Runtime.evaluate", {"expression": WEBMARKER_SCRIPT})
        
        result = driver.execute_cdp_cmd("Runtime.evaluate", {"expression": f"window.getDomSnapshot({json.dumps(args)});", "returnByValue": True})
        
        # Handle the CDP response structure properly
        if "result" in result and "value" in result["result"]:
            interactable = result["result"]["value"]
        elif "result" in result and "result" in result["result"]:
            interactable = result["result"]["result"]
        else:
            # Fallback: try to get the value directly
            interactable = result.get("result", result)
    except Exception as e:
        raise Exception("Failed to mark DOM: " + str(e))
    
    try: 
        # Use Selenium's built-in screenshot method which is much faster
        # and returns base64 encoded PNG data directly
        screenshot_base64 = driver.get_screenshot_as_base64()

        # Save the screenshot to a file
        # with open(f"screenshot_{time.time()}.png", "wb") as f:
        #     f.write(base64.b64decode(screenshot_base64))
    except Exception as e:
        raise Exception("Failed to take screenshot: " + str(e))
    
    return interactable, screenshot_base64

def unmark_dom(driver) -> None:
    """Removes the highlights from the DOM."""
    # This script finds the highlight container by its ID and removes it.
    # It also runs any cleanup functions to remove event listeners.
    unmark_script = """
    try {
        // Run cleanup functions first
        if (window._highlightCleanupFunctions && window._highlightCleanupFunctions.length) {
            window._highlightCleanupFunctions.forEach(fn => {
                try {
                    fn();
                } catch (e) {
                    console.warn('Error running cleanup function:', e);
                }
            });
            window._highlightCleanupFunctions = [];
        }
        
        // Remove the main highlight container
        const container = document.getElementById('playwright-highlight-container');
        if (container) {
            container.remove();
            console.log('Removed highlight container');
        }
        
        // Also remove any stray highlight elements
        const highlights = document.querySelectorAll('.playwright-highlight-label, [id*="playwright-highlight"]');
        highlights.forEach(el => el.remove());
        
        // Clear any remaining highlight styles
        const elementsWithHighlight = document.querySelectorAll('[style*="border"][style*="background"]');
        elementsWithHighlight.forEach(el => {
            if (el.style.border && el.style.backgroundColor && el.style.position === 'fixed') {
                el.remove();
            }
        });
        
        true; // Return value for verification
    } catch (e) {
        console.error('Error in unmark_dom:', e);
        false;
    }
    """
    driver.execute_cdp_cmd("Runtime.evaluate", {"expression": unmark_script, "returnByValue": True})

with open(os.path.join(os.path.dirname(__file__), 'avaliable_trigger.js'), 'r') as f:
    AVAILABLE_TRIGGER_SCRIPT = f.read()

def find_trigger(driver) -> list:
    """Finds potential trigger elements in the DOM."""
    return driver.execute_cdp_cmd("Runtime.evaluate", {"expression": AVAILABLE_TRIGGER_SCRIPT, "returnByValue": True})["result"]["value"]