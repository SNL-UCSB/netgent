from __future__ import annotations

from collections import Counter
from typing import Any

from browser_use import AgentHistoryList
from pydantic import BaseModel, Field

IGNORED_ACTION_TYPES = {
    "done",
    "extract_page_content",
    "get_dropdown_options",
    "read_file",
    "replace_file_str",
    "write_file",
}
IGNORED_URLS = {"about:blank"}
MAX_URLS = 3
MAX_ACTIONS = 5
MAX_ERRORS = 3


class BrowserEvolution(BaseModel):
    task: str
    runs: int = 0
    successes: int = 0
    best_step_count: int | None = None
    best_action_sequence: list[str] = Field(default_factory=list)
    successful_action_counts: dict[str, int] = Field(default_factory=dict)
    error_action_counts: dict[str, int] = Field(default_factory=dict)
    error_messages: dict[str, int] = Field(default_factory=dict)
    url_counts: dict[str, int] = Field(default_factory=dict)


def coerce_evolution(
    task: str, evolution: BrowserEvolution | dict[str, Any] | None
) -> BrowserEvolution:
    if isinstance(evolution, BrowserEvolution):
        if evolution.task == task:
            return evolution
        return BrowserEvolution(task=task)

    if isinstance(evolution, dict):
        profile = BrowserEvolution.model_validate(evolution)
        if profile.task == task:
            return profile

    return BrowserEvolution(task=task)


def _counter_from_mapping(values: dict[str, int]) -> Counter[str]:
    return Counter(values)


def _mapping_from_counter(counter: Counter[str]) -> dict[str, int]:
    return dict(counter.most_common())


def _action_type(action_label: str) -> str:
    return action_label.split(" on ", 1)[0]


def _is_relevant_action_label(action_label: str) -> bool:
    return _action_type(action_label) not in IGNORED_ACTION_TYPES


def _truncate(value: str, limit: int = 80) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _describe_interacted_element(interacted_element: Any) -> str | None:
    if not isinstance(interacted_element, dict):
        return None

    tag_name = interacted_element.get("tag_name")
    attributes = interacted_element.get("attributes")
    css_selector = interacted_element.get("css_selector")
    xpath = interacted_element.get("xpath")

    details: list[str] = []
    if isinstance(tag_name, str) and tag_name:
        details.append(tag_name)

    if isinstance(attributes, dict):
        for key in (
            "aria-label",
            "title",
            "name",
            "placeholder",
            "alt",
            "href",
            "id",
            "value",
        ):
            value = attributes.get(key)
            if isinstance(value, str) and value.strip():
                details.append(f'{key}="{_truncate(value)}"')
                break

    if len(details) == 1:
        if isinstance(css_selector, str) and css_selector:
            details.append(f'selector="{_truncate(css_selector)}"')
        elif isinstance(xpath, str) and xpath:
            details.append(f'xpath="{_truncate(xpath)}"')

    if not details:
        return None

    return " ".join(details)


def _describe_action(action_type: str, interacted_element: Any) -> str:
    element_description = _describe_interacted_element(interacted_element)
    if not element_description:
        return action_type
    return f"{action_type} on {element_description}"


def build_evolutionary_prompt(task: str, evolution: BrowserEvolution) -> str:
    if evolution.runs == 0:
        return task

    best_action_sequence = [
        action
        for action in evolution.best_action_sequence
        if _is_relevant_action_label(action)
    ]

    successful_action_counts = _counter_from_mapping(evolution.successful_action_counts)
    error_action_counts = _counter_from_mapping(evolution.error_action_counts)
    error_messages = _counter_from_mapping(evolution.error_messages)
    url_counts = _counter_from_mapping(evolution.url_counts)

    preferred_actions = [
        action
        for action, _ in successful_action_counts.most_common()
        if _is_relevant_action_label(action)
    ][:MAX_ACTIONS]
    avoid_actions = [
        action
        for action, _ in error_action_counts.most_common()
        if _is_relevant_action_label(action)
    ][:MAX_ACTIONS]
    common_urls = [
        url for url, _ in url_counts.most_common(MAX_URLS) if url not in IGNORED_URLS
    ]
    common_errors = [message for message, _ in error_messages.most_common(MAX_ERRORS)]

    lines = [
        task,
        "",
        "Historical guidance from previous attempts:",
        f"- This task has been attempted {evolution.runs} time(s).",
        f"- Successful completions: {evolution.successes}/{evolution.runs}.",
    ]

    if isinstance(evolution.best_step_count, int):
        lines.append(
            f"- Best known completion used {evolution.best_step_count} step(s)."
        )

    if best_action_sequence:
        lines.append(
            "- Best known high-level action sequence: "
            + " -> ".join(best_action_sequence[:MAX_ACTIONS])
        )

    if common_urls:
        lines.append("- Likely pages or URLs involved: " + ", ".join(common_urls))

    if preferred_actions:
        lines.append(
            "- Actions that have tended to help: " + ", ".join(preferred_actions)
        )

    if avoid_actions:
        lines.append(
            "- Actions that have often correlated with errors or wasted steps: "
            + ", ".join(avoid_actions)
        )

    if common_errors:
        lines.append("- Failure patterns to avoid: " + "; ".join(common_errors))

    lines.extend(
        [
            "- Reuse what worked before, but adapt if the page differs.",
            "- Prefer the shortest reliable path and avoid exploratory detours.",
        ]
    )

    return "\n".join(lines)


def update_evolution(
    task: str,
    history: AgentHistoryList,
    evolution: BrowserEvolution | dict[str, Any] | None,
) -> BrowserEvolution:
    profile = coerce_evolution(task, evolution).model_copy(deep=True)
    successful_action_counts = _counter_from_mapping(profile.successful_action_counts)
    error_action_counts = _counter_from_mapping(profile.error_action_counts)
    error_messages = _counter_from_mapping(profile.error_messages)
    url_counts = _counter_from_mapping(profile.url_counts)

    history_dump = history.model_dump()
    action_sequence: list[str] = []

    for step in history_dump.get("history", []):
        if not isinstance(step, dict):
            continue

        state = step.get("state") or {}
        if isinstance(state, dict):
            url = state.get("url")
            if isinstance(url, str) and url and url not in IGNORED_URLS:
                url_counts[url] += 1

        model_output = step.get("model_output") or {}
        actions = model_output.get("action") if isinstance(model_output, dict) else None
        interacted_elements = (
            state.get("interacted_element") if isinstance(state, dict) else None
        )
        action_labels: list[str] = []
        if isinstance(actions, list):
            for index, action in enumerate(actions):
                if not isinstance(action, dict) or not action:
                    continue
                action_type = next(iter(action))
                if action_type in IGNORED_ACTION_TYPES:
                    continue
                interacted_element = None
                if isinstance(interacted_elements, list) and index < len(
                    interacted_elements
                ):
                    interacted_element = interacted_elements[index]
                action_label = _describe_action(action_type, interacted_element)
                action_labels.append(action_label)
                action_sequence.append(action_label)

        results = step.get("result")
        errors = []
        if isinstance(results, list):
            errors = [
                result.get("error")
                for result in results
                if isinstance(result, dict) and isinstance(result.get("error"), str)
            ]

        if errors:
            for action_label in action_labels:
                error_action_counts[action_label] += 1
            for error in errors:
                error_messages[error[:200]] += 1
        else:
            for action_label in action_labels:
                successful_action_counts[action_label] += 1

    profile.runs += 1
    if history.is_successful():
        profile.successes += 1
        step_count = len(history)
        if profile.best_step_count is None or step_count < profile.best_step_count:
            profile.best_step_count = step_count
            profile.best_action_sequence = action_sequence

    profile.successful_action_counts = _mapping_from_counter(successful_action_counts)
    profile.error_action_counts = _mapping_from_counter(error_action_counts)
    profile.error_messages = _mapping_from_counter(error_messages)
    profile.url_counts = _mapping_from_counter(url_counts)
    return profile
