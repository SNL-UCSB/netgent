from __future__ import annotations

import json
import re
from typing import Any

from engine.schema import (
    WorkflowAction,
    WorkflowCheck,
    WorkflowSchema,
    WorkflowState,
)

INTERACTED_ELEMENT_ATTRIBUTE_PRIORITY = (
    "data-testid",
    "data-test",
    "data-qa",
    "data-cy",
    "id",
    "name",
    "aria-label",
    "aria-labelledby",
    "aria-describedby",
    "placeholder",
    "title",
    "role",
    "type",
    "href",
    "value",
)
SAFE_SELECTOR_ATTRIBUTES = {
    "id",
    "name",
    "type",
    "placeholder",
    "aria-label",
    "aria-labelledby",
    "aria-describedby",
    "role",
    "for",
    "autocomplete",
    "required",
    "readonly",
    "alt",
    "title",
    "src",
    "href",
    "target",
    "data-id",
    "data-qa",
    "data-cy",
    "data-testid",
    "data-test",
}
PRIMARY_SELECTOR_ATTRIBUTES = (
    "data-testid",
    "data-test",
    "data-qa",
    "data-cy",
    "id",
    "name",
    "aria-label",
    "placeholder",
    "role",
    "type",
)
FALLBACK_SELECTOR_ATTRIBUTES = (
    "aria-labelledby",
    "aria-describedby",
    "title",
    "href",
    "value",
    "src",
    "alt",
    "target",
)
ACTION_TYPE_ALIASES = {
    "click_element_by_index": "click_element",
    "click_element": "click_element",
    "go_back": "go_back",
    "go_to_url": "go_to_url",
    "input_text": "input_text",
    "press_key": "send_keys",
    "scroll": "scroll",
    "scroll_to_text": "scroll_to_text",
    "select_dropdown_option": "select_dropdown_option",
    "send_keys": "send_keys",
    "wait": "wait",
}
GENERIC_ATTRIBUTE_VALUES = {
    "button",
    "btn",
    "container",
    "content",
    "icon",
    "image",
    "input",
    "item",
    "label",
    "link",
    "text",
    "value",
    "wrapper",
}
GENERIC_CLASS_TOKENS = {
    "active",
    "button",
    "btn",
    "disabled",
    "hidden",
    "input",
    "selected",
}
VALID_CSS_CLASS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
PROBABLY_DYNAMIC_VALUE_RE = re.compile(r"(^\d+$)|([0-9]{4,})|([a-f0-9]{8,})|([A-Za-z0-9_-]{24,})")
LONG_TEXT_ATTRIBUTE_KEYS = {
    "title",
    "aria-label",
    "aria-labelledby",
    "aria-describedby",
}


def _quoted_attr(value: str) -> str:
    return json.dumps(value)


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip()


def _normalize_xpath(xpath: str) -> str:
    normalized = xpath.strip()
    if not normalized:
        return normalized
    if normalized.startswith("xpath="):
        return normalized
    if normalized.startswith("/"):
        return f"xpath={normalized}"
    return f"xpath=/{normalized}"


def _is_generic_attribute_value(key: str, value: str) -> bool:
    normalized = _normalize_text(value).lower()
    if not normalized:
        return True
    if key == "id":
        return normalized in GENERIC_ATTRIBUTE_VALUES
    return False


def _is_probably_dynamic_value(value: str) -> bool:
    normalized = _normalize_text(value)
    if not normalized:
        return True
    if PROBABLY_DYNAMIC_VALUE_RE.search(normalized):
        return True
    if any(marker in normalized for marker in ("__", "--", ":r", "?si=", "?v=")):
        return True
    return False


def _is_robust_attribute(key: str, value: str) -> bool:
    normalized = _normalize_text(value)
    if not normalized:
        return False
    if _is_generic_attribute_value(key, normalized):
        return False
    if key in {"id", "data-testid", "data-test", "data-qa", "data-cy"}:
        return not _is_probably_dynamic_value(normalized)
    if key in {"name", "placeholder", "role", "type"}:
        return True
    if key in LONG_TEXT_ATTRIBUTE_KEYS:
        return len(normalized) <= 40
    if key == "href":
        if normalized.startswith(("#", "javascript:")):
            return False
        if "?" in normalized:
            return False
        return len(normalized) <= 60
    if key in {"value", "src", "target"}:
        return len(normalized) <= 40 and not _is_probably_dynamic_value(normalized)
    return True


def _attribute_selector(key: str, value: str) -> str:
    return f"[{key}={_quoted_attr(value)}]"


def _append_candidate(
    candidates: list[str],
    seen: set[str],
    selector: str | None,
) -> None:
    if not selector:
        return
    normalized = selector.strip()
    if not normalized or normalized in seen:
        return
    seen.add(normalized)
    candidates.append(normalized)


def _get_element_metadata(interacted_element: Any) -> dict[str, Any]:
    if not isinstance(interacted_element, dict):
        return {}
    metadata = interacted_element.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _get_element_string(interacted_element: dict[str, Any], *keys: str) -> str:
    metadata = _get_element_metadata(interacted_element)
    for key in keys:
        value = interacted_element.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _meaningful_class_tokens(attributes: dict[str, Any]) -> list[str]:
    raw_value = attributes.get("class")
    if not isinstance(raw_value, str):
        return []

    tokens: list[str] = []
    for token in raw_value.split():
        normalized = token.strip()
        if not normalized:
            continue
        if normalized.lower() in GENERIC_CLASS_TOKENS:
            continue
        if normalized.startswith(("ng-", "ember", "css-")):
            continue
        if _is_probably_dynamic_value(normalized):
            continue
        if not VALID_CSS_CLASS_RE.match(normalized):
            continue
        tokens.append(normalized)

    return tokens[:2]


def _meaningful_attributes(attributes: dict[str, Any]) -> list[tuple[str, str]]:
    selected: list[tuple[str, str]] = []
    for key in INTERACTED_ELEMENT_ATTRIBUTE_PRIORITY:
        value = _normalize_text(attributes.get(key))
        if not value or not _is_robust_attribute(key, value):
            continue
        selected.append((key, value))
    return selected


def _short_css_selector(css_selector: str) -> str | None:
    normalized = css_selector.strip()
    if not normalized:
        return None
    if " > " not in normalized:
        return normalized

    parts = [part.strip() for part in normalized.split(" > ") if part.strip()]
    if not parts:
        return None

    for length in (2, 1):
        tail = " > ".join(parts[-length:])
        if "nth-of-type" not in tail:
            return tail

    return None


def _build_enhanced_css_selector(
    tag: str,
    attributes: dict[str, Any],
) -> str | None:
    if not tag:
        return None

    selector = tag

    for class_name in _meaningful_class_tokens(attributes):
        selector += f".{class_name}"

    selected_attributes = 0

    for key in PRIMARY_SELECTOR_ATTRIBUTES:
        value = _normalize_text(attributes.get(key))
        if not value:
            continue
        if key not in SAFE_SELECTOR_ATTRIBUTES:
            continue
        if not _is_robust_attribute(key, value):
            continue
        selector += _attribute_selector(key, value)
        selected_attributes += 1
        if selected_attributes >= 2:
            break

    if selected_attributes == 0:
        for key in FALLBACK_SELECTOR_ATTRIBUTES:
            value = _normalize_text(attributes.get(key))
            if not value:
                continue
            if key not in SAFE_SELECTOR_ATTRIBUTES:
                continue
            if not _is_robust_attribute(key, value):
                continue
            selector += _attribute_selector(key, value)
            selected_attributes += 1
            if selected_attributes >= 1:
                break

    return selector if selector != tag or attributes else selector


def generate_selectors(interacted_element: Any) -> list[str]:
    if not isinstance(interacted_element, dict):
        return []

    tag = _normalize_text(_get_element_string(interacted_element, "tag_name", "tagName"))
    attributes = interacted_element.get("attributes")
    if not isinstance(attributes, dict):
        attributes = {}

    candidates: list[str] = []
    seen: set[str] = set()
    meaningful_attributes = _meaningful_attributes(attributes)
    class_selector = "".join(f".{token}" for token in _meaningful_class_tokens(attributes))

    enhanced_selector = _build_enhanced_css_selector(tag, attributes)
    _append_candidate(candidates, seen, enhanced_selector)

    strong_attribute = next(
        (
            (key, value)
            for key, value in meaningful_attributes
            if key in {"data-testid", "data-test", "data-qa", "data-cy", "id", "name"}
        ),
        None,
    )
    descriptive_attribute = next(
        (
            (key, value)
            for key, value in meaningful_attributes
            if key
            in {
                "aria-label",
                "aria-labelledby",
                "aria-describedby",
                "placeholder",
                "title",
                "href",
                "value",
            }
        ),
        None,
    )

    if strong_attribute is not None:
        key, value = strong_attribute
        base = f"{tag}{_attribute_selector(key, value)}" if tag else _attribute_selector(key, value)
        _append_candidate(candidates, seen, base)

        if (
            descriptive_attribute is not None
            and descriptive_attribute[0] != key
            and descriptive_attribute[0] not in {"href", "title"}
        ):
            descriptor_key, descriptor_value = descriptive_attribute
            _append_candidate(
                candidates,
                seen,
                f"{base}{_attribute_selector(descriptor_key, descriptor_value)}",
            )

    if (
        class_selector
        and descriptive_attribute is not None
        and descriptive_attribute[0] not in {"href", "title"}
        and tag
    ):
        key, value = descriptive_attribute
        _append_candidate(
            candidates,
            seen,
            f"{tag}{class_selector}{_attribute_selector(key, value)}",
        )

    for key, value in meaningful_attributes[:3]:
        _append_candidate(
            candidates,
            seen,
            (f"{tag}{_attribute_selector(key, value)}" if tag else _attribute_selector(key, value)),
        )

    if class_selector and tag:
        _append_candidate(candidates, seen, f"{tag}{class_selector}")

    raw_css_selector = _get_element_string(
        interacted_element,
        "css_selector",
        "cssSelector",
    )
    _append_candidate(candidates, seen, _short_css_selector(raw_css_selector))

    xpath = _get_element_string(interacted_element, "xpath")
    if xpath:
        _append_candidate(candidates, seen, _normalize_xpath(xpath))

    return candidates


def _selector_from_interacted_element(interacted_element: Any) -> str | None:
    selectors = generate_selectors(interacted_element)
    return selectors[0] if selectors else None


def _coerce_wait_seconds(value: Any) -> int:
    if isinstance(value, bool):
        return 3
    if isinstance(value, int | float):
        return max(int(value), 1)
    if isinstance(value, str):
        try:
            return max(int(float(value.strip())), 1)
        except ValueError:
            return 3
    return 3


def _convert_action(action: dict[str, Any]) -> WorkflowAction | None:
    action_type = action.get("type")
    if not isinstance(action_type, str):
        return None

    workflow_action_type = ACTION_TYPE_ALIASES.get(action_type)
    if workflow_action_type is None:
        return None

    params = action.get("params")
    if not isinstance(params, dict):
        params = {}

    interacted_element = action.get("interacted_element")
    selector = _selector_from_interacted_element(interacted_element)

    if workflow_action_type == "go_to_url":
        url = params.get("url")
        if not isinstance(url, str) or not url.strip():
            return None
        return WorkflowAction(
            type="go_to_url",
            params={
                "url": url,
                "new_tab": bool(params.get("new_tab", False)),
            },
        )

    if workflow_action_type == "go_back":
        return WorkflowAction(type="go_back", params={})

    if workflow_action_type == "wait":
        seconds = _coerce_wait_seconds(params.get("seconds", 3))
        return WorkflowAction(type="wait", params={"seconds": seconds})

    if workflow_action_type == "input_text":
        text = params.get("text")
        if selector is None or not isinstance(text, str):
            return None
        return WorkflowAction(
            type="input_text",
            params={"selector": selector, "text": text},
        )

    if workflow_action_type == "click_element":
        if selector is None:
            return None
        return WorkflowAction(type="click_element", params={"selector": selector})

    if workflow_action_type == "scroll":
        down = params.get("down")
        num_pages = params.get("num_pages", 1)
        if not isinstance(down, bool):
            return None
        if not isinstance(num_pages, int | float):
            num_pages = 1
        scroll_params: dict[str, Any] = {
            "down": down,
            "num_pages": float(num_pages),
        }
        if selector is not None:
            scroll_params["selector"] = selector
        return WorkflowAction(type="scroll", params=scroll_params)

    if workflow_action_type == "send_keys":
        keys = params.get("keys", params.get("key"))
        if not isinstance(keys, str) or not keys.strip():
            return None
        return WorkflowAction(type="send_keys", params={"keys": keys})

    if workflow_action_type == "scroll_to_text":
        text = params.get("text")
        if not isinstance(text, str) or not text.strip():
            return None
        return WorkflowAction(type="scroll_to_text", params={"text": text})

    if workflow_action_type == "select_dropdown_option":
        text = params.get("text", params.get("value"))
        if selector is None or not isinstance(text, str) or not text.strip():
            return None
        return WorkflowAction(
            type="select_dropdown_option",
            params={"selector": selector, "text": text},
        )

    return None


def gen_workflow(
    parsed_history: list[dict[str, Any]],
    specification: str = "Replay browser task history",
    parameters: list[str] | None = None,
) -> dict[str, Any]:
    actions: list[WorkflowAction] = []
    for step in parsed_history:
        if not isinstance(step, dict):
            continue
        for action in step.get("actions", []):
            if not isinstance(action, dict):
                continue
            workflow_action = _convert_action(action)
            if workflow_action is not None:
                actions.append(workflow_action)

    workflow = WorkflowSchema(
        specification=specification,
        states=[
            WorkflowState(
                checks=[WorkflowCheck(type="always_true")],
                actions=actions,
                end_state="Workflow Completed",
            )
        ],
        parameters=list(parameters or []),
    )
    return workflow.model_dump(mode="json")
