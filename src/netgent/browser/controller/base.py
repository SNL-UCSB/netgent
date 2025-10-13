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
    
    def quit(self):
        """Quit the browser (not an action - used for cleanup)"""
        if self.driver:
            self.driver.quit()

    # -- Actions Methods --
    @abstractmethod
    @action()
    def click(self, by: str, selector: str):
        """Click on a specified element"""
        pass

    @abstractmethod
    @action(name="type")  # Custom name to match common JSON schema naming
    def type_text(self, by: str, selector: str, text: str):
        """Type text into a specified element"""
        pass
    
    @abstractmethod
    @action()
    def scroll_to(self, by: str, selector: str):
        """Scroll to a specified element"""
        pass
    
    @abstractmethod
    @action()
    def scroll(self, pixels: int, direction: str, by: str = None, selector: str = None):
        """Scroll a specified number of pixels in a specified direction.
        
        Args:
            pixels: Number of pixels to scroll
            direction: Direction to scroll ("up" or "down")
            by: Locator strategy (optional)
            selector: Selector string (optional)
        """
        pass
    
    @abstractmethod
    @action()
    def press_key(self, key: str):
        """Press a specified key"""
        pass

    @abstractmethod
    @action()
    def move(self, by: str, selector: str):
        """Move to a specified element"""
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
    
