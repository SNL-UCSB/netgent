from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import pyautogui
import time
import random
import threading

def bezier(n, control_point_1=(0.25, 0.1), control_point_2=(0.75, 0.9)):
        """
        Bezier curve tween function for smooth mouse movement.
        
        Args:
            n: Float between 0.0 and 1.0 representing progress
            control_point_1: First control point (x, y) for curve shape
            control_point_2: Second control point (x, y) for curve shape
        
        Returns:
            Float between 0.0 and 1.0 representing the tweened value
        """
        if not 0.0 <= n <= 1.0:
            raise ValueError("Argument must be between 0.0 and 1.0.")
        
        t = n
        u = 1 - t
        y = (u ** 3 * 0 +
            3 * u ** 2 * t * control_point_1[1] +
            3 * u * t ** 2 * control_point_2[1] +
            t ** 3 * 1)
        return max(0.0, min(1.0, y))


class HumanInputController:
    """
    Human-like Input Controller using pyautogui with optional mouse shaking when idle.
    Args:
        human_movement: Whether to simulate human-like mouse movement and typing
        shake: Whether to enable slight mouse shaking when idle
        
    Methods:
        click(x, y, button='left'): Click at (x, y) with specified button
        hover(x, y): Move mouse to (x, y)
        typewrite(text, base_interval=0.1): Type text with optional human-like behavior
        press_key(key): Press a single key
        scroll(x, y, direction, scroll_amount=10): Scroll up or down at (x, y)
        wait(seconds): Wait for specified seconds
        hotkey(*args, **kwargs): Press a combination of keys
        stop(): Stop the controller and perform cleanup tasks
    """
    def __init__(self, human_movement: bool = True, shake: bool = False):
       self.human_movement = human_movement
       
       # Shaking Thread #
       self.shake = shake
       self.action_in_progress = False
       self.shake_thread = None
       self.shake_running = False
       # Start shake thread if shake is enabled
       if self.shake:
           self.start_shake_thread()

    def start_shake_thread(self):
        """Start the background thread for mouse shaking when idle."""
        if not self.shake_running:
            self.shake_running = True
            self.shake_thread = threading.Thread(target=self._shake_loop, daemon=True)
            self.shake_thread.start()

    def stop_shake_thread(self):
        """Stop the background shake thread."""
        self.shake_running = False
        if self.shake_thread and self.shake_thread.is_alive():
            self.shake_thread.join(timeout=1.0)

    def stop(self):
        """Stop the controller and perform all cleanup tasks."""
        self.stop_shake_thread()
        self.action_in_progress = False
        self.shake = False
        

    def _shake_loop(self):
        """Background loop that performs mouse shaking when no action is in progress."""
        while self.shake_running:
            if not self.action_in_progress and self.shake:
                self._perform_slight_shake()
            time.sleep(0.05)

    def _perform_slight_shake(self):
        """Perform a more pronounced mouse shake to simulate human-like idle behavior."""
        try:
            current_x, current_y = pyautogui.position()
            
            # Larger random offset for more noticeable shake (3-8 pixels)
            shake_x = random.randint(-3, 3)
            shake_y = random.randint(-3, 3)
            
            # Move with more movement and back
            pyautogui.moveTo(current_x + shake_x, current_y + shake_y, 
                           duration=random.uniform(0.02, 0.05), _pause=False)
            time.sleep(random.uniform(0.02, 0.05))
            pyautogui.moveTo(current_x, current_y, 
                           duration=random.uniform(0.02, 0.05), _pause=False)
        except Exception:
            # Ignore shake errors to avoid interrupting main functionality
            pass

    def _set_action_state(self, in_progress: bool):
        """Set the action state to track when actions are happening."""
        self.action_in_progress = in_progress

    def wait(self, seconds: float):
        self._set_action_state(True)
        time.sleep(seconds)
        self._set_action_state(False)
        return "Waited for " + str(seconds) + " seconds"
    
    def click(self, x: int, y: int, button: str = 'left'):
        self._set_action_state(True)
        self.wait(0.5)
        try:
            if self.human_movement:
                smooth_bezier = lambda n: bezier(n, (0.25, 0.1), (0.75, 0.9))
                duration = random.uniform(0.5, 1.2)
                pyautogui.click(x, y, button=button, duration=duration, tween=smooth_bezier, _pause=False)
            else:
                pyautogui.click(x, y)
        except Exception as e:
            self._set_action_state(False)
            raise Exception("Error clicking at position (" + str(x) + ", " + str(y) + "): " + str(e))
        self._set_action_state(False)

    def hotkey(self, *args, **kwargs):
        self._set_action_state(True)
        pyautogui.hotkey(*args, **kwargs)
        self._set_action_state(False)

    def typewrite(self, text: str, base_interval: float = 0.1):
        """Type text with optional human-like behavior.
        
        Args:
            text: The text to type
            human_typing: Whether to simulate human-like typing behavior with mistakes
            base_interval: Base interval between keystrokes in seconds
        """
        self._set_action_state(True)
        try:
            if self.human_movement:
                # Type with human-like behavior including mistakes
                for char in text:
                    # Small chance of typo
                    # if random.random() < 0.05:  # 5% chance
                    #     wrong_char = random.choice('qwertyuiopasdfghjklzxcvbnm')
                    #     interval = max(0.02, base_interval + random.uniform(-0.03, 0.03))
                    #     pyautogui.keyUp('fn')
                    #     pyautogui.typewrite(wrong_char, interval=interval)
                    #     pyautogui.keyUp('fn')
                    #     pyautogui.press('backspace')
                    #     pyautogui.sleep(interval)
                        
                    # Type correct character    
                    interval = max(0.02, base_interval + random.uniform(-0.03, 0.03))
                    pyautogui.keyUp('fn')
                    pyautogui.typewrite(char, interval=interval)
                    pyautogui.keyUp('fn')
                    # Random pause
                    if random.random() < 0.1:  # 10% chance
                        pyautogui.sleep(random.uniform(0.1, 0.3))
            else:
                pyautogui.keyUp('fn')
                pyautogui.typewrite(text)
                pyautogui.keyUp('fn')

        except Exception as e:
            self._set_action_state(False)
            raise Exception("Error typing text: " + str(e))
        self._set_action_state(False)
            
    def press_key(self, key: str) -> str:
        self._set_action_state(True)
        try:
            pyautogui.press(key)

        except Exception as e:
            self._set_action_state(False)
            raise Exception("Error pressing key: " + str(e))
        self._set_action_state(False)
        
    def hover(self, x: int, y: int):
        self._set_action_state(True)
        try:
            if self.human_movement:
                smooth_bezier = lambda n: bezier(n, (0.25, 0.1), (0.75, 0.9))
                duration = random.uniform(0.5, 1.2)
                pyautogui.moveTo(x, y, duration=duration, tween=smooth_bezier, _pause=False)
            else:
                pyautogui.moveTo(x, y)
        except Exception as e:
            self._set_action_state(False)
            raise Exception("Error hovering at position (" + str(x) + ", " + str(y) + "): " + str(e))
        self._set_action_state(False)
    
    def scroll(self, x: int, y: int, direction: str, scroll_amount: int = 10) -> str:
        self._set_action_state(True)
        try:
            if self.human_movement:
                if direction == "up":
                    self.hover(x, y)
                    pyautogui.scroll(scroll_amount, _pause=False)
                elif direction == "down":
                    self.hover(x, y)
                    pyautogui.scroll(-scroll_amount, _pause=False)
            else:
                if direction == "up":
                    self.hover(x, y)
                    self.wait(0.5)
                    pyautogui.scroll(scroll_amount, _pause=False)
                elif direction == "down":
                    self.hover(x, y)
                    self.wait(0.5)
                    pyautogui.scroll(-scroll_amount, _pause=False)
        except Exception as e:
            self._set_action_state(False)
            raise Exception("Error scrolling: " + str(e))
        self._set_action_state(False)

    def __del__(self):
        """Cleanup method to stop shake thread when controller is destroyed."""
        self.stop()


def main():
    controller = HumanInputController(human_movement=True, shake=True)  # Enable shake for testing
    controller.click(100, 100)
    controller.typewrite("Hello, world!")
    controller.press_key("Enter")


if __name__ == "__main__":
    main()