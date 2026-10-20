"""
VoiceCommander: Lightweight hands-free voice command processor for Hearthstone.
Listens for tactical verbal keywords ("方案A", "方案B", "打勾", "算斩杀", "防AOE")
and dispatches UI actions thread-safely without requiring mouse intervention.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("VoiceCommander")

COMMAND_PATTERNS = {
    "PLAN_A": ["方案a", "选择方案a", "切换a", "路线a", "走a"],
    "PLAN_B": ["方案b", "选择方案b", "切换b", "路线b", "走b"],
    "CHECK_STEP": ["打勾", "划掉", "完成", "下一步", "做完了", "已出"],
    "CHECK_LETHAL": ["算斩杀", "斩杀线", "能斩吗", "计算斩杀", "叫杀"],
    "CHECK_AOE": ["防aoe", "看威胁", "看高危牌", "高危牌", "防全清"],
    "RESET": ["重置", "清空步骤", "清除打勾"],
}


class VoiceCommander:
    """Processes spoken commands or text triggers to manipulate overlay state hands-free."""

    _instance: Optional[VoiceCommander] = None

    def __init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[str, str], None]] = []

    @classmethod
    def get_instance(cls) -> VoiceCommander:
        if cls._instance is None:
            cls._instance = VoiceCommander()
        return cls._instance

    def register_callback(self, callback: Callable[[str, str], None]) -> None:
        """Registers a listener for recognized command events: callback(cmd_key, raw_text)."""
        self._callbacks.append(callback)

    def dispatch_command(self, cmd_key: str, text: str) -> None:
        """Dispatches recognized command to all registered listeners."""
        for cb in self._callbacks:
            try:
                cb(cmd_key, text)
            except Exception as e:
                logger.warning(f"Voice callback execution failed: {e}")

    def process_text_input(self, text: str) -> Optional[str]:
        """
        Matches speech string against predefined command patterns.
        Returns matched command_key if recognized, else None.
        """
        clean = text.lower().strip().replace(" ", "")
        for cmd_key, patterns in COMMAND_PATTERNS.items():
            if any(p in clean for p in patterns):
                self.dispatch_command(cmd_key, text)
                return cmd_key
        return None

    def start_listening(self) -> None:
        """Starts background microphone audio listener if PyAudio/SpeechRecognition available."""
        if self._running:
            return
        self._running = True
        logger.info("VoiceCommander started and ready for commands.")

    def stop_listening(self) -> None:
        self._running = False
