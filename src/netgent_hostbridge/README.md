# NetGent Host Bridge

The host bridge lets NetGent automate **native macOS desktop applications**
while the NetGent orchestrator (state machine, code generation, code execution)
runs inside Docker exactly as it does for the browser.

A Docker container cannot reach the host's macOS Accessibility API or move its
real mouse/keyboard. So NetGent is split in two:

```
┌─────────────────────────────┐        HTTP         ┌──────────────────────────────┐
│  Docker container           │   /snapshot         │  Host bridge (native macOS)  │
│  ─ NetGent state machine    │   /triggers         │  ─ AX tree perception        │
│  ─ state synthesis + agent  │ ──/trigger────────▶ │    (atomacos / pyobjc)       │
│  ─ DesktopController        │   /context          │  ─ PyAutoGUI actuation       │
│    (HTTP client)            │   /action           │  ─ opens apps (launch svcs)   │
└─────────────────────────────┘ ◀───────────────── └──────────────────────────────┘
        no browser here            host.docker.internal:8765     acts on YOUR screen
```

**Perception is the accessibility tree, not a screenshot.** Each element the
agent sees has a role, a title, and its true on-screen position/size (AX
reports global, top-left coordinates in points — exactly PyAutoGUI's units), so
the agent selects an element by id and the bridge clicks its real coordinates.
It never guesses from pixels. A screenshot is still sent as *supplementary*
context, matching the browser path.

Every observation and action is **scoped to one target application** (the one
opened/activated by the workflow) and the bridge **activates that app before
each action**, which prevents clicks from landing outside the window or in a
background app.

## 1. Install (on the macOS host, outside Docker)

```bash
pip install -r src/netgent_hostbridge/requirements.txt
```

## 2. Grant permissions

The process running the bridge (your terminal / Python) needs, in
**System Settings → Privacy & Security**:

- **Accessibility** — required (read the AX tree, synthesize input).
- **Screen Recording** — required only if you want screenshots in snapshots.

## 3. Start the bridge

```bash
python -m netgent_hostbridge --port 8765
# listening on http://0.0.0.0:8765  (Docker reaches it at host.docker.internal:8765)
```

Leave it running. It targets whichever app the workflow opens/activates.

> **Isolated environment note**: `netgent_hostbridge` is a standalone top-level
> package (not `netgent.hostbridge`) precisely so you can install and run it in
> its own minimal virtualenv, isolated from the orchestrator's dependencies
> (pydantic/langchain/langgraph/seleniumbase), which typically live in a
> different environment (or only inside the Docker image).

## HTTP API

| Method & path | Body | Returns |
|---|---|---|
| `GET /health` | — | `{ok, service}` |
| `POST /snapshot` | `{app?, include_screenshot?}` | `{ok, elements, prompt, screenshot, context}` |
| `POST /context` | `{app?}` | `{ok, context: {app, title}}` |
| `POST /triggers` | `{app?}` | `{ok, candidates}` |
| `POST /trigger` | `{type, params, app?}` | `{ok, result: bool}` |
| `POST /action` | `{action, params, app?}` | `{ok, result}` |

Trigger types: `element` (AX locator or `role[:title]`), `text`, `app`, `window`.
Actions: `open_application`, `activate_application`, `click`, `type`, `move`,
`scroll`, `scroll_to`, `press_key`, `hotkey`.

## Files

- `ax.py` — accessibility tree walk, snapshot, locator re-resolution, triggers.
- `actuator.py` — PyAutoGUI mouse/keyboard, app open/activate, coordinate validation.
- `server.py` — stdlib `http.server` exposing the API above.
