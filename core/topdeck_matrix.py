"""
TopdeckMatrix: Real-Time Remaining Deck Odds & Miracle Out Matrix.
Calculates draw probabilities by category (Lethal, Sweeper, Survival, Draw, Brick),
evaluates Draw Winrate Impact (DWI), and identifies clutch miracle outs.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .card_db import CardInfo

logger = logging.getLogger("TopdeckMatrix")


@dataclass
class CardTopdeckProfile:
    card_id: str
    card_name: str
    cost: int
    card_type: str                  # "MINION", "SPELL", "WEAPON"
    category: str                   # "BURST_LETHAL", "SURVIVAL_TAUNT_HEAL", "AOE_CLEAR", "VALUE_DRAW", "CURVE_PLAY", "BRICK"
    count: int
    draw_probability_pct: float     # % chance to draw this card in next draw
    draw_winrate_impact: float      # expected % winrate boost (+/- %) when drawn
    is_miracle_out: bool            # whether this card singlehandedly salvages the match
    tag: str                        # "翻盘神抽", "终结斩杀", "解场护脸", "节奏巩固", "资源补充", "死卡/鬼抽"
    text: str = ""


@dataclass
class TopdeckCategorySummary:
    category: str
    category_name: str
    count: int
    probability_pct: float
    card_names: List[str] = field(default_factory=list)


@dataclass
class TopdeckMatrixReport:
    total_remaining: int
    minion_count: int
    spell_count: int
    weapon_count: int
    minion_ratio_pct: float
    spell_ratio_pct: float
    weapon_ratio_pct: float
    categories: Dict[str, TopdeckCategorySummary] = field(default_factory=dict)
    all_cards: List[CardTopdeckProfile] = field(default_factory=list)
    top_outs: List[CardTopdeckProfile] = field(default_factory=list)
    miracle_outs: List[CardTopdeckProfile] = field(default_factory=list)
    brick_cards: List[CardTopdeckProfile] = field(default_factory=list)
    next_turn_draw_count: int = 1
    p_draw_any_miracle_pct: float = 0.0
    summary_markdown: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_remaining": self.total_remaining,
            "minion_count": self.minion_count,
            "spell_count": self.spell_count,
            "weapon_count": self.weapon_count,
            "minion_ratio_pct": round(self.minion_ratio_pct, 1),
            "spell_ratio_pct": round(self.spell_ratio_pct, 1),
            "weapon_ratio_pct": round(self.weapon_ratio_pct, 1),
            "next_turn_draw_count": self.next_turn_draw_count,
            "p_draw_any_miracle_pct": round(self.p_draw_any_miracle_pct, 1),
            "categories": {
                k: {
                    "category": v.category,
                    "category_name": v.category_name,
                    "count": v.count,
                    "probability_pct": round(v.probability_pct, 1),
                    "card_names": v.card_names,
                }
                for k, v in self.categories.items()
            },
            "miracle_outs": [
                {
                    "card_name": c.card_name,
                    "cost": c.cost,
                    "category": c.category,
                    "tag": c.tag,
                    "draw_prob_pct": round(c.draw_probability_pct, 1),
                    "dwi": round(c.draw_winrate_impact, 1),
                }
                for c in self.miracle_outs
            ],
            "top_outs": [
                {
                    "card_name": c.card_name,
                    "cost": c.cost,
                    "tag": c.tag,
                    "draw_prob_pct": round(c.draw_probability_pct, 1),
                    "dwi": round(c.draw_winrate_impact, 1),
                }
                for c in self.top_outs[:5]
            ],
            "summary_markdown": self.summary_markdown,
        }


class TopdeckMatrix:
    """Calculates comprehensive next-turn draw probabilities and miracle outs."""

    @classmethod
    def evaluate(
        cls,
        remaining_cards: List[Tuple[CardInfo, int]],
        friendly_hp: int,
        enemy_hp: int,
        friendly_field_atk: int,
        enemy_field_atk: int,
        available_mana: int = 10,
        draw_count: int = 1,
    ) -> TopdeckMatrixReport:
        total_remaining = sum(count for _, count in remaining_cards)
        if total_remaining <= 0:
            return TopdeckMatrixReport(
                total_remaining=0,
                minion_count=0,
                spell_count=0,
                weapon_count=0,
                minion_ratio_pct=0.0,
                spell_ratio_pct=0.0,
                weapon_ratio_pct=0.0,
                summary_markdown="牌库已空，已进入疲劳阶段。",
            )

        minion_count = 0
        spell_count = 0
        weapon_count = 0

        # Categorization buckets
        cat_counts: Dict[str, int] = {
            "BURST_LETHAL": 0,
            "SURVIVAL_TAUNT_HEAL": 0,
            "AOE_CLEAR": 0,
            "VALUE_DRAW": 0,
            "CURVE_PLAY": 0,
            "BRICK": 0,
        }
        cat_names: Dict[str, str] = {
            "BURST_LETHAL": "直接斩杀",
            "SURVIVAL_TAUNT_HEAL": "嘲讽/治疗护脸",
            "AOE_CLEAR": "范围清场",
            "VALUE_DRAW": "过牌/资源",
            "CURVE_PLAY": "准时节奏随从",
            "BRICK": "暂时卡手/死卡",
        }
        cat_cards: Dict[str, List[str]] = {k: [] for k in cat_counts}

        profiles: List[CardTopdeckProfile] = []
        missing_lethal_damage = max(0, enemy_hp - friendly_field_atk)
        is_in_fatal_danger = (friendly_hp <= enemy_field_atk) or (friendly_hp <= 12 and enemy_field_atk >= 8)

        next_turn_mana = min(10, available_mana + 1)

        for card, count in remaining_cards:
            ctype = (card.card_type or "MINION").upper()
            if ctype == "MINION":
                minion_count += count
            elif ctype == "SPELL":
                spell_count += count
            elif ctype == "WEAPON":
                weapon_count += count

            # Determine damage potential
            direct_damage = 0
            text = card.clean_text or card.text or ""
            mechanics = card.mechanics or []

            if ctype == "SPELL":
                if "造成" in text or "伤害" in text:
                    m = re.search(r"(\d+)点伤害", text)
                    if m:
                        direct_damage = int(m.group(1))
                    elif "造成$" in card.text:
                        direct_damage = 6
            elif ctype == "WEAPON":
                direct_damage = card.attack or 0
            elif "CHARGE" in mechanics:
                direct_damage = card.attack or 0

            # Classify category
            category = "CURVE_PLAY"
            tag = "节奏巩固"
            dwi = 2.0  # default mild positive impact
            is_miracle = False

            is_aoe = any(keyword in text for keyword in ["消灭所有", "对所有随从", "对所有敌方", "所有其他随从", "全场", "星辰坠落"])
            is_taunt_or_heal = ("TAUNT" in mechanics) or ("恢复" in text and "生命值" in text) or ("获得" in text and "护甲" in text)
            is_draw = any(keyword in text for keyword in ["抽一张牌", "抽两张牌", "抽三张牌", "抽牌", "探索", "发现"])

            if direct_damage >= missing_lethal_damage and missing_lethal_damage > 0 and card.cost <= next_turn_mana:
                category = "BURST_LETHAL"
                tag = "终结斩杀"
                dwi = 45.0
                is_miracle = True
            elif is_in_fatal_danger and (is_aoe or is_taunt_or_heal) and card.cost <= next_turn_mana:
                category = "AOE_CLEAR" if is_aoe else "SURVIVAL_TAUNT_HEAL"
                tag = "翻盘神抽"
                dwi = 35.0
                is_miracle = True
            elif is_aoe:
                category = "AOE_CLEAR"
                tag = "解场清盘"
                dwi = 15.0
            elif is_taunt_or_heal:
                category = "SURVIVAL_TAUNT_HEAL"
                tag = "护脸稳场"
                dwi = 12.0
            elif is_draw:
                category = "VALUE_DRAW"
                tag = "资源补充"
                dwi = 8.0
            elif card.cost > next_turn_mana:
                category = "BRICK"
                tag = "死卡/卡手"
                dwi = -15.0
            else:
                category = "CURVE_PLAY"
                tag = "节奏巩固"
                dwi = 5.0

            cat_counts[category] += count
            if card.name not in cat_cards[category]:
                cat_cards[category].append(card.name)

            draw_prob = (count / total_remaining) * 100.0

            profiles.append(
                CardTopdeckProfile(
                    card_id=getattr(card, "id", getattr(card, "card_id", "")),
                    card_name=card.name,
                    cost=card.cost,
                    card_type=ctype,
                    category=category,
                    count=count,
                    draw_probability_pct=draw_prob,
                    draw_winrate_impact=dwi,
                    is_miracle_out=is_miracle,
                    tag=tag,
                    text=text,
                )
            )

        # Sort profiles: miracles first, then highest winrate impact
        profiles.sort(key=lambda x: (not x.is_miracle_out, -x.draw_winrate_impact, -x.draw_probability_pct))

        miracle_outs = [p for p in profiles if p.is_miracle_out]
        brick_cards = [p for p in profiles if p.category == "BRICK"]
        top_outs = [p for p in profiles if not p.is_miracle_out and p.category != "BRICK"][:5]

        # Calculate probability of drawing at least 1 miracle out across `draw_count` draws
        # Hypergeometric: 1 - C(N - K, n) / C(N, n)
        miracle_count = sum(p.count for p in miracle_outs)
        if miracle_count > 0 and total_remaining > 0:
            draw_n = min(draw_count, total_remaining)
            prob_no_miracle = math.comb(total_remaining - miracle_count, draw_n) / math.comb(total_remaining, draw_n)
            p_draw_miracle = (1.0 - prob_no_miracle) * 100.0
        else:
            p_draw_miracle = 0.0

        # Category summaries
        cat_summaries: Dict[str, TopdeckCategorySummary] = {}
        for cat_key, c_count in cat_counts.items():
            prob = (c_count / total_remaining) * 100.0
            cat_summaries[cat_key] = TopdeckCategorySummary(
                category=cat_key,
                category_name=cat_names[cat_key],
                count=c_count,
                probability_pct=prob,
                card_names=cat_cards[cat_key],
            )

        # Markdown summary formatting
        summary_lines = [
            f"**牌库残余**: {total_remaining} 张 (随从 {minion_count} / 法术 {spell_count} / 武器 {weapon_count})",
        ]

        if miracle_outs:
            summary_lines.append(
                f"🌟 **翻盘神抽概率**: **{p_draw_miracle:.1f}%** ({len(miracle_outs)} 种翻盘手段共 {miracle_count} 张)"
            )
            for m in miracle_outs[:3]:
                summary_lines.append(f"  • `{m.card_name}` ({m.cost}费) - 单抽率 {m.draw_probability_pct:.1f}% [{m.tag}]")
        else:
            if cat_counts["BURST_LETHAL"] > 0:
                summary_lines.append(f"⚡ **直接斩杀率**: {cat_summaries['BURST_LETHAL'].probability_pct:.1f}%")
            if cat_counts["AOE_CLEAR"] > 0:
                summary_lines.append(f"🌪️ **AOE清场率**: {cat_summaries['AOE_CLEAR'].probability_pct:.1f}%")
            if cat_counts["BRICK"] > 0:
                summary_lines.append(f"⚠️ **鬼抽/卡手率**: {cat_summaries['BRICK'].probability_pct:.1f}% ({cat_counts['BRICK']}张)")

        summary_md = "\n".join(summary_lines)

        return TopdeckMatrixReport(
            total_remaining=total_remaining,
            minion_count=minion_count,
            spell_count=spell_count,
            weapon_count=weapon_count,
            minion_ratio_pct=(minion_count / total_remaining) * 100.0,
            spell_ratio_pct=(spell_count / total_remaining) * 100.0,
            weapon_ratio_pct=(weapon_count / total_remaining) * 100.0,
            categories=cat_summaries,
            all_cards=profiles,
            top_outs=top_outs,
            miracle_outs=miracle_outs,
            brick_cards=brick_cards,
            next_turn_draw_count=draw_count,
            p_draw_any_miracle_pct=p_draw_miracle,
            summary_markdown=summary_md,
        )
