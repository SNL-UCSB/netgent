from typing import List, Optional, TypedDict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from dotenv import load_dotenv
from state_agent.actions.browser_manager import BrowserManager
from ..message import Message, Code, format_context, Metadata
import contextlib
from pyautogui import FailSafeException
import builtins
import time
import io
import functools
import inspect
from state_agent.state_agent.browser_agent.prompt import PLAN_PROMPT, EXECUTE_PROMPT, ACTION_PROMPT, RULES_PROMPT, REPLAN_PROMPT, ACTION_SHORT_PROMPT
load_dotenv()

class BrowserAgentState(TypedDict):
    user_query: str

    # Intermediate State #
    script: Optional[str]
    summary: str
    messages: List[Message]
    use_image: bool
    global_plan: str
    timestep: int
    parameters: dict[str, Any]  # Parameters passed to the agent


class BrowserAgent():
    def __init__(self, llm: BaseChatModel, browser_manager: BrowserManager, wait_period: float = 0.5):
        self.llm = llm
        self.browser_manager = browser_manager
        self.workflow = self._initalize_workflow()
        self.graph = self.workflow.compile()
        self.wait_period = wait_period

        ## HTML DOM Related ##
        self.elements = None
        self.prompt = None
        self.screenshot = None
        
        ## Temp Code ##
        self.temp_code = []

        # CodeAct Context #
        self.locals = {
            "click": self.click,
            "press_key": self.press_key,
            "navigate_to": self.navigate_to,
            "type": self.type,
            "wait": self.wait,
            "scroll": self.scroll,
            "terminate": self.terminate,
        }

    def prompt_parameters(self, parameters: dict[str, Any]):
        prompt = []
        for key, value in parameters.items():
            prompt.append(f"parameters['{key}'] <{type(value).__name__}> = {value}")
        result = "\n".join(prompt)
        print("# PROMPT PARAMETERS: \n", result)
        return result

    

    def log_action(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            sig       = inspect.signature(func)
            bound     = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arg_dict  = dict(bound.arguments)

            arg_dict.pop('self', None)

            # Replace actual parameter values with their key references
            if hasattr(args[0], 'locals') and 'parameters' in args[0].locals:
                parameters = args[0].locals['parameters']
                # Create reverse mapping from parameter values to their keys
                value_to_key = {v: k for k, v in parameters.items()}
                
                for k, v in arg_dict.items():
                    if k != "mmid" and isinstance(v, str):
                        # Check if this value matches any parameter value
                        if v in value_to_key:
                            # Replace with the parameter key reference
                            arg_dict[k] = f"parameters['{value_to_key[v]}']"
                        # If it's not a parameter value and not already a key reference,
                        # it's not a parameter

            filtered = {k: v for k, v in arg_dict.items() if k != "mmid"}

            if hasattr(args[0], 'temp_code'):
                element = None
                if "mmid" in arg_dict and arg_dict["mmid"] is not None:
                    element = args[0].elements[str(int(arg_dict["mmid"]))]
                args[0].temp_code.append(
                    Code(name=func.__name__, args=filtered, element=element, error=None)
                )

            return func(*args, **kwargs)

        return wrapper
    
    ### Tools ###
    @log_action
    def click(self, mmid: int, button: str, percentage: float):
        if str(int(mmid)) not in self.elements:
            raise Exception(f"Element is not found")

        try:
            element = self.elements[str(int(mmid))]
            x, y = self.browser_manager.get_element_coordinates(element["x"], element["y"], element["width"], element["height"], percentage)
            self.browser_manager.controller.click(x, y, button)
        except FailSafeException as e:
            raise Exception(e)
        except Exception as e:
            raise Exception(f"Error clicking element: {str(e)}")

    @log_action
    def press_key(self, key: str):
        try:
            self.browser_manager.controller.press_key(key)
            time.sleep(0.5)  # WAIT_TIME equivalent
        except FailSafeException as e:
            raise Exception(e)
        except Exception as e:
            raise Exception(f"Error pressing key: {str(e)}")

    @log_action
    def navigate_to(self, url: str):
        try:
            self.browser_manager.navigate_to(url)
            time.sleep(0.5)  # WAIT_TIME equivalent
        except Exception as e:
            raise Exception(f"Error navigating to {url}: {str(e)}")

    @log_action
    def type(self, mmid: int, text: str):
        if str(int(mmid)) not in self.elements:
            raise Exception("Element is not found")
        
        try:
            element = self.elements[str(int(mmid))]
            x, y = self.browser_manager.get_element_coordinates(element["x"], element["y"], element["width"], element["height"])
            self.browser_manager.controller.click(x, y)
            self.browser_manager.controller.typewrite(text)
            time.sleep(0.5)  # WAIT_TIME equivalent
        except FailSafeException as e:
            raise Exception(e)
        except Exception as e:
            raise Exception(f"Error typing text: {str(e)}")

    @log_action
    def terminate(self, reason: str = "") -> str:
        print("Terminating task with reason: ", reason)
        return "Terminate: " + reason

    @log_action
    def wait(self, seconds: int):
        self.browser_manager.controller.wait(seconds)

    @log_action
    def scroll(self, direction: str, scroll_amount: int = 10, mmid: int = None):
        if mmid:
            # Check if Interactable Elements are Loaded
            if str(int(mmid)) not in self.elements:
                raise Exception("Element is not found")
            
            element = self.elements[str(int(mmid))]
            x, y = self.browser_manager.get_element_coordinates(element["x"], element["y"], element["width"], element["height"])

            if direction == "up":
                self.browser_manager.controller.scroll(x, y, "up", scroll_amount)
                time.sleep(0.5)  # WAIT_TIME equivalent
            elif direction == "down":
                self.browser_manager.controller.scroll(x, y, "down", scroll_amount)
                time.sleep(0.5)  # WAIT_TIME equivalent
            else:
                raise Exception(f"Invalid direction: {direction}")
        else:        
            window_pos = self.browser_manager.driver.get_window_position()
            window_x = window_pos['x']
            window_y = window_pos['y']
            window_size = self.browser_manager.driver.get_window_size()
            
            # Calculate right side of the browser window
            right_x = window_x + window_size['width'] - 10
            center_y = window_y + (window_size['height'] // 2)
            
            if direction == "up":
                self.browser_manager.controller.scroll(right_x, center_y, "up", scroll_amount)
                time.sleep(0.5)  # WAIT_TIME equivalent
            elif direction == "down":
                self.browser_manager.controller.scroll(right_x, center_y, "down", scroll_amount)
                time.sleep(0.5)  # WAIT_TIME equivalent
            else:
                raise Exception(f"Invalid direction: {direction}")


    def run(self, user_query: str, messages: List[Message] = [], parameters: dict[str, Any] = {}):
        self.locals = {**self.locals, "parameters": parameters}
        state = BrowserAgentState(user_query=user_query, summary="", messages=messages, script="None", timestep=0, global_plan="", parameters=parameters)
        state = self.graph.invoke(state, { "recursion_limit": 100})
        return state
    
    def _annotate(self, state: BrowserAgentState):
        time.sleep(2 * self.wait_period)
        self.elements, self.prompt, self.screenshot = self.browser_manager.mark_page.with_retry().invoke(None)
        state["messages"] += [Metadata(
            timestamp=state["timestep"], 
            elements=self.elements, 
            element_description=self.prompt, 
            screenshot=self.screenshot, 
            dom="",
            url=self.browser_manager.driver.current_url, 
            title=self.browser_manager.driver.title
        )]
        state["timestep"] += 1
        return { **state }
    
    def _observe(self, state: BrowserAgentState):
        return { **state }

    def _plan(self, state: BrowserAgentState):
        prompt = PLAN_PROMPT
        if state["global_plan"] != "":
            prompt = REPLAN_PROMPT

        response = self.llm.invoke(input=[
            SystemMessage(content=ACTION_SHORT_PROMPT + "\n\n" + prompt),
            HumanMessage(content=[
                {
                    "type": "text", 
                    "text": f"""## User Query: {state['user_query']}
                    ## Initial HTML State: {self.prompt}
                    You MUST start with the '## Step 1' header and follow the format provided in the examples."""
                },
                {
                    "type": "text",
                    "text": f"""## Previous Action Trajectory:\n{format_context(state['messages'])}\n## Current HTML: {self.prompt}\n## Parameters: {self.prompt_parameters(state['parameters'])}"""
                },
                {
                    "type": "image",
                    "source_type": "base64",
                    "data": self.screenshot,
                    "mime_type": "image/png"
                }
            ])
        ])
        print(self.prompt)
        return { **state, "global_plan": response.content }
    
    ### Code Execution ###
    def _eval(self, code: str, _locals: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        original_keys = set(_locals.keys())

        try:
            with contextlib.redirect_stdout(io.StringIO()) as f:
                exec(code, builtins.__dict__, _locals)
            result = f.getvalue()
            if not result:
                result = "<code ran, no output printed to stdout>"
        except Exception as e:
            result = f"Error during execution: {repr(e)}"

        new_keys = set(_locals.keys()) - original_keys
        new_vars = {key: _locals[key] for key in new_keys}
        return result, new_vars
    
    def _execute(self, state: BrowserAgentState):
        response = self.llm.invoke(input=[
            SystemMessage(content=RULES_PROMPT + "\n\n" + EXECUTE_PROMPT.format(intent=state['user_query'], global_plan=state['global_plan']) + "\n\n" + ACTION_PROMPT),
            HumanMessage(content=f"## Previous Action Trajectory:\n{format_context(state['messages'])}\n## Current HTML: {self.prompt}\n## Parameters (DONT USE THE ACTUAL VALUES, USE THE KEYS (parameters['KEY'])):\n{self.prompt_parameters(state['parameters'])}"),
            HumanMessage(content=f"You MUST provide your response in the following format:\n```python\naction_name(parameters)\n```\n\nFor example:\n```python\nnavigate_to(\"https://www.google.com/\")\n```"),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": f"""Screenshot of the Current Page"""
                },
                {
                    "type": "image",
                    "source_type": "base64",
                    "data": self.screenshot,
                    "mime_type": "image/png"
                }
            ])
        ])
        code = extract_and_combine_codeblocks(response.content)
        print("RESPONSE: ", response.content)
        print("CODE: ", code)
        
        # Execute the extracted code or fallback to raw response
        script_to_execute = code.strip() if code.strip() else response.content
        result, new_vars = self._eval(script_to_execute, self.locals)
        self.locals = {**self.locals, **new_vars}
        print(result)
        
        # Update state with execution results
        state["messages"] += self.temp_code
        self.temp_code = []
        state["script"] = script_to_execute
        
        return { **state }
    
    def _should_continue(self, state: BrowserAgentState):
        script = state.get("script", "")
        if script and "terminate" in script:
            return END
        return "annotate"
    
    def _initalize_workflow(self):
        workflow = StateGraph(BrowserAgentState)
        workflow.add_node("annotate", self._annotate)
        workflow.add_node("observe", self._observe)
        workflow.add_node("plan", self._plan)
        workflow.add_node("execute", self._execute)
        workflow.add_edge(START, "annotate")
        workflow.add_edge("annotate", "observe")
        workflow.add_edge("observe", "plan")
        workflow.add_edge("plan", "execute")
        workflow.add_conditional_edges("execute", self._should_continue)
        return workflow


import re

BACKTICK_PATTERN = r"```(.*?)```"


def extract_and_combine_codeblocks(text: str) -> str:
    """
    Extracts all codeblocks from a text string and combines them into a single code string.

    Args:
        text: A string containing zero or more codeblocks, where each codeblock is
            surrounded by triple backticks (```).

    Returns:
        A string containing the combined code from all codeblocks, with each codeblock
        separated by a newline.

    Example:
        text = '''Here's some code:

        ```python
        print('hello')
        ```
        And more:

        ```
        print('world')
        ```'''

        result = extract_and_combine_codeblocks(text)

        Result:

        print('hello')

        print('world')
    """
    # Find all code blocks in the text using regex
    # Pattern matches anything between triple backticks, with or without a language identifier
    code_blocks = re.findall(BACKTICK_PATTERN, text, re.DOTALL)

    if not code_blocks:
        return ""

    # Process each codeblock
    processed_blocks = []
    for block in code_blocks:
        # Strip leading and trailing whitespace
        block = block.strip()

        # If the first line looks like a language identifier, remove it
        lines = block.split("\n")
        if lines and (not lines[0].strip() or " " not in lines[0].strip()):
            # First line is empty or likely a language identifier (no spaces)
            block = "\n".join(lines[1:])

        processed_blocks.append(block)

    # Combine all codeblocks with newlines between them
    combined_code = "\n\n".join(processed_blocks)
    return combined_code
