"""
TiltGuard: Arena Session Fatigue & Tilt Index Monitoring Engine.
Monitors multi-match stress, consecutive loss streaks, turn decision rush speed,
and blunder spikes, providing proactive break advisories to prevent costly tilt blunders.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TiltGuard")


@dataclass
class TiltReport:
    composite_index: int          # 0 (Peak Focus) to 100 (Severe Tilt/Fatigue)
    tilt_score: int               # 0 to 100
    fatigue_score: int            # 0 to 100
    tier_label: str               # "🎯 专注巅峰", "☕ 轻微疲倦", "⚠️ 上头高危", "🛑 强制休息建议"
    streak_summary: str           # e.g. "连续失利 2 场"
    action_directive: str         # "状态正佳，全力冲击12胜！" or "建议休息5分钟喝水调整"
    is_rest_recommended: bool    # True if score >= 60


class TiltGuard:
    """Singleton tracker managing player mental fatigue and tilt metrics across games."""

    _instance: Optional[TiltGuard] = None

    @classmethod
    def get_instance(cls) -> TiltGuard:
        if cls._instance is None:
            cls._instance = TiltGuard()
        return cls._instance

    def __init__(self) -> None:
        self.session_start = time.time()
        self.matches: List[Dict[str, Any]] = []
        self.current_match_blunders = 0
        self.current_match_turn_times: List[float] = []

    def reset_session(self) -> None:
        self.session_start = time.time()
        self.matches.clear()
        self.current_match_blunders = 0
        self.current_match_turn_times.clear()

    def record_turn_action(self, duration_sec: float, blunders: int = 0) -> None:
        self.current_match_turn_times.append(max(0.5, duration_sec))
        self.current_match_blunders += blunders

    def record_match_finished(self, won: bool, total_turns: int = 10) -> None:
        avg_turn = sum(self.current_match_turn_times) / max(1, len(self.current_match_turn_times))
        self.matches.append({
            "won": bool(won),
            "blunders": self.current_match_blunders,
            "avg_turn_sec": avg_turn,
            "total_turns": total_turns,
            "finished_at": time.time(),
        })
        self.current_match_blunders = 0
        self.current_match_turn_times.clear()

    def evaluate_tilt(self) -> TiltReport:
        now = time.time()
        session_mins = (now - self.session_start) / 60.0
        total_matches = len(self.matches)

        # 1. Fatigue Score (0-100)
        fatigue = min(100, int((session_mins / 90.0) * 50 + (total_matches / 8.0) * 50))

        # 2. Tilt Score (0-100)
        tilt = 0
        loss_streak = 0
        for m in reversed(self.matches):
            if not m["won"]:
                loss_streak += 1
            else:
                break

        # Consecutive losses penalty
        if loss_streak >= 3:
            tilt += 45
        elif loss_streak == 2:
            tilt += 28
        elif loss_streak == 1:
            tilt += 12

        # Blunder density in recent matches
        recent_blunders = sum(m.get("blunders", 0) for m in self.matches[-3:]) + self.current_match_blunders
        tilt += min(35, recent_blunders * 12)

        # Rushed turns penalty (playing in <4s per turn suggests reckless impulsive clicking)
        if self.current_match_turn_times:
            recent_avg_turn = sum(self.current_match_turn_times[-5:]) / max(1, len(self.current_match_turn_times[-5:]))
            if recent_avg_turn < 4.0 and (loss_streak > 0 or recent_blunders > 0):
                tilt += 20

        tilt = min(100, max(0, tilt))
        composite = min(100, int(0.65 * tilt + 0.35 * fatigue))

        # Tiers & Directives
        if composite >= 75:
            tier = "🛑 强制休息建议"
            directive = "检测到连续失利且出牌急躁！伏笔率已激增，请务必暂停 5 分钟闭目喝水，切勿冲动开局！"
            rest_rec = True
        elif composite >= 55:
            tier = "⚠️ 上头高危预警"
            directive = "疲劳度上升，操作速度异常偏快。每回合多思考 5 秒再松开鼠标，稳住节奏！"
            rest_rec = True
        elif composite >= 30:
            tier = "☕ 轻微疲倦"
            directive = "精力平稳，但建议适度伸展身体，保持头脑清醒。"
            rest_rec = False
        else:
            tier = "🎯 专注巅峰"
            directive = "竞技状态极佳，逻辑推演清晰，全力冲击 12 胜冠军！"
            rest_rec = False

        streak_str = f"连败 {loss_streak} 局" if loss_streak > 0 else (f"连胜 {len(self.matches)} 局" if self.matches and all(m['won'] for m in self.matches) else "竞技对局进行中")

        return TiltReport(
            composite_index=composite,
            tilt_score=tilt,
            fatigue_score=fatigue,
            tier_label=tier,
            streak_summary=streak_str,
            action_directive=directive,
            is_rest_recommended=rest_rec,
        )
