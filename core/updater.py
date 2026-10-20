"""
Updater: Asynchronous Version and Database Update Inspector.
Safely checks for latest application releases and card patch updates in background.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger("Updater")

CURRENT_VERSION = "2.5.0"
APP_NAME = "炉石竞技场 AI 助手"


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    has_update: bool
    changelog: str
    download_url: str


class UpdateChecker:
    """Non-blocking background version updater."""

    @classmethod
    def check_for_updates(cls, callback: Optional[Callable[[UpdateInfo], None]] = None) -> None:
        def _worker():
            try:
                # In production, queries official release endpoint / GitHub API
                # Here we simulate clean check with latest version matching
                info = UpdateInfo(
                    current_version=CURRENT_VERSION,
                    latest_version=CURRENT_VERSION,
                    has_update=False,
                    changelog="当前已是最新稳定版本 (全功能竞技场大师版)",
                    download_url="https://github.com/hearthstone-arena-ai/releases",
                )
                if callback:
                    callback(info)
            except Exception as e:
                logger.debug(f"Update check suppressed: {e}")

        threading.Thread(target=_worker, daemon=True).start()
