from typing import List, Optional, TypedDict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from dotenv import load_dotenv
from ...browser.controller.base import BaseController
from ...browser.registry import ActionRegistry, TriggerRegistry
from ...browser.utils import mark_page
from utils.message import Message, Code, format_context, Metadata
import contextlib
from pyautogui import FailSafeException
import builtins
import time
import io
import functools
import inspect
import os
load_dotenv()

class WebAgentState(TypedDict):
    user_query: str

    # Intermediate State #
    script: Optional[str]
    summary: str
    messages: List[Message]
    use_image: bool
    global_plan: str
    timestep: int
    parameters: dict[str, Any]  # Parameters passed to the agent


class WebAgent():
    def __init__(self, llm: BaseChatModel, controller: BaseController, wait_period: float = 0.5):
        self.llm = llm
        self.controller = controller
        self.driver = controller.driver
        self.action_registry = ActionRegistry(controller)
        self.trigger_registry = TriggerRegistry(controller)
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
            # Tools will be added here
        }

    def _get_prompt(self, name: str) -> str:
        """Load prompt from the prompts directory."""
        prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
        prompt_file = os.path.join(prompts_dir, f"{name}.md")
        with open(prompt_file, 'r') as f:
            return f.read()

    def prompt_parameters(self, parameters: dict[str, Any]):
        prompt = []
        for key, value in parameters.items():
            prompt.append(f"parameters['{key}'] <{type(value).__name__}> = {value}")
        result = "\n".join(prompt)
        print("# PROMPT PARAMETERS: \n", result)
        return result

    def _mmid_to_selector(self, mmid: int) -> tuple[str, str, dict]:
        """
        Convert mmid to selector information.
        
        Returns:
            tuple: (by, selector, element_dict) where element_dict contains fallback coordinates
        """
        if str(int(mmid)) not in self.elements:
            raise Exception(f"Element with mmid {mmid} not found")
        
        element = self.elements[str(int(mmid))]
        # Use enhanced_css_selector if available, otherwise use css_selector
        selector = element.get('enhanced_css_selector') or element.get('css_selector')
        if not selector:
            raise Exception(f"No selector found for element with mmid {mmid}")
        
        return "css selector", selector, element

    def check_element_by_mmid(self, mmid: int, check_visibility: bool = True) -> bool:
        """
        Check if an element exists using mmid, converting to TriggerRegistry call.
        
        Args:
            mmid: The element ID from the marked page
            check_visibility: Whether to check if element is visible
            
        Returns:
            bool: True if element exists (and is visible if check_visibility=True)
        """
        try:
            by, selector, element = self._mmid_to_selector(mmid)
            return self.trigger_registry.check("element", {
                "by": by,
                "selector": selector,
                "check_visibility": check_visibility
            })
        except Exception:
            return False


    ### Tools ###
    # TODO: Add tool methods here


    def run(self, user_query: str, messages: List[Message] = [], parameters: dict[str, Any] = {}):
        self.locals = {**self.locals, "parameters": parameters}
        state = WebAgentState(user_query=user_query, summary="", messages=messages, script="None", timestep=0, global_plan="", parameters=parameters)
        state = self.graph.invoke(state, { "recursion_limit": 100})
        return state
    
    def _annotate(self, state: WebAgentState):
        time.sleep(2 * self.wait_period)
        # Use mark_page utility from the browser utils
        mark_page_chain = mark_page(self.driver)
        self.elements, self.prompt, self.screenshot = mark_page_chain.with_retry().invoke(None)
        state["messages"] += [Metadata(
            timestamp=state["timestep"], 
            elements=self.elements, 
            element_description=self.prompt, 
            screenshot=self.screenshot, 
            dom="",
            url=self.driver.current_url, 
            title=self.driver.title
        )]
        state["timestep"] += 1
        return { **state }
    
    def _observe(self, state: WebAgentState):
        return { **state }

    def _plan(self, state: WebAgentState):
        prompt = self._get_prompt("PLAN_PROMPT")
        if state["global_plan"] != "":
            prompt = self._get_prompt("REPLAN_PROMPT")

        response = self.llm.invoke(input=[
            SystemMessage(content=self._get_prompt("ACTION_SHORT_PROMPT") + "\n\n" + prompt),
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
    
    def _execute(self, state: WebAgentState):
        response = self.llm.invoke(input=[
            SystemMessage(content=self._get_prompt("RULES_PROMPT") + "\n\n" + self._get_prompt("EXECUTE_PROMPT").format(intent=state['user_query'], global_plan=state['global_plan']) + "\n\n" + self._get_prompt("ACTION_PROMPT")),
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
    
    def _should_continue(self, state: WebAgentState):
        script = state.get("script", "")
        if script and "terminate" in script:
            return END
        return "annotate"
    
    def _initalize_workflow(self):
        workflow = StateGraph(WebAgentState)
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
