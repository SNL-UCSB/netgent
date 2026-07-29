from abc import ABC, abstractmethod
from seleniumbase import Driver
import time
from ..registry import action, trigger, ActionTriggerMeta
from ..stats_logger import VideoStatsLogger

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.support.ui import WebDriverWait

# Interactions that reference a perceived element by its mmid. Shared by the
# perception layer so both browser and desktop controllers agree on which
# actions need an element resolved before execution.
ELEMENT_ACTIONS = {"click", "type", "scroll_to", "move", "scroll"}

class BaseController(ABC, metaclass=ActionTriggerMeta):
    """Base controller with automatic action and trigger registration via combined metaclass."""
    
    def __init__(self, driver: Driver):
        self.driver = driver
        self.stats_logger = VideoStatsLogger(driver)

    @action()
    def navigate(self, url: str):
        """Navigate to a specified URL"""
        self.driver.get(url)

    @action()
    def start_stats_logging(self, out_path: str = "netgent_video_stats.jsonl", interval: float = 2.0):
        """Start logging video 'Stats for Nerds' metrics (YouTube/Twitch) to a JSONL file in the background.

        Args:
            out_path: File to append JSONL stats samples to
            interval: Seconds between samples
        """
        self.stats_logger.configure(out_path=out_path, interval=interval)
        self.stats_logger.start()
        return out_path

    @action()
    def stop_stats_logging(self):
        """Stop the background video stats logger and flush the log file."""
        self.stats_logger.stop()

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
        if self.stats_logger:
            self.stats_logger.stop()
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

    # -- Perception Layer --
    #
    # These methods give the agent (web_agent / state_synthesis) a
    # controller-agnostic way to observe the target. The browser controller
    # implements them on top of the DOM (mark_page / find_trigger / driver).
    # The desktop controller overrides them to observe the macOS accessibility
    # tree through the host bridge. Everything downstream (the LangGraph state
    # machine, triggers, actions, code generation and replay) is identical.

    def snapshot(self) -> tuple[dict, str, str]:
        """Return (elements, prompt, screenshot_b64) for the current view.

        - elements: dict keyed by mmid (str) with per-element metadata used to
          resolve an action back to a selector/coordinates.
        - prompt: a human/LLM readable listing of the interactable elements.
        - screenshot_b64: base64 PNG of the current view (supplementary only).
        """
        from ..utils import mark_page
        elements, prompt, screenshot = mark_page(self.driver).with_retry().invoke(None)
        return elements, prompt, screenshot

    def get_context(self) -> dict:
        """Return lightweight context about the current view (url + title)."""
        try:
            return {"url": self.driver.current_url, "title": self.driver.title}
        except Exception:
            return {"url": "", "title": ""}

    def build_trigger_candidates(self) -> dict:
        """Build the dict of candidate triggers offered to state synthesis.

        Returns a mapping of trigger-key -> {"type": ..., "params": {...}}.
        The browser controller derives these from the current URL plus the
        visible interactable elements (text and enhanced CSS selectors).
        """
        from ..utils import find_trigger
        page_triggers = find_trigger(self.driver)

        triggers_dict: dict = {}
        # URL is always offered as a trigger for the browser domain.
        triggers_dict["URL"] = {
            "type": "url",
            "params": {"url": self.driver.current_url},
        }
        for i, trig in enumerate(page_triggers):
            if trig.get("text", "") != "":
                triggers_dict[f"TEXT_{i}"] = {
                    "type": "text",
                    "params": {"text": trig.get("text", "")},
                }
            if trig.get("enhancedCssSelector", "") != "":
                triggers_dict[f"CSS_{i}"] = {
                    "type": "element",
                    "params": {
                        "by": "css selector",
                        "selector": trig.get("enhancedCssSelector", ""),
                    },
                }
        return triggers_dict

    def resolve_element_action(self, action_output: dict, elements: dict) -> dict:
        """Convert an LLM action (referencing an mmid) into a replayable action.

        Produces {"type": <action>, "params": {...}} where element-targeting
        actions carry both a durable selector (re-resolved at replay time) and
        fallback absolute screen coordinates.
        """
        action_name = action_output.get("action")
        mmid = action_output.get("mmid")
        params = dict(action_output.get("params", {}))

        if mmid is not None and action_name in ELEMENT_ACTIONS and elements:
            element_data = elements.get(str(mmid))
            if element_data:
                selector = (
                    element_data.get('enhanced_css_selector') or
                    element_data.get('css_selector') or
                    element_data.get('xpath')
                )
                if selector:
                    if element_data.get('enhanced_css_selector') or element_data.get('css_selector'):
                        params['by'] = 'css selector'
                    else:
                        params['by'] = 'xpath'
                    params['selector'] = selector

                abs_x, abs_y = self.get_element_coordinates(
                    element_data.get('x', 0),
                    element_data.get('y', 0),
                    element_data.get('width', 0),
                    element_data.get('height', 0),
                    percentage=0.5,
                )
                params['x'] = abs_x
                params['y'] = abs_y

        return {"type": action_name, "params": params}
    
