# Two-person Google Meet

Use a Chrome profile already signed in to two Google accounts (`authuser=0`
hosts; `authuser=1` joins).

Generate:

```bash
netgent -g api_keys.json '{}' \
  examples/video_conference/google-meet-two-person/prompts/google-meet-two-person_prompts.json \
  --user-data-dir examples/user_data \
  -o examples/video_conference/google-meet-two-person/results/google-meet-two-person_result.json
```

Replay:

```bash
netgent -e \
  examples/video_conference/google-meet-two-person/results/google-meet-two-person_result.json \
  --user-data-dir examples/user_data
```

Smoke test:

```bash
./scripts/smoke_google_meet_two_person.sh /path/to/signed-in-chrome-profile
```

Like the Twitch smoke test, this builds and runs the real NetGent container with
the generated workflow mounted read-only. The Chrome profile is mounted at
`/tmp/browser-cache`; close Chrome before running so the profile is not locked.
Results and fresh WebRTC metrics are written to `out/`.

Success requires the waiting-room text to disappear and the joiner-side
`Meeting details` button to appear. Metrics are written to
`/out/google_meet_two_person_metrics.json`.

Proof from a successful 30-second, two-participant run is checked in at
[`results/google-meet-two-person_metrics.json`](results/google-meet-two-person_metrics.json).
