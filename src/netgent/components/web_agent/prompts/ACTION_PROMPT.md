# Available Actions

## Actions with MMID (Element Interactions)

### **click** - Click on an element

- **action**: "click"
- **mmid** (int): The unique identifier of the DOM element to click on from the page's bounding boxes
- **params** (dict): Empty dict `{}` (button and percentage are handled automatically by the system)
- **Description**: Clicks on the specified element. The system will automatically determine the optimal click position (center of the element) and use the left mouse button by default.
- **Example JSON**:
  ```json
  {
    "action": "click",
    "mmid": 123,
    "params": {},
    "reasoning": "Clicking the search button to submit the query"
  }
  ```

### **type** - Type text into an element

- **action**: "type"
- **mmid** (int): The unique identifier of the input element (text field, textarea, etc.) to type into
- **params** (dict): `{"text": "the actual text content to type"}`
- **Description**: Types the specified text into the input element. Use this for filling out forms, search boxes, or any text input fields.
- **Example JSON**:
  ```json
  {
    "action": "type",
    "mmid": 456,
    "params": { "text": "hello world" },
    "reasoning": "Typing the search query into the search box"
  }
  ```

### **scroll** - Scroll within an element or the page

- **action**: "scroll"
- **mmid** (int or null): Element to scroll within; use `null` to scroll the entire page
- **params** (dict): `{"direction": "up" or "down", "pixels": 10}`
- **Description**: Scrolls the page or a specific scrollable element. Make sure to scroll gradually - you MUST scroll 10 pixels at a time for smooth scrolling.
- **Example JSON (scroll entire page)**:
  ```json
  {
    "action": "scroll",
    "mmid": null,
    "params": { "direction": "down", "pixels": 10 },
    "reasoning": "Scrolling down to view more content on the page"
  }
  ```
- **Example JSON (scroll within element)**:
  ```json
  {
    "action": "scroll",
    "mmid": 789,
    "params": { "direction": "up", "pixels": 10 },
    "reasoning": "Scrolling up within the dropdown menu to see earlier options"
  }
  ```

## Actions without MMID (General Actions)

### **press_key** - Press a keyboard key

- **action**: "press_key"
- **mmid**: null
- **params** (dict): `{"key": "enter"}`
- **Description**: Presses a keyboard key. Useful for navigation, submitting forms, or interacting with keyboard shortcuts.
- **Common keys**: "enter", "tab", "down", "up", "left", "right", "space", "backspace", "esc"
- **Example JSON**:
  ```json
  {
    "action": "press_key",
    "mmid": null,
    "params": { "key": "enter" },
    "reasoning": "Pressing Enter to submit the search form"
  }
  ```

### **navigate** - Navigate to a URL

- **action**: "navigate"
- **mmid**: null
- **params** (dict): `{"url": "https://www.google.com"}`
- **Description**: Navigates the browser to the specified URL. The URL must include the protocol (http:// or https://).
- **Example JSON**:
  ```json
  {
    "action": "navigate",
    "mmid": null,
    "params": { "url": "https://www.google.com" },
    "reasoning": "Navigating to Google homepage to start the search"
  }
  ```

### **wait** - Wait for a specified number of seconds

- **action**: "wait"
- **mmid**: null
- **params** (dict): `{"seconds": 2}`
- **Description**: Pauses execution for the specified number of seconds. Useful for waiting for page loads, ads to finish, or dynamic content to appear.
- **Example JSON**:
  ```json
  {
    "action": "wait",
    "mmid": null,
    "params": { "seconds": 3 },
    "reasoning": "Waiting for the page to fully load before interacting"
  }
  ```

### **terminate** - End the task

- **action**: "terminate"
- **mmid**: null
- **params** (dict): `{"reason": "Descriptive explanation of why the task is being terminated"}`
- **Description**: Signals that the task has been completed successfully or cannot be completed. Provide a clear reason explaining the outcome.
- **Example JSON**:
  ```json
  {
    "action": "terminate",
    "mmid": null,
    "params": { "reason": "Task completed successfully" },
    "reasoning": "Successfully found and accessed the LangChain documentation as requested"
  }
  ```

## Output Format

You MUST respond with a JSON object following this exact schema:

```json
{
  "action": "string (required) - The name of the action to execute",
  "mmid": "number or null (optional) - The MMID of the element to interact with",
  "params": "object (required) - Additional parameters for the action",
  "reasoning": "string (required) - Brief explanation of why this action is being taken"
}
```

## Complete Action Examples

### Example 1: Clicking an element

```json
{
  "action": "click",
  "mmid": 5,
  "params": {},
  "reasoning": "Clicking the search button to submit the query"
}
```

### Example 2: Typing text

```json
{
  "action": "type",
  "mmid": 10,
  "params": { "text": "LangChain documentation" },
  "reasoning": "Typing the search query into the search box"
}
```

### Example 3: Pressing a key

```json
{
  "action": "press_key",
  "mmid": null,
  "params": { "key": "enter" },
  "reasoning": "Pressing enter to submit the search"
}
```

### Example 4: Navigating to a URL

```json
{
  "action": "navigate",
  "mmid": null,
  "params": { "url": "https://www.google.com" },
  "reasoning": "Navigating to Google homepage to start search"
}
```

### Example 5: Scrolling the page

```json
{
  "action": "scroll",
  "mmid": null,
  "params": { "direction": "down", "pixels": 10 },
  "reasoning": "Scrolling down to view more search results"
}
```

### Example 6: Scrolling within an element

```json
{
  "action": "scroll",
  "mmid": 789,
  "params": { "direction": "up", "pixels": 10 },
  "reasoning": "Scrolling up within the dropdown menu"
}
```

### Example 7: Waiting

```json
{
  "action": "wait",
  "mmid": null,
  "params": { "seconds": 2 },
  "reasoning": "Waiting for the page to fully load"
}
```

### Example 8: Terminating

```json
{
  "action": "terminate",
  "mmid": null,
  "params": { "reason": "Task completed successfully" },
  "reasoning": "Successfully found and accessed the LangChain documentation"
}
```

## IMPORTANT NOTES

- If you see `<empty/>` in element description, you cannot interact with it
- Scroll gradually: 10 pixels at a time when scrolling
- Always provide reasoning for your action choice
- ONLY output the JSON, no additional text before or after
