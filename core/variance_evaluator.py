"""
VarianceEvaluator: RNG Variance & Risk-Tolerance Evaluator for Hearthstone Arena.
Distinguishes between ahead/behind board states:
- Winning states: Mandates zero-variance deterministic lines to prevent catastrophic tilts.
- Losing states: Actively encourages high-variance miracle plays to maximize comeback probability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger("VarianceEvaluator")

# Common RNG-dependent Arena cards
RNG_CARDS = {
    "奥术飞弹", "ARCANE MISSILES",
    "疯狂投弹者", "MAD BOMBER",
    "闪电风暴", "LIGHTNING STORM",
    "轰击", "FLAMECANNON",
    "致命射击", "DEADLY SHOT",
    "连环爆裂", "CRACKLE",
    "复仇之怒", "AVENGING WRATH",
    "尤格-萨隆", "YOGG-SARON",
    "大乱斗", "BRAWL",
    "狂乱", "HYSTERIA",
}


@dataclass
class VariancePolicyReport:
    winrate_pct: float
    recommended_policy: str         # "VARIANCE_FREE", "HIGH_VARIANCE_MIRACLE", "BALANCED"
    policy_badge: str
    variance_directive: str
    action_involves_rng: bool = False
    warning_flag: Optional[str] = None


class VarianceEvaluator:
    """Calculates risk tolerance and guides RNG decision-making."""

    @classmethod
    def evaluate_risk_policy(
        cls,
        winrate_pct: float,
        planned_actions: List[str],
    ) -> VariancePolicyReport:
        # Check if any planned actions mention RNG cards
        has_rng = any(
            any(rng_k in act.upper() for rng_k in RNG_CARDS)
            for act in planned_actions
        )

        if winrate_pct >= 58.0:
            policy = "VARIANCE_FREE"
            badge = "🛡️ 优势稳健·零方差原则"
            if has_rng:
                directive = (
                    f"【当前胜率 {winrate_pct:.1f}% 占据明显优势】本回合包含随机效果动作，"
                    f"但优势局应坚决奉行「零方差确定性路线」！"
                    f"切勿贪图随机解场/打脸，优先选择100%稳定解怪换怪路线，防止意外翻车！"
                )
                warning = "⚠️ 优势局切勿贪随机性！推荐走稳健路线"
            else:
                directive = (
                    f"【当前胜率 {winrate_pct:.1f}% 占优】规划路线完全无随机性折损，"
                    f"100%确定性控场压制，持续滚雪球稳固胜势。"
                )
                warning = None
        elif winrate_pct <= 42.0:
            policy = "HIGH_VARIANCE_MIRACLE"
            badge = "🎲 劣势搏命·放手一搏"
            if has_rng:
                directive = (
                    f"【当前胜率 {winrate_pct:.1f}% 处于被动】当前常规稳扎稳打已难以逆转颓势！"
                    f"高度推荐本回合走高上限随机博弈路线，放手一搏追求翻盘奇迹！"
                )
                warning = "✨ 劣势放手一搏！博弈上限路线"
            else:
                directive = (
                    f"【当前胜率 {winrate_pct:.1f}% 落后】局势不利，若常规控场节奏滞后，"
                    f"可积极寻求随机直伤、发现或高方差手段破局！"
                )
                warning = None
        else:
            policy = "BALANCED"
            badge = "⚖️ 均势博弈·权衡得失"
            directive = (
                f"【当前胜率 {winrate_pct:.1f}% 处于均势】适度承受小概率方差风险，"
                f"以最大化每点水晶的综合场面期望值（EV）。"
            )
            warning = None

        return VariancePolicyReport(
            winrate_pct=winrate_pct,
            recommended_policy=policy,
            policy_badge=badge,
            variance_directive=directive,
            action_involves_rng=has_rng,
            warning_flag=warning,
        )
