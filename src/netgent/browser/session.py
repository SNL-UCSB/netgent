from seleniumbase import Driver
import logging
logger = logging.getLogger(__name__)

"""
Initializes Browser Session with SeleniumBase.
With the pre-defined settings, the browser is ready to use.
"""
class BrowserSession:
    def __init__(self, proxy: str = None, user_data_dir: str | None = None):
        self._driver: Driver | None = None
        self._default_args: list[str] = [
            "--force-device-scale-factor=1",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
        ]
        if user_data_dir:
            self._default_args.append(f" --user-data-dir={user_data_dir}")
        self._args: str = ",".join(self._default_args)
        self.proxy: str = proxy
        self.user_data_dir: str | None = user_data_dir
        self.start()
    
    @property
    def driver(self) -> Driver:
        if self._driver is None:
            raise ValueError("Driver is not initialized")
        return self._driver

    def start(self):
        if self._driver is not None:
            raise ValueError("Driver is already initialized")
        self._driver = Driver(uc=True, headed=True, browser="chrome", chromium_arg=self._args, use_auto_ext=False,
            undetectable=True, proxy=self.proxy, user_data_dir=self.user_data_dir)

    def quit(self):
        if self._driver is None:
            raise ValueError("Driver is not initialized")
        self._driver.quit()
