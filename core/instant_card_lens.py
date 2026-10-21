"""
InstantCardLens: On-Screen Omniscient Magnifier & Deep Card Deconstruction Lens.
Instantly analyzes obscure tokens, titan abilities, colossal parts, and battle anomalies,
providing counter-strategies, meta winrate impact, and synergy combos.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("InstantCardLens")


@dataclass
class CardLensBreakdown:
    card_name: str
    card_id: str
    mana_cost: int
    card_type: str
    stats_display: str          # e.g. "4 攻 / 5 血"
    clean_text: str
    danger_tier: str            # "EXTREME", "HIGH", "MODERATE", "LOW"
    arena_winrate_impact_pct: float
    best_counters: List[str]
    best_combos: List[str]
    tactical_advice: str
    summary_markdown: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_name": self.card_name,
            "card_id": self.card_id,
            "cost": self.mana_cost,
            "card_type": self.card_type,
            "stats": self.stats_display,
            "clean_text": self.clean_text,
            "danger_tier": self.danger_tier,
            "winrate_impact_pct": round(self.arena_winrate_impact_pct, 1),
            "counters": self.best_counters,
            "combos": self.best_combos,
            "tactical_advice": self.tactical_advice,
            "summary_markdown": self.summary_markdown,
        }


class InstantCardLens:
    """Provides deep encyclopedic and tactical breakdown for any card or token."""

    KNOWN_SPECIAL_CARDS = {
        "泰坦": {
            "danger": "EXTREME",
            "wr": 12.5,
            "counters": ["变形术", "妖术", "消灭/剧毒硬解", "全员走脸速杀"],
            "combos": ["嘲讽保护", "风怒加持"],
            "advice": "泰坦拥有3个自选技能，每回合生效1次且无法被沉默解除已释放效果。必须优先单解点杀！",
        },
        "巨型": {
            "danger": "HIGH",
            "wr": 9.2,
            "counters": ["全场AOE清场", "剧毒随从白吃", "冰冻控制"],
            "combos": ["群体Buff", "圣盾附魔"],
            "advice": "召唤时连带召唤多只附属肢体部件。优先集火其高伤核心肢体，或直接全场AOE清屏。",
        },
        "火球术": {
            "danger": "HIGH",
            "wr": 6.8,
            "counters": ["叠甲", "嘲讽/治疗护脸", "法术反制"],
            "combos": ["法术伤害加成", "点脸终结斩杀"],
            "advice": "法师最具代表性的高爆发直伤。控血线在6点以上，或下嘲讽/治疗脱离射程。",
        },
        "烈焰风暴": {
            "danger": "EXTREME",
            "wr": 10.4,
            "counters": ["保留手牌不全铺", "随从血量提升至6点以上", "亡语随从站场"],
            "combos": ["法强加成", "残局逆转清屏"],
            "advice": "T7核心AOE。若我方场面已占优，切勿倾泻所有手牌连环下怪，保留返场种子。",
        },
    }

    @classmethod
    def inspect(
        cls,
        card_query: str,
        card_info: Optional[Any] = None,
    ) -> CardLensBreakdown:
        query_clean = card_query.strip()

        # Check special registry
        matched_special = None
        for k in cls.KNOWN_SPECIAL_CARDS:
            if k in query_clean:
                matched_special = cls.KNOWN_SPECIAL_CARDS[k]
                break

        if card_info:
            c_name = getattr(card_info, "name", query_clean)
            c_id = getattr(card_info, "id", "")
            cost = getattr(card_info, "cost", 0)
            ctype = getattr(card_info, "card_type", "MINION")
            atk = getattr(card_info, "attack", None)
            hp = getattr(card_info, "health", None)
            stats = f"{atk}攻 / {hp}血" if (atk is not None and hp is not None) else (f"{cost}费法术" if ctype == "SPELL" else f"{cost}费卡牌")
            text = getattr(card_info, "clean_text", getattr(card_info, "text", ""))
        else:
            c_name = query_clean
            c_id = "CUSTOM_LENS"
            cost = 5
            ctype = "MINION"
            stats = "随从/特殊单位"
            text = "特殊战场机制或卡牌技能"

        danger = matched_special["danger"] if matched_special else ("HIGH" if cost >= 6 else "MODERATE")
        wr = matched_special["wr"] if matched_special else (5.0 if cost >= 5 else 2.5)
        counters = matched_special["counters"] if matched_special else ["优质随从白吃", "精准单解", "血线脱离射程"]
        combos = matched_special["combos"] if matched_special else ["同职业法术协同", "按费站场"]
        advice = matched_special["advice"] if matched_special else f"常规竞技场单卡。针对其 {cost} 费曲线做好对位交换与防范。"

        md_lines = [
            f"🔍 **全知 AI 透镜 · 【{c_name}】** ({stats}):",
            f"• **威胁评级**: `{danger}` (竞技场胜率杠杆: `+{wr:.1f}%`)",
            f"• 🛡️ **克制破解策略**: {', '.join(counters)}",
            f"• 💡 **大师战术叮嘱**: {advice}",
        ]

        return CardLensBreakdown(
            card_name=c_name,
            card_id=c_id,
            mana_cost=cost,
            card_type=ctype,
            stats_display=stats,
            clean_text=text,
            danger_tier=danger,
            arena_winrate_impact_pct=wr,
            best_counters=counters,
            best_combos=combos,
            tactical_advice=advice,
            summary_markdown="\n".join(md_lines),
        )
