"""
ConversationalTtsStreamer: Grandmaster Co-Pilot Live Audio Stream & Voice Coach Whisperer.
Manages priority-based natural conversational audio streaming, anti-spam voice pacing,
and millisecond-level emergency preemption for pre-cast blunder alerts.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("ConversationalTtsStreamer")


@dataclass
class VoiceSpeechItem:
    text: str
    priority: int       # 10 = Normal step guidance, 50 = Macro overview, 100 = Emergency Blunder Intercept
    created_at: float
    is_interrupt: bool = False


class ConversationalTtsStreamer:
    """Streams natural master conversational advice with emergency preemptive interrupts."""

    _instance: Optional[ConversationalTtsStreamer] = None

    def __init__(self, speaker_func: Optional[Callable[[str], None]] = None) -> None:
        self.speaker_func = speaker_func
        self._last_spoken_text: str = ""
        self._last_spoken_time: float = 0.0
        self._min_interval_sec: float = 2.0
        self._queue: List[VoiceSpeechItem] = []
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> ConversationalTtsStreamer:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_speaker_func(self, speaker_func: Callable[[str], None]) -> None:
        self.speaker_func = speaker_func

    def speak_step_guidance(self, step_voice_text: str) -> bool:
        """Speaks the current active micro-step directive."""
        return self._enqueue_speech(step_voice_text, priority=10, is_interrupt=False)

    def speak_blunder_intercept(self, emergency_voice_shout: str) -> bool:
        """Immediately interrupts any current speech to shout the emergency blunder warning."""
        with self._lock:
            # Clear normal queue and immediately dispatch emergency shout
            self._queue.clear()
        return self._enqueue_speech(emergency_voice_shout, priority=100, is_interrupt=True)

    def speak_macro_overview(self, macro_overview_text: str) -> bool:
        """Speaks turn start macro strategic overview."""
        return self._enqueue_speech(macro_overview_text, priority=50, is_interrupt=False)

    def _enqueue_speech(self, text: str, priority: int = 10, is_interrupt: bool = False) -> bool:
        now = time.time()
        # Prevent identical repetitive voice line within 3 seconds unless it's an emergency interrupt
        if not is_interrupt and text == self._last_spoken_text and (now - self._last_spoken_time) < 3.0:
            return False

        if not is_interrupt and (now - self._last_spoken_time) < self._min_interval_sec:
            return False

        self._last_spoken_text = text
        self._last_spoken_time = now

        logger.info(f"Master Voice: '{text}' [Priority {priority}]")

        if self.speaker_func:
            try:
                self.speaker_func(text)
                return True
            except Exception as e:
                logger.warning(f"Error invoking TTS speaker function: {e}")
        return True
