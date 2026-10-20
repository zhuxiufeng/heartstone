"""
MatchupMicroMetaEngine: Matchup-Specific Micro-Meta Synergy & Arena Rotation Meta Evaluator.
Provides dynamic card evaluation score adjustments (+12 to -12) based on opponent class archetypes
(Aggro, Control, Value Midrange) and current Arena Rotation threat profiles.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .card_db import CardInfo

logger = logging.getLogger("MatchupMicroMeta")

# High-frequency arena meta classes in current rotation (Tier 1 to Tier 3)
ARENA_META_CLASS_WEIGHTS: Dict[str, float] = {
    "MAGE": 1.25,        # High frequency spell/discover meta
    "DEATHKNIGHT": 1.20,  # High frequency corpse/board presence
    "PALADIN": 1.15,     # High frequency divine shield tempo
    "HUNTER": 1.10,      # Aggressive face pressure
    "WARLOCK": 1.05,     # Self-damage & hand advantage
    "ROGUE": 1.00,       # Combo tempo
    "SHAMAN": 0.95,      # Elementals & totems
    "PRIEST": 0.90,      # Attritional control
    "WARRIOR": 0.90,     # Armor & taunt control
    "DRUID": 0.85,       # Ramp & tokens
    "DEMONHUNTER": 0.85, # Aggro rush
}


@dataclass
class MatchupDeltaResult:
    score_delta: int
    meta_tag: str
    explanation: str


class MatchupMicroMetaEngine:
    """Calculates granular matchup-specific card value variations."""

    AGGRO_CLASSES = {"HUNTER", "PALADIN", "DEMONHUNTER", "ROGUE"}
    CONTROL_CLASSES = {"PRIEST", "WARRIOR", "DEATHKNIGHT", "WARLOCK"}
    FLEXIBLE_CLASSES = {"MAGE", "SHAMAN", "DRUID"}

    @classmethod
    def evaluate_card_matchup_delta(
        cls,
        card: CardInfo,
        opponent_class: str,
    ) -> MatchupDeltaResult:
        """
        Calculates score delta for a card against a specific opponent class.
        e.g. AOE/Taunts against Hunter/Paladin yield +10 score.
             Value/Greedy cards against Priest/Warrior yield +8 score.
        """
        opp = (opponent_class or "UNKNOWN").upper().strip()
        c_cost = getattr(card, "cost", 2)
        c_text = (getattr(card, "clean_text", "") or getattr(card, "text", "") or "").lower()
        c_name = getattr(card, "name", "")
        c_type = (getattr(card, "card_type", "") or "").upper()

        is_aoe = any(kw in c_text or kw in c_name for kw in ["全场", "所有", "随机对所有", "消灭所有", "暴风雪", "烈焰风暴", "横扫", "乱斗", "奉献", "奉献"])
        is_taunt = "嘲讽" in c_text or "TAUNT" in getattr(card, "mechanics", [])
        is_rush = "突袭" in c_text or "冲锋" in c_text or "RUSH" in getattr(card, "mechanics", [])
        is_draw = any(kw in c_text for kw in ["抽", "过牌", "发现", "置入你的手牌"])
        is_heal = any(kw in c_text for kw in ["恢复", "治疗", "获得护甲", "吸血"])

        delta = 0
        tag = ""
        exp = ""

        if opp in cls.AGGRO_CLASSES:
            # Against Aggro / Fast Tempo: Speed and stabilization reign supreme
            if is_aoe:
                delta += 10
                tag = "🔥 降速清场克星"
                exp = f"对阵快节奏【{opponent_class}】：AOE清场能直接瓦解对手压制链(+10分)"
            elif is_taunt or is_rush:
                delta += 8
                tag = "🛡️ 护脸筑墙神器"
                exp = f"对阵快节奏【{opponent_class}】：嘲讽/突袭稳固血线，阻止直伤斩杀(+8分)"
            elif is_heal:
                delta += 6
                tag = "❤️ 续命脱险保障"
                exp = f"对阵【{opponent_class}】：生命回复提升斩杀容错(+6分)"
            elif c_type == "MINION" and c_cost in (1, 2):
                delta += 5
                tag = "⚡ 前期争夺先机"
                exp = f"对阵【{opponent_class}】：低费站场防止开局被滚雪球(+5分)"
            elif c_cost >= 7 and not is_aoe:
                delta -= 10
                tag = "⚠️ 笨重大哥卡手陷阱"
                exp = f"对阵高攻速【{opponent_class}】：7+费笨重大哥极易卡死在手牌中(-10分)"

        elif opp in cls.CONTROL_CLASSES:
            # Against Control / Attrition: Resource endurance and bomb finishers win
            if is_draw:
                delta += 10
                tag = "🔮 消耗战续航核心"
                exp = f"对阵控制型【{opponent_class}】：过牌与发现能确保消耗战手牌不断档(+10分)"
            elif c_cost >= 7:
                delta += 8
                tag = "👑 破防终结重锤"
                exp = f"对阵控制型【{opponent_class}】：高费高质量随从可施加致命制胜压力(+8分)"
            elif c_cost == 1 and not is_draw:
                delta -= 6
                tag = "💤 消耗战低效杂毛"
                exp = f"对阵控制型【{opponent_class}】：1费白板随从后期价值极低(-6分)"

        elif opp in cls.FLEXIBLE_CLASSES:
            # Flexible classes (Mage/Shaman/Druid): Balanced tempo & board presence
            if is_draw and c_cost <= 4:
                delta += 5
                tag = "📈 润滑展开"
                exp = f"对阵法系【{opponent_class}】：轻量过牌保持法力连贯(+5分)"
            elif is_rush:
                delta += 6
                tag = "🐗 抢占先手主动"
                exp = f"对阵【{opponent_class}】：突袭随从能即时反解关键战吼怪(+6分)"

        return MatchupDeltaResult(
            score_delta=max(-15, min(15, delta)),
            meta_tag=tag or "⚖️ 均势适配",
            explanation=exp or f"面对【{opponent_class}】表现平稳",
        )

    @classmethod
    def evaluate_draft_meta_bias(
        cls,
        hero_class: str,
        card: CardInfo,
    ) -> MatchupDeltaResult:
        """
        Calculates meta-frequency weighted compensation during Arena Draft.
        Gives proactive anti-Mage / anti-DK adjustments since they represent >50% of high-win arenas.
        """
        # Anti-Mage (AOE protection & burst survival) and Anti-DK (corpse wipe prevention)
        c_text = (getattr(card, "clean_text", "") or getattr(card, "text", "") or "").lower()
        c_cost = getattr(card, "cost", 2)
        c_type = (getattr(card, "card_type", "") or "").upper()

        delta = 0
        tag = ""
        exp = ""

        # Check deathrattle (Anti-Mage AOE)
        if "亡语" in c_text or "DEATHRATTLE" in getattr(card, "mechanics", []):
            delta += 7
            tag = "💀 竞技场主流防清场"
            exp = "当前竞技场法师/死骑清场高频，亡语生物能极大提升赖场与防AOE韧性(+7分)"
        elif any(kw in c_text for kw in ["消灭", "变形", "暗言术", "妖术"]):
            delta += 8
            tag = "🗡️ 竞技场环境硬解急需"
            exp = "当前竞技场大身材随从泛滥，优质单体硬解是高胜必备战术组件(+8分)"
        elif c_cost in (2, 3) and c_type == "MINION" and getattr(card, "health", 0) >= 3:
            delta += 4
            tag = "🛡️ 3血避开补刀"
            exp = "3血及以上前期随从可免疫法师/盗贼英雄技能补刀(+4分)"

        return MatchupDeltaResult(
            score_delta=delta,
            meta_tag=tag or "🌐 环境标准",
            explanation=exp or "契合当前竞技场轮换环境",
        )
