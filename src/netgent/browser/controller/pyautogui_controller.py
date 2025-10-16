from math import pi
from .base import BaseController
from seleniumbase import Driver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyautogui
import time
import random
import logging

logger = logging.getLogger(__name__)


def bezier(n, control_point_1=(0.25, 0.1), control_point_2=(0.75, 0.9)):
    """Bezier curve tween function for smooth mouse movement."""
    if not 0.0 <= n <= 1.0:
        raise ValueError("Argument must be between 0.0 and 1.0.")
    
    t = n
    u = 1 - t
    y = (u ** 3 * 0 +
        3 * u ** 2 * t * control_point_1[1] +
        3 * u * t ** 2 * control_point_2[1] +
        t ** 3 * 1)
    return max(0.0, min(1.0, y))


class PyAutoGUIController(BaseController):
    def __init__(self, driver: Driver):
        super().__init__(driver)

    def click(self, by: str = None, selector: str = None, x: float = None, y: float = None):
        """Click on a specified element or coordinates"""
        click_x, click_y = None, None
        
        # Try using by/selector first if provided
        if by is not None and selector is not None:
            try:
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((by, selector))
                )
                click_x, click_y = self.get_element_coordinates(
                    element.location['x'], 
                    element.location['y'], 
                    element.size['width'], 
                    element.size['height']
                )
            except Exception as e:
                logger.warning(f"Could not find element with by={by}, selector={selector}: {e}")
                # Fall through to use x,y coordinates if available
        
        # Use provided x,y coordinates if element lookup failed or wasn't provided
        if click_x is None and x is not None and y is not None:
            click_x, click_y = x, y
        
        # Raise error if we don't have coordinates from either method
        if click_x is None or click_y is None:
            raise ValueError("Must provide either (by, selector) or (x, y) coordinates")
        
        bezier_fn = lambda n: bezier(n, (0.25, 0.1), (0.75, 0.9))
        pyautogui.click(click_x, click_y, duration=0.5, tween=bezier_fn)

    def type_text(self, text: str, by: str = None, selector: str = None, x: float = None, y: float = None):
        """Type text into a specified element or at coordinates"""
        # Click on the element or coordinates first
        self.click(by=by, selector=selector, x=x, y=y)
        ## Delete the Existing Text
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('delete')
        time.sleep(0.1)
        interval = max(0.02, 0.02 + random.uniform(-0.03, 0.03))
        ## Type the New Text
        for char in text:
            pyautogui.keyUp('fn')
            pyautogui.typewrite(char, interval=interval)
            pyautogui.keyUp('fn')

    def move(self, by: str = None, selector: str = None, x: float = None, y: float = None):
        """Move to a specified element or coordinates"""
        move_x, move_y = None, None
        
        # Try using by/selector first if provided
        if by is not None and selector is not None:
            try:
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((by, selector))
                )
                move_x, move_y = self.get_element_coordinates(
                    element.location['x'], 
                    element.location['y'], 
                    element.size['width'], 
                    element.size['height']
                )
            except Exception as e:
                logger.warning(f"Could not find element with by={by}, selector={selector}: {e}")
                # Fall through to use x,y coordinates if available
        
        # Use provided x,y coordinates if element lookup failed or wasn't provided
        if move_x is None and x is not None and y is not None:
            move_x, move_y = x, y
        
        # Raise error if we don't have coordinates from either method
        if move_x is None or move_y is None:
            raise ValueError("Must provide either (by, selector) or (x, y) coordinates")
        
        bezier_fn = lambda n: bezier(n, (0.25, 0.1), (0.75, 0.9))
        pyautogui.moveTo(move_x, move_y, duration=0.5, tween=bezier_fn)
    
    def scroll_to(self, by: str = None, selector: str = None, x: float = None, y: float = None):
        """Scroll to a specified element or coordinates"""
        # If by/selector provided, use element-based scrolling
        if by is not None and selector is not None:
            try:
                if not self.check_element(by, selector, check_visibility=False):
                    logger.warning(f"Element with by={by}, selector={selector} not found, trying coordinates")
                else:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((by, selector))
                    )

                    while not self.check_element(by, selector, check_visibility=True):
                        element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((by, selector))
                        )
                        viewport_height = self.driver.execute_cdp_cmd("Runtime.evaluate", {"expression": "window.innerHeight", "returnByValue": True})["result"]["value"]
                        scroll_y = self.driver.execute_cdp_cmd("Runtime.evaluate", {"expression": "window.pageYOffset || document.documentElement.scrollTop", "returnByValue": True})["result"]["value"]
                        elem_y = element.location['y']
                        if elem_y < scroll_y:
                            self.scroll(direction="up", pixels=5)
                        elif elem_y > scroll_y + viewport_height - element.size['height']:
                            self.scroll(direction="down", pixels=5)
                        else:
                            break
                    return
            except Exception as e:
                logger.warning(f"Could not scroll to element: {e}, trying coordinates")
        
        # If coordinates provided, use coordinate-based scrolling
        if x is not None and y is not None:
            # Move mouse to coordinates and scroll until visible
            pyautogui.moveTo(x, y, duration=0.2)
        else:
            raise ValueError("Must provide either (by, selector) or (x, y) coordinates")

    def scroll(self, pixels: int, direction: str, by: str = None, selector: str = None, x: float = None, y: float = None):
        """Scroll the page or a specific element.
        
        Args:
            pixels: Number of pixels to scroll
            direction: Direction to scroll ("up" or "down")
            by: Locator strategy (optional, if provided will scroll to element first)
            selector: Selector string (optional, if provided will scroll to element first)
            x: X coordinate (optional, if provided will move to coordinates before scrolling)
            y: Y coordinate (optional, if provided will move to coordinates before scrolling)
        """
        # If by and selector are provided, move to that element first
        if by is not None and selector is not None:
            try:
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((by, selector))
                )
                scroll_x, scroll_y = self.get_element_coordinates(
                    element.location['x'], 
                    element.location['y'], 
                    element.size['width'], 
                    element.size['height']
                )
                # Move mouse to element before scrolling
                pyautogui.moveTo(scroll_x, scroll_y, duration=0.2)
            except Exception as e:
                logger.warning(f"Could not move to element before scrolling: {e}")
                # Try using x,y coordinates if provided
                if x is not None and y is not None:
                    pyautogui.moveTo(x, y, duration=0.2)
        # If coordinates are provided but not by/selector, use coordinates
        elif x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=0.2)
        
        if direction == "up":
            pyautogui.scroll(pixels)
        elif direction == "down":
            pyautogui.scroll(-pixels)
        else:
            raise ValueError(f"Invalid direction: {direction}")

    def press_key(self, key: str):
        pyautogui.press(key)

