# Desktop Automation Example (macOS)

This example drives the native **Maps** app: open it, click the
search field, and search for an address. It works exactly like the browser
examples — same state repository, same triggers/actions, same `-e` (execute)
and `-g` (generate) modes — but interactions happen on **your** Mac through the
[host bridge](../../src/netgent_hostbridge/README.md), while NetGent's
orchestrator can run inside Docker.

The search field is clicked via its **accessibility (AX) element**, not a
guessed screen coordinate: [maps_result.json](maps_result.json) targets it with
an AX locator (`{"by": "ax", "selector": "{\"role\": \"AXSearchField\"}"}`),
which the host bridge re-resolves against the live accessibility tree and
clicks at its true on-screen position.

## Prerequisites (once)

On the macOS host (outside Docker), in its own virtualenv (see the main
[README](../../README.md#desktop-application-automation-macos) for why):

```bash
python3 -m venv .hostbridge-venv
source .hostbridge-venv/bin/activate
pip install -r src/netgent_hostbridge/requirements.txt
PYTHONPATH=src python3 -m netgent_hostbridge --port 8765
```

Grant the process **Accessibility** (required) and **Screen Recording**
(optional, for screenshots) in *System Settings → Privacy & Security*. Leave the
bridge running.

## Run the pre-built workflow (code execution mode)

```bash
docker build --platform linux/amd64 -t netgent .
```

```bash
docker run --platform=linux/amd64 --rm \
  -e NETGENT_HOSTBRIDGE_URL=http://host.docker.internal:8765 \
  -v "$PWD/examples/desktop/maps_result.json:/maps.json:ro" \
  -v "$PWD/out:/out" \
  netgent \
  -e /maps.json --desktop -o /out/maps_execution.json
```

## Generate a workflow from natural language (code generation mode)

[maps_prompts.json](maps_prompts.json) is a **multi-state** prompt set (open →
search → directions). Each prompt becomes a state, and NetGent makes every
generated state *self-clearing* automatically so the workflow advances instead
of looping (see the next section for how). It writes to `maps_generated.json`
so it doesn't overwrite the hand-authored `maps_result.json`:

```bash
docker run --platform=linux/amd64 --rm \
  -e NETGENT_HOSTBRIDGE_URL=http://host.docker.internal:8765 \
  -v "$PWD/api_keys.json:/keys.json:ro" \
  -v "$PWD/examples/desktop/maps_prompts.json:/prompts.json:ro" \
  -v "$PWD/examples/desktop:/work" \
  netgent \
  -g /keys.json '{}' /prompts.json --desktop -o /work/maps_generated.json
```

The generated `maps_generated.json` contains the AX locators actually discovered
by the agent against your live Maps window (the same way the browser examples'
CSS selectors were discovered by a real run, not hand-written). Replay it with
`-e /path/to/maps_generated.json --desktop`.

> **The two files:** `maps_result.json` is the hand-authored reference workflow
> (for `-e`); `maps_prompts.json` is the natural-language generation input
> (for `-g`). Both are multi-state.

## Multi-state desktop workflows (the recommended pattern)

This example is a **3-state** workflow — open Maps, search an address, open
directions — and it shows the general recipe for reliable multi-state desktop
automation. NetGent's state machine re-checks every state's `checks` on each
cycle and runs whichever one matches, so a multi-state workflow only behaves if
its triggers obey two rules:

1. **Self-clearing** — a state's trigger must be TRUE right before its actions
   run and FALSE once they're done. Otherwise the state matches forever and
   re-runs in a loop.
2. **Mutually exclusive** — no two states are ever true at the same time
   (otherwise you get a "Multiple states matched" error).

The problem on the desktop is that most AX signals are *persistent*: once Maps
is frontmost it stays frontmost; the search field stays on screen after you
search. Plain "element is present" checks are therefore **not** self-clearing.
The fix is the **`negate`** trigger option — trigger on the *absence* of the
marker that appears in the *next* step:

| State | `checks` (AX, deterministic) | becomes false when… |
|-------|------------------------------|---------------------|
| 1. Open Maps | `app: Maps` **negate** (Maps not running) | Maps has launched |
| 2. Search | search field present **AND** `Directions` button **negate** (absent) | a result appears (Directions button shows) |
| 3. Open directions | `Directions` button present | — (terminal: `end_state` set) |

Each state's trigger goes false exactly when the next state's goes true, so the
machine walks forward 1 → 2 → 3 and stops (state 3 has a non-empty `end_state`).

Rules of thumb:

- Give the **last** state a non-empty `end_state` so the workflow ends.
- For every non-terminal state, pair a "present" check for *this* step with a
  `"negate": true` check for a marker that only appears in the *next* step.
- `negate: true` works on `app`, `window`, `text`, and `element` triggers.
- The very first "open the app" state uses `app: <name>` with `negate: true`
  (the `app` trigger checks whether the app is *running*, so this is true only
  until the app has launched — it does not depend on window focus).

### Code generation builds these self-clearing checks for you

You don't have to hand-write the `negate` checks — **code generation adds them
automatically**. As it synthesizes each state it:

- gives an "open the app" state an `app … negate` (not-running) trigger derived
  from its `open_application` action; and
- for every other state, snapshots the accessibility tree *before* and *after*
  the state's actions run, and adds a `negate` check for a control that only
  **appeared** afterward (e.g. the `Directions` button for the Search state).

That's why the multi-state `maps_prompts.json` generates a workflow that walks
1 → 2 → 3 instead of looping. (Timing note: a step whose result loads slowly —
e.g. a network-backed search — relies on the after-snapshot capturing the new
control; NetGent waits `transition_period` seconds first, but if a marker is
very slow you may need to nudge the wait up.)

> You can still collapse everything into a **single** state (empty `checks`, one
> `end_state`) that does the whole task and ends — simpler, but no intermediate
> re-synchronization if a step's UI is slow.

## If the search field isn't found

Maps exposes its search box as an `AXTextField` titled `Apple Maps` (that's what
[maps_result.json](maps_result.json) targets), but accessibility roles/titles
can vary by OS version. To confirm what your Maps actually exposes, hit the
bridge directly while Maps is open:

```bash
curl -X POST http://localhost:8765/snapshot \
  -H 'Content-Type: application/json' \
  -d '{"app":"Maps","include_screenshot":false}' | python3 -m json.tool
```

Look through `elements` for the search box's `role`/`title`, and adjust the
`selector` in [maps_result.json](maps_result.json) accordingly (or just run
code generation mode once — it will discover and record the correct locator
for you automatically).

## Notes

- The agent selects UI elements from the **accessibility tree** (role + label),
  never by guessing coordinates from the screenshot. The bridge resolves each
  element to its true on-screen position and clicks it with PyAutoGUI.
- Every action re-activates the target app first and validates the point is on
  screen, so clicks never land in a background app or outside the window.
- Swap `Maps` for any app (e.g. `Calculator`, `Notes`, or a bundle id like
  `com.apple.Maps`) and adjust the prompts/actions accordingly.
