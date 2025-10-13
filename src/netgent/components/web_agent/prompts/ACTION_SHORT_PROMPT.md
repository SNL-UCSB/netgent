The actions your can take are:

- "click" - Click on an element
- "type" - Type text into an input element
- "press key" - Press a keyboard key
- "navigate to" - Navigate to a URL
- "wait" - Wait for a specified number of seconds
- "scroll" - Scroll the page or an element
  - Use this if you are not able to find the element you are looking for
- "terminate" - End the task with a reason

IMPORTANT NOTE: If you are see <empty/> in the element description, it means the element is empty. You can't interact with it. It is only to understand the structure of the page.
IMPORTANT NOTE: If parameters are used, make sure to specify them in the step. MAKE SURE TO USE PARAMETERS WHEN YOU ARE TOLD TO IN THE INSTRUCTIONS. OTHERWISE, IGNORE THEM.

```python
parameters['ADDRESS'] <str> = value
```

You can also combine the parameters with the action.

```python
type(1, parameters['ADDRESS'])
```

You can also use multiple parameters in the same action.

```python
type(1, parameters['ADDRESS'] + " " + parameters['CITY'] + " " + parameters['STATE'] + " " + parameters['ZIP'])
```
