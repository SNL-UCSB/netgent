#!/usr/bin/env python3
"""
NetGent CLI Interface

This module provides command-line interface for NetGent with dual operation modes:
- Code Execution Mode (-e): Runs pre-generated executable code
- Code Generation Mode (-g): Runs the full agent pipeline

Usage:
    netgent -e <executable_code_file> [credentials] [-s]
    netgent -g <api_keys_file> <credentials> <prompts> [-s]
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from netgent.agent import NetGent
from netgent.utils.message import StatePrompt
from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import ChatGoogleGenerativeAI


def load_api_keys(api_keys_file: str) -> Dict[str, str]:
    """Load API keys from JSON file."""
    try:
        with open(api_keys_file, 'r') as f:
            api_keys = json.load(f)
        return api_keys
    except FileNotFoundError:
        print(f"Error: API keys file '{api_keys_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{api_keys_file}'.")
        sys.exit(1)


def load_executable_code(code_file: str) -> List[Dict[str, Any]]:
    """Load executable code (NFA) from JSON file."""
    try:
        with open(code_file, 'r') as f:
            code = json.load(f)
        return code
    except FileNotFoundError:
        print(f"Error: Executable code file '{code_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{code_file}'.")
        sys.exit(1)


def load_credentials(credentials_input: str) -> Dict[str, str]:
    """Load credentials from file or parse as JSON string."""
    # Check if it's a file path
    if os.path.isfile(credentials_input):
        try:
            with open(credentials_input, 'r') as f:
                credentials = json.load(f)
            return credentials
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in credentials file '{credentials_input}'.")
            sys.exit(1)
    else:
        # Try to parse as JSON string
        try:
            credentials = json.loads(credentials_input)
            return credentials
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in credentials string.")
            sys.exit(1)


def load_prompts(prompts_input: str) -> List[StatePrompt]:
    """Load prompts from file or parse as JSON string."""
    # Check if it's a file path
    if os.path.isfile(prompts_input):
        try:
            with open(prompts_input, 'r') as f:
                prompts_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in prompts file '{prompts_input}'.")
            sys.exit(1)
    else:
        # Try to parse as JSON string
        try:
            prompts_data = json.loads(prompts_input)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in prompts string.")
            sys.exit(1)
    
    # Convert to StatePrompt objects
    prompts = []
    for prompt_data in prompts_data:
        prompt = StatePrompt(
            name=prompt_data.get('name', ''),
            description=prompt_data.get('description', ''),
            triggers=prompt_data.get('triggers', []),
            actions=prompt_data.get('actions', []),
            end_state=prompt_data.get('end_state', '')
        )
        prompts.append(prompt)
    
    return prompts


def create_llm(api_keys: Dict[str, str]) -> Any:
    """Create LLM instance based on available API keys."""
    # Try Google Generative AI first
    if 'google_api_key' in api_keys:
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp", 
            temperature=0.2, 
            api_key=api_keys['google_api_key']
        )
    
    # Try Google Vertex AI
    if 'google_vertex_project' in api_keys and 'google_vertex_location' in api_keys:
        return ChatVertexAI(
            model_name="gemini-2.0-flash-exp",
            temperature=0.2,
            project=api_keys['google_vertex_project'],
            location=api_keys['google_vertex_location']
        )
    
    print("Error: No valid API keys found. Please provide 'google_api_key' or 'google_vertex_project'/'google_vertex_location'.")
    sys.exit(1)


def setup_browser_cache(credentials: Dict[str, str]) -> Optional[str]:
    """Setup browser cache for persistent sessions if provided."""
    cache_file = credentials.get('browser_cache_file')
    if cache_file and os.path.isfile(cache_file):
        print(f"Using browser cache file: {cache_file}")
        return cache_file
    return None


def execution_mode(args):
    """Run in code execution mode (-e)."""
    print("Running in Code Execution Mode...")
    
    # Load executable code
    executable_code = load_executable_code(args.executable_code)
    
    # Load credentials if provided (optional for execution mode)
    credentials = {}
    cache_file = None
    if hasattr(args, 'credentials') and args.credentials:
        credentials = load_credentials(args.credentials)
        # Setup browser cache if provided
        cache_file = setup_browser_cache(credentials)
    
    # Initialize agent with LLM disabled (execution mode)
    # Pass cache directory to browser session if available
    agent = NetGent(llm=None, llm_enabled=False, user_data_dir=cache_file)
    
    print(f"Loaded {len(executable_code)} executable states")
    if cache_file:
        print(f"Using browser cache: {cache_file}")
    else:
        print("No browser cache specified - using fresh browser session")
    print("Starting execution...")
    
    # Run the agent
    result = agent.run(state_prompts=[], state_repository=executable_code)
    
    print("Execution completed!")
    return result


def generation_mode(args):
    """Run in code generation mode (-g)."""
    print("Running in Code Generation Mode...")
    
    # Load API keys
    api_keys = load_api_keys(args.api_keys)
    
    # Load credentials
    credentials = load_credentials(args.credentials)
    
    # Load prompts
    prompts = load_prompts(args.prompts)
    
    # Setup browser cache if provided
    cache_file = setup_browser_cache(credentials)
    
    # Create LLM instance
    llm = create_llm(api_keys)
    
    # Initialize agent with LLM enabled (generation mode)
    # Pass cache directory to browser session if available
    agent = NetGent(llm=llm, llm_enabled=True, user_data_dir=cache_file)
    
    print(f"Loaded {len(prompts)} state prompts")
    if cache_file:
        print(f"Using browser cache: {cache_file}")
    print("Starting code generation...")
    
    # Run the agent
    result = agent.run(state_prompts=prompts, state_repository=[])
    
    print("Code generation completed!")
    return result


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NetGent - Agent-Based Automation of Network Application Workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Code Execution Mode (credentials optional)
  netgent -e executable_code.json
  netgent -e executable_code.json credentials.json
  netgent -e executable_code.json '{"browser_cache_file": "/path/to/cache"}' -s
  
  # Code Generation Mode (credentials required)
  netgent -g api_keys.json credentials.json prompts.json
  netgent -g api_keys.json credentials.json '{"name": "test", "triggers": [], "actions": []}' -s
        """
    )
    
    # Create mutually exclusive group for modes
    mode_group = parser.add_mutually_exclusive_group(required=True)
    
    # Code execution mode
    mode_group.add_argument(
        '-e', '--execute',
        metavar='EXECUTABLE_CODE',
        help='Run in code execution mode with pre-generated executable code'
    )
    
    # Code generation mode
    mode_group.add_argument(
        '-g', '--generate',
        metavar='API_KEYS',
        help='Run in code generation mode with API keys'
    )
    
    # Common arguments
    parser.add_argument(
        'credentials',
        nargs='?',
        help='Login credentials as JSON file or JSON string (optional for execution mode, required for generation mode)'
    )
    
    parser.add_argument(
        'prompts',
        nargs='?',
        help='User prompts in natural language (JSON file or JSON string) - required for generation mode'
    )
    
    parser.add_argument(
        '-s', '--screen',
        action='store_true',
        help='Connect to screen for live verification/observation'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='NetGent 0.1.0'
    )
    
    args = parser.parse_args()
    
    # Validate arguments based on mode
    if args.execute:
        # Execution mode: executable_code, credentials (optional)
        args.executable_code = args.execute
        if not args.prompts:
            # Remove prompts from args for execution mode
            delattr(args, 'prompts')
        else:
            print("Warning: Prompts are not used in execution mode. Ignoring prompts argument.")
    else:
        # Generation mode: api_keys, credentials (required), prompts (required)
        args.api_keys = args.generate
        if not args.credentials:
            print("Error: Credentials are required for generation mode.")
            sys.exit(1)
        if not args.prompts:
            print("Error: Prompts are required for generation mode.")
            sys.exit(1)
    
    # Print mode and screen status
    mode = "Code Execution" if args.execute else "Code Generation"
    screen_status = "with screen monitoring" if args.screen else "without screen monitoring"
    print(f"Mode: {mode} ({screen_status})")
    
    try:
        if args.execute:
            result = execution_mode(args)
        else:
            result = generation_mode(args)
        
        # Save results if requested
        if hasattr(args, 'output') and args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to {args.output}")
            
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
