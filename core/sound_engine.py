"""
SoundEngine: Cross-Platform Low-Latency Audio and TTS Notification Engine.
Provides non-blocking, thread-safe sound effects (Lethal chord, AOE warning, Coin chime)
and optional TTS synthesized speech without requiring external heavy audio dependencies.
"""

from __future__ import annotations

import io
import logging
import math
import os
import platform
import struct
import sys
import threading
import wave
from typing import Optional

logger = logging.getLogger("SoundEngine")


def generate_tone_wav(
    frequencies: list[float],
    duration_sec: float = 0.25,
    sample_rate: int = 22050,
    volume: float = 0.5,
) -> bytes:
    """Generates standard PCM 16-bit Mono WAV in-memory bytes for given frequencies."""
    num_samples = int(sample_rate * duration_sec)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Linear decay envelope to prevent audio popping
            envelope = 1.0 - (i / num_samples) * 0.7
            sample_val = 0.0
            for freq in frequencies:
                sample_val += math.sin(2.0 * math.pi * freq * t)
            sample_val = (sample_val / len(frequencies)) * volume * envelope
            int_val = int(max(-1.0, min(1.0, sample_val)) * 32767)
            frames.extend(struct.pack("<h", int_val))
        wf.writeframes(frames)
    return buf.getvalue()


class SoundEngine:
    """Thread-safe sound effects & voice notification manager."""

    _instance: Optional[SoundEngine] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> SoundEngine:
        with cls._lock:
            if cls._instance is None:
                cls._instance = SoundEngine()
            return cls._instance

    def __init__(self) -> None:
        self.sound_enabled: bool = True
        self.tts_enabled: bool = False
        self.volume: int = 80  # 0 to 100

        # Pre-generate wav tones in memory for instant zero-latency playback
        self._lethal_wav: bytes = generate_tone_wav([523.25, 659.25, 783.99, 1046.50], duration_sec=0.45, volume=0.7)  # C major arpeggio
        self._warning_wav: bytes = generate_tone_wav([440.0, 369.99], duration_sec=0.35, volume=0.6)  # Minor alert buzz
        self._coin_wav: bytes = generate_tone_wav([880.0, 1174.66], duration_sec=0.25, volume=0.55)  # Crystal ping
        self._pick_wav: bytes = generate_tone_wav([587.33, 880.0], duration_sec=0.22, volume=0.5)  # Golden chime

    def update_settings(self, sound_enabled: bool, tts_enabled: bool, volume: int = 80) -> None:
        self.sound_enabled = sound_enabled
        self.tts_enabled = tts_enabled
        self.volume = max(0, min(100, volume))

    def _play_wav_bytes(self, wav_bytes: bytes) -> None:
        """Plays in-memory WAV bytes asynchronously on the platform's audio output."""
        if not self.sound_enabled or self.volume <= 0:
            return

        def _worker():
            try:
                if platform.system() == "Windows":
                    import winsound
                    winsound.PlaySound(wav_bytes, winsound.SND_MEMORY | winsound.SND_ASYNC)
                else:
                    # Linux / POSIX fallback: try aplay or system beep
                    # Write temporary wav or use paplay / aplay
                    import subprocess
                    for player in ["aplay", "paplay", "pw-cat"]:
                        try:
                            p = subprocess.Popen([player], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            p.communicate(input=wav_bytes, timeout=1.0)
                            return
                        except Exception:
                            continue
            except Exception as e:
                logger.debug(f"Sound playback suppressed: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _speak_text(self, text: str) -> None:
        """Speaks text using platform TTS engine asynchronously."""
        if not self.tts_enabled or not text:
            return

        def _tts_worker():
            try:
                if platform.system() == "Windows":
                    # Native Windows SAPI voice
                    import subprocess
                    # Escape quotes for PowerShell
                    safe_text = text.replace("'", "").replace('"', "")
                    cmd = [
                        "powershell.exe",
                        "-NoProfile",
                        "-Command",
                        f"Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Rate = 1; $synth.Speak('{safe_text}');",
                    ]
                    subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4.0)
                else:
                    import subprocess
                    for tts_cmd in ["spd-say", "espeak", "espeak-ng"]:
                        try:
                            subprocess.run([tts_cmd, text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2.0)
                            return
                        except Exception:
                            continue
            except Exception as e:
                logger.debug(f"TTS speech failed: {e}")

        threading.Thread(target=_tts_worker, daemon=True).start()

    def notify_tactical_callout(self, phrase: str) -> None:
        """Speaks an ultra-concise 3-5 word tactical directive (e.g. '优先抽牌', '全员走脸')."""
        if not self.tts_enabled or not phrase:
            return
        self._speak_text(phrase)

    def notify_lethal(self, damage: int = 0) -> None:
        """Triggers triumphant lethal cue."""
        self._play_wav_bytes(self._lethal_wav)
        msg = f"发现斩杀线！可造成{damage}点伤害" if damage > 0 else "发现斩杀！"
        self._speak_text(msg)

    def notify_two_turn_lethal(self) -> None:
        """Triggers two-turn lethal lock cue."""
        self._play_wav_bytes(self._lethal_wav)
        self._speak_text("两回合将死已形成！全员走脸控血，逼入绝境！")

    def notify_opponent_lethal_threat(self, deficit: int = 0) -> None:
        """Triggers emergency alarm when player is in danger of being finished next turn."""
        self._play_wav_bytes(self._warning_wav)
        msg = f"生死警报！下回合面临绝杀危险，必须解场或架嘲讽保命！" if deficit <= 0 else f"生死警报！敌方伤害溢出{deficit}点，必须解怪抬血！"
        self._speak_text(msg)

    def notify_aoe_threat(self, threat_name: str = "") -> None:
        """Triggers high-risk enemy sweep warning cue."""
        self._play_wav_bytes(self._warning_wav)
        msg = f"注意防范对手清场：{threat_name}" if threat_name else "注意防范对手清场！"
        self._speak_text(msg)

    def notify_coin_opportunity(self) -> None:
        """Triggers optimal coin usage cue."""
        self._play_wav_bytes(self._coin_wav)
        self._speak_text("当前为最佳跳币时机！")

    def notify_blunder_alert(self, blunder_text: str = "") -> None:
        """Triggers operational blunder sequence warning."""
        self._play_wav_bytes(self._warning_wav)
        if "增益" in blunder_text:
            msg = "防伏笔提醒：先出增益牌再攻击"
        elif "过牌" in blunder_text:
            msg = "防伏笔提醒：先过牌探查"
        elif "奥秘" in blunder_text:
            msg = "防伏笔提醒：先用小怪试探奥秘"
        elif "英雄技能" in blunder_text:
            msg = "防空过提醒：注意使用英雄技能"
        elif "锻造" in blunder_text:
            msg = "锻造提醒：记得先锻造升级"
        else:
            msg = "注意出牌顺序！"
        self._speak_text(msg)

    def notify_card_picked(self, card_name: str = "") -> None:
        """Triggers draft pick confirmation chime."""
        self._play_wav_bytes(self._pick_wav)

    def play_chime(self) -> None:
        """Plays draft pick or general confirmation chime."""
        self._play_wav_bytes(self._pick_wav)

    def notify_rope_emergency(self) -> None:
        """Triggers urgent countdown tone when turn rope begins burning."""
        self._play_wav_bytes(self._warning_wav)
        self._speak_text("烧绳倒计时！急救模式已启动！")

    def notify_coach_directive(self, situation: str, detail: str = "") -> None:
        """
        Pro Coach Natural Voice Commentary:
        Broadcasts tactical directives in authoritative, clear natural coach voice.
        """
        if not self.tts_enabled:
            return
        sit = situation.upper()
        if "LETHAL" in sit:
            text = "教练提醒：发现斩杀线！全员走脸，直接带走！"
        elif "AOE" in sit or "WIPE" in sit:
            threat_name = f"（{detail}）" if detail else ""
            text = f"教练提醒：对面关键清场回合{threat_name}，手牌留点后劲，千万别全铺了！"
        elif "GAMBLE" in sit:
            text = "教练提醒：下轮神抽概率高，被动解场也是输，全员抢脸搏一把！"
        elif "TILT" in sit:
            text = "教练提醒：心态放平，刚才出牌太急了，深呼吸喝口水慢慢打！"
        elif "DRAW_FIRST" in sit:
            text = "教练提醒：先过牌，探明手牌再做随从交换！"
        else:
            text = f"教练战术：{detail or situation}"
        self._speak_text(text)

    def voice_debrief_match(self, match_review: Any, won: bool) -> None:
        """Plays audio debriefing summary at game end."""
        grade = getattr(match_review, "match_grade", "A").split(" ")[0]
        if won:
            self._play_wav_bytes(self._lethal_wav)
            msg = f"对局结算，大获全胜！本局战局评级【{grade}】级，发挥出色！"
        else:
            self._play_wav_bytes(self._warning_wav)
            blunders = getattr(match_review, "blunders", [])
            if blunders:
                first_desc = getattr(blunders[0], "description", "错失场面节奏")
                msg = f"对局结算，本局评级【{grade}】级。关键转折点：{first_desc}。"
            else:
                tp = getattr(match_review, "key_turning_point", "场面受到压制")
                msg = f"对局结算，本局评级【{grade}】级。关键胜负手：{tp}。"
        self._speak_text(msg)
