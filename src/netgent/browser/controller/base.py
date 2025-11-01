from abc import ABC, abstractmethod
from seleniumbase import Driver
import time
from ..registry import action, trigger, ActionTriggerMeta

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.support.ui import WebDriverWait

class BaseController(ABC, metaclass=ActionTriggerMeta):
    """Base controller with automatic action and trigger registration via combined metaclass."""
    
    def __init__(self, driver: Driver):
        self.driver = driver

    @action()
    def navigate(self, url: str):
        """Navigate to a specified URL"""
        self.driver.get(url)

    @action()
    def wait(self, seconds: float):
        """Wait for a specified number of seconds"""
        time.sleep(seconds)
    
    @action()
    def terminate(self, reason: str = "Task completed"):
        """Terminate the agent execution"""
        print(f"TERMINATING: {reason}")
        return reason
    
    def quit(self):
        """Quit the browser (not an action - used for cleanup)"""
        if self.driver:
            self.driver.quit()

    # -- Actions Methods --
    @abstractmethod
    @action()
    def click(self, by: str = None, selector: str = None, x: float = None, y: float = None, percentage: float = 0.5):
        """Click on a specified element or coordinates.
        
        Args:
            by: Locator strategy (optional)
            selector: Selector string (optional)
            x: X coordinate (optional, used if by/selector not provided or fails)
            y: Y coordinate (optional, used if by/selector not provided or fails)
            percentage: Percentage of the element to click (0.0 to 1.0) for the x coordinate
        """
        pass

    @abstractmethod
    @action(name="type")  # Custom name to match common JSON schema naming
    def type_text(self, text: str, by: str = None, selector: str = None, x: float = None, y: float = None):
        """Type text into a specified element or at coordinates.
        
        Args:
            text: Text to type
            by: Locator strategy (optional)
            selector: Selector string (optional)
            x: X coordinate (optional, used if by/selector not provided or fails)
            y: Y coordinate (optional, used if by/selector not provided or fails)
        """
        pass
    
    @abstractmethod
    @action()
    def scroll_to(self, by: str = None, selector: str = None, x: float = None, y: float = None):
        """Scroll to a specified element or coordinates.
        
        Args:
            by: Locator strategy (optional)
            selector: Selector string (optional)
            x: X coordinate (optional, used if by/selector not provided or fails)
            y: Y coordinate (optional, used if by/selector not provided or fails)
        """
        pass
    
    @abstractmethod
    @action()
    def scroll(self, pixels: int, direction: str, by: str = None, selector: str = None, x: float = None, y: float = None):
        """Scroll a specified number of pixels in a specified direction.
        
        Args:
            pixels: Number of pixels to scroll
            direction: Direction to scroll ("up" or "down")
            by: Locator strategy (optional)
            selector: Selector string (optional)
            x: X coordinate (optional, used if by/selector not provided or fails)
            y: Y coordinate (optional, used if by/selector not provided or fails)
        """
        pass
    
    @abstractmethod
    @action()
    def press_key(self, key: str):
        """Press a specified key"""
        pass

    @abstractmethod
    @action()
    def move(self, by: str = None, selector: str = None, x: float = None, y: float = None, percentage: float = 0.5):
        """Move to a specified element or coordinates.
        
        Args:
            by: Locator strategy (optional)
            selector: Selector string (optional)
            x: X coordinate (optional, used if by/selector not provided or fails)
            y: Y coordinate (optional, used if by/selector not provided or fails)
            percentage: Percentage of the element to move to (0.0 to 1.0) for the x coordinate
        """
        pass

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

    # -- Trigger Methods --
    @trigger(name="element")
    def check_element(self, by: str, selector: str, check_visibility: bool = True, timeout: float = 0.1) -> bool:
        """Check if an element exists and optionally if it's visible."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            if check_visibility:
                return self.is_element_visible_in_viewpoint(element)
            return True
        except Exception:
            return False
    
    @trigger(name="url")
    def check_url(self, url: str) -> bool:
        """Check if the current URL matches the given URL."""
        try:
            return self.driver.current_url == url
        except Exception:
            return False

    @trigger(name="text")
    def check_text(self, text: str, check_visibility: bool = True, timeout: float = 0.1) -> bool:
        """Check if text exists on the page and optionally if it's visible."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, f"//*[normalize-space(text())='{text}']"))
            )
            if check_visibility:
                return self.is_element_visible_in_viewpoint(element)
            return True
        except Exception:
            return False

    
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
    
