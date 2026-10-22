"""
Bio-Feedback Tilt & Flow State Guardian (玩家操作微表情与抗上头心流守护神)
- Monitors player micro-behavior telemetry: rapid click jitter, rushed turns (<6s), loss streaks, rapid rematches.
- Computes Flow State Score (0 to 100) and Tilt Risk Tier (OPTIMAL_ZEN, MILD_FATIGUE, HIGH_TILT_ALERT).
- Provides proactive empathetic voice interventions and cooldown protocols to safeguard player MMR/stars.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class TiltRiskTier(str, Enum):
    OPTIMAL_ZEN = "OPTIMAL_ZEN"          # 极佳心流: 节奏沉稳、计算清晰
    MILD_FATIGUE = "MILD_FATIGUE"        # 轻度疲倦: 操作稍显急促，注意力开始分散
    HIGH_TILT_ALERT = "HIGH_TILT_ALERT"  # 上头暴躁预警: 连败盲目极速出牌，极易伏笔送局


@dataclass
class FlowTiltStatus:
    flow_score: float                  # 心流指数 (0.0 ~ 100.0)
    tilt_tier: TiltRiskTier
    tier_label: str
    is_intervention_needed: bool
    recommended_cooldown_sec: int
    spoken_comfort_line: str
    tactical_guidance: str
    summary_markdown: str


class FlowTiltGuardian:
    """
    Guards the player against psychological tilt, burnout, and emotional blunder sprees.
    """

    @classmethod
    def evaluate_player_state(
        cls,
        loss_streak: int = 0,
        avg_turn_sec: float = 25.0,
        click_jitter_apm: float = 80.0,
        consecutive_matches: int = 1,
    ) -> FlowTiltStatus:
        """
        Calculates holistic tilt and flow status.
        """
        # Baseline flow is 85
        score = 85.0

        # Loss streak heavily drains flow
        score -= min(45.0, loss_streak * 12.0)

        # Rushed turns (< 10s) indicates emotional impatience
        if avg_turn_sec < 8.0:
            score -= 25.0
        elif avg_turn_sec < 14.0:
            score -= 10.0

        # High click APM (> 180) in Hearthstone signals anxious clicking
        if click_jitter_apm > 200.0:
            score -= 15.0
        elif click_jitter_apm > 140.0:
            score -= 8.0

        # Long sessions (> 6 consecutive matches) cause mental fatigue
        if consecutive_matches >= 8:
            score -= 18.0
        elif consecutive_matches >= 5:
            score -= 8.0

        final_score = max(5.0, min(100.0, round(score, 1)))

        if final_score <= 45.0 or loss_streak >= 3 or (loss_streak >= 2 and avg_turn_sec < 10.0):
            tier = TiltRiskTier.HIGH_TILT_ALERT
            label = "🚨 上头高危警报 (心态起伏，急躁出牌)"
            needed = True
            cooldown = 45
            spoken = (
                "先深呼吸 5 秒，把手从鼠标上移开。刚刚那局对面纯属神抽，你的操作没有任何毛病。"
                "听大师的，先喝口水闭目养神 30 秒，我们稳住心态再开！"
            )
            guidance = "启动冷静协议：暂停盲目快速匹配，回合开始强制思考 15 秒再出第一张牌。"
        elif final_score <= 70.0 or loss_streak >= 1 or consecutive_matches >= 6:
            tier = TiltRiskTier.MILD_FATIGUE
            label = "☕ 轻度疲倦提醒 (反应迟滞，注意劳逸结合)"
            needed = False
            cooldown = 15
            spoken = "连打了挺多把，节奏稍微有点赶，适当放慢操作，看清每张牌的费用再打。"
            guidance = "放缓出牌速度，每回合执行前置伏笔检查。"
        else:
            tier = TiltRiskTier.OPTIMAL_ZEN
            label = "🧘 极佳心流沉浸 (心态沉着，状态火热)"
            needed = False
            cooldown = 0
            spoken = "状态非常棒！节奏稳健、算计缜密，保持这个手感继续连胜！"
            guidance = "继续保持当前专注度，执行最佳期望值打法。"

        md = (
            f"**心流与抗上头守护仪 (实战生理与情绪监测)**:\n"
            f"• **心流指数**: **{final_score:.1f} / 100**\n"
            f"• **状态定级**: **{label}**\n"
            f"• **连败与连续场次**: 连败 {loss_streak} 场 | 连续作战 {consecutive_matches} 场\n"
            f"• **平均决策耗时**: {avg_turn_sec:.1f} 秒/回合 | 操作抖动 APM: {click_jitter_apm:.0f}\n"
            f"• **大师心理陪伴**: {spoken}"
        )

        return FlowTiltStatus(
            flow_score=final_score,
            tilt_tier=tier,
            tier_label=label,
            is_intervention_needed=needed,
            recommended_cooldown_sec=cooldown,
            spoken_comfort_line=spoken,
            tactical_guidance=guidance,
            summary_markdown=md,
        )
