from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dom.webmarker import mark_dom, unmark_dom, find_trigger
from dom.dom_parser import parse_dom
import time
from selenium.common.exceptions import StaleElementReferenceException
from .humanInputController import HumanInputController
from langchain_core.runnables import chain as chain_decorator 
import platform

class BrowserManager:
    '''
    Manages browser interactions using Selenium and undetected-chromedriver.
    Provides methods for navigation, element interaction, and DOM parsing.
    Args:
        human_movement (bool): If True, simulates human-like mouse movements.
        shake (bool): If True, adds slight random shake to mouse movements.
        proxy (str): Proxy server to use for browser connections.
        user_data_dir (str | None): Path to user data directory for browser profile.
    Returns:
        BrowserManager instance with configured browser session.
        
    '''
    def __init__(self, human_movement: bool = True, shake: bool = False, proxy: str = None, user_data_dir: str | None = None):
        self.humanInputController = HumanInputController(human_movement=human_movement, shake=shake)
        self.ctrl_cmd = "ctrl" if platform.system() == "Linux" else "command"

        self.proxy = proxy
        self.user_data_dir = user_data_dir
        print(self.proxy)
        
        # Set Chrome Arguments
        self.chrome_args = [
            "--force-device-scale-factor=1",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
        ]

        # If a user data dir is provided, also append the raw Chromium flag for redundancy
        if self.user_data_dir:
            self.chrome_args.append(f"--user-data-dir={self.user_data_dir}")
        
        self.chromium_arg = ",".join(self.chrome_args)
        
        self.driver = Driver(
            uc=True,
            headed=True,
            browser="chrome",
            chromium_arg=self.chromium_arg,
            use_auto_ext=False,
            undetectable=True,
            proxy=proxy,
            # Pass through to SeleniumBase/undetected-chromedriver
            user_data_dir=self.user_data_dir if self.user_data_dir else None,
        )

    @property
    def mark_page(self):    
        @chain_decorator
        def _mark_page(args):
            driver = self.driver
            max_retries = 10
            retry_delay = 2
            # Retry loop for marking DOM
            for attempt in range(max_retries):
                try:
                    interactable, screenshot = mark_dom(driver, args=args)
                    prompt, elements = parse_dom(interactable)
                    unmark_dom(driver)
                    return elements, prompt, screenshot
                    
                except StaleElementReferenceException as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise
                    
                    try:
                        unmark_dom(driver)
                    except:
                        pass
                    
                    time.sleep(retry_delay)

            raise Exception("Failed to mark DOM after all retries")
            
        return _mark_page
            
        
    def navigate_to(self, url: str):
        if not url.startswith(('http://', 'https://')):
            raise Exception("Invalid URL: " + url + " - Please include the protocol (http:// or https://)")
        try:
            self.driver.get(url)
            return "Navigated to " + url
        except Exception as e:
            raise Exception("Error navigating to " + url + ": " + str(e))

    def get_element_coordinates(self, x, y, width, height, percentage=0.5):
        """
        Get the absolute screen coordinates for an element.
        
        Args:
            element: Selenium WebElement
            percentage: Horizontal offset percentage within the element (0.0 to 1.0)
            
        Returns:
            tuple: (abs_x, abs_y) absolute screen coordinates
        """
        # Get element coordinates relative to the document
        element_x = x
        element_y = y

        # Get current scroll position
        scroll_x = self.driver.execute_cdp_cmd("Runtime.evaluate", {"expression": "window.pageXOffset || document.documentElement.scrollLeft", "returnByValue": True})["result"]["value"]
        scroll_y = self.driver.execute_cdp_cmd("Runtime.evaluate", {"expression": "window.pageYOffset || document.documentElement.scrollTop", "returnByValue": True})["result"]["value"]

        # Get browser window position and panel dimensions
        panel_height = self.driver.execute_cdp_cmd("Runtime.evaluate", {"expression": "window.outerHeight - window.innerHeight", "returnByValue": True})["result"]["value"]
        panel_width = self.driver.execute_cdp_cmd("Runtime.evaluate", {"expression": "window.outerWidth - window.innerWidth", "returnByValue": True})["result"]["value"]
        
        window_pos = self.driver.get_window_position()
        window_x = window_pos['x']
        window_y = window_pos['y']

        # Calculate coordinates relative to the viewport (subtract scroll position)
        viewport_x = element_x - scroll_x
        viewport_y = element_y - scroll_y

        # Calculate absolute screen coordinates (account for both horizontal and vertical panels)
        abs_x = window_x + viewport_x + panel_width
        abs_y = window_y + viewport_y + panel_height

        abs_x += width * percentage
        abs_y += height * 0.5
        
        return abs_x, abs_y

        
    def close_browser(self):
        try:
            self.driver.quit()
        except Exception as e:
            raise Exception("Error closing browser: " + str(e))
        
    def reset_browser(self):
        try:
            self.close_browser()
            self.driver = Driver(
                uc=True, 
                headless=False, 
                browser="chrome", 
                chromium_arg=self.chromium_arg,
                use_auto_ext=False,
                undetectable=True,
                proxy=self.proxy,
                user_data_dir=self.user_data_dir if self.user_data_dir else None,
            )
        except Exception as e:
            raise Exception("Error resetting browser: " + str(e))
    
    ### Element Based Interactions ###
    def click(self, by, selector, button='left', timeout=10, percentage=0.5, scroll_to=True, fallback_x=None, fallback_y=None, fallback_width=None, fallback_height=None):
        print("trying to click on element", selector)
        try:

            if scroll_to:
                self.scroll_to(by, selector)
                self.wait(0.25)

            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            print("element found", element)

            # Get absolute screen coordinates for the element
            abs_x, abs_y = self.get_element_coordinates(element.location['x'], element.location['y'], element.size['width'], element.size['height'], percentage)     
            print("click on element", selector, abs_x, abs_y)      
            self.humanInputController.click(abs_x, abs_y, button=button)
                
        except Exception as e:
            print("error clicking element", selector, e)
            print("fallback", fallback_height, fallback_width, fallback_x, fallback_y)
            if fallback_height is not None and fallback_width is not None and fallback_x is not None and fallback_y is not None:
                print("fallback coordinates running")
                abs_x, abs_y = self.get_element_coordinates(fallback_x, fallback_y, fallback_width, fallback_height, percentage=percentage)
                print(f"fallback click on coordinates {abs_x}, {abs_y}")
                self.humanInputController.click(abs_x, abs_y, button=button)
            else:
                raise Exception("Error clicking element: " + str(e))
        
    def type(self, by, selector, text: str, timeout=10, base_interval=0.1, scroll_to=True, fallback_x=None, fallback_y=None, fallback_width=None, fallback_height=None):
        try:
            print(f"trying to type '{text}' in element {selector}")

            if scroll_to:
                self.scroll_to(by, selector)
                self.wait(0.25)
            

            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            print(f"element found for typing: {element}")

            abs_x, abs_y = self.get_element_coordinates(element.location['x'], element.location['y'], element.size['width'], element.size['height'])
            print(f"clicking on element {selector} at coordinates {abs_x}, {abs_y}")
            self.humanInputController.click(abs_x, abs_y)
            # Clear any existing text first by selecting all and deleting
            self.humanInputController.hotkey(self.ctrl_cmd, 'a', 'delete', interval=0.5)
            self.wait(0.1)
            print(f"typing text: {text}")
            self.humanInputController.typewrite(text, base_interval=base_interval)
        except Exception as e:
            if fallback_height is not None and fallback_width is not None and fallback_x is not None and fallback_y is not None:
                print("fallback coordinates running for typing")
                abs_x, abs_y = self.get_element_coordinates(fallback_x, fallback_y, fallback_width, fallback_height, percentage=0.5)
                print(f"fallback click on coordinates {abs_x}, {abs_y} for typing")
                self.humanInputController.click(abs_x, abs_y)
                self.humanInputController.hotkey(self.ctrl_cmd, 'a', 'delete', interval=0.5)
                self.wait(0.1)
                self.humanInputController.typewrite(text, base_interval=base_interval)
            else:
                raise Exception("Error typing " + text + " in element: " + str(e))
    
    def scroll(self, by=None, selector=None, direction: str = "down", scroll_amount: int = 10, timeout=10):
        try:
            if by and selector:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
                abs_x, abs_y = self.get_element_coordinates(element.location['x'], element.location['y'], element.size['width'], element.size['height'])
                self.humanInputController.scroll(abs_x, abs_y, direction, scroll_amount)
            else:
                # Scroll on page (no specific element)
                window_pos = self.driver.get_window_position()
                window_x = window_pos['x']
                window_y = window_pos['y']
                window_size = self.driver.get_window_size()
                
                # Calculate right side of the browser window
                right_x = window_x + window_size['width'] - 10
                center_y = window_y + (window_size['height'] // 2)
                
                if direction == "up":
                    self.humanInputController.scroll(right_x, center_y, direction, scroll_amount)
                elif direction == "down":
                    self.humanInputController.scroll(right_x, center_y, direction, scroll_amount)
                else:
                    raise Exception("Invalid direction: " + direction)
                
        except Exception as e:
            raise Exception("Error scrolling element: " + str(e))
    
    def scroll_to(self, by, selector, timeout=10):
        if not self.check_element(by, selector, check_visibility=False):
            return

        driver = self.driver
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )

        while not self.check_element(by, selector, check_visibility=True):
            # Get element coordinates
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            # Get viewport dimensions and scroll position
            viewport_height = driver.execute_cdp_cmd("Runtime.evaluate", {"expression": "window.innerHeight", "returnByValue": True})["result"]["value"]
            scroll_y = driver.execute_cdp_cmd("Runtime.evaluate", {"expression": "window.pageYOffset || document.documentElement.scrollTop", "returnByValue": True})["result"]["value"]
            elem_y = element.location['y']
            # If element is above the viewport, scroll up
            if elem_y < scroll_y:
                self.scroll(direction="up", scroll_amount=5)
            # If element is below the viewport, scroll down
            elif elem_y > scroll_y + viewport_height - element.size['height']:
                self.scroll(direction="down", scroll_amount=5)
            else:
                break

    
    def wait(self, seconds: float):
        try:
            self.humanInputController.wait(seconds)
        except Exception as e:
            raise Exception("Error waiting: " + str(e))
    
    def press_key(self, key: str):
        try:
            self.humanInputController.press_key(key)
        except Exception as e:
            raise Exception("Error pressing key: " + str(e))
    
    def is_element_visible_in_viewpoint(self, element) -> bool:
        return self.driver.execute_script("""
    const elem = arguments[0];
    const style = window.getComputedStyle(elem);
    const rect = elem.getBoundingClientRect();

    const isVisible = (
        style.display !== 'none' &&
        style.visibility !== 'hidden' &&
        style.opacity !== '0'
    );

    const isInViewport = (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );

    return isVisible && isInViewport;
""", element)
    
    
    ### Checkers ###
    def check_element(self, by, selector, timeout=2, check_visibility=True):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            if check_visibility:
                return self.is_element_visible_in_viewpoint(element)
            return True
        except Exception:
            return False
    
    def check_url(self, url):
        try:
            return self.driver.current_url == url
        except Exception:
            return False

    def check_text(self, text: str, timeout=2, check_visibility=True):
        try:
            return self.check_element(By.XPATH, f"//*[normalize-space(text())='{text}']", timeout=timeout, check_visibility=check_visibility)
        except Exception:
            return False
    
    def find_trigger(self) -> list:
        """Returns a list of potential trigger elements in the DOM."""
        return find_trigger(self.driver)
    
    def detect_trigger(self, type: str, value: str) -> bool:
        """Detects if a trigger is present in the DOM."""
        if type == "url":
            return self.check_url(value)
        trigger_elements = self.find_trigger()
        for element in trigger_elements:
            if type == "element":
                if element["enhancedCssSelector"] == value:
                    return True
            else:
                if element[type] == value:
                    return True
        return False

def main():
    browser = BrowserManager(human_movement=False)
    browser.navigate_to("https://www.google.com")
    browser.type(By.CSS_SELECTOR, "textarea[name='q']", "Hello, world!")
    browser.press_key("Enter")
    browser.wait(1)
    browser.scroll(direction="down")
    browser.wait(10)

if __name__ == "__main__":
    main()