from pydantic import BaseModel, Field
from typing import Optional
import json

class Message(BaseModel):
    pass

class Element(BaseModel):
    enhanced_css_selector: Optional[str] = None
    css_selector: Optional[str] = None
    aria_label: Optional[str] = None
    accessible_name: Optional[str] = None
    text: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None

    def __str__(self):
        parts = []
        if self.enhanced_css_selector:
            parts.append(f"enhanced css selector: {self.enhanced_css_selector}")
        if self.css_selector:
            parts.append(f"css selector: {self.css_selector}")
        if self.aria_label:
            parts.append(f"aria label: {self.aria_label}")
        if self.accessible_name:
            parts.append(f"accessible name: {self.accessible_name}")
        if self.text:
            parts.append(f"text: {self.text}")
        
        content = "\n\t".join(parts) if parts else ""
        return f"<element>\n\t{content}\n</element>"
    

class Toolcall(Message):
    name: str
    args: dict
    element: Optional[Element] = None
    error: Optional[str] = None
    
    def __str__(self):
        args_str = "\n".join([f"{k}: {v}" for k, v in self.args.items() if k != "mmid"])
        content_parts = [args_str] if args_str else []
        if self.element and any(getattr(self.element, field) for field in self.element.__class__.model_fields):
            content_parts.append(str(self.element))
        if self.error:
            content_parts.append(f"error: {self.error}")
        content = "\n".join(content_parts)
        return f"<{self.name}>\n{content}\n</{self.name}>"

class ActionOutput(Message):
    action: str = Field(description="The name of the action to execute (e.g., 'click', 'type', 'navigate', 'scroll', 'press_key', 'wait', 'terminate')")
    mmid: Optional[int] = Field(default=None, description="The MMID (unique identifier) of the element to interact with. Required for actions like click, type that interact with specific elements.")
    params: dict = Field(default_factory=dict, description="Additional parameters for the action (e.g., text for type action, url for navigate, key for press_key, etc.)")
    reasoning: str = Field(description="Brief explanation of why this action is being taken")
    def __str__(self):
        return f"<action_output>\naction: {self.action}\nmmid: {self.mmid}\nparams: {self.params}\nreasoning: {self.reasoning}\n</action_output>"

class Decision(Message):
    action: str = Field(description="The action to be taken.")
    reasoning: str = Field(description="The reasoning for the action. This should be a detailed explanation of why the action was chosen.")

    def __str__(self):
        return f"<decision>\naction: {self.action}\nreasoning: {self.reasoning}\n</decision>"

class Reflection(Message):
    is_successful: bool = Field(description="Whether the action was completed successfully.")
    reason: str = Field(description="The reason for the action being a success or failure.")
    next_step: str = Field(description="The next step to be taken.")
    
    def __str__(self):
        return f"<reflection>\nis_successful: {self.is_successful}\nreason: {self.reason}\nnext_step: {self.next_step}\n</reflection>"

class Metadata(Message):
    timestamp: Optional[int] = Field(description="The timestamp iteration of the current page.")
    elements: Optional[dict] = Field(description="The elements on the current page.")
    element_description: str = Field(description="A description of the elements on the current page.")
    screenshot: str = Field(description="A screenshot of the current page.")
    dom: str = Field(description="The DOM of the current page.")
    url: str = Field(description="The URL of the current page.")
    title: str = Field(description="The title of the current page.")

    def __str__(self):
        return f"<TIMESTEP {self.timestamp}\nTitle: {self.title}\n>"


class ExecutedState(Message):
    timestamp: int = Field(description="The timestamp of the state.")
    name: str = Field(description="The name of the state.")
    description: str = Field(description="The description of the state.")
    checks: list[dict] = Field(description="The checks of the state.")
    actions: list[str] = Field(description="The actions of the state.")

    def __str__(self):
        checks_str = ""
        for check in self.checks:
            checks_str += f"  - {check}\n"
        
        actions_str = ""
        for action in self.actions:
            actions_str += f"  - {action}\n"
            
        return f"""<Executed State {self.timestamp}>
NAME: {self.name}
DESCRIPTION: {self.description if self.description else 'No Description'}
CHECKS:
{checks_str}ACTIONS:
{actions_str}</Executed State>"""
    
    
    

def format_context(context: list[Message]):
    overall_str = ""
    for message in context:
        if isinstance(message, Metadata):
            overall_str += "\n" + str(message) + "\n"
        else:
            overall_str += str(message) + "\n"
    return overall_str

def format_context_without_reflection(context: list[Message]):
    overall_str = ""
    for message in context:
        if isinstance(message, Metadata):
            overall_str += "\n" + str(message) + "\n"
        elif not isinstance(message, Reflection):
            overall_str += str(message) + "\n"
    return overall_str


def save_context_to_file(context: list[Message], filename: str = "context_output.json"):
    """Save context messages to a JSON file."""
    context_data = []
    for message in context:
        context_data.append(message.model_dump())
    
    with open(filename, "w") as f:
        json.dump(context_data, f, indent=2)


def load_context_from_file(filename: str = "context_output.json") -> list[Message]:
    """Load context messages from a JSON file."""
    with open(filename, "r") as f:
        context_data = json.load(f)
    
    context_objects = []
    for item in context_data:
        if "action" in item and "reasoning" in item:
            context_objects.append(Decision(**item))
        elif "name" in item and "args" in item:
            context_objects.append(Toolcall(**item))
        elif "is_successful" in item and "reason" in item and "next_step" in item:
            context_objects.append(Reflection(**item))
        elif "timestamp" in item and "elements" in item:
            context_objects.append(Metadata(**item))
    
    return context_objects


class StatePrompt(BaseModel):
    name: str = Field(description="Name of the State")
    description: str = Field(description="Description of the State (What the State Does)")
    triggers: list[str] = Field(description="Triggers of the State (What Triggers the State to Run the Actions)")
    actions: list[str] = Field(description="Actions of the State (What the State Does. What It Should Run)")
    end_state: Optional[str] = Field(description="The reason for the state to end", default="")
    
    def __str__(self):
        actions_str = "\n".join([f"\t{i+1}. {action}" for i, action in enumerate(self.actions)])
        triggers_str = "\n".join([f"\t{i+1}. {trigger}" for i, trigger in enumerate(self.triggers)])
        end_state_str = f"\n- **End State:** {self.end_state}" if self.end_state else ""
        return f"## State: {self.name}\n- **Description:** {self.description}\n- **Triggers:**\n{triggers_str}\n- **Actions:**\n{actions_str}{end_state_str}"
