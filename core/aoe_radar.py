"""
AoeRadar: Opponent AOE and high-impact removal danger radar.
Simulates board lethality against opponent class-specific board clears for upcoming turns.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AoeRadar")


@dataclass
class AoeSpell:
    name: str
    hero_class: str
    mana_cost: int
    damage: int             # Total direct damage, or 999 for hard destroy
    targets_friendly: bool  # True if hits both sides (like Hellfire)
    is_hard_destroy: bool   # e.g. Brawl, Twisting Nether, Vanish
    description: str


# Comprehensive Arena AOE & Key Removal Spell Database across all Hearthstone classes
ARENA_AOE_SPELLS: List[AoeSpell] = [
    # Mage
    AoeSpell("冰霜新星", "Mage", 2, 0, False, False, "全场随从冻结1回合"),
    AoeSpell("燃烧", "Mage", 3, 4, False, False, "打4点伤害，多余扩散至相邻"),
    AoeSpell("暴风雪", "Mage", 4, 2, False, False, "全场打2点伤害并冻结"),
    AoeSpell("烈焰风暴", "Mage", 7, 5, False, False, "敌方全场随从造成 5 点伤害"),
    
    # Warlock
    AoeSpell("亵渎", "Warlock", 1, 3, True, False, "全场打1，若有随从死亡则重复触发"),
    AoeSpell("地狱烈焰", "Warlock", 4, 3, True, False, "对所有角色造成 3 点伤害"),
    AoeSpell("扭曲虚空", "Warlock", 8, 999, True, True, "消灭所有随从"),
    
    # Priest
    AoeSpell("狂乱", "Priest", 4, 999, False, False, "选择一个随从使其随机攻击其他随从直至死亡"),
    AoeSpell("神圣新星", "Priest", 4, 2, False, False, "敌方全场打2，友方全场回2"),
    AoeSpell("暗影之言：毁", "Priest", 4, 999, True, True, "消灭所有攻击力大于或等于5的随从"),
    AoeSpell("灵魂之镜", "Priest", 7, 999, False, True, "召唤敌方全场镜像并自动互撞"),
    
    # Paladin
    AoeSpell("生而平等", "Paladin", 2, 0, True, False, "将所有随从生命值变为1"),
    AoeSpell("奉献", "Paladin", 4, 2, False, False, "对所有敌人造成 2 点伤害"),
    AoeSpell("棱彩光束", "Paladin", 7, 3, False, False, "敌方全场打3，每有一个敌人费用减1"),

    # Shaman
    AoeSpell("闪电风暴", "Shaman", 3, 3, False, False, "对所有敌方随从造成 3 点伤害 (过载: 2)"),
    AoeSpell("衰变", "Shaman", 2, 0, False, False, "使所有敌方随从变形为法力值减1的随从"),
    AoeSpell("元素毁灭", "Shaman", 5, 5, True, False, "对所有随从造成 5 点伤害 (过载: 5)"),

    # Warrior
    AoeSpell("绝命乱斗", "Warrior", 5, 999, True, True, "消灭除一个随从外的所有随从"),
    AoeSpell("剑刃风暴", "Warrior", 3, 999, True, False, "全场打1直至有随从死亡"),
    AoeSpell("裂地之斧/旋风斩", "Warrior", 1, 1, True, False, "对所有随从造成 1 点伤害"),

    # Death Knight
    AoeSpell("残骸爆炸", "DeathKnight", 2, 999, False, False, "消耗残骸造成全场递增伤害"),
    AoeSpell("血液沸腾", "DeathKnight", 5, 3, False, False, "汲取敌方全场生命"),
    AoeSpell("尸爆", "DeathKnight", 6, 999, True, True, "消耗残骸每次打1直至无残骸或全灭"),

    # Hunter
    AoeSpell("爆炸陷阱", "Hunter", 2, 2, False, False, "敌方走脸触发全场打2"),
    AoeSpell("爆炸射击", "Hunter", 4, 5, False, False, "对一个随从打5，相邻打2"),

    # Druid
    AoeSpell("横扫", "Druid", 3, 4, False, False, "对一个目标打4，其他所有敌人打1"),
    AoeSpell("星辰坠落", "Druid", 5, 2, False, False, "抉择：全场打2或单体打5"),

    # Rogue
    AoeSpell("刀扇", "Rogue", 3, 1, False, False, "对所有敌方随从造成 1 点伤害并抽一张牌"),
    AoeSpell("消失", "Rogue", 6, 999, True, True, "将所有随从移回所有者的手牌"),

    # Demon Hunter
    AoeSpell("邪能弹幕", "DemonHunter", 2, 2, False, False, "全场打2"),
    AoeSpell("混乱新星", "DemonHunter", 3, 4, True, False, "对所有随从造成 4 点伤害"),
]


@dataclass
class AoeDangerThreat:
    spell: AoeSpell
    mana_accessible: bool         # Can opponent cast this next turn?
    minions_killed_count: int      # How many friendly minions would die
    friendly_minions_total: int
    casualty_rate: float           # 0.0 ~ 1.0
    danger_level: str              # "CRITICAL", "HIGH", "MODERATE", "LOW"
    warning_advice: str


class AoeRadar:
    """Evaluates opponent AOE threats for upcoming opponent turns."""

    def __init__(self) -> None:
        pass

    def evaluate_threats(
        self,
        opponent_class: str,
        current_turn: int,
        friendly_minions: List[Dict[str, Any]],
        opponent_has_coin: bool = False,
        has_long_held_card: bool = False,
    ) -> List[AoeDangerThreat]:
        """
        Calculates upcoming turn threats given opponent class, predicted mana, and friendly board state.
        Considers opponent card holding duration from HandTracker.
        """
        if not friendly_minions:
            return []

        # Predict opponent's next turn mana
        next_mana = min(10, current_turn + 1 + (1 if opponent_has_coin else 0))

        # Filter spells for opponent class
        opp_class_norm = opponent_class.lower()
        class_spells = [
            s for s in ARENA_AOE_SPELLS
            if s.hero_class.lower() in opp_class_norm or opp_class_norm in s.hero_class.lower()
        ]

        threats: List[AoeDangerThreat] = []
        total_friendly = len(friendly_minions)

        for spell in class_spells:
            # Check if mana is within reach (accessible on next turn)
            mana_accessible = spell.mana_cost <= next_mana

            # Simulate damage to friendly board
            killed_count = 0
            for m in friendly_minions:
                hp = int(m.get("health", 1))
                shield = bool(m.get("divine_shield", False))

                if shield and not spell.is_hard_destroy:
                    # Divine shield absorbs the damage
                    continue

                if spell.is_hard_destroy or spell.damage >= hp:
                    killed_count += 1

            casualty_rate = killed_count / total_friendly if total_friendly > 0 else 0.0

            # Determine danger level
            prob_suffix = " (⚠️ 敌方手牌蓄力多轮，极大概率准备释放！)" if has_long_held_card and mana_accessible else ""

            if mana_accessible and casualty_rate >= 0.7 and total_friendly >= 2:
                danger_level = "CRITICAL"
                advice = f"🚨 极度危险！敌方下回合拥有 {next_mana} 费，【{spell.name}】将团灭我方 {killed_count}/{total_friendly} 个随从！严禁继续铺场，优先贴圣盾/Buff防范。{prob_suffix}"
            elif mana_accessible and casualty_rate >= 0.5:
                danger_level = "CRITICAL" if has_long_held_card else "HIGH"
                advice = f"⚠️ 高危警戒！敌方可下回合使用【{spell.name}】({spell.description})，将重创我方半数场面，建议合理分散投资。{prob_suffix}"
            elif mana_accessible and killed_count > 0:
                danger_level = "HIGH" if has_long_held_card else "MODERATE"
                advice = f"⚡ 留意【{spell.name}】({spell.mana_cost}费) 可能清掉我方残血小随从。{prob_suffix}"
            else:
                danger_level = "LOW"
                advice = f"🛡️ 我方随从血量安全，【{spell.name}】无法造成实质威胁。"

            # Only report relevant accessible threats or high damage spells
            if mana_accessible and killed_count > 0:
                threats.append(AoeDangerThreat(
                    spell=spell,
                    mana_accessible=mana_accessible,
                    minions_killed_count=killed_count,
                    friendly_minions_total=total_friendly,
                    casualty_rate=casualty_rate,
                    danger_level=danger_level,
                    warning_advice=advice,
                ))

        # Sort threats by danger level (CRITICAL > HIGH > MODERATE) and casualties
        danger_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
        threats.sort(key=lambda t: (danger_order.get(t.danger_level, 4), -t.casualty_rate))

        return threats


@dataclass
class OverextensionAssessment:
    is_overextended: bool
    risk_level: str                # "CRITICAL_FUSE", "WARNING", "SAFE"
    fuse_alert_text: str
    signature_threat_aoe: str
    lethal_wipe_pct: float
    tactical_directive: str


class AOEOverextensionGuard:
    """Minimax guard against catastrophic overextension into opponent class AOE wipes."""

    @classmethod
    def check_overextension(
        cls,
        friendly_minions: List[Dict[str, Any]],
        opponent_class: str,
        next_turn_mana: int,
        enemy_hp: int,
    ) -> OverextensionAssessment:
        if not friendly_minions:
            return OverextensionAssessment(
                is_overextended=False,
                risk_level="SAFE",
                fuse_alert_text="",
                signature_threat_aoe="",
                lethal_wipe_pct=0.0,
                tactical_directive="当前场面无随从，无过度铺场风险",
            )

        f_atk = sum(m.get("attack", m.get("atk", 0)) for m in friendly_minions)
        total_friendly = len(friendly_minions)

        # 1. Check if friendly board already has sufficient pressure (>= 35% of enemy HP or >= 10 attack with >= 3 minions)
        pressure_established = (f_atk >= max(6, int(enemy_hp * 0.35))) and (total_friendly >= 3)

        # 2. Find signature AOE for opponent class accessible next turn
        norm_class = opponent_class.lower()
        threat_spells = [
            s for s in ARENA_AOE_SPELLS
            if s.hero_class.lower() == norm_class and s.mana_cost <= next_turn_mana
        ]
        threat_spells.sort(key=lambda s: s.damage if not s.is_hard_destroy else 999, reverse=True)

        if not threat_spells:
            return OverextensionAssessment(
                is_overextended=False,
                risk_level="SAFE",
                fuse_alert_text="",
                signature_threat_aoe="",
                lethal_wipe_pct=0.0,
                tactical_directive="敌方下回合无已知强力清场，安全展开场面",
            )

        worst_spell = threat_spells[0]
        # Calculate casualties against worst spell
        wiped_count = sum(
            1 for m in friendly_minions
            if worst_spell.is_hard_destroy or worst_spell.damage >= m.get("health", m.get("hp", 0))
        )
        wipe_pct = (wiped_count / total_friendly) * 100.0 if total_friendly > 0 else 0.0

        if pressure_established and wipe_pct >= 60.0:
            fuse_text = (
                f"🚨【过度铺场熔断警报】我方场攻达 {f_atk} 点已足够终结（对手剩余 {enemy_hp} 血）！"
                f"敌方下回合拥有 {next_turn_mana} 费，【{worst_spell.name}】可一举歼灭我方 {wiped_count}/{total_friendly} 个随从！"
            )
            directive = "严禁继续铺低血随从！改打高血大怪/亡语站场，或转为解场摇技能蓄力！"
            return OverextensionAssessment(
                is_overextended=True,
                risk_level="CRITICAL_FUSE",
                fuse_alert_text=fuse_text,
                signature_threat_aoe=f"{worst_spell.name} ({worst_spell.mana_cost}费 {worst_spell.damage}伤)",
                lethal_wipe_pct=wipe_pct,
                tactical_directive=directive,
            )

        if wipe_pct >= 60.0 and total_friendly >= 3:
            return OverextensionAssessment(
                is_overextended=False,
                risk_level="WARNING",
                fuse_alert_text=f"⚠️ 敌方下回合可施放【{worst_spell.name}】，建议提高随从血量防清场",
                signature_threat_aoe=worst_spell.name,
                lethal_wipe_pct=wipe_pct,
                tactical_directive="注意随从交换与血量分配，防范群解",
            )

        return OverextensionAssessment(
            is_overextended=False,
            risk_level="SAFE",
            fuse_alert_text="",
            signature_threat_aoe=worst_spell.name if threat_spells else "",
            lethal_wipe_pct=wipe_pct,
            tactical_directive="场面血量安全，正常展开节奏",
        )
