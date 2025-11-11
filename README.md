# NetGent

### Reseach Paper:

[NetGent: Agent-Based Automation of Network Application Workflows](https://arxiv.org/abs/2509.00625)

### Agent-Based Automation of Network Application Workflows

NetGent is an AI-agent framework for automating complex application workflows to generate realistic network traffic datasets.

Developing generalizable ML models for networking requires data collection from environments with traffic produced by diverse real-world web applications. Existing browser automation tools that aim for diversity, repeatability, realism, and efficiency are often fragile and costly. NetGent addresses this challenge by allowing users to specify workflows as natural-language rules that define state-dependent actions. These specifications are compiled into nondeterministic finite automata (NFAs), which a state synthesis component translates into reusable, executable code.

Key features:

- Deterministic replay of workflows
- Reduced redundant LLM calls via state caching
- Fast adaptation to changing application interfaces
- Automation of 50+ workflows, including:
  - Video-on-demand streaming
  - Live video streaming
  - Video conferencing
  - Social media
  - Web scraping

By combining the flexibility of language-based agents with the reliability of compiled execution, NetGent provides a scalable foundation for generating diverse and repeatable datasets to advance ML in networking.

## Repository Structure

- **src/netgent/browser/**: Browser automation core (sessions, controllers, actions, triggers, DOM utilities).
- **src/netgent/components/**: Core components for workflow execution, synthesis, and web agent control.
- **src/netgent/utils/**: Shared utility classes for message formatting, data models, and context serialization.
- **examples/**: Scripts and configuration for sample automation workflows.

See individual subfolder `README.md` files for details on usage and implementation.

## NetGent Workflow

![workflow](docs/figures/workflow.png)

## NetGent Architecture

![architecture](docs/figures/architecture.png)

## Getting Started

### Using the CLI Tool

NetGent provides a flexible command-line interface for automating workflows in two modes:

**1. Code Execution Mode (`-e`)**

- Runs a pre-generated workflow (concrete NFA) reproducibly in a browser.
- Accepts an optional credentials input and browser cache for persistent sessions.

**Example:**

```bash
docker run --platform=linux/amd64 --rm -d \
  -p 8080:8080 \
  -v "$PWD/examples/states/google_result.json:/executable_code.json:ro" \
  -v "$PWD/out:/out" \
  netgent:amd64 \
  -e /executable_code.json \
  --user-data-dir /tmp/browser-cache \
  -o /out/execution_result.json \
  -s
```

Note: With `-s` enabled, you can view the browser automation at http://localhost:8080 in view-only mode. The container will automatically exit when the task completes.

**2. Code Generation Mode (`-g`)**

- Synthesizes workflows from high-level, natural language prompts using an LLM (requires prompts, credentials, API keys, and an output file).

**Example:**

```bash
docker run --platform=linux/amd64 --rm -d \
  -p 8080:8080 \
  -v "$PWD/google_creds.json:/keys.json:ro" \
  -v "$PWD/examples/prompts/google_prompts.json:/prompts.json:ro" \
  -v "$PWD/out:/out" \
  netgent:amd64 \
  -g /keys.json '{}' /prompts.json \
  --user-data-dir /tmp/browser-cache \
  -o /out/state_repository.json \
  -s
```

Note: With `-s` enabled, you can view the browser automation at http://localhost:8080 in view-only mode. The container will automatically exit when the task completes.

- Use `-s` or `--screen` to enable VNC/noVNC for live screen viewing in **view-only mode** (read-only access - you can watch but not control). Access at http://localhost:8080 when running in Docker with `-p 8080:8080`. The container will automatically exit when the task completes.
- Use `--user-data-dir` to specify a browser profile directory.
- See all options with `netgent --help`.

### Initializing the Docker Container

A Dockerfile is provided to simplify environment setup and sandboxed execution.

**Build the image:**

```bash
docker build --platform linux/amd64 -t netgent .
```

Once inside, use the CLI tool or Python as described above.

### Using the Python SDK

NetGent can be scripted from Python for custom workflows and advanced integrations.

**Example usage:**

```python
from netgent import NetGent, StatePrompt
from langchain_google_vertexai import ChatVertexAI

prompts = [
    StatePrompt(
        name="On Home Page",
        description="Start state",
        triggers=["If homepage is visible"],
        actions=["Navigate to https://example.com"]
    ),
    # More prompts ...
]

# To generate a new workflow from prompts
llm = ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2)
agent = NetGent(llm=llm, llm_enabled=True)
results = agent.run(state_prompts=prompts)

# To replay an existing script
agent = NetGent(llm=None, llm_enabled=False)
results = agent.run(state_prompts=[], state_repository=your_saved_repo)
```

See the example scripts and CLI source for more patterns, and customize credentials or cache directory as needed.
