The actions you can take are:

- "click" - Click an accessibility element (by its mmid)
- "type" - Type text into a text field / text area (by its mmid)
- "press key" - Press a keyboard key
- "hotkey" - Press a chord of keys together (e.g. command,s)
- "open application" - Launch a macOS application directly (via launch services, like Spotlight); this is the only way to open an app -- never click through Finder/Dock/Spotlight
- "activate application" - Bring an already-running application to the foreground
- "wait" - Wait for a specified number of seconds
- "scroll" - Scroll the view or an element
  - Use this if you cannot yet find the element you are looking for
- "terminate" - End the task with a reason

IMPORTANT NOTE: Elements come from the macOS Accessibility tree, each with an
mmid, a role, and a label. Only act on elements in that list; never guess screen
coordinates. If you see `<empty/>` in an element description it has no label and
is usually not interactable.
