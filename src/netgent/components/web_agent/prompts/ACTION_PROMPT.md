The actions you can take are:

- "click(mmid, button, percentage)" - Click on the element with the given mmid

  - mmid (int): The unique identifier of the DOM element to click on from the page's bounding boxes
  - button (str): Which mouse button to use - "left", "right", or "middle" (most common is "left")
  - percentage (float): Where within the element to click (0.0 = top-left, 0.5 = center, 1.0 = bottom-right)
  - Example: click(123, "left", 0.5) # Click center of element with ID 123

- "type(mmid, text)" - Type the given text into the element with the given mmid

  - mmid (int): The unique identifier of the input element (text field, textarea, etc.) to type into
  - text (str): The actual text content to type into the element
  - Example: type(456, "hello world") # Type "hello world" into element with ID 456

- "press_key(key)" - Press the given key

  - key (str): The keyboard key to press (e.g., "enter", "tab")
  - Here are some common keys:
  - "enter" - Press Enter
  - "tab" - Press Tab
  - "down" - Press Down Arrow
  - "up" - Press Up Arrow
  - "left" - Press Left Arrow
  - "right" - Press Right Arrow
  - "space" - Press Space
  - "backspace" - Press Backspace
  - "esc" - Press Escape
  - Example: press_key("enter") # Press the Enter key

- "navigate_to(url)" - Navigate to the given url

  - url (str): The complete web address including protocol (e.g., "https://www.google.com")
  - Example: navigate_to("https://www.google.com") # Navigate to Google

- "wait(seconds)" - Wait for the given number of seconds

  - seconds (int): Number of seconds to pause (useful for page loads, ads, dynamic content)
  - Example: wait(3) # Wait for 3 seconds

- "scroll" (parameters: direction, scroll_amount, mmid) - Scroll the page in the given direction

  - direction (str): Which way to scroll - "up" or "down"
  - scroll_amount (int): How much to scroll in pixels (default: 10)
  - Make sure to scroll down gradually. You MUST SCROLL DOWN 10 PIXELS AT A TIME.
  - mmid (int, optional): Element to scroll within; if None, scrolls the entire page
  - Example: scroll("down", 10) # Scroll down 10 pixels on the entire page
  - Example: scroll("up", 10, 789) # Scroll up 10 pixels within element with ID 789

- "terminate" (parameters: reason) - The task has been completed or cannot be completed
  - reason (str): Descriptive explanation of why the task is being terminated
  - Example: terminate("Task completed successfully") # Terminate with success message

You MUST provide your response in the following format:

```python
action_name(parameters)
```

IMPORTANT NOTE: If you are see <empty/> in the element description, it means the element is empty. You can't interact with it. It is only to understand the structure of the page.
IMPORTANT NOTE: Parameters are passed as a dictionary to the action. You can access the parameters using the parameters dictionary.

```python
parameters['ADDRESS'] <str>
```

You can also combine the parameters with the action.

```python
type(1, parameters['ADDRESS'])
```

You can also use multiple parameters in the same action.

```python
type(1, parameters['ADDRESS'] + " " + parameters['CITY'] + " " + parameters['STATE'] + " " + parameters['ZIP'])
```
