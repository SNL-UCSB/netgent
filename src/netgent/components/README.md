# NetGent Components

This folder contains the core subsystems implementing the NetGent workflow logic. Each submodule corresponds to a major part of the control, execution, synthesis, and agent functionalities.

## Main Submodules

- **program_controller/**: ProgramController (checks triggers, routes workflow)
- **state_executor/**: StateExecutor (executes browser actions)
- **state_synthesis/**: StateSynthesis (uses LLM to select/generate states)
- **web_agent/**: WebAgent (intelligent browser interaction, vision-language, action planning)

## Typical Workflow

1. NetGent Agent initializes with state_prompts and repository
2. ProgramController matches states and routes to the executor or synthesis
3. StateExecutor executes matched state actions
4. StateSynthesis generates new states via LLM
5. WebAgent generates/executing granular actions

These modules collectively enable robust, repeatable, and adaptive workflow automation.
