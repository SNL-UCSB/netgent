from abc import ABC, abstractmethod
from seleniumbase import Driver
import os
import time
from ..registry import action, trigger, ActionTriggerMeta
from ..stats_logger import VideoStatsLogger

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.support.ui import WebDriverWait


def _xpath_literal(value: str) -> str:
    """Return an XPath string literal for values that may contain quotes."""
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    return "concat(" + ", '\"', ".join(f"'{part}'" for part in value.split('"')) + ")"


def _normalize_env_value(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
        return value[1:-1]
    return value


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


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
    def start_stats_logging(
        self,
        out_path: str = "netgent_video_stats.jsonl",
        interval: float = 2.0,
        filename: str = None,
        file: str = None,
        output_file: str = None,
    ):
        """Start logging video 'Stats for Nerds' metrics (YouTube/Twitch) to a JSONL file in the background.

        Args:
            out_path: File to append JSONL stats samples to
            interval: Seconds between samples
        """
        out_path = output_file or file or filename or out_path
        self.stats_logger.configure(out_path=out_path, interval=interval)
        self.stats_logger.start()
        return out_path

    @action()
    def start_twitch_stats_logging(
        self,
        filename: str = None,
        out_path: str = None,
        output_file: str = None,
        interval: float = 2.0,
    ):
        """Compatibility alias for LLM-generated Twitch-specific stats logging actions."""
        return self.start_stats_logging(
            out_path=out_path or output_file or filename or "twitch_stats.jsonl",
            interval=interval,
        )

    @action()
    def stop_stats_logging(self):
        """Stop the background video stats logger and flush the log file."""
        self.stats_logger.stop()

    @action()
    def stop_twitch_stats_logging(self):
        """Compatibility alias for LLM-generated Twitch-specific stats logging actions."""
        self.stop_stats_logging()

    @action()
    def wait(self, seconds: float):
        """Wait for a specified number of seconds"""
        time.sleep(seconds)
    
    @action()
    def terminate(self, reason: str = "Task completed"):
        """Terminate the agent execution"""
        print(f"TERMINATING: {reason}")
        return reason

    @action()
    def type_env(
        self,
        env_var: str,
        by: str = None,
        selector: str = None,
        x: float = None,
        y: float = None,
        default: str = None,
    ):
        """Type a value from the process environment without storing it in workflow JSON."""
        value = _normalize_env_value(os.environ.get(env_var, default))
        if value is None or value == "":
            raise ValueError(f"Environment variable '{env_var}' is required")
        return self.type_text(text=value, by=by, selector=selector, x=x, y=y)

    @action()
    def set_env_value(
        self,
        env_var: str,
        selectors: list[str] | str,
        default: str = None,
        timeout: float = 10,
    ):
        """Set the first matching input from an env var and dispatch browser events."""
        value = _normalize_env_value(os.environ.get(env_var, default))
        if value is None or value == "":
            raise ValueError(f"Environment variable '{env_var}' is required")

        last_error = None
        for selector in _as_list(selectors):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    element,
                )
                try:
                    element.click()
                    element.send_keys(Keys.CONTROL, "a")
                    element.send_keys(Keys.BACKSPACE)
                    element.send_keys(value)
                except Exception:
                    self.driver.execute_script(
                        """
                        const el = arguments[0];
                        const value = arguments[1];
                        el.focus();
                        el.value = value;
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                        """,
                        element,
                        value,
                    )
                return selector
            except Exception as exc:
                last_error = exc
        raise ValueError(f"Could not set {env_var}; no selectors matched: {last_error}")

    @action()
    def click_first(self, selectors: list[str] | str, timeout: float = 10):
        """Click the first clickable element from a list of CSS selectors."""
        last_error = None
        for selector in _as_list(selectors):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    element,
                )
                try:
                    element.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", element)
                return selector
            except Exception as exc:
                last_error = exc
        raise ValueError(f"No clickable selector matched: {last_error}")

    @action()
    def click_text_env(self, env_var: str, default: str = None, exact: bool = True):
        """Click an element whose visible text comes from the process environment."""
        value = _normalize_env_value(os.environ.get(env_var, default))
        if value is None or value == "":
            raise ValueError(f"Environment variable '{env_var}' is required")
        return self.click_text(text=value, exact=exact)

    @action()
    def click_text(self, text: str, exact: bool = True, timeout: float = 10):
        """Click an element by visible text."""
        value = text.strip()
        literal = _xpath_literal(value.strip())
        if exact:
            selector = f"//*[normalize-space(text())={literal}]"
        else:
            selector = f"//*[contains(normalize-space(text()), {literal})]"
        element = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, selector))
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            element,
        )
        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
        return text

    @action()
    def play_video(self, selector: str = "video", muted: bool = None, timeout: float = 10):
        """Ask the first matching HTML video element to play."""
        video = WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        self.driver.execute_script(
            """
            const video = arguments[0];
            const muted = arguments[1];
            video.scrollIntoView({block: 'center'});
            if (muted !== null) {
                video.muted = muted;
            }
            try {
                const result = video.play();
                if (result && typeof result.catch === 'function') {
                    result.catch(() => {});
                }
            } catch (e) {}
            """,
            video,
            muted,
        )
        time.sleep(1)
        return self.driver.execute_script(
            """
            const video = arguments[0];
            return {
                paused: video.paused,
                current_time_secs: video.currentTime,
                video_width: video.videoWidth,
                video_height: video.videoHeight
            };
            """,
            video,
        )
    
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
    
