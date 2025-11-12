# NetGent Examples

This folder contains example scripts and configuration files demonstrating how to use NetGent to automate workflows for real web applications.

## Important: Credentials Required

**All example files have credentials removed for security.** To run any of the existing workflows, you must:

1. **Replace empty credential placeholders** in the Python files (e.g., `"Type the Email is "` → `"Type the Email is your-email@example.com"`)
2. **Or use the state prompts** we've created as templates and add your own credentials when defining your workflows

The JSON result files contain the execution history but have all credential values sanitized (empty strings in text fields).

## Directory Structure

- **basic_example/**: Basic example showing Google search workflow
- **web_browsing/**: Examples for browsing social media and content platforms (Instagram, X/Twitter, Reddit, YouTube, etc.)
- **video_conference/**: Examples for video conferencing platforms (Zoom, Google Meet, Microsoft Teams, etc.)
- **video_streaming/**: Examples for streaming platforms (Disney+, Hulu, Twitch, Tubi, etc.)

Each example includes:
- Python script with `StatePrompt` definitions
- `results/` folder containing execution history JSON files

Use these examples to create and iterate on your own workflow specifications and benchmarks.
