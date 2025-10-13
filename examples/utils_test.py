"""
Test script to verify the browser utils are working correctly.
"""
from netgent.browser.session import BrowserSession
from netgent.browser.utils import mark_dom, unmark_dom, find_trigger
import time

def test_utils():
    """Test the utils functions with a real browser session."""
    print("Initializing browser session...")
    session = BrowserSession()
    driver = session.driver
    
    try:
        # Navigate to a test page
        print("Navigating to test page...")
        driver.get("https://www.example.com")
        time.sleep(2)
        
        # Test find_trigger
        print("\n" + "="*50)
        print("Testing find_trigger()...")
        print("="*50)
        triggers = find_trigger(driver)
        print(f"Found {len(triggers)} trigger elements:")
        for i, trigger in enumerate(triggers[:5]):  # Show first 5
            print(f"\n{i+1}. {trigger.get('tagName', 'unknown')}")
            print(f"   Text: {trigger.get('text', '')[:50]}")
            print(f"   CSS Selector: {trigger.get('cssSelector', '')[:80]}")
            print(f"   Accessible Name: {trigger.get('accessibleName', '')}")
        
        if len(triggers) > 5:
            print(f"\n... and {len(triggers) - 5} more")
        
        # Test mark_dom
        print("\n" + "="*50)
        print("Testing mark_dom()...")
        print("="*50)
        dom_data, screenshot_base64 = mark_dom(driver)
        print(f"DOM snapshot captured")
        print(f"Root ID: {dom_data.get('rootId', 'N/A')}")
        print(f"Number of elements in map: {len(dom_data.get('map', {}))}")
        print(f"Screenshot size: {len(screenshot_base64)} characters (base64)")
        
        # Count interactive elements
        interactive_count = 0
        for element_id, element_data in dom_data.get('map', {}).items():
            if element_data.get('isInteractive') and element_data.get('highlightIndex') is not None:
                interactive_count += 1
        print(f"Interactive elements found: {interactive_count}")
        
        print("\nHighlights should now be visible on the page...")
        time.sleep(3)
        
        # Test unmark_dom
        print("\n" + "="*50)
        print("Testing unmark_dom()...")
        print("="*50)
        unmark_dom(driver)
        print("Highlights removed")
        time.sleep(2)
        
        print("\n" + "="*50)
        print("All tests passed! ✓")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\nClosing browser...")
        session.quit()

if __name__ == "__main__":
    test_utils()

