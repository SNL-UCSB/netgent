import json

from netgent.browser.controller.base import BaseController


class _SwitchTo:
    def __init__(self, driver):
        self.driver = driver

    def new_window(self, _kind):
        handle = f"tab-{len(self.driver.window_handles)}"
        self.driver.window_handles.append(handle)
        self.driver.current_window_handle = handle
        self.driver.urls[handle] = "about:blank"

    def window(self, handle):
        self.driver.current_window_handle = handle


class _Driver:
    def __init__(self):
        self.window_handles = ["host"]
        self.current_window_handle = "host"
        self.urls = {"host": "about:blank"}
        self.switch_to = _SwitchTo(self)
        self.cdp_calls = []

    @property
    def current_url(self):
        return self.urls[self.current_window_handle]

    def get(self, url):
        self.urls[self.current_window_handle] = url

    def execute_cdp_cmd(self, name, params):
        self.cdp_calls.append((name, params))

    def execute_script(self, _script):
        return None

    def execute_async_script(self, _script):
        return {
            "url": self.current_url,
            "webrtc": {"connection_count": 1, "bytes_sent": 10},
        }


class _Controller(BaseController):
    def click(self, **_kwargs):
        return None

    def type_text(self, **_kwargs):
        return None

    def scroll_to(self, **_kwargs):
        return None

    def scroll(self, **_kwargs):
        return None

    def press_key(self, **_kwargs):
        return None

    def move(self, **_kwargs):
        return None


def test_two_tabs_share_the_generated_meeting_url():
    driver = _Driver()
    controller = _Controller(driver)

    controller.remember_tab("host")
    driver.get("https://meet.google.com/abc-defg-hij?authuser=0")
    controller.store_current_url("meeting_url", strip_query=True)
    controller.open_stored_url(
        "meeting_url",
        suffix="?authuser=1",
        tab_name="joiner",
    )

    assert driver.current_url == "https://meet.google.com/abc-defg-hij?authuser=1"
    controller.switch_tab("host")
    assert driver.current_url == "https://meet.google.com/abc-defg-hij?authuser=0"


def test_metrics_include_only_the_active_meeting(tmp_path):
    driver = _Driver()
    controller = _Controller(driver)
    controller.start_webrtc_tracking()
    driver.get("https://meet.google.com/abc-defg-hij?authuser=0")
    controller.store_current_url("meeting_url", strip_query=True)
    controller.open_stored_url(
        "meeting_url",
        suffix="?authuser=1",
        tab_name="joiner",
    )
    output = tmp_path / "metrics.json"

    metrics = controller.collect_webrtc_metrics(str(output))

    assert driver.cdp_calls[0][0] == "Page.addScriptToEvaluateOnNewDocument"
    assert metrics["page_count"] == 2
    assert json.loads(output.read_text()) == metrics
