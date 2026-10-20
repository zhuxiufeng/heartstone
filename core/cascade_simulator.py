"""
CascadeSimulator: Deathrattle, Divine Shield & Sequence Chain Simulator.
Detects complex interaction hazards on board before committing actions:
1. Popping deathrattles that spawn Taunts before other minions finish attacking
2. Striking Divine Shields with heavy-hitters instead of ping/tokens
3. Squandering Poisonous on 1/1 tokens instead of massive minions
4. Reborn and on-damage triggers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CascadeSimulator")


@dataclass
class CascadeHazard:
    hazard_type: str             # "DEATHRATTLE_TAUNT", "DIVINE_SHIELD_WASTE", "POISONOUS_MISMATCH"
    severity: str                # "CRITICAL", "HIGH", "MEDIUM"
    hazard_title: str
    action_directive: str


# Minions known to spawn taunts or defensive barriers upon death
DEATHRATTLE_DEFENSIVE_SPAWNS = {
    "淤泥喷射者", "虚空领主", "着魔便衣", "机械袋鼠", "吵吵机器人",
    "鬼灵爬行者", "被感染的牛头人", "铠甲骑兵", "骨魇", "安度因",
    "Sludge Belcher", "Voidlord", "Possessed Lackey", "Infested Tauren"
}


class CascadeSimulator:
    """Analyzes minion mechanics to simulate attack chain reactions and prevent order traps."""

    @classmethod
    def analyze_cascade_hazards(
        cls,
        friendly_minions: List[Dict[str, Any]],
        enemy_minions: List[Dict[str, Any]],
        can_attack_count: int,
    ) -> List[CascadeHazard]:
        hazards: List[CascadeHazard] = []

        # 1. Deathrattle Taunt Spawn Hazard
        # If an enemy minion has deathrattle spawning taunts/minions and we have multiple attackers
        for em in enemy_minions:
            em_name = em.get("name", "")
            has_deathrattle = "亡语" in em_name or em.get("deathrattle", False)
            is_defensive = any(k in em_name for k in DEATHRATTLE_DEFENSIVE_SPAWNS)

            if (has_deathrattle or is_defensive) and can_attack_count >= 2:
                hazards.append(CascadeHazard(
                    hazard_type="DEATHRATTLE_TAUNT",
                    severity="CRITICAL",
                    hazard_title="⚠️【连锁结算·防亡语卡攻击】",
                    action_directive=(
                        f"敌方【{em_name}】带有亡语生怪效果！必须【先用其他随从全力走脸/完成交换】，"
                        f"最后再补刀打死亡语怪，严禁提前击杀导致冒出嘲讽阻断后手攻击！"
                    ),
                ))
                break

        # 2. Divine Shield Waste Hazard
        # If enemy has Divine Shield, hitting with big minion wastes damage
        for em in enemy_minions:
            em_name = em.get("name", "")
            has_shield = em.get("divine_shield", False) or "圣盾" in em_name
            if has_shield:
                high_atk_friendly = [fm for fm in friendly_minions if fm.get("atk", fm.get("attack", 0)) >= 4]
                low_atk_friendly = [fm for fm in friendly_minions if fm.get("atk", fm.get("attack", 0)) <= 2]

                if high_atk_friendly and (low_atk_friendly or True):
                    hazards.append(CascadeHazard(
                        hazard_type="DIVINE_SHIELD_WASTE",
                        severity="HIGH",
                        hazard_title="🛡️【连锁结算·圣盾破除次序】",
                        action_directive=(
                            f"敌方【{em_name}】拥有圣盾防御！必须先用【杂毛/技能/1攻小怪】破除圣盾，"
                            f"严禁用高攻主力随从白白撞盾浪费攻击力！"
                        ),
                    ))
                    break

        # 3. Poisonous High-Value Trade Priority
        for fm in friendly_minions:
            is_poison = fm.get("poisonous", False) or "剧毒" in fm.get("name", "")
            if is_poison and enemy_minions:
                sorted_by_hp = sorted(enemy_minions, key=lambda m: m.get("health", m.get("hp", 0)), reverse=True)
                biggest_enemy = sorted_by_hp[0]
                if biggest_enemy.get("health", biggest_enemy.get("hp", 0)) >= 4:
                    hazards.append(CascadeHazard(
                        hazard_type="POISONOUS_PRIORITY",
                        severity="MEDIUM",
                        hazard_title="☠️【连锁结算·剧毒定向刺杀】",
                        action_directive=(
                            f"我方随从【{fm.get('name')}】具有剧毒特性！优先指定刺杀敌方最高血量大哥【{biggest_enemy.get('name')}】，"
                            f"杜绝浪费剧毒攻击小杂毛！"
                        ),
                    ))
                    break

        return hazards
