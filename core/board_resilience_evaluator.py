"""
BoardResilienceEvaluator: Board wipe resistance & anti-reversal Monte Carlo resilience analyzer.
Evaluates the robustness of a friendly board state against next-turn opponent counter-attacks (AOE wipes,
hard removals, counter-swarms) and calculates the Board Resilience Score (0 to 100).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BoardResilienceEvaluator")


@dataclass
class BoardResilienceReport:
    resilience_score: int          # 0 to 100
    resilience_tier: str           # "HIGH_RESILIENCE", "BALANCED", "VULNERABLE_RISK"
    badge_text: str                # e.g. "🛡️ 韧性 86/100 (防灭极佳)"
    wipe_survivor_count: int
    total_minions_count: int
    deathrattle_count: int
    divine_shield_count: int
    hand_refill_count: int
    detailed_verdict: str


class BoardResilienceEvaluator:
    """Simulates opponent next-turn counter-wipe scenarios to evaluate board robustness."""

    CLASS_AOE_THREATS: Dict[str, Dict[str, Any]] = {
        "MAGE": {"name": "烈焰风暴/暴风雪", "mana": 6, "dmg": 4, "all": True},
        "PRIEST": {"name": "神圣新星/狂乱", "mana": 4, "dmg": 2, "all": True},
        "WARLOCK": {"name": "地狱烈焰/暗影烈焰", "mana": 4, "dmg": 3, "all": True},
        "PALADIN": {"name": "奉献", "mana": 4, "dmg": 2, "all": True},
        "WARRIOR": {"name": "绝命乱斗/剑刃风暴", "mana": 5, "dmg": 6, "all": True},
        "SHAMAN": {"name": "闪电风暴", "mana": 3, "dmg": 3, "all": True},
        "DRUID": {"name": "横扫", "mana": 4, "dmg": 1, "all": False}, # 4 to target, 1 to rest
        "DEATHKNIGHT": {"name": "血液沸腾/邪恶狂暴", "mana": 5, "dmg": 3, "all": True},
        "DEMONHUNTER": {"name": "献祭光环", "mana": 2, "dmg": 2, "all": True},
        "HUNTER": {"name": "爆炸陷阱", "mana": 2, "dmg": 2, "all": True},
        "ROGUE": {"name": "刀扇", "mana": 3, "dmg": 1, "all": True},
    }

    @classmethod
    def evaluate_board_resilience(
        cls,
        friendly_minions: List[Dict[str, Any]],
        remaining_hand_size: int,
        opponent_class: str,
        opponent_mana: int,
    ) -> BoardResilienceReport:
        """
        Calculates board resilience against next turn AOE wipes.
        friendly_minions format: [{"name": str, "atk": int, "health": int, "deathrattle": bool, "shield": bool}]
        """
        total_m = len(friendly_minions)
        if total_m == 0:
            return BoardResilienceReport(
                resilience_score=50,
                resilience_tier="BALANCED",
                badge_text="⚖️ 空场韧性平衡",
                wipe_survivor_count=0,
                total_minions_count=0,
                deathrattle_count=0,
                divine_shield_count=0,
                hand_refill_count=remaining_hand_size,
                detailed_verdict="当前我方空场，无随从覆灭风险",
            )

        opp = (opponent_class or "UNKNOWN").upper().strip()
        aoe_info = cls.CLASS_AOE_THREATS.get(opp, {"name": "常见AOE", "mana": 4, "dmg": 2, "all": True})

        can_cast_aoe = (opponent_mana >= aoe_info["mana"])
        aoe_dmg = aoe_info["dmg"] if can_cast_aoe else 1

        survivors = 0
        deathrattles = 0
        shields = 0

        for m in friendly_minions:
            hp = m.get("health", 2)
            has_shield = m.get("shield", False) or m.get("divine_shield", False) or ("圣盾" in m.get("name", ""))
            has_dr = m.get("deathrattle", False) or ("亡语" in m.get("name", ""))

            if has_shield:
                shields += 1
                survivors += 1
            elif hp > aoe_dmg:
                survivors += 1

            if has_dr:
                deathrattles += 1

        # 1. Base survivability ratio (0 - 45 pts)
        surv_ratio = survivors / total_m
        score_surv = surv_ratio * 45.0

        # 2. Deathrattle and Divine Shield Insurance (0 - 25 pts)
        dr_shield_count = deathrattles + shields
        score_insurance = min(25.0, dr_shield_count * 12.0)

        # 3. Hand Refill Capacity after wipe (0 - 30 pts)
        # If player has 0 cards, wipe = immediate defeat (0 pts)
        # If player has >= 4 cards, wipe is easily mitigated (30 pts)
        score_refill = min(30.0, remaining_hand_size * 7.5)

        total_score = int(round(score_surv + score_insurance + score_refill))
        total_score = max(10, min(99, total_score))

        if total_score >= 75:
            tier = "HIGH_RESILIENCE"
            badge = f"🛡️ 韧性 {total_score}/100 (抗灭高韧)"
            verdict = (
                f"🛡️ 场面抗反扑韧性极高 ({total_score}分): "
                f"预计【{aoe_info['name']}】下可保留 {survivors}/{total_m} 具生力军，"
                f"手牌余 {remaining_hand_size} 张足以保障长效续航。"
            )
        elif total_score >= 50:
            tier = "BALANCED"
            badge = f"⚖️ 韧性 {total_score}/100 (均势适中)"
            verdict = (
                f"⚖️ 场面韧性中等 ({total_score}分): "
                f"若遭【{aoe_info['name']}】将有 {total_m - survivors} 个随从阵亡，"
                f"建议利用手牌 ({remaining_hand_size}张) 稳住下一轮返场。"
            )
        else:
            tier = "VULNERABLE_RISK"
            badge = f"⚠️ 韧性 {total_score}/100 (过铺脆弱)"
            verdict = (
                f"⚠️ 场面极度脆弱 ({total_score}分): "
                f"多数随从血量 ≤{aoe_dmg}，且手牌仅余 {remaining_hand_size} 张！"
                f"若被【{aoe_info['name']}】清场将面临空场断手牌死局，请勿盲目投入全部资源！"
            )

        return BoardResilienceReport(
            resilience_score=total_score,
            resilience_tier=tier,
            badge_text=badge,
            wipe_survivor_count=survivors,
            total_minions_count=total_m,
            deathrattle_count=deathrattles,
            divine_shield_count=shields,
            hand_refill_count=remaining_hand_size,
            detailed_verdict=verdict,
        )
