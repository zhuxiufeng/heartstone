"""
OpponentPunishEnvelope: Opponent Next-Turn Worst-Case Punish Envelope & Safe HP Ceiling (敌方下轮极限威慑包络线).
Calculates theoretical maximum enemy burst face damage, maximum single-target removal damage,
and the safe minion health ceiling required to survive opponent's next turn response.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("OpponentPunishEnvelope")


@dataclass
class OpponentPunishEnvelope:
    opponent_class: str
    next_turn_mana: int
    max_burst_face: int
    max_single_removal_dmg: int
    max_aoe_dmg: int
    signature_single_spell: str
    signature_aoe_spell: str
    safe_minion_hp_threshold: int
    envelope_badge: str
    tactical_directive: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opponent_class": self.opponent_class,
            "next_turn_mana": self.next_turn_mana,
            "max_burst_face": self.max_burst_face,
            "max_single_removal_dmg": self.max_single_removal_dmg,
            "max_aoe_dmg": self.max_aoe_dmg,
            "signature_single_spell": self.signature_single_spell,
            "signature_aoe_spell": self.signature_aoe_spell,
            "safe_minion_hp_threshold": self.safe_minion_hp_threshold,
            "envelope_badge": self.envelope_badge,
            "tactical_directive": self.tactical_directive,
        }


# Signature removal and burst damages by class and mana tier
CLASS_PUNISH_PROFILES: Dict[str, Dict[str, Any]] = {
    "MAGE": {
        "single_removals": [(2, 3, "寒冰箭"), (4, 6, "火球术")],
        "aoes": [(7, 4, "烈焰风暴"), (6, 2, "暴风雪"), (3, 1, "奥术散射")],
        "burst_spells": [(4, 6, "火球术"), (2, 3, "寒冰箭")],
        "hero_power_dmg": 1,
    },
    "HUNTER": {
        "single_removals": [(3, 5, "杀戮命令"), (2, 3, "快速射击")],
        "aoes": [(6, 2, "凶猛狂暴"), (4, 2, "侧翼打击")],
        "burst_spells": [(3, 5, "杀戮命令"), (2, 3, "快速射击")],
        "hero_power_dmg": 2,
    },
    "PALADIN": {
        "single_removals": [(4, 4, "真银圣剑"), (3, 3, "愤怒之锤")],
        "aoes": [(4, 2, "奉献")],
        "burst_spells": [(4, 4, "真银圣剑"), (6, 6, "王者祝福buff")],
        "hero_power_dmg": 0,
    },
    "WARRIOR": {
        "single_removals": [(1, 999, "斩杀"), (2, 5, "盾牌猛击"), (4, 4, "库卡隆精英卫士")],
        "aoes": [(5, 999, "绝命乱斗"), (3, 1, "全场旋风斩")],
        "burst_spells": [(4, 4, "库卡隆精英卫士"), (2, 2, "英勇打击")],
        "hero_power_dmg": 0,
    },
    "PRIEST": {
        "single_removals": [(2, 999, "暗言术：灭"), (1, 3, "神圣惩击")],
        "aoes": [(5, 999, "暗言术：毁"), (6, 3, "神圣新星")],
        "burst_spells": [(1, 3, "神圣惩击")],
        "hero_power_dmg": 0,
    },
    "ROGUE": {
        "single_removals": [(2, 4, "刺骨"), (5, 999, "刺杀")],
        "aoes": [(2, 1, "刀扇")],
        "burst_spells": [(2, 4, "刺骨"), (3, 3, "毁灭之刃")],
        "hero_power_dmg": 1,
    },
    "SHAMAN": {
        "single_removals": [(1, 3, "闪电箭"), (3, 999, "妖术")],
        "aoes": [(3, 2, "闪电风暴")],
        "burst_spells": [(1, 3, "闪电箭"), (3, 5, "熔岩爆裂")],
        "hero_power_dmg": 0,
    },
    "WARLOCK": {
        "single_removals": [(3, 4, "灵魂残片/吸取"), (6, 999, "灵魂虹吸")],
        "aoes": [(4, 3, "地狱烈焰"), (8, 999, "扭曲虚空")],
        "burst_spells": [(4, 3, "地狱烈焰"), (3, 4, "暗影箭")],
        "hero_power_dmg": 0,
    },
    "DRUID": {
        "single_removals": [(4, 4, "横扫"), (3, 999, "自然平衡")],
        "aoes": [(5, 2, "星辰坠落"), (4, 1, "横扫副目标")],
        "burst_spells": [(4, 4, "横扫"), (3, 4, "凶猛撕咬")],
        "hero_power_dmg": 1,
    },
    "DEMONHUNTER": {
        "single_removals": [(1, 2, "流放划击"), (3, 4, "眼棱")],
        "aoes": [(5, 3, "混乱新星")],
        "burst_spells": [(3, 4, "混沌打击/战刃"), (2, 2, "恶魔之咬")],
        "hero_power_dmg": 1,
    },
    "DEATHKNIGHT": {
        "single_removals": [(2, 3, "冰霜打击"), (5, 999, "窒息")],
        "aoes": [(5, 2, "血液沸腾"), (6, 5, "侏儒切肉者")],
        "burst_spells": [(2, 3, "冰霜打击"), (4, 4, "骨髓打击")],
        "hero_power_dmg": 1,
    },
}


class OpponentPunishEnvelopeCalculator:
    """Computes worst-case opponent punish envelope for the next turn."""

    @classmethod
    def calculate_envelope(
        cls,
        opponent_class: str,
        current_turn_mana: int,
        enemy_board_attack: int = 0,
    ) -> OpponentPunishEnvelope:
        norm_class = opponent_class.upper()
        if "法师" in norm_class or "MAGE" in norm_class:
            c_key = "MAGE"
        elif "猎人" in norm_class or "HUNTER" in norm_class:
            c_key = "HUNTER"
        elif "圣骑士" in norm_class or "PALADIN" in norm_class:
            c_key = "PALADIN"
        elif "战士" in norm_class or "WARRIOR" in norm_class:
            c_key = "WARRIOR"
        elif "牧师" in norm_class or "PRIEST" in norm_class:
            c_key = "PRIEST"
        elif "潜行者" in norm_class or "盗贼" in norm_class or "ROGUE" in norm_class:
            c_key = "ROGUE"
        elif "萨满" in norm_class or "SHAMAN" in norm_class:
            c_key = "SHAMAN"
        elif "术士" in norm_class or "WARLOCK" in norm_class:
            c_key = "WARLOCK"
        elif "德鲁伊" in norm_class or "DRUID" in norm_class:
            c_key = "DRUID"
        elif "恶魔猎手" in norm_class or "DEMONHUNTER" in norm_class:
            c_key = "DEMONHUNTER"
        elif "死亡骑士" in norm_class or "死骑" in norm_class or "DEATHKNIGHT" in norm_class:
            c_key = "DEATHKNIGHT"
        else:
            c_key = "MAGE"

        profile = CLASS_PUNISH_PROFILES.get(c_key, CLASS_PUNISH_PROFILES["MAGE"])
        next_mana = min(10, current_turn_mana + 1)

        # 1. Single-target removal capacity
        valid_singles = [s for s in profile["single_removals"] if s[0] <= next_mana]
        if valid_singles:
            best_single = max(valid_singles, key=lambda s: s[1])
            max_single_dmg = best_single[1]
            single_name = best_single[2]
        else:
            max_single_dmg = profile.get("hero_power_dmg", 1)
            single_name = "英雄技能"

        # 2. AOE capacity
        valid_aoes = [a for a in profile["aoes"] if a[0] <= next_mana]
        if valid_aoes:
            best_aoe = max(valid_aoes, key=lambda a: a[1])
            max_aoe_dmg = best_aoe[1]
            aoe_name = best_aoe[2]
        else:
            max_aoe_dmg = 0
            aoe_name = "无群体清场"

        # 3. Burst face capacity
        valid_bursts = [b for b in profile["burst_spells"] if b[0] <= next_mana]
        burst_spell_dmg = sum(b[1] for b in valid_bursts[:1]) if valid_bursts else 0
        hero_power_dmg = profile.get("hero_power_dmg", 0) if (next_mana - (valid_bursts[0][0] if valid_bursts else 0)) >= 2 else 0
        max_burst_face = enemy_board_attack + burst_spell_dmg + hero_power_dmg

        # 4. Safe minion health threshold
        effective_single = max_single_dmg if max_single_dmg < 999 else 6
        safe_hp = max(effective_single + 1, max_aoe_dmg + 1)

        badge = f"🛡️ 下轮敌方威慑包络 (T{next_mana}费): 极限斩杀 {max_burst_face}点 · 单解 {single_name} ({max_single_dmg if max_single_dmg < 999 else '硬解'}点) · 安全血线 ≥{safe_hp}血"
        directive = f"下回合敌方拥有 {next_mana} 费。随从生命值保持在 {safe_hp} 点以上，可完全免除敌方单解斩杀与技能补刀威胁！"

        return OpponentPunishEnvelope(
            opponent_class=c_key,
            next_turn_mana=next_mana,
            max_burst_face=max_burst_face,
            max_single_removal_dmg=max_single_dmg,
            max_aoe_dmg=max_aoe_dmg,
            signature_single_spell=single_name,
            signature_aoe_spell=aoe_name,
            safe_minion_hp_threshold=safe_hp,
            envelope_badge=badge,
            tactical_directive=directive,
        )
