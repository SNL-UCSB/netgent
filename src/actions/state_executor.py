from .browser_manager import BrowserManager
from typing import Optional
import time
import pandas as pd

class StateExecutor:
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.check_functions = {
            "text": self.browser_manager.check_text,
            "url": self.browser_manager.check_url,
            "element": self.browser_manager.check_element,
        }
        self.action_functions = {
            "__builtins__": __builtins__,
            "navigate_to": self.browser_manager.navigate_to,
            "click": self.browser_manager.click,
            "type": self.browser_manager.type,
            "scroll_to": self.browser_manager.scroll_to,
            "scroll": self.browser_manager.scroll,
            "wait": self.browser_manager.wait,
            "press_key": self.browser_manager.press_key,
            "save_html": self.save_html,
        }

    def save_html(self, filename: str = "saved_page.html"):
        html_dom = self.browser_manager.driver.page_source
        with open(filename, "w", encoding="utf-8") as file:
            file.write(html_dom)
    
    # Check If Any Of The State's Checks Are Triggered
    def _check_trigger(self, state: dict):
        for check in state.get("checks", []):
            if not self.browser_manager.detect_trigger(check["type"], check["value"]):
                return False
        return True
    
    # Get the Passed States
    def get_passed_states(self, states: list[dict]) -> list[dict]:
        passed_states = []
        for state in states:
            if self._check_trigger(state):
                passed_states.append(state)
        return passed_states
    
    # Execute a Line of Code
    def _execute_line(self, line: str, parameters: Optional[dict] = {}):
        try:
            self.action_functions["parameters"] = parameters # Added Parameters to the Action Functions
            result = exec(line, self.action_functions)
        except Exception as e:
            return f"Error in Line [{line}]: {e}"
        return result
        
    # Execute a State
    def execute_state(self, state: dict, parameters: Optional[dict] = {}, config: Optional[dict] = None):
        # Manage Default Configurations
        default_config = {"action_period": 1}
        config = {**default_config, **(config or {})}

        # Result Dictionary
        result = {
            "success": True,
            "error": None,
        }

        # Execute the Actions for this State
        for i, action in enumerate(state.get("actions", [])):
            self.browser_manager.wait(config["action_period"])
            try:
                self.action_functions["parameters"] = parameters
                exec(action, self.action_functions)
            except Exception as e:
                result["success"] = False
                result["error"] = f"Error in State '{state['name']}' in Line {i + 1} [{action}]: {e}"
                return result
        return result
    
    def execute(self, states: list[dict], parameters: Optional[dict] = {}, config: Optional[dict] = None):
        default_config = {"action_period": 1, "transition_period": 3, "recursion_limit": 10, "allow_multiple_states": False, "state_timeout": 30, "no_states_timeout": 60}
        config = {**default_config, **(config or {})}

        result = {
            "success": True,
            "error": None,
            "message": None,
            "executed": [],
        }

        if states == []:
            result["success"] = False
            result["error"] = {"message": "No states provided"}
            return result

        previous_state = None
        timeout_start = None
        no_states_timeout_start = None
        
        recursion = 0
        while recursion < config["recursion_limit"]:
            self.browser_manager.wait(config["transition_period"])
            passed_states = self.get_passed_states(states)
            
            # No States Passed
            if len(passed_states) == 0:
                # Start no states timeout timer if enabled
                if config["no_states_timeout"] and no_states_timeout_start is None:
                    no_states_timeout_start = time.time()
                    print(f"No states passed - starting no states timeout timer: {config['no_states_timeout']} seconds")
                
                # Check if no states timeout has been exceeded
                if config["no_states_timeout"] and no_states_timeout_start is not None:
                    elapsed_time = time.time() - no_states_timeout_start
                    if elapsed_time > config["no_states_timeout"]:
                        result["success"] = False
                        result["error"] = {"message": f"No states have been passed for more than {config['no_states_timeout']} seconds. No states timeout exceeded."}
                        return result
                    print(f"No states passed - timer running: {elapsed_time:.2f}s")
                
                # If no states timeout is not enabled, return error immediately
                if not config["no_states_timeout"]:
                    result["success"] = False
                    result["error"] = {"message": "No States Passed"}
                    return result
                
                # Continue waiting if timeout is enabled
                continue
            else:
                # Reset no states timeout when states are found
                no_states_timeout_start = None
            
            if not config["allow_multiple_states"] and len(passed_states) > 1:
                result["success"] = False
                result["error"] = {"message": "Multiple States Passed", "states": passed_states}
                return result
            
            # Execute the State
            print("Passed States:", [state["name"] for state in passed_states])
            state = passed_states[0]

            # Timer for Non-Continuous States
            if previous_state is not None and previous_state["name"] == state["name"]:
                if state.get("config", {}).get("continous", False) == False:
                    if timeout_start is None:
                        timeout_start = time.time()
                        print(f"Timer started for state '{state['name']}' - will timeout after {config['state_timeout']} seconds")
                    
                    if time.time() - timeout_start > config["state_timeout"]:
                        result["success"] = False
                        result["error"] = {"message": f"State '{state['name']}' has been running for more than {config['state_timeout']} seconds. Timer exceeded."}
                        return result
                    
                    print(f"State '{state['name']}' repeated - timer running: {time.time() - timeout_start:.2f}s")
                    continue
            else:
                timeout_start = None

            # Run the State
            state_result = self.execute_state(state, parameters, config)
            result["executed"].append(state)
            previous_state = state
            
            ## Check for Termination
            if state.get("end_state"):
                result["success"] = True
                result["message"] = state["end_state"]
                return result
            
            # Check for Errors
            if state_result["error"] is not None:
                result["success"] = False
                result["error"] = {"message": f"Error in State {state['name']}", "state": state, "result": state_result}
                return result
            recursion += 1
        # If we reach here, we've hit the recursion limit
        result["success"] = False
        result["error"] = {"message": "Recursion limit reached"}

        return result


def main():
    proxy = "brd-customer-hl_bdb3a3b4-zone-static:zjblan9e6w2q@brd.superproxy.io:33335"
    browser_manager = BrowserManager(human_movement=True, proxy=proxy)
    executor = StateExecutor(browser_manager)
    # Execute the States

    transitions = {
        "states": [
            {
                "name": "Cookies Popup",
                "description": "Navigated to the Xfinity Website",
                "checks": [
                    {
                        "type": "text",
                        "value": "We use Cookies to improve our Services, optimize your experience, and serve ads relevant to your int..."
                    }
                ],
                "actions": [
                    "click(by='css selector', selector='button#onetrust-reject-all-handler', button='left', percentage=0.5, scroll_to=True)"
                ],
            },
            {
                "name": "Internet Avaliable in Address on the Xfinity Website - 3ffb549e-5f3e-4e08-9649-6484d29fc03c",
                "description": "Internet is avaliable for this address",
                "checks": [
                    {
                        "type": "text",
                        "value": "Xfinity is available at your address. Build your plan.",
                    },
                    {
                        "type": "text",
                        "value": "Internet"
                    }
                ],
                "actions": [
                    "click(by='css selector', selector='div[data-testid=\"Internet-lob-drawer-cta\"]', button='left', percentage=0.5, scroll_to=True)",
                    "click(by='css selector', selector='button[data-testid=\"price-lock-5-year-button\"]', button='left', percentage=0.5, scroll_to=True)"
                ],
                "end_state": "Address is Avaliable"
            },
            {
                "name": "Internet Not Avaliable in Address on the Xfinity Website - 3ffb549e-5f3e-4e08-9649-6484d29fc03c",
                "description": "Navigated to the Xfinity Website",
                "checks": [
                    {
                        "type": "text",
                        "value": "Call SmartMove at (855) 718-0392 to find a local provider."
                    }
                ],
                "end_state": "Address is Not Avaliable"
            },
            {
                "name": "Internet Not Avaliable in Address on the Xfinity Website - 3ffb549e-5f3e-4e08-9649-6484d29fc03c",
                "description": "Internet is not avaliable for this address",
                "checks": [
                    {
                        "type": "text",
                        "value": "Hmm, we couldn't find that address"
                    }
                ],
                "end_state": "Address is Not Avaliable"
            },
            {
                "name": "Internet Unknown in Address on the Xfinity Website - 3ffb549e-5f3e-4e08-9649-6484d29fc03c",
                "description": "Internet is unknown for this address",
                "checks": [
                    {
                        "type": "text",
                        "value": "Great deals are just around the corner. Just tell us where you'd like Xfinity service."
                    }
                ],
                "end_state": "Address is Unknown"
            },
            {
                "name": "Internet Avaliable in Address on the Xfinity Website - 3ffb549e-5f3e-4e08-9649-6484d29fc03c",
                "description": "Internet is avaliable for this address",
                "checks": [
                    {
                        "type": "text",
                        "value": "Is this a home or business address?"
                    }
                ],
                "actions": [
                    "click(by='css selector', selector='button.btn.md.neutral.outline.dir-row.horizontal.default.standard.sc-prism-button.sc-prism-button-s', button='left', percentage=0.5, scroll_to=True)"
                ],
            },
            {
                "name": "Search for Address in Xfinity Website - dc2b5b5b-aea7-408d-b31b-f191490d8c0c",
                "description": "Searched for the address on the Xfinity Website",
                "checks": [
                    {
                        "type": "text",
                        "value": "Where do you live? Enter your address for the best offers"
                    }
                ],
                "actions": [
                    "type(by='css selector', selector='input.input.text.contained.body1.sc-prism-input-text', text=parameters['ADDRESS'] + ' ' + parameters['CITY'] + ' ' + parameters['STATE'] + ' ' + parameters['ZIP'], scroll_to=True)",
                    "press_key('down')",
                    "press_key('enter')",
                    "click(by='css selector', selector='button.btn.md.neutral.fill.dir-row.horizontal.default.standard.sc-prism-button.sc-prism-button-s', button='left', percentage=0.5, scroll_to=True)"
                ],

            },
            {
                "name": "Business Address",
                "description": "Searched for the address on the Xfinity Website",
                "checks": [
                    {
                        "type": "text",
                        "value": "This looks like a business address."
                    }
                ],
                "end_state": "Address is Business"

            },
            {
                "name": "Navigate To Xfinity",
                "description": "Navigated to the Xfinity Website",
                "checks": [
                    {
                        "type": "url",
                        "value": "chrome://new-tab-page/"
                    }
                ],
                "actions": [
                    "navigate_to('https://www.xfinity.com/overview')"
                ],
            },
            {
                "name": "Hmm, we couldn't find that address​",
                "description": "Internet is avaliable for this address",
                "checks": [
                    {
                        "type": "text",
                        "value": "Hmm, we couldn't find that address​"
                    }
                ],
                "actions": [
                    "type(by='css selector', selector='input[name=\"localizationAddressField\"]', text=parameters['ADDRESS'], scroll_to=True)",
                    "type(by='css selector', selector='input[name=\"localizationZipField\"]', text=parameters['ZIP'], scroll_to=True)",
                    "press_key('tab')",
                    "press_key('enter')",
                ],
            },
            {
                "name": "Find My Plan",
                "description": "Is this the correct address?",
                "checks": [
                    {
                        "type": "text",
                        "value": "Is this the correct address?"
                    }
                ],
                "actions": [
                    "press_key('tab')",
                    "press_key('enter')",
                ],
            },
            {
                "name": "Address Already Exist for Xfinity",
                "description": "An Xfinity account already exists at this address",
                "checks": [
                    {
                        "type": "text",
                        "value": "An Xfinity account already exists at this address"
                    }
                ],
                "actions": [
                    "click(by='css selector', selector='button[data-testid=\"moving-new-button\"]', button='left', percentage=0.5, scroll_to=True)"
                ],
            },
            {
                "name": "Existing Xfinity Deals",
                "description": "An Existing Xfinity Deal is Available",
                "checks": [
                    {
                        "type": "text",
                        "value": "Choose your speed"
                    }
                ],
                "actions": [
                    "click(by='css selector', selector='button[data-testid=\"price-lock-5-year-button\"]', button='left', percentage=0.5, scroll_to=True)"
                ],
                "end_state": "Existing Xfinity Deals"
            },
            {
                "name": "Is one of these the correct address?",
                "description": "Is one of these the correct address?",
                "checks": [
                    {
                        "type": "text",
                        "value": "Is one of these the correct address?"
                    }
                ],
                "actions": [
                    "press_key('tab')",
                    "press_key('space')",
                    "click(by='css selector', selector='.btn.md.neutral.fill > prism-text:first-child', button='left', percentage=0.5, scroll_to=True)"
                ],
            }
        ]
    }


    # result = executor.execute(transitions["states"], config={"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 10, "action_period": 2}, parameters={"ADDRESS": row["PropertyFullStreetAddress"], "CITY": row["PropertyCity"], "STATE": row["PropertyState"], "ZIP": row["PropertyZip"]})
    # print(result)
    # browser_manager.reset_browser()
    # time.sleep(10)
    df = pd.read_csv("state_agent/actions/xfinity_addresses.csv")
    results_list = []

    browser_manager = BrowserManager(human_movement=True, proxy=proxy)
    executor = StateExecutor(browser_manager)
    # result = executor.execute(transitions["states"], config={"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 10, "action_period": 2}, parameters={"ADDRESS": "9464 Quartz St", "CITY": "Plymouth", "STATE": "CA", "ZIP": "95669"})
    result = executor.execute(transitions["states"], config={"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 25, "action_period": 2}, parameters={"ADDRESS": "Rollingside Dr", "CITY": "", "STATE": "", "ZIP": "95148"})
    print(result)
    browser_manager.close_browser()
    
    # Start from row 23 (index 22 since pandas is 0-indexed)
    # for index, row in df.iloc[21:].iterrows():
    #     print(row["PropertyFullStreetAddress"], row["PropertyCity"], row["PropertyState"], row["PropertyZip"])
        
    #     result_row = {
    #         "PropertyFullStreetAddress": row["PropertyFullStreetAddress"],
    #         "PropertyCity": row["PropertyCity"], 
    #         "PropertyState": row["PropertyState"],
    #         "PropertyZip": row["PropertyZip"],
    #         "success": False,
    #         "message": None,
    #         "attempts": 0
    #     }
        
    #     for i in range(10):
    #         print(f"Attempt {i+1} of 10")
    #         browser_manager = BrowserManager(human_movement=True, proxy=proxy)
    #         executor = StateExecutor(browser_manager)
    #         result = executor.execute(transitions["states"], config={"allow_multiple_states": False, "transition_period": 5, "no_states_timeout": 10, "action_period": 2}, parameters={"ADDRESS": row["PropertyFullStreetAddress"], "CITY": row["PropertyCity"], "STATE": row["PropertyState"], "ZIP": str(row["PropertyZip"]).replace('.0', '')})
    #         browser_manager.close_browser()
    #         result_row["attempts"] = i + 1
    #         if result["success"] == True:
    #             print(result["message"])
    #             result_row["success"] = True
    #             result_row["message"] = result["message"]
    #             break
    #     else:
    #         print("Failure - all 10 attempts failed")
    #         result_row["message"] = "Failure - all 10 attempts failed"
        
    #     results_list.append(result_row)
        
    #     # Save results to CSV after each row
    #     results_df = pd.DataFrame(results_list)
    #     results_df.to_csv("state_agent/actions/xfinity_results_3.csv", index=False)
    #     print(f"Progress saved to xfinity_results_3.csv ({len(results_list)} rows completed)")
    
    # print("All results saved to xfinity_results_3.csv")

if __name__ == "__main__":
    main()