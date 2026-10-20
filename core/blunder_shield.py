"""
BlunderShield: Real-time Live Mistake Interceptor for Hearthstone Arena.
Detects hazardous operational sequencing and warns players BEFORE committing classic mistakes:
1. Attacking before deploying attack-buffing minions/spells
2. Committing resources before card draw
3. Triggering unknown secrets with big minions instead of tokens
4. Forgetting to Forge before playing
5. Wasting Coin on redundant hero powers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from .card_db import CardInfo

logger = logging.getLogger("BlunderShield")


@dataclass
class BlunderAlert:
    blunder_type: str                # e.g. "BUFF_BEFORE_ATTACK", "DRAW_FIRST", "SECRET_CHECK"
    severity: str                    # "CRITICAL", "HIGH", "INFO"
    alert_title: str
    action_directive: str


class BlunderShield:
    """Detects sequential play hazards and intercepts potential blunders in real time."""

    @classmethod
    def scan_for_blunders(
        cls,
        hand_cards: List[CardInfo],
        friendly_minions: List[Dict],
        enemy_secrets_count: int,
        available_mana: int,
        hero_power_available: bool,
        enemy_minions: Optional[List[Dict]] = None,
    ) -> List[BlunderAlert]:
        """
        Scans current turn state for dangerous misplay conditions.
        """
        alerts: List[BlunderAlert] = []

        can_attack_minions = [m for m in friendly_minions if m.get("can_attack", True)]

        # 1. Buff Before Attack Interceptor
        # Hand has attack-buffing cards while friendly minions can attack
        buff_cards = []
        for c in hand_cards:
            if c.cost <= available_mana:
                txt = c.clean_text
                if ("获得+" in txt and "攻击力" in txt) or "在本回合中拥有+" in txt or "叫嚣" in c.name or "恐狼" in c.name:
                    buff_cards.append(c)

        if buff_cards and can_attack_minions:
            card_names = "、".join(f"【{c.name}】" for c in buff_cards[:2])
            alerts.append(BlunderAlert(
                blunder_type="BUFF_BEFORE_ATTACK",
                severity="CRITICAL",
                alert_title="⚠️【伏笔拦截·先增益后攻击】",
                action_directive=f"手牌拥有增益卡 {card_names}！必须【先打出增益牌】，再操纵随从攻击，切勿提前用随从白白撞死或丢失额外斩杀伤害！",
            ))

        # 2. Draw First Interceptor
        # Hand has pure card draw while actions are pending
        draw_cards = []
        for c in hand_cards:
            if c.cost <= available_mana:
                txt = c.clean_text
                if ("抽" in txt and "张牌" in txt) or c.name in {"奥术智慧", "滋养", "疾跑", "编写音乐", "盾牌猛击"}:
                    draw_cards.append(c)

        if draw_cards and len(hand_cards) > len(draw_cards):
            card_names = "、".join(f"【{c.name}】" for c in draw_cards[:2])
            alerts.append(BlunderAlert(
                blunder_type="DRAW_FIRST",
                severity="HIGH",
                alert_title="💡【伏笔拦截·先过牌探查】",
                action_directive=f"可用手牌拥有过牌手段 {card_names}！必须【先执行过牌】，探知摸到的新卡牌是否带来更优解场或斩杀路线，再行决策！",
            ))

        # 3. Secret Testing Interceptor
        # Enemy has active secret, we have both small and large minions
        if enemy_secrets_count > 0 and len(can_attack_minions) >= 2:
            sorted_by_atk = sorted(can_attack_minions, key=lambda m: m.get("attack", 0))
            smallest = sorted_by_atk[0]
            largest = sorted_by_atk[-1]

            if largest.get("attack", 0) >= 4 and smallest.get("attack", 0) <= 2:
                alerts.append(BlunderAlert(
                    blunder_type="SECRET_CHECK",
                    severity="CRITICAL",
                    alert_title="🔮【伏笔拦截·用小怪测奥秘】",
                    action_directive=(
                        f"敌方头顶有 {enemy_secrets_count} 个未解奥秘！走脸必须先用小杂毛【{smallest.get('name')}】(攻{smallest.get('attack')}) 试探！"
                        f"严禁用主力大怪【{largest.get('name')}】(攻{largest.get('attack')}) 盲目踩雷（规避【蒸发/冰冻陷阱/火焰结界】等大亏解）！"
                    ),
                ))

        # 4. Forge (锻造) Reminder
        for c in hand_cards:
            if "FORGE" in c.mechanics or "锻造" in c.clean_text:
                if available_mana >= 2 and c.cost + 2 <= available_mana + 2:
                    alerts.append(BlunderAlert(
                        blunder_type="FORGE_REMINDER",
                        severity="INFO",
                        alert_title="🔨【锻造机制提示】",
                        action_directive=f"手牌【{c.name}】可进行【锻造】升级！当前剩余 ≥ 2 费，若需触发质变战吼，先将其拖动至牌库完成锻造！",
                    ))
                    break

        # 5. Hero Power Mana Utilization Reminder
        affordable = [c for c in hand_cards if c.cost <= available_mana]
        if hero_power_available and available_mana >= 2 and not affordable:
            alerts.append(BlunderAlert(
                blunder_type="USE_HERO_POWER",
                severity="HIGH",
                alert_title="💎【法力防空过·使用英雄技能】",
                action_directive="手牌已无法继续打出，结束回合前必须打出【英雄技能】消耗 2 费，杜绝法力水晶浪费！",
            ))

        # 6. Deathrattle & Cascade Order Interceptors
        if enemy_minions:
            try:
                from .cascade_simulator import CascadeSimulator
                cascade_hazards = CascadeSimulator.analyze_cascade_hazards(
                    friendly_minions=friendly_minions,
                    enemy_minions=enemy_minions,
                    can_attack_count=len(can_attack_minions),
                )
                for ch in cascade_hazards:
                    alerts.append(BlunderAlert(
                        blunder_type=ch.hazard_type,
                        severity=ch.severity,
                        alert_title=ch.hazard_title,
                        action_directive=ch.action_directive,
                    ))
            except Exception as e:
                logger.debug(f"CascadeSimulator check skipped: {e}")

        return alerts
