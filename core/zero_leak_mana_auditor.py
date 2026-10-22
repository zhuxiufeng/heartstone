"""
ZeroLeakManaAuditor: Zero-Leak Mana Audit & Curve Weaving Engine (法力无损转化与技能穿插审计).
Audits mana expenditure against available crystals and hero power opportunities,
detecting tempo leaks and recommending curve weaving to achieve 100% mana utilization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .card_db import CardInfo

logger = logging.getLogger("ZeroLeakManaAuditor")


@dataclass
class ManaLeakAuditResult:
    has_leak: bool
    leak_mana: int
    mana_utilization_pct: float
    audit_tag: str
    weaving_advice: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_leak": self.has_leak,
            "leak_mana": self.leak_mana,
            "mana_utilization_pct": self.mana_utilization_pct,
            "audit_tag": self.audit_tag,
            "weaving_advice": self.weaving_advice,
        }


class ZeroLeakManaAuditor:
    """Detects wasted mana crystals and computes optimal hero power weaving."""

    @classmethod
    def audit_mana_spending(
        cls,
        available_mana: int,
        spent_mana: int,
        hand_cards: List[CardInfo],
        hero_power_cost: int = 2,
        hero_power_available: bool = True,
    ) -> ManaLeakAuditResult:
        if available_mana <= 0:
            return ManaLeakAuditResult(
                has_leak=False,
                leak_mana=0,
                mana_utilization_pct=100.0,
                audit_tag="💎 100% 水晶无损兑现",
                weaving_advice="当前法力水晶已完全兑现，无节奏损耗。",
            )

        leak = max(0, available_mana - spent_mana)
        util_pct = min(100.0, (spent_mana / available_mana) * 100.0)

        if leak == 0:
            return ManaLeakAuditResult(
                has_leak=False,
                leak_mana=0,
                mana_utilization_pct=100.0,
                audit_tag="💎 100% 水晶无损兑现",
                weaving_advice="当前出牌完全榨干本回合可用水晶，节奏极佳！",
            )

        # Check if hero power can absorb the leak
        if hero_power_available and leak >= hero_power_cost:
            return ManaLeakAuditResult(
                has_leak=True,
                leak_mana=leak,
                mana_utilization_pct=util_pct,
                audit_tag=f"⚠️ 存在 {leak} 费闲置泄漏",
                weaving_advice=(
                    f"出牌后余留 {leak} 费！强烈建议穿插打出【英雄技能】(消耗 {hero_power_cost} 费)，"
                    f"将法力兑现率从 {util_pct:.0f}% 提升至 100%，杜绝暗中亏费！"
                ),
            )

        # Check if hand has a cheap filler card
        fillers = [c for c in hand_cards if c.cost <= leak]
        if fillers:
            best_filler = max(fillers, key=lambda c: c.cost)
            return ManaLeakAuditResult(
                has_leak=True,
                leak_mana=leak,
                mana_utilization_pct=util_pct,
                audit_tag=f"⚠️ 存在 {leak} 费闲置泄漏",
                weaving_advice=(
                    f"出牌后余留 {leak} 费！手牌中存在【{best_filler.name}】({best_filler.cost}费)，"
                    f"建议顺带打出垫刀填补曲线，实现节奏最大化！"
                ),
            )

        return ManaLeakAuditResult(
            has_leak=leak > 0,
            leak_mana=leak,
            mana_utilization_pct=util_pct,
            audit_tag=f"💡 闲置 {leak} 费 (手牌无可垫卡牌)",
            weaving_advice=f"当前手牌无合适 {leak} 费填充手段，接受微小费率损耗，注重下回合大生物展开。",
        )
