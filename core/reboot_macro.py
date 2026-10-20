"""
RebootMacro: Rope emergency quick-reboot & animation skip utility for Hearthstone.
Instantly terminates Hearthstone.exe to abort long animation queues and reconnects in ~5 seconds,
reclaiming up to 30 seconds of critical turn deliberation time.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys

logger = logging.getLogger("RebootMacro")


class RebootMacro:
    """Manages emergency fast-reboot macros to skip animations during rope emergencies."""

    @classmethod
    def execute_rope_emergency_reboot(cls) -> bool:
        """
        Forcefully terminates Hearthstone.exe and restarts it immediately.
        Skips all accumulated animations (Deathrattles, card shuffle loops)
        and fast-reconnects directly into the active match.
        """
        logger.info("Triggered Rope Emergency Quick-Reboot Macro!")

        if sys.platform != "win32":
            logger.info("Simulated emergency reboot on non-Windows environment.")
            return True

        try:
            # 1. Force kill Hearthstone.exe
            subprocess.run(
                ["taskkill", "/F", "/IM", "Hearthstone.exe"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=3,
            )

            # 2. Re-launch Hearthstone through Battle.net URI or standard launcher
            bnet_uri = "battlenet://WTCG"
            os.system(f'start "" "{bnet_uri}"')
            logger.info("Dispatched launch command for battlenet://WTCG")
            return True
        except Exception as e:
            logger.warning(f"Rope emergency reboot failed: {e}")
            return False
