"""Desktop + mobile screenshots of a prospect's website (installed Chrome, one browser per batch)."""

import logging
from pathlib import Path
from typing import Optional, Tuple

from config.settings import settings

logger = logging.getLogger("showcase.screenshots")

DESKTOP = {"width": 1366, "height": 820}
MOBILE = {"width": 390, "height": 844}
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


class ScreenshotSession:
    """Use as a context manager so Chrome starts once for a batch and always closes."""

    def __init__(self):
        self._pw = None
        self._browser = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        launch = {"headless": True, "args": ["--disable-gpu", "--no-first-run", "--mute-audio"]}
        if Path(settings.CHROME_EXECUTABLE_PATH).exists():
            launch["executable_path"] = settings.CHROME_EXECUTABLE_PATH
        self._browser = self._pw.chromium.launch(**launch)
        return self

    def __exit__(self, *exc):
        try:
            if self._browser:
                self._browser.close()
        finally:
            if self._pw:
                self._pw.stop()

    def capture(self, url: str, out_dir: Path) -> Tuple[Optional[Path], Optional[Path]]:
        out_dir.mkdir(parents=True, exist_ok=True)
        desktop = self._shot(url, out_dir / "desktop.jpg", DESKTOP, None)
        mobile = self._shot(url, out_dir / "mobile.jpg", MOBILE, MOBILE_UA)
        return desktop, mobile

    def _shot(self, url: str, path: Path, viewport: dict, user_agent: Optional[str]) -> Optional[Path]:
        context = None
        try:
            args = {"viewport": viewport, "device_scale_factor": 1}
            if user_agent:
                args.update(user_agent=user_agent, is_mobile=True, has_touch=True)
            context = self._browser.new_context(**args)
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2500)  # let fonts, images and cookie banners settle
            page.screenshot(path=str(path), full_page=False, type="jpeg", quality=72)
            return path
        except Exception as e:
            logger.info(f"Screenshot failed for {url}: {type(e).__name__}: {str(e)[:120]}")
            return None
        finally:
            if context:
                context.close()
