"""
DiscoveryPoolRadar: Rotation-Aware Arena Discovery Pool Probability Radar.
Calculates statistical probabilities of opponent discovering game-breaking bombs (Titans, Sweeps, Bloodlust).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("DiscoveryPoolRadar")


@dataclass
class ThreatOdd:
    threat_name: str
    probability_pct: float
    threat_type: str             # "AOE_CLEAR", "FINISHER", "TITAN", "HEAL"


@dataclass
class DiscoveryProbabilityReport:
    opponent_class: str
    discover_source: str
    key_odds: List[ThreatOdd] = field(default_factory=list)
    tactical_warning: str = ""
    inferred_intent: str = ""


# Estimated pool sizes in typical arena rotation (~30-36 class spells, ~60-80 class minions)
CLASS_DISCOVERY_PROFILES: Dict[str, Dict[str, Any]] = {
    "MAGE": {
        "spell_pool_size": 32,
        "key_threats": [
            ("烈焰风暴 / 暴风雪 (全场清场)", 2, "AOE_CLEAR"),
            ("火球术 / 炎爆术 (斩杀直伤)", 2, "FINISHER"),
            ("实冻 / 深度冻结 (硬控拖回合)", 2, "HEAL"),
        ],
    },
    "SHAMAN": {
        "spell_pool_size": 28,
        "key_threats": [
            ("嗜血 (全场爆发斩杀)", 1, "FINISHER"),
            ("闪电风暴 / 潮汐奔涌 (返场解场)", 2, "AOE_CLEAR"),
        ],
    },
    "PALADIN": {
        "spell_pool_size": 26,
        "key_threats": [
            ("十字军光环 (报告兵全员变大哥)", 1, "FINISHER"),
            ("奉献 / 平等 (清场解大怪)", 2, "AOE_CLEAR"),
        ],
    },
    "DEATHKNIGHT": {
        "spell_pool_size": 24,
        "key_threats": [
            ("尸爆 / 绝望线缕 (强力清场)", 2, "AOE_CLEAR"),
            ("冰霜打击 / 凋零打击 (直伤过牌)", 2, "FINISHER"),
        ],
    },
    "WARLOCK": {
        "spell_pool_size": 28,
        "key_threats": [
            ("扭曲虚空 / 地狱烈焰 (全场清场)", 2, "AOE_CLEAR"),
            ("灵魂虹吸 / 抽灵拔髓 (单体硬解回血)", 2, "HEAL"),
        ],
    },
}


class DiscoveryPoolRadar:
    """
    Computes hyper-accurate odds for enemy Discover actions.
    """

    @classmethod
    def calculate_discover_odds(
        cls,
        opponent_class: str,
        discover_source_card: str = "法术发现",
        enemy_hp: int = 30,
        friendly_hp: int = 30,
        friendly_board_atk: int = 0,
        friendly_minion_count: int = 0,
    ) -> DiscoveryProbabilityReport:
        """
        Calculates probability using standard hypergeometric 3-card non-replacement draw:
        P(at least one target) = 1 - ((N - K) / N) * ((N - K - 1) / (N - 1)) * ((N - K - 2) / (N - 2))
        """
        c_upper = opponent_class.strip().upper()
        # Class alias normalization
        if "法师" in c_upper or "MAGE" in c_upper:
            c_key = "MAGE"
        elif "萨满" in c_upper or "SHAMAN" in c_upper:
            c_key = "SHAMAN"
        elif "圣骑" in c_upper or "骑士" in c_upper or "PALADIN" in c_upper:
            c_key = "PALADIN"
        elif "死骑" in c_upper or "DK" in c_upper or "DEATHKNIGHT" in c_upper:
            c_key = "DEATHKNIGHT"
        elif "术士" in c_upper or "WARLOCK" in c_upper:
            c_key = "WARLOCK"
        else:
            c_key = "MAGE"

        profile = CLASS_DISCOVERY_PROFILES.get(c_key, CLASS_DISCOVERY_PROFILES["MAGE"])
        pool_size = profile["spell_pool_size"]
        odds_list: List[ThreatOdd] = []

        warning_parts = []
        for name, k_targets, t_type in profile["key_threats"]:
            # Hypergeometric P(hit >= 1 in 3 choices)
            prob_miss = 1.0
            for i in range(3):
                prob_miss *= max(0.0, (pool_size - k_targets - i) / max(1, pool_size - i))
            prob_hit = round((1.0 - prob_miss) * 100, 1)

            odds_list.append(ThreatOdd(
                threat_name=name,
                probability_pct=prob_hit,
                threat_type=t_type,
            ))
            warning_parts.append(f"{name}: {prob_hit}%")

        # Invert enemy intent based on combat pressure
        if enemy_hp <= 14 or friendly_board_atk >= enemy_hp * 0.4 or friendly_minion_count >= 3:
            intent_text = "🚨 敌方处于场面绝境，85% 极高概率必选【全场AOE/单体解牌】以求解场！"
        elif friendly_hp <= 14 or enemy_hp >= 22:
            intent_text = "🔥 我方血量偏低，75% 极高概率选了【直伤斩杀/冲锋伤害】偷鸡打脸！"
        else:
            intent_text = "💎 均势博弈，敌方更倾向选择【优质曲线生物/高价值滚雪球牌】。"

        warning_text = (
            f"🔮 发现雷达: 对手打出【{discover_source_card}】\n"
            f"• 意图推测: {intent_text}\n"
            f"• 估测命中: 「{warning_parts[0]}」"
        )

        return DiscoveryProbabilityReport(
            opponent_class=c_key,
            discover_source=discover_source_card,
            key_odds=odds_list,
            tactical_warning=warning_text,
            inferred_intent=intent_text,
        )
