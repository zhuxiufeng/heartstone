"""
SequenceOptimizer: Recommends the optimal play sequence and action ordering.
Enforces fundamental competitive Hearthstone principles:
1. Maximize Information First (Draw / Discover / Tap before committing)
2. Buffs before Minion Attacks
3. Board clears / AoE before summoning new friendly minions
4. Prudent Coin usage
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SequenceOptimizer")


@dataclass
class SequencingRule:
    rule_name: str
    priority: int       # Higher priority should be executed earlier (100 = earliest, 10 = latest)
    action_text: str
    reasoning: str


@dataclass
class SequencingAdvice:
    recommended_sequence: List[str]
    critical_warnings: List[str]
    has_info_draw: bool
    draw_first_directive: str = ""


class SequenceOptimizer:
    """Optimizes in-turn action order to prevent misplays and maximize information."""

    def __init__(self) -> None:
        pass

    def evaluate_sequence(
        self,
        planned_cards: List[Dict[str, Any]],
        friendly_minions_can_attack: bool = True,
        hero_power_available: bool = True,
        hero_power_name: str = "",
        friendly_hero_class: str = "",
    ) -> SequencingAdvice:
        """
        Analyzes the planned actions and generates an optimal sequence with anti-misplay warnings.
        """
        rules: List[SequencingRule] = []
        warnings: List[str] = []
        has_info_draw = False

        # 1. Check Hero Power for Draw / Tap (Warlock Life Tap, etc.)
        if hero_power_available and ("生命分流" in hero_power_name or friendly_hero_class.lower() == "warlock"):
            has_info_draw = True
            rules.append(SequencingRule(
                rule_name="HeroPowerDraw",
                priority=100,
                action_text="1️⃣ 【生命分流 / 英雄技能抽牌】",
                reasoning="竞技场铁律：先抽牌拓宽信息边界，新牌可能会完全改变当回合最优打法！",
            ))

        # 2. Check Cards for Card Draw, Discover, or Generation
        draw_cards = []
        rng_cards = []
        aoe_cards = []
        buff_cards = []
        summon_cards = []

        for c in planned_cards:
            name = c.get("name", "")
            text = c.get("text", "")

            # Card draw / discover
            if any(k in name or k in text for k in ["抽", "发现", "置入你的手牌", "战利品", "奥术智慧"]):
                draw_cards.append(c)
            # RNG effects
            elif any(k in name or k in text for k in ["随机造成", "随机对", "随机召唤", "火炮"]):
                rng_cards.append(c)
            # AoE clears
            elif any(k in name or k in text for k in ["对所有", "所有角色", "地狱烈焰", "乱斗", "奉献", "暴风雪", "烈焰风暴"]):
                aoe_cards.append(c)
            # Attack buffs
            elif any(k in name or k in text for k in ["获得+", "使其获得+", "咆哮", "嗜血", "本回合获得攻击力"]):
                buff_cards.append(c)
            else:
                summon_cards.append(c)

        # 2.5 Add RNG cards (Priority 95)
        for rc in rng_cards:
            rules.append(SequencingRule(
                rule_name="RngAction",
                priority=95,
                action_text=f"🎲【先打随机效果】打出【{rc.get('name')}】",
                reasoning="先观察随机伤害或召唤落点，再决定后续随从攻击或补刀目标！",
            ))

        # 3. Add Draw Cards (Priority 90)
        for dc in draw_cards:
            has_info_draw = True
            rules.append(SequencingRule(
                rule_name="CardDraw",
                priority=90,
                action_text=f"【优先过牌/发现】打出【{dc.get('name')}】",
                reasoning="在下怪或交解牌前先抽取新卡，根据获得的新手牌调整决策。",
            ))

        # 4. Add AoE clears (Priority 80)
        for ac in aoe_cards:
            rules.append(SequencingRule(
                rule_name="AoEClear",
                priority=80,
                action_text=f"【先清场】施放 AOE【{ac.get('name')}】",
                reasoning="严防伏笔：务必在召唤新随从前释放全场清场法术，避免误伤友方新随从！",
            ))
            if summon_cards:
                warnings.append(f"⚠️ 严禁先下随从再放【{ac.get('name')}】！必须先清场再铺怪！")

        # 5. Add Buffs (Priority 70)
        for bc in buff_cards:
            rules.append(SequencingRule(
                rule_name="Buff",
                priority=70,
                action_text=f"【施加增益】使用【{bc.get('name')}】",
                reasoning="在随从攻击前先加攻，确保攻击随从吃到攻击力增益！",
            ))
            if friendly_minions_can_attack:
                warnings.append(f"⚠️ 注意攻击时序：请先打出【{bc.get('name')}】增益，再操控随从攻击！")

        # 6. Minion Attacks / Trading (Priority 60)
        if friendly_minions_can_attack:
            rules.append(SequencingRule(
                rule_name="Attack",
                priority=60,
                action_text="【随从战场交换/走脸攻击】",
                reasoning="完成法术铺垫后进行随从攻击，残血随从完成交换后再下新生物填补场面。",
            ))

        # 7. Add Summoning / Normal Minions (Priority 50)
        for sc in summon_cards:
            rules.append(SequencingRule(
                rule_name="Summon",
                priority=50,
                action_text=f"【铺场召唤】打出随从【{sc.get('name')}】",
                reasoning="随从登场并站位（防陨石/防背叛站位，大怪居中或两侧），结束回合前站稳场面。",
            ))

        # 8. Sort rules by priority descending
        rules.sort(key=lambda r: r.priority, reverse=True)

        ordered_steps = [f"{idx+1}. {r.action_text} ➔ {r.reasoning}" for idx, r in enumerate(rules)]
        if not ordered_steps:
            ordered_steps = ["1. 按照常规法力曲线打出预定手牌并进行随从交换。"]

        draw_directive = ""
        if has_info_draw:
            draw_directive = "🎲【不确定性先行铁律】当前手牌含过牌/发现，请务必先过牌拓宽信息边界，新牌可能会完全改变当回合最优打法！"

        return SequencingAdvice(
            recommended_sequence=ordered_steps,
            critical_warnings=warnings,
            has_info_draw=has_info_draw,
            draw_first_directive=draw_directive,
        )
