"""
TradeOptimizer: Calculates optimal minion trading combinations and tactical actions.
Evaluates favorable trades (白吃), equal trades, taunt breaking, and face damage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    from .ping_protector import PingProtector
except ImportError:
    from ping_protector import PingProtector

logger = logging.getLogger("TradeOptimizer")


@dataclass
class MinionState:
    name: str
    attack: int
    health: int
    divine_shield: bool = False
    taunt: bool = False
    poisonous: bool = False
    windfury: bool = False
    can_attack: bool = True
    entity_id: int = 0


@dataclass
class TradeAction:
    attacker_name: str
    target_name: str
    action_type: str        # "favorable_trade" (白吃), "equal_trade" (均势对换), "taunt_break" (破嘲讽), "face" (走脸)
    damage_dealt: int
    attacker_survives: bool
    attacker_remaining_hp: int
    target_killed: bool
    priority_score: float
    description: str


@dataclass
class TradePlan:
    actions: List[TradeAction]
    total_face_damage: int
    retained_friendly_attack: int
    retained_friendly_health: int
    remaining_enemy_minions: int
    tactical_summary: str


class TradeOptimizer:
    """Calculates the best tactical combat trades between friendly and enemy minions."""

    def __init__(self) -> None:
        pass

    def calculate_trades(
        self,
        friendly_minions: List[Dict[str, Any]],
        enemy_minions: List[Dict[str, Any]],
        enemy_hero_health: int = 30,
        face_aggression: float = 1.0,  # >1.0 prioritizes face; <1.0 prioritizes board clear
        opponent_class: str = "",
    ) -> TradePlan:
        """
        Determines the optimal attack assignments for friendly minions.
        Respects Taunt rules, divine shields, poison, and value retention.
        """
        # Parse minions
        friendlies: List[MinionState] = []
        for idx, m in enumerate(friendly_minions):
            if m.get("attack", 0) <= 0:
                continue
            friendlies.append(MinionState(
                name=m.get("name", f"随从#{idx+1}"),
                attack=int(m.get("attack", 0)),
                health=int(m.get("health", 1)),
                divine_shield=bool(m.get("divine_shield", False)),
                taunt=bool(m.get("taunt", False)),
                poisonous=bool(m.get("poisonous", False)),
                windfury=bool(m.get("windfury", False)),
                can_attack=bool(m.get("can_attack", True)),
                entity_id=m.get("entity_id", idx),
            ))

        enemies: List[MinionState] = []
        for idx, m in enumerate(enemy_minions):
            enemies.append(MinionState(
                name=m.get("name", f"敌方随从#{idx+1}"),
                attack=int(m.get("attack", 0)),
                health=int(m.get("health", 1)),
                divine_shield=bool(m.get("divine_shield", False)),
                taunt=bool(m.get("taunt", False)),
                poisonous=bool(m.get("poisonous", False)),
                windfury=bool(m.get("windfury", False)),
                entity_id=m.get("entity_id", idx + 100),
            ))

        # Check total board attack vs enemy hero health (instant face lethal check)
        total_friendly_atk = sum(f.attack for f in friendlies if f.can_attack)
        has_taunts = any(e.taunt for e in enemies)

        if not has_taunts and total_friendly_atk >= enemy_hero_health and enemy_hero_health > 0:
            # Full Face Lethal!
            lethal_actions = [
                TradeAction(
                    attacker_name=f"{f.name} ({f.attack}/{f.health})",
                    target_name="敌方英雄",
                    action_type="face",
                    damage_dealt=f.attack,
                    attacker_survives=True,
                    attacker_remaining_hp=f.health,
                    target_killed=True,
                    priority_score=999.0,
                    description=f"【绝杀走脸】攻击敌方英雄打出 {f.attack} 点伤害",
                )
                for f in friendlies if f.can_attack
            ]
            return TradePlan(
                actions=lethal_actions,
                total_face_damage=total_friendly_atk,
                retained_friendly_attack=total_friendly_atk,
                retained_friendly_health=sum(f.health for f in friendlies),
                remaining_enemy_minions=len(enemies),
                tactical_summary=f"⚡ 发现斩杀线！全员走脸直接造成 {total_friendly_atk} 点伤害终结对局！",
            )

        # Simulation algorithm for trading
        # 1. Separate enemies into Taunts and Non-Taunts
        actions: List[TradeAction] = []
        active_friendlies = [f for f in friendlies if f.can_attack]
        # Sort attackers by attack ascending (use smaller minions to trade or pop shields first)
        active_friendlies.sort(key=lambda m: (m.attack, -m.health))

        # Copy enemy states for dynamic HP simulation
        sim_enemies = [
            MinionState(
                name=e.name,
                attack=e.attack,
                health=e.health,
                divine_shield=e.divine_shield,
                taunt=e.taunt,
                poisonous=e.poisonous,
                entity_id=e.entity_id,
            )
            for e in enemies
        ]

        total_face = 0

        # Step 1: Must clear all Taunt minions first
        for enemy in sim_enemies:
            if not enemy.taunt or enemy.health <= 0:
                continue

            # Taunt exists! Must break with available friendlies
            for f in list(active_friendlies):
                if enemy.health <= 0:
                    break

                action = self._simulate_attack(f, enemy, is_taunt=True)
                actions.append(action)
                active_friendlies.remove(f)

        # Step 2: For remaining friendlies, check for Favorable Trades (白吃) or High-Value Trades
        for enemy in sim_enemies:
            if enemy.health <= 0:
                continue

            # Look for friendly minion that can KILL this enemy while SURVIVING
            # Prefer attacker that retains highest remaining HP or takes zero damage
            best_favorable_attacker = None
            best_surplus_score = -999.0

            for f in active_friendlies:
                # Can f kill enemy?
                can_kill = (f.attack >= enemy.health or f.poisonous) and not enemy.divine_shield
                # Does f survive?
                survives = f.divine_shield or (f.health > enemy.attack and not enemy.poisonous)

                if can_kill and survives:
                    rem_hp = f.health if f.divine_shield else (f.health - enemy.attack)
                    ping_res = PingProtector.evaluate_trade_residual(
                        attacker_name=f.name,
                        attacker_atk=f.attack,
                        attacker_rem_hp=rem_hp,
                        attacker_has_shield=f.divine_shield,
                        opponent_class=opponent_class,
                    )
                    # Score = enemy value (enemy.attack) minus friendly damage taken + ping resistance score
                    surplus = (enemy.attack * 1.5) - (0 if f.divine_shield else enemy.attack) + ping_res.penalty_score
                    if surplus > best_surplus_score:
                        best_surplus_score = surplus
                        best_favorable_attacker = f

            if best_favorable_attacker and (face_aggression < 1.8):
                action = self._simulate_attack(best_favorable_attacker, enemy, is_taunt=False, opponent_class=opponent_class)
                actions.append(action)
                active_friendlies.remove(best_favorable_attacker)

        # Step 3: Check remaining threats on enemy board (high attack minions)
        sim_enemies_alive = [e for e in sim_enemies if e.health > 0]
        # Sort enemies by attack descending (kill the biggest threats first)
        sim_enemies_alive.sort(key=lambda e: (e.attack, e.health), reverse=True)

        for enemy in sim_enemies_alive:
            if enemy.health <= 0 or not active_friendlies:
                continue

            # If enemy has high threat (attack >= 4) or we are in control mode
            if enemy.attack >= 4 or face_aggression < 0.9:
                for f in list(active_friendlies):
                    if enemy.health <= 0:
                        break
                    # If f has lower attack than enemy, positive trade
                    if f.attack <= enemy.attack:
                        action = self._simulate_attack(f, enemy, is_taunt=False)
                        actions.append(action)
                        active_friendlies.remove(f)

        # Step 4: Any leftover friendlies GO FACE!
        # Check if any taunts are still alive
        taunts_still_alive = any(e.taunt and e.health > 0 for e in sim_enemies)

        for f in active_friendlies:
            if taunts_still_alive:
                # Must hit the remaining taunt
                taunt_target = next(e for e in sim_enemies if e.taunt and e.health > 0)
                action = self._simulate_attack(f, taunt_target, is_taunt=True)
                actions.append(action)
            else:
                # Go face!
                total_face += f.attack
                actions.append(TradeAction(
                    attacker_name=f"{f.name} ({f.attack}/{f.health})",
                    target_name="敌方英雄",
                    action_type="face",
                    damage_dealt=f.attack,
                    attacker_survives=True,
                    attacker_remaining_hp=f.health,
                    target_killed=False,
                    priority_score=50.0 * face_aggression,
                    description=f"【走脸压迫】攻击敌方英雄造成 {f.attack} 点伤害",
                ))

        # Calculate remaining stats
        retained_attack = sum(a.damage_dealt for a in actions if a.attacker_survives)
        retained_health = sum(a.attacker_remaining_hp for a in actions if a.attacker_survives)
        remaining_enemies = sum(1 for e in sim_enemies if e.health > 0)

        # Build summary
        favorable_count = sum(1 for a in actions if a.action_type == "favorable_trade")
        cleared_count = sum(1 for a in actions if a.target_killed and a.action_type != "face")

        summary_parts = []
        if favorable_count > 0:
            summary_parts.append(f"🎯 实现 {favorable_count} 次无伤/白吃交换")
        if cleared_count > 0:
            summary_parts.append(f"清理敌方 {cleared_count} 个随从")
        if total_face > 0:
            summary_parts.append(f"走脸造成 {total_face} 点伤害")
        if remaining_enemies == 0 and len(enemies) > 0:
            summary_parts.append("✨ 敌方场面全清！")

        summary_text = "；".join(summary_parts) if summary_parts else "保持场面蓄势待发"

        return TradePlan(
            actions=actions,
            total_face_damage=total_face,
            retained_friendly_attack=retained_attack,
            retained_friendly_health=retained_health,
            remaining_enemy_minions=remaining_enemies,
            tactical_summary=summary_text,
        )

    def _simulate_attack(
        self,
        attacker: MinionState,
        target: MinionState,
        is_taunt: bool = False,
        opponent_class: str = "",
    ) -> TradeAction:
        """Simulates single attack, updating target HP and returning TradeAction."""
        # 1. Divine shield interaction
        target_dmg = attacker.attack
        attacker_dmg = target.attack

        if target.divine_shield:
            target.divine_shield = False
            effective_target_dmg = 0
        else:
            effective_target_dmg = target_dmg

        if attacker.divine_shield:
            attacker.divine_shield = False
            effective_attacker_dmg = 0
        else:
            effective_attacker_dmg = attacker_dmg

        # Apply damage
        if attacker.poisonous and effective_target_dmg > 0:
            target.health = 0
        else:
            target.health -= effective_target_dmg

        attacker_remaining_hp = attacker.health - effective_attacker_dmg
        attacker_survives = attacker_remaining_hp > 0
        target_killed = target.health <= 0

        # Ping safety tag
        ping_tag = ""
        if opponent_class and PingProtector.is_ping_class(opponent_class) and attacker_survives:
            if attacker_remaining_hp == 1:
                ping_tag = " (⚠️ 留1血防技能补刀)"
            elif attacker_remaining_hp >= 2:
                ping_tag = " (🛡️ 残血≥2防补刀)"

        # Classify action type
        if is_taunt:
            action_type = "taunt_break"
            desc = f"【破嘲讽】{attacker.name} 攻击嘲讽怪 {target.name}{ping_tag}"
        elif attacker_survives and target_killed and effective_attacker_dmg == 0:
            action_type = "favorable_trade"
            desc = f"【完美白吃】{attacker.name} 无伤吃掉 {target.name} (存活 {attacker.attack}/{attacker_remaining_hp}){ping_tag}"
        elif attacker_survives and target_killed:
            action_type = "favorable_trade"
            desc = f"【优质交换】{attacker.name} 击杀 {target.name} 并存活 ({attacker.attack}/{attacker_remaining_hp}){ping_tag}"
        elif target_killed:
            action_type = "equal_trade"
            desc = f"【一换一对兑】{attacker.name} 换掉敌方 {target.name}"
        else:
            action_type = "damage_soften"
            desc = f"【垫刀压血】{attacker.name} 攻击 {target.name} (削减至 {max(0, target.health)} 血)"

        return TradeAction(
            attacker_name=f"{attacker.name} ({attacker.attack}/{attacker.health})",
            target_name=f"{target.name} ({target.attack}/{max(0, target.health)})",
            action_type=action_type,
            damage_dealt=target_dmg,
            attacker_survives=attacker_survives,
            attacker_remaining_hp=max(0, attacker_remaining_hp),
            target_killed=target_killed,
            priority_score=100.0 if is_taunt else 80.0,
            description=desc,
        )
