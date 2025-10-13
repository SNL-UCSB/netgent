"""
Test script to test the mark_page function.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from netgent.browser.session import BrowserSession
from netgent.browser.utils import mark_page
import time
import json

def test_mark_page():
    """Test the mark_page function with a real browser session."""
    print("Initializing browser session...")
    session = BrowserSession()
    driver = session.driver
    
    try:
        # Navigate to a test page
        print("Navigating to test page...")
        driver.get("https://www.example.com")
        time.sleep(3)  # Wait for page to load
        
        print("\n" + "="*50)
        print("Testing mark_page()...")
        print("="*50)
        
        # Create the mark_page function for this driver
        mark_page_func = mark_page(driver)
        
        # Test with default args
        print("Testing with default arguments...")
        elements, prompt, screenshot = mark_page_func.invoke({})
        
        print(f"✅ Success! mark_page returned:")
        print(f"   - Elements dict keys: {list(elements.keys())}")
        print(f"   - Prompt length: {len(prompt)} characters")
        print(f"   - Screenshot size: {len(screenshot)} characters (base64)")
        
        # Show some sample elements
        if elements:
            print(f"\n📋 Sample elements found:")
            for i, (key, element) in enumerate(list(elements.items())[:3]):
                print(f"   {i+1}. Key: {key}")
                print(f"      Tag: {element.get('tag_name', 'N/A')}")
                print(f"      Text: {element.get('text', 'N/A')[:50]}")
                print(f"      Accessible Name: {element.get('accessible_name', 'N/A')}")
        
        # Show a snippet of the prompt
        if prompt:
            print(f"\n📝 Prompt preview (first 200 chars):")
            print(f"   {prompt[:200]}...")
        
        # Test with custom args
        print(f"\n🔧 Testing with custom arguments...")
        custom_args = {
            "doHighlightElements": True,
            "focusHighlightIndex": -1,
            "viewportExpansion": 0,
            "debugMode": True,
            "filterEmptyElements": True,
        }
        
        elements2, prompt2, screenshot2 = mark_page_func.invoke(custom_args)
        print(f"✅ Custom args test successful!")
        print(f"   - Elements found: {len(elements2)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing mark_page: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        print("\n🔄 Cleaning up...")
        try:
            session.quit()
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting mark_page test...")
    success = test_mark_page()
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)
