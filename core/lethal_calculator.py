"""
LethalCalculator: Analyzes board minions, hand spells, spell damage, and taunt blockers
to calculate exact available lethal damage on the current turn.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .card_db import CardDatabase, CardInfo

logger = logging.getLogger("LethalCalculator")

# Common direct damage spells and weapons
BURN_CARD_DAMAGE: Dict[str, int] = {
    # Mage
    "CS2_029": 6,   # 火球术 (Fireball)
    "CS2_024": 3,   # 寒冰箭 (Frostbolt)
    "CS2_027": 10,  # 炎爆术 (Pyroblast)
    "CS2_023": 1,   # 奥术飞弹 (Arcane Missiles)
    # Hunter
    "EX1_539": 5,   # 杀戮命令 (Kill Command)
    "DS1_185": 2,   # 奥术射击 (Arcane Shot)
    # Shaman
    "CS2_087": 3,   # 闪电箭 (Lightning Bolt)
    "EX1_238": 3,   # 闪电风暴 (min)
    "EX1_248": 2,   # 熔岩震击
    # Rogue
    "CS2_075": 3,   # 影袭 (Sinister Strike)
    "CS2_076": 2,   # 刺骨 (Eviscerate - base)
    # Paladin
    "CS2_093": 2,   # 奉献
    # Warlock
    "CS2_062": 3,   # 地狱烈焰 (Hellfire)
    "CS2_061": 3,   # 灵魂之火 (Soulfire)
}


@dataclass
class LethalResult:
    is_lethal: bool
    total_damage: int
    target_hp: int
    overkill: int
    board_damage: int
    hand_damage: int
    hero_power_damage: int
    action_steps: List[str] = field(default_factory=list)
    taunt_blockers: List[str] = field(default_factory=list)


class LethalCalculator:
    """Calculates maximum burst damage to enemy face on the active turn."""

    def __init__(self, card_db: Optional[CardDatabase] = None) -> None:
        self.card_db = card_db or CardDatabase.get_instance()

    def calculate_lethal(
        self,
        friendly_minions: List[Dict[str, Any]],  # [{"name": ..., "atk": int, "can_attack": bool, "windfury": bool}]
        enemy_taunts: List[Dict[str, Any]],      # [{"name": ..., "health": int}]
        hand_cards: List[CardInfo],
        available_mana: int,
        enemy_hp: int,
        enemy_armor: int = 0,
        hero_class: str = "MAGE",
        hero_power_available: bool = True,
        spell_damage_bonus: int = 0,
    ) -> LethalResult:
        """
        Calculates whether current resources yield guaranteed lethal damage.
        """
        target_effective_hp = enemy_hp + enemy_armor
        action_steps: List[str] = []
        taunt_names = [t.get("name", "嘲讽随从") for t in enemy_taunts]

        # 1. Total Taunt Health to break through
        total_taunt_hp = sum(t.get("health", 0) for t in enemy_taunts)

        # 2. Board minion damage
        board_damage = 0
        minions_for_face: List[str] = []

        for m in friendly_minions:
            if m.get("can_attack", True):
                atk = m.get("atk", 0)
                name = m.get("name", "随从")
                mult = 2 if m.get("windfury", False) else 1
                total_m_atk = atk * mult
                board_damage += total_m_atk
                minions_for_face.append(f"{name} ({total_m_atk}点)")

        # Subtract taunt barrier from board damage if taunts exist
        effective_board_face_damage = max(0, board_damage - total_taunt_hp)
        if total_taunt_hp > 0:
            if board_damage >= total_taunt_hp:
                action_steps.append(f"先用随从击杀敌方嘲讽 ({total_taunt_hp}血)")
            else:
                action_steps.append(f"随从无法全清嘲讽，剩余嘲讽阻挡脸伤")

        if effective_board_face_damage > 0:
            action_steps.append(f"场面剩余随从走脸: +{effective_board_face_damage} 点")

        # 3. Hand Burn Spells & Direct Damage
        hand_damage = 0
        current_mana = available_mana

        # Sort spells by damage-per-mana efficiency
        spells_available = []
        for c in hand_cards:
            dmg = BURN_CARD_DAMAGE.get(c.id, 0)
            if dmg > 0 and c.cost <= current_mana:
                # Add spell damage bonus
                real_dmg = dmg + spell_damage_bonus
                spells_available.append((c, real_dmg))

        # Greedy choice of affordable burn
        spells_available.sort(key=lambda s: s[1] / max(1, s[0].cost), reverse=True)
        for card, dmg in spells_available:
            if card.cost <= current_mana:
                hand_damage += dmg
                current_mana -= card.cost
                action_steps.append(f"打出法术 【{card.name}】 ({card.cost}费): +{dmg} 点")

        # 4. Hero Power Burst
        hp_damage = 0
        if hero_power_available and current_mana >= 2:
            if hero_class.upper() in ["MAGE", "HUNTER", "DRUID", "DEMONHUNTER"]:
                hp_val = 2 if hero_class.upper() == "HUNTER" else 1
                hp_damage = hp_val
                current_mana -= 2
                action_steps.append(f"使用英雄技能点脸: +{hp_damage} 点")

        # 5. Total damage calculation
        total_damage = effective_board_face_damage + hand_damage + hp_damage
        is_lethal = total_damage >= target_effective_hp
        overkill = max(0, total_damage - target_effective_hp)

        return LethalResult(
            is_lethal=is_lethal,
            total_damage=total_damage,
            target_hp=target_effective_hp,
            overkill=overkill,
            board_damage=effective_board_face_damage,
            hand_damage=hand_damage,
            hero_power_damage=hp_damage,
            action_steps=action_steps,
            taunt_blockers=taunt_names,
        )
