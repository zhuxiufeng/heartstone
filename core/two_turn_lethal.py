"""
TwoTurnLethalEngine: Anticipates unavoidable 2-turn lethal / checkmate setups.
Enables pro-level transition from defensive trading to lethal checkmate before enemy can stabilize.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .card_db import CardDatabase, CardInfo
from .lethal_calculator import BURN_CARD_DAMAGE

logger = logging.getLogger("TwoTurnLethalEngine")


@dataclass
class TwoTurnLethalPlan:
    is_two_turn_lethal: bool
    turn1_face_damage: int
    enemy_residual_hp: int
    projected_turn2_damage: int
    total_2turn_damage: int
    confidence: float  # 0.0 to 1.0 based on enemy hand size and class
    recommendation: str = ""
    breakdown: List[str] = field(default_factory=list)


class TwoTurnLethalEngine:
    """
    Evaluates whether pushing all accessible face damage on Turn 1 guarantees
    or near-guarantees a lethal checkmate on Turn 2.
    """

    HEAL_ARMOR_CLASSES = {"PRIEST", "牧师", "WARRIOR", "战士", "DEATHKNIGHT", "死亡骑士"}

    @classmethod
    def evaluate_two_turn_lethal(
        cls,
        friendly_minions: List[Dict[str, Any]],  # [{"name": str, "atk": int, "health": int, "can_attack": bool}]
        enemy_taunts: List[Dict[str, Any]],      # [{"name": str, "health": int}]
        hand_cards: List[CardInfo],
        available_mana: int,
        enemy_hp: int,
        enemy_armor: int = 0,
        enemy_hand_count: int = 3,
        enemy_class: str = "MAGE",
        hero_power_damage: int = 0,
        friendly_hp: int = 30,
        enemy_board_attack: int = 0,
    ) -> TwoTurnLethalPlan:
        """
        Calculates 2-turn checkmate viability:
        1. Turn 1: Max face damage after breaking taunts.
        2. Enemy Turn: Can enemy kill us first? (Counter-lethal check).
        3. Turn 2: Surviving board attack + next turn hero power + remaining hand burn.
        """
        enemy_effective_hp = enemy_hp + enemy_armor
        if enemy_effective_hp <= 0:
            return TwoTurnLethalPlan(
                is_two_turn_lethal=False,
                turn1_face_damage=0,
                enemy_residual_hp=0,
                projected_turn2_damage=0,
                total_2turn_damage=0,
                confidence=0.0,
                recommendation="敌方已无生命值",
            )

        # 1. Break taunt with minimum necessary minion damage
        total_taunt_hp = sum(t.get("health", 0) for t in enemy_taunts)
        ready_minions = [m for m in friendly_minions if m.get("can_attack", True)]
        
        # Sort minions by attack ascending to trade small minions into taunts efficiently
        sorted_minions = sorted(ready_minions, key=lambda m: m.get("atk", 0))
        remaining_taunt_hp = total_taunt_hp
        face_minions: List[Dict[str, Any]] = []

        for m in sorted_minions:
            m_atk = m.get("atk", 0)
            if remaining_taunt_hp > 0:
                remaining_taunt_hp -= m_atk
            else:
                face_minions.append(m)

        # If taunts cannot be cleared by board minions, 2-turn lethal via face swing is compromised
        if remaining_taunt_hp > 0:
            return TwoTurnLethalPlan(
                is_two_turn_lethal=False,
                turn1_face_damage=0,
                enemy_residual_hp=enemy_effective_hp,
                projected_turn2_damage=0,
                total_2turn_damage=0,
                confidence=0.0,
                recommendation="敌方嘲讽血量过高，无法穿透走脸叫杀",
            )

        # Calculate Turn 1 board face damage
        t1_board_damage = sum(m.get("atk", 0) for m in face_minions)

        # Turn 1 hand burn spells that fit within available mana
        t1_hand_damage = 0
        mana_budget = available_mana
        used_cards: List[str] = []
        for c in hand_cards:
            cid = getattr(c, "id", getattr(c, "card_id", ""))
            burn = BURN_CARD_DAMAGE.get(cid, 0)
            if burn > 0 and c.cost <= mana_budget:
                t1_hand_damage += burn
                mana_budget -= c.cost
                used_cards.append(c.name)

        # Add hero power if mana permits
        t1_hp_dmg = 0
        if mana_budget >= 2 and hero_power_damage > 0:
            t1_hp_dmg = hero_power_damage
            mana_budget -= 2

        turn1_total = t1_board_damage + t1_hand_damage + t1_hp_dmg
        enemy_residual_hp = enemy_effective_hp - turn1_total

        # If already lethal on Turn 1, delegate to 1-turn lethal
        if enemy_residual_hp <= 0:
            return TwoTurnLethalPlan(
                is_two_turn_lethal=False,
                turn1_face_damage=turn1_total,
                enemy_residual_hp=0,
                projected_turn2_damage=0,
                total_2turn_damage=turn1_total,
                confidence=1.0,
                recommendation="当前回合已直接达成斩杀！",
            )

        # 2. Counter-lethal Safety Check
        # If enemy current board attack can kill friendly hero next turn, going face is suicidal
        if enemy_board_attack >= friendly_hp:
            return TwoTurnLethalPlan(
                is_two_turn_lethal=False,
                turn1_face_damage=turn1_total,
                enemy_residual_hp=enemy_residual_hp,
                projected_turn2_damage=0,
                total_2turn_damage=turn1_total,
                confidence=0.1,
                recommendation=f"⚠️ 对手场攻({enemy_board_attack}点)已对我方({friendly_hp}血)形成斩杀，不可冒进走脸叫杀！",
            )

        # 3. Project Turn 2 Available Damage
        # Assuming our face minions survive (discounting small percentage based on enemy hand)
        t2_board_damage = sum(m.get("atk", 0) for m in face_minions)
        t2_hero_power = hero_power_damage  # Assuming hero power usable next turn

        # Unused hand burn playable next turn with refreshed mana (~Turn N+1)
        t2_hand_damage = 0
        for c in hand_cards:
            if c.name not in used_cards:
                cid = getattr(c, "id", getattr(c, "card_id", ""))
                burn = BURN_CARD_DAMAGE.get(cid, 0)
                if burn > 0:
                    t2_hand_damage += burn

        turn2_projected = t2_board_damage + t2_hero_power + t2_hand_damage
        total_2turn = turn1_total + turn2_projected

        # Check if 2-turn lethal threshold reached
        if turn2_projected >= enemy_residual_hp:
            # Confidence score calculation
            base_confidence = 0.85
            # Penalty if enemy can heal or armor
            if enemy_class.upper() in cls.HEAL_ARMOR_CLASSES:
                base_confidence -= 0.15
            # Penalty if enemy has large hand (potential taunt / heal)
            if enemy_hand_count >= 5:
                base_confidence -= 0.20
            elif enemy_hand_count <= 2:
                base_confidence += 0.10

            confidence = max(0.2, min(0.95, base_confidence))

            breakdown = [
                f"T1打脸伤害: {turn1_total}点 (场攻{t1_board_damage} + 法术{t1_hand_damage} + 技能{t1_hp_dmg})",
                f"T1后敌方残血: {enemy_residual_hp}点",
                f"T2推演保底伤害: {turn2_projected}点 (场攻{t2_board_damage} + 法术{t2_hand_damage} + 技能{t2_hero_power})",
                f"敌方手牌: {enemy_hand_count}张 (翻盘概率估算: {(1-confidence)*100:.0f}%)",
            ]

            recommendation = (
                f"🔥 两回合叫杀成立 (胜率把握 {confidence*100:.0f}%)！"
                f"本轮全员走脸压至 {enemy_residual_hp} 血，下轮保底场攻 {turn2_projected} 点直接终结对手！"
            )

            return TwoTurnLethalPlan(
                is_two_turn_lethal=True,
                turn1_face_damage=turn1_total,
                enemy_residual_hp=enemy_residual_hp,
                projected_turn2_damage=turn2_projected,
                total_2turn_damage=total_2turn,
                confidence=confidence,
                recommendation=recommendation,
                breakdown=breakdown,
            )

        return TwoTurnLethalPlan(
            is_two_turn_lethal=False,
            turn1_face_damage=turn1_total,
            enemy_residual_hp=enemy_residual_hp,
            projected_turn2_damage=turn2_projected,
            total_2turn_damage=total_2turn,
            confidence=0.0,
            recommendation="两回合伤害不足以叫杀，维持控场交换",
        )
