# NetGent
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
