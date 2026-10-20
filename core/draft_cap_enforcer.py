"""
DraftCapEnforcer: Structural deck balance and curve hard-cap optimizer.
Enforces grandmaster draft ratios: heavy bomb ceiling, early drop anchor, and spell overload limits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .card_db import CardInfo

logger = logging.getLogger("DraftCapEnforcer")


@dataclass
class DraftCapModifier:
    score_delta: float
    reasons: List[str] = field(default_factory=list)
    is_hard_cap_violation: bool = False


class DraftCapEnforcer:
    """
    Evaluates candidate draft cards against macro deck balance rules.
    """

    @classmethod
    def evaluate_card_caps(
        cls,
        candidate: CardInfo,
        picked_deck: List[CardInfo],
    ) -> DraftCapModifier:
        """
        Calculates penalty or bonus based on deck macro composition.
        """
        reasons: List[str] = []
        score_delta: float = 0.0
        is_hard_violation = False

        picked_count = len(picked_deck)
        c_cost = candidate.cost
        c_type = (candidate.card_type or "").upper()
        c_text = (candidate.text or "").upper()

        # 1. Heavy Bomb Cap (7+ Mana)
        heavy_bombs = [c for c in picked_deck if c.cost >= 7]
        bomb_count = len(heavy_bombs)

        if c_cost >= 7:
            if bomb_count == 1:
                score_delta -= 3.0
                reasons.append("⚠️ 套牌已有1张高费大哥，曲线开始偏重")
            elif bomb_count == 2:
                score_delta -= 10.0
                reasons.append("⛔ 7费以上大哥已达2张临界值，非顶级神卡不建议再选")
                is_hard_violation = True
            elif bomb_count >= 3:
                penalty = 18.0 + (bomb_count - 3) * 6.0
                score_delta -= penalty
                reasons.append(f"🛑 7费大哥严重超载(已有{bomb_count}张)！极易前期断节奏卡手暴毙")
                is_hard_violation = True

        # 2. Early Drop Anchor (2-drop Minions)
        two_drops = [c for c in picked_deck if c.cost == 2 and (c.card_type or "").upper() == "MINION"]
        two_drop_count = len(two_drops)

        if c_cost == 2 and c_type == "MINION":
            if picked_count >= 20 and two_drop_count < 5:
                score_delta += 14.0
                reasons.append(f"🔥 选牌末期2费生物极度匮乏(仅{two_drop_count}张)，紧急补足前期曲线支点！")
            elif picked_count >= 12 and two_drop_count < 4:
                score_delta += 8.0
                reasons.append(f"📈 2费曲线偏弱(当前{two_drop_count}张)，优先抓取保障前2回合先手站场")

        # 3. Spell & Weapon Overload Cap
        non_minions = [c for c in picked_deck if (c.card_type or "").upper() in ("SPELL", "WEAPON")]
        non_minion_count = len(non_minions)

        if c_type in ("SPELL", "WEAPON"):
            if non_minion_count >= 10:
                score_delta -= 16.0
                reasons.append(f"🛑 法术/武器比例严重过载(已有{non_minion_count}张)！竞技场以生物随从站场为根本")
                is_hard_violation = True
            elif non_minion_count >= 7:
                score_delta -= 8.0
                reasons.append(f"⚠️ 法术/武器达{non_minion_count}张上限，避免情境解牌过多导致无随从下场")

        # 4. Late Game Card Draw / Value Fuel Anchor
        if picked_count >= 16:
            draw_cards = [
                c for c in picked_deck
                if any(kw in (c.text or "").upper() for kw in ("DRAW", "DISCOVER", "ADD A", "抽", "发现"))
            ]
            if len(draw_cards) <= 1:
                if any(kw in c_text for kw in ("DRAW", "DISCOVER", "ADD A", "抽", "发现")):
                    score_delta += 7.0
                    reasons.append("💎 套牌续航过牌严重不足，优先抓取补充资源引擎")

        return DraftCapModifier(
            score_delta=score_delta,
            reasons=reasons,
            is_hard_cap_violation=is_hard_violation,
        )
