# BQT+ Workflow

## Environment Setup

### 1. Install `uv`
This project uses `uv` for fast package management.
https://docs.astral.sh/uv/getting-started/installation/

### 2. Install NetGent
Install the project dependencies and set up the virtual environment:

```bash
uv sync
```

### 3. Environment Variables
Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Update `.env` with your credentials:

```properties
# Database Credentials
DB_USERNAME=your_username
DB_PASSWORD=your_password

# LLM Configuration
GOOGLE_API_KEY="your_gemini_api_key"

#### How to get a Google AI Studio API Key:
1.  Go to [Google AI Studio](https://aistudio.google.com/).
2.  Click on **"Get API key"** in the bottom left.
3.  Click **"Create API key"**.
4.  Select an existing Google Cloud project or create a new one.
5.  Copy the generated key and paste it into your `.env` file as `GOOGLE_API_KEY`.

# Tracing / Observability (Optional)
PHOENIX_COLLECTOR_ENDPOINT=""
```

## Running ISP Automations

ISP scripts are located in `examples/isps/`. Run them using `uv run` to ensure they use the correct environment.

**Make sure you are in the project root directory before running the commands:**


**Syntax:**
```bash
uv run examples/isps/<isp_name>.py
```

**Examples:**
```bash
uv run examples/isps/optimum.py
uv run examples/isps/xfinity.py
```

## Logging & Tracing

"Logging" in this project refers to **observability and tracing** powered by [Arize Phoenix](https://docs.arize.com/phoenix/). This allows you to inspect the internal decision-making of the agent.

### What is logged?
*   **LLM Traces**: See exactly what prompts were sent to Gemini and what the model returned.
*   **Agent Execution**: Track the flow of the agent through different states.
*   **Latency & Errors**: Identify bottlenecks or reasons for failure.

1.  **Configure `.env`**:
    Ensure your `.env` file points to the local collector:
    ```properties
    PHOENIX_COLLECTOR_ENDPOINT="PHOENIX_COLLECTOR_ENDPOINT"
    ```

2.  **Run an ISP Script**:
    When you run a script (e.g., `uv run examples/isps/optimum.py`), logs and traces will automatically appear in the Phoenix UI.

## What Happens When Running an ISP Script?


When you execute an ISP script (e.g., `uv run examples/isps/optimum.py`), the following process occurs:

1.  **Initialization**:
    *   The `NetGent` agent is initialized with an LLM (typically Gemini via `ChatGoogleGenerativeAI`) to power its decision-making.
    *   It may be configured with a proxy to ensure requests appear from residential IP addresses.

2.  **Workflow Definition**:
    *   The script defines a list of `StatePrompt` objects. Each prompt describes a potential state of the ISP's website (e.g., "Home Page", "Address Entry", "Service Available").
    *   State prompts include **Triggers** (what to look for to identify the state) and **Actions** (what to do in that state, like clicking buttons or typing text).

3.  **Data Retrieval**:
    *   The script connects to the BQT database to fetch a list of real addresses to test for service availability.

4.  **Execution Loop**:
    *   The agent launches a controlled browser instance.
    *   It navigates to the ISP's website.
    *   At each step, it captures the current page state (screenshots, DOM) and uses the LLM to match it against the defined `StatePrompt`s.
    *   It executes the actions defined for the matching state (e.g., typing an address from the database).
    *   This loop continues until a terminal state is reached (e.g., "Service Available" or "No Service").

5.  **Result Capture**:
    *   The agent records the path taken and the final outcome.
    *   Wait for the user to press "Enter" to finish execution.
    *   Finally, it saves the execution trace and learned states to a JSON file (e.g., `examples/isps/results/<isp_name>_result.json`). This "State Repository" allows future runs to be faster and cheaper by replaying known paths without querying the LLM.
