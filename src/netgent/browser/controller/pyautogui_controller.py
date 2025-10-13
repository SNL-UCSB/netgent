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


    def click(self, by: str, selector: str):
        """Click on a specified element"""
        element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((by, selector))
            )
        x, y = self.get_element_coordinates(element.location['x'], element.location['y'], element.size['width'], element.size['height'])
        bezier_fn = lambda n: bezier(n, (0.25, 0.1), (0.75, 0.9))
        pyautogui.click(x, y, duration=0.5, tween=bezier_fn)

    def type_text(self, by: str, selector: str, text: str):
        """Type text into a specified element"""
        self.click(by, selector)
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

    def move(self, by: str, selector: str):
        element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((by, selector))
            )
        x, y = self.get_element_coordinates(element.location['x'], element.location['y'], element.size['width'], element.size['height'])
        bezier_fn = lambda n: bezier(n, (0.25, 0.1), (0.75, 0.9))
        pyautogui.moveTo(x, y, duration=0.5, tween=bezier_fn)
    
    def scroll_to(self, by, selector):
        if not self.check_element(by, selector, check_visibility=False):
            return

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

    def scroll(self, pixels: int, direction: str, by: str = None, selector: str = None):
        """Scroll the page or a specific element.
        
        Args:
            pixels: Number of pixels to scroll
            direction: Direction to scroll ("up" or "down")
            by: Locator strategy (optional, if provided will scroll to element first)
            selector: Selector string (optional, if provided will scroll to element first)
        """
        # If by and selector are provided, move to that element first
        if by and selector:
            try:
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((by, selector))
                )
                x, y = self.get_element_coordinates(
                    element.location['x'], 
                    element.location['y'], 
                    element.size['width'], 
                    element.size['height']
                )
                # Move mouse to element before scrolling
                pyautogui.moveTo(x, y, duration=0.2)
            except Exception as e:
                logger.warning(f"Could not move to element before scrolling: {e}")
        
        if direction == "up":
            pyautogui.scroll(pixels)
        elif direction == "down":
            pyautogui.scroll(-pixels)
        else:
            raise ValueError(f"Invalid direction: {direction}")

    def press_key(self, key: str):
        pyautogui.press(key)

