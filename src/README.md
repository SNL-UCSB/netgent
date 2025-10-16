# Source Code

This directory contains the main source code for the NetGent framework and its utilities.

## Directory Structure

```
src/
├── netgent/          # Core NetGent framework
└── utils/            # Utility functions and message handling
```

## Components

### netgent/

The main NetGent package containing the core agent framework, browser automation components, and workflow management system. This is where all the primary functionality of NetGent resides.

**Key Features:**

- Agent orchestration and workflow execution
- Browser automation and control
- State synthesis and execution
- Web agent for LLM-driven browser interaction
- Registry system for actions and triggers

For detailed information, see the [netgent README](netgent/README.md).

### utils/

Utility modules providing common functionality used across the NetGent framework.

**Key Features:**

- Message and data model definitions
- Context formatting for LLM interactions
- State representation classes
- Serialization helpers

For detailed information, see the [utils README](../utils/README.md).

## Architecture Overview

NetGent uses a modular architecture with clear separation of concerns:

1. **Agent Layer** (`netgent/agent.py`): Orchestrates the workflow execution using LangGraph state machines
2. **Browser Layer** (`netgent/browser/`): Handles browser automation and DOM interaction
3. **Components Layer** (`netgent/components/`): Implements core functionality like state synthesis and web agents
4. **Utils Layer** (`utils/`): Provides shared utilities and data structures

## Key Design Principles

- **Separation of Concerns**: Each module has a specific responsibility
- **Extensibility**: Easy to add new actions, triggers, and components
- **Type Safety**: Uses Pydantic models for data validation
- **Flexibility**: Supports both natural language and code-based workflows
- **Reusability**: State caching reduces redundant LLM calls

## Development

When developing new features:

1. Add new actions/triggers in `netgent/browser/controller/`
2. Extend components in `netgent/components/`
3. Add utility functions in `utils/`
4. Register components using the registry system
5. Follow existing patterns for consistency

## Dependencies

Core dependencies:

- `langgraph`: State graph workflow management
- `selenium`/`seleniumbase`: Browser automation
- `langchain`: LLM integration framework
- `pydantic`: Data validation and modeling

See `pyproject.toml` in the root directory for complete dependency list.
