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

### API Keys Configuration

NetGent requires API keys for LLM access when running in **Code Generation Mode**. Supported providers include Google Generative AI (Gemini) and Google Vertex AI.

**📖 For detailed instructions on obtaining and configuring API keys, see [API_KEYS.md](API_KEYS.md).**

### Using the CLI Tool

NetGent provides a flexible command-line interface for automating workflows in two modes:

**1. Code Execution Mode (`-e`)**

- Runs a pre-generated workflow (concrete NFA) reproducibly in a browser.
- Accepts an optional credentials input and browser cache for persistent sessions.

**Example:**
```bash
docker build --platform linux/amd64 -t netgent .
```
```bash
docker run --platform=linux/amd64 --rm -d \
  -p 8080:8080 \
  -v "$PWD/examples/basic_example/google_result.json:/executable_code.json:ro" \
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
- **API Keys Required**: See [API_KEYS.md](API_KEYS.md) for detailed instructions on obtaining and configuring API keys.

**Example:**

```bash
docker run --platform=linux/amd64 --rm -d \
  -p 8080:8080 \
  -v "$PWD/api_keys.json:/keys.json:ro" \
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
# See API_KEYS.md for LLM setup instructions
llm = ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2)
agent = NetGent(llm=llm, llm_enabled=True)
results = agent.run(state_prompts=prompts)

# To replay an existing script
agent = NetGent(llm=None, llm_enabled=False)
results = agent.run(state_prompts=[], state_repository=your_saved_repo)
```

See the example scripts and CLI source for more patterns, and customize credentials or cache directory as needed.

For API key configuration details, refer to [API_KEYS.md](API_KEYS.md).

## QoE Logging (Stats for Nerds)

NetGent can record video Quality-of-Experience (QoE) metrics throughout a streaming session, the same data that YouTube exposes via its "Stats for Nerds" overlay. This is useful for correlating the network traffic NetGent generates with the player's perceived playback quality.

Instead of scraping the fragile right-click overlay, the logger reads the metrics directly from the player via JavaScript and samples them on a background thread, writing one JSON object per sample to a JSONL file.

### Supported platforms

| Platform | Source | Captured metrics (when playing) |
|----------|--------|---------------------------------|
| **YouTube** | `movie_player.getStatsForNerds()` + `<video>` | resolution, codecs, bandwidth, buffer health, dropped/total frames, network activity, live latency, video id/title/author |
| **Twitch** | `HTMLVideoElement` API | resolution, dropped/total frames, buffer-ahead seconds, playback rate, paused/muted/volume, channel name, live vs. VOD |

The platform is detected per-sample from the page URL, so a single logger handles a session that navigates between sites.

### How to enable it in a workflow

QoE logging is exposed as two ordinary workflow **actions**, so you enable it by adding them to a workflow state (no flags or env vars required):

| Action | Parameters | Description |
|--------|------------|-------------|
| `start_stats_logging` | `out_path` (default `netgent_video_stats.jsonl`), `interval` (seconds, default `2.0`) | Starts the background sampler. |
| `stop_stats_logging` | — | Stops the sampler and flushes the log. (Also called automatically on browser shutdown.) |

A typical pattern is to start logging once the player is present and keep the state alive for the session using the `"config": { "continuous": true }` state flag:

```json
{
  "name": "Watching YouTube Video",
  "description": "On a YouTube watch page - log QoE stats for the session",
  "config": { "continuous": true },
  "checks": [
    { "type": "element", "params": { "by": "css selector", "selector": "#movie_player", "check_visibility": false, "timeout": 5 } }
  ],
  "actions": [
    { "type": "start_stats_logging", "params": { "out_path": "youtube_stats.jsonl", "interval": 2.0 } },
    { "type": "wait", "params": { "seconds": 5 } }
  ],
  "end_state": ""
}
```

Because each sample is flushed to disk immediately (line-buffered append), the log survives even if the session is interrupted before `stop_stats_logging` runs.

### Ready-to-run examples

```bash
# YouTube
netgent -e examples/web_browsing/youtube/results/youtube_stats_result.json   # -> youtube_stats.jsonl

# Twitch
netgent -e examples/web_browsing/twitch-watch/results/twitch-stats_result.json   # -> twitch_stats.jsonl
```

Each line of the resulting JSONL file looks like:

```json
{"timestamp": 1781242765.92, "url": "https://www.youtube.com/watch?v=...", "stats": {"platform": "youtube", "resolution": "1920x1080", "bandwidth_kbps": "5120 Kbps", "buffer_health_seconds": "12.34 s", "dropped_video_frames": 0, "total_video_frames": 900, "title": "...", "author": "..."}}
```

> **Note:** Browsers block autoplay on fresh, gesture-less sessions, so a video may load paused (reporting `0x0` resolution and zeroed playback counters). To capture live playback metrics, make sure the workflow actually starts playback (e.g. a click on the player or a `playVideo()` call) before/while logging.

The generated `*_stats.jsonl` logs are git-ignored.

## Running Multiple Applications Concurrently

NetGent can run **several application workflows at the same time** in a single invocation — for example, watching YouTube while also streaming Twitch and running a `wget` download. This is separate from generating workflows with AI; it is purely about *executing* one or more pre-built workflows in parallel.

### How it works

You pass **one or more workflow files**, and each is classified by its extension:

| Extension | Type | What runs |
|-----------|------|-----------|
| `*.json` | NetGent executable workflow | A full browser session. Each one gets its **own virtual display, its own Chrome profile, and (with `-s`) its own noVNC port**, so their mouse/keyboard inputs never collide. |
| `*.sh` | Bash workflow | An arbitrary shell command (e.g. `wget`, `ping`, `curl`). No browser/display is used. |

Key behaviors:

- **Isolation:** every browser workflow runs on its own display (`:99`, `:100`, …) with its own Chrome profile, so concurrent workflows don't interfere with each other. A failure in one workflow does not stop the others.
- **Live viewing:** with `-s`, each browser workflow is assigned its own noVNC port, sequentially from `8080` (1st browser → `:8080`, 2nd → `:8081`, …). Open one browser tab per workflow to watch them live, exactly like the single-workflow view. Map each port you want to see.
- **Output:** per-workflow results and logs are written under `out/<workflow-name>/` (e.g. `out/youtube/youtube_result.json`, `out/youtube/youtube.log`). Bash workflows also run in their own `out/<name>/` directory, so relative output files never clobber each other.
- **Completion:** the run finishes once **all** workflows have completed.
- Single-workflow usage (`-e` / `-g`) is unchanged and fully backward compatible.

Two ready-to-run bash workflow examples are provided in [`examples/bash_workflows/`](examples/bash_workflows/): `wget-download.sh` and `ping.sh`.

> **Resource note:** each browser workflow starts its own Chrome + virtual display, so memory/CPU usage grows with the number of concurrent browser workflows.

### Docker

Pass the workflow files as the container's arguments and map one host port per browser workflow you want to watch:

```bash
docker run --platform=linux/amd64 --rm -d \
  -p 8080:8080 -p 8081:8081 \
  -v "$PWD/examples/web_browsing/youtube/results/youtube_stats_result.json:/youtube.json:ro" \
  -v "$PWD/examples/web_browsing/twitch-watch/results/twitch-stats_result.json:/twitch.json:ro" \
  -v "$PWD/examples/bash_workflows/wget-download.sh:/wget.sh:ro" \
  -v "$PWD/out:/out" \
  netgent \
  /youtube.json /twitch.json /wget.sh -s
```

- `youtube` (1st browser workflow) → watch at http://localhost:8080
- `twitch` (2nd browser workflow) → watch at http://localhost:8081
- `wget` (bash workflow) → no screen; output and logs in `out/wget/`
- Results/logs for each are written under the mounted `out/` directory.

### CLI

Inside the container the same orchestrator is available on `PATH` as `start-netgent`, accepting the same arguments. This is useful when you already have a running container:

```bash
start-netgent /youtube.json /twitch.json /wget.sh -s
```

> The multi-workflow orchestrator manages the virtual displays (Xvfb), VNC, and noVNC servers, which are only present inside the provided Docker image. Run it via the container (as the entrypoint above) or from a shell inside the container, rather than directly on a host without an X server.
