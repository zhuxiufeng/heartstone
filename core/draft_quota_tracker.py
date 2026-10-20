"""
DraftQuotaTracker: Arena 12-Win Deck Role & Functional Component Quota Tracker.
Tracks functional proportions of early tempo, hard removal, direct burn, card advantage,
and rush/taunt tools. Provides dynamic draft score adjustments to avoid single-card traps.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .card_db import CardInfo

logger = logging.getLogger("DraftQuotaTracker")


@dataclass
class QuotaItem:
    key: str
    label: str
    target_min: int
    target_max: int
    current_count: int
    status: str       # "OPTIMAL", "ACCEPTABLE", "DEFICIT", "DEFICIT_CRITICAL", "SURPLUS"
    tag_color: str
    urgency_comment: str


@dataclass
class DraftQuotaReport:
    total_cards: int
    pick_number: int
    quotas: List[QuotaItem] = field(default_factory=list)
    short_status_strip: str = ""
    most_urgent_need: str = ""


class DraftQuotaTracker:
    """Evaluates arena functional quotas and calculates strategic pick score compensation."""

    # Keywords for functional classification
    HARD_REMOVAL_KEYWORDS = ["消灭", "变形", "暗言术", "刺杀", "妖术", "变羊", "绝命乱斗", "扭曲虚空", "斩杀", "致命射击"]
    BURN_KEYWORDS = ["造成", "伤害", "打", "直伤", "火球", "寒冰箭", "刺骨", "杀戮命令"]
    DRAW_KEYWORDS = ["抽", "过牌", "发现", "置入你的手牌", "抽一张", "抽两张"]
    RUSH_TAUNT_KEYWORDS = ["突袭", "冲锋", "嘲讽", "圣盾"]

    @classmethod
    def classify_card(cls, card: CardInfo) -> Dict[str, bool]:
        """Identifies functional roles of a card."""
        cost = getattr(card, "cost", 2)
        c_type = (getattr(card, "card_type", "") or "").upper()
        text = getattr(card, "clean_text", "") or getattr(card, "text", "") or ""
        name = getattr(card, "name", "")

        is_minion = (c_type == "MINION")
        is_spell = (c_type == "SPELL")
        is_weapon = (c_type == "WEAPON")

        roles = {
            "early_tempo": is_minion and (cost in [1, 2]),
            "mid_core": is_minion and (cost in [3, 4]),
            "late_finisher": is_minion and (cost >= 6),
            "hard_removal": any(kw in text for kw in cls.HARD_REMOVAL_KEYWORDS) or any(kw in name for kw in cls.HARD_REMOVAL_KEYWORDS),
            "burn_or_pings": is_spell and any(kw in text for kw in cls.BURN_KEYWORDS),
            "card_advantage": any(kw in text for kw in cls.DRAW_KEYWORDS),
            "rush_or_taunt": any(kw in text for kw in cls.RUSH_TAUNT_KEYWORDS),
        }
        return roles

    @classmethod
    def evaluate_deck_quotas(
        cls,
        deck_so_far: List[CardInfo],
        pick_number: Optional[int] = None,
    ) -> DraftQuotaReport:
        """Calculates current component quotas against 12-win championship standard."""
        total = len(deck_so_far)
        pick = pick_number or (total + 1)

        counts = {
            "early_tempo": 0,
            "mid_core": 0,
            "late_finisher": 0,
            "hard_removal": 0,
            "burn_or_pings": 0,
            "card_advantage": 0,
            "rush_or_taunt": 0,
        }

        for c in deck_so_far:
            roles = cls.classify_card(c)
            for k, active in roles.items():
                if active:
                    counts[k] += 1

        targets = [
            ("early_tempo", "⚡ 1-2费节奏", 6, 8),
            ("mid_core", "🛡️ 3-4费中坚", 8, 10),
            ("late_finisher", "👑 6+费终结", 2, 4),
            ("hard_removal", "🗡️ 单体大解", 2, 3),
            ("burn_or_pings", "🔥 直伤/补刀", 2, 4),
            ("card_advantage", "🔮 过牌/资源", 2, 4),
            ("rush_or_taunt", "🐗 突袭/嘲讽", 3, 5),
        ]

        quota_items: List[QuotaItem] = []
        strip_parts: List[str] = []
        urgent_parts: List[str] = []

        for key, label, min_val, max_val in targets:
            cur = counts[key]
            if cur < min_val:
                deficit = min_val - cur
                if pick >= 16 and deficit >= 2:
                    status = "DEFICIT_CRITICAL"
                    color = "#ef4444"
                    cmt = f"严重缺乏！已过半程还差 {deficit} 张，遇相关卡牌务必优先抓取！"
                    urgent_parts.append(f"{label}(差{deficit})")
                    badge = f"{label}: {cur}/{min_val} 🚨急需"
                else:
                    status = "DEFICIT"
                    color = "#f59e0b"
                    cmt = f"数量偏少 (目前 {cur}/{min_val})，后半程注意补充。"
                    badge = f"{label}: {cur}/{min_val} 需补"
            elif cur > max_val + 2:
                status = "SURPLUS"
                color = "#94a3b8"
                cmt = f"配置偏多 ({cur}张)，避免过度抓取挤占关键位置。"
                badge = f"{label}: {cur}/{max_val} 偏多"
            else:
                status = "OPTIMAL"
                color = "#10b981"
                cmt = f"配比优异 ({cur}张)，符合冠军套牌结构。"
                badge = f"{label}: {cur}/{min_val} ✅"

            quota_items.append(QuotaItem(
                key=key,
                label=label,
                target_min=min_val,
                target_max=max_val,
                current_count=cur,
                status=status,
                tag_color=color,
                urgency_comment=cmt,
            ))
            strip_parts.append(badge)

        short_strip = " • ".join(strip_parts[:4])
        most_urgent = f"⚠️ 套牌战术短板: 【{'、'.join(urgent_parts[:2])}】极度告急！" if urgent_parts else "✨ 套牌组件配比均衡，无明显结构性缺失"

        return DraftQuotaReport(
            total_cards=total,
            pick_number=pick,
            quotas=quota_items,
            short_status_strip=short_strip,
            most_urgent_need=most_urgent,
        )

    @classmethod
    def calculate_quota_score_bonus(
        cls,
        card: CardInfo,
        deck_so_far: List[CardInfo],
        pick_number: int,
    ) -> int:
        """
        Dynamically adjusts card evaluation score (+5 to +18) if it fills an urgent deficit,
        or penalizes (-8 to -12) if category is oversaturated.
        """
        if pick_number < 10 or not deck_so_far:
            return 0

        roles = cls.classify_card(card)
        report = cls.evaluate_deck_quotas(deck_so_far, pick_number)
        bonus = 0

        for q in report.quotas:
            if roles.get(q.key, False):
                if q.status == "DEFICIT_CRITICAL":
                    bonus += 14  # Urgent deficit boost
                elif q.status == "DEFICIT":
                    bonus += 6
                elif q.status == "SURPLUS":
                    bonus -= 10  # Prevent over-drafting

        return max(-15, min(20, bonus))
