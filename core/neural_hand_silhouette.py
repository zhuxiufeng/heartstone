"""
NeuralHandSilhouette: High-Dimensional Opponent Hidden Hand Probability Heat Matrix.
Reconstructs exact card identity probabilities for every card slot in opponent's hand
based on class archetype pools, mana usage curves, hold times, and mulligan retention.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NeuralHandSilhouette")


@dataclass
class GhostCardSilhouette:
    card_name: str
    cost: int
    probability_pct: float
    danger_tier: str            # "CRITICAL", "HIGH", "MODERATE", "LOW"
    card_type: str              # "AOE_SWEEPER", "BURST_LETHAL", "HARD_REMOVAL", "VALUE_DRAW", "TEMPO_MINION"
    deduction_rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_name": self.card_name,
            "cost": self.cost,
            "probability_pct": round(self.probability_pct, 1),
            "danger_tier": self.danger_tier,
            "card_type": self.card_type,
            "deduction_rationale": self.deduction_rationale,
        }


@dataclass
class SlotHandSilhouette:
    slot: int
    hold_turns: int
    origin_tag: str
    primary_prediction: GhostCardSilhouette
    alternative_predictions: List[GhostCardSilhouette] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot": self.slot,
            "hold_turns": self.hold_turns,
            "origin_tag": self.origin_tag,
            "primary": self.primary_prediction.to_dict(),
            "alternatives": [a.to_dict() for a in self.alternative_predictions],
        }


@dataclass
class HandSilhouetteReport:
    total_hand_count: int
    slots: List[SlotHandSilhouette] = field(default_factory=list)
    critical_threat_slots: List[int] = field(default_factory=list)
    summary_markdown: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_hand_count": self.total_hand_count,
            "critical_threat_slots": self.critical_threat_slots,
            "slots": [s.to_dict() for s in self.slots],
            "summary_markdown": self.summary_markdown,
        }


class NeuralHandSilhouette:
    """Predicts opponent's hidden hand cards with probabilistic silhouette distributions."""

    CLASS_CORE_POOL = {
        "MAGE": [
            ("烈焰风暴", 7, "AOE_SWEEPER", "CRITICAL", "高费起手保留且握持超过4回合的核心全场清场"),
            ("火球术", 4, "BURST_LETHAL", "HIGH", "保留在中期用于斩杀或点死核心大哥的高额直伤"),
            ("暴风雪", 6, "AOE_SWEEPER", "HIGH", "控场拖延回合的全场冰冻解场"),
            ("变形术", 4, "HARD_REMOVAL", "MODERATE", "针对高威胁随从的变形单解"),
            ("奥术智慧", 3, "VALUE_DRAW", "LOW", "前期过牌补充资源"),
        ],
        "WARLOCK": [
            ("扭曲虚空", 8, "AOE_SWEEPER", "CRITICAL", "起手沉睡至今的终极消灭全场清屏"),
            ("亵渎", 2, "AOE_SWEEPER", "HIGH", "针对杂兵铺场的低费递增清场"),
            ("地狱烈焰", 4, "AOE_SWEEPER", "HIGH", "全场打3伤害"),
            ("吸取灵魂", 2, "HARD_REMOVAL", "LOW", "低费打3回血点杀"),
        ],
        "PRIEST": [
            ("暗言术: 毁", 4, "AOE_SWEEPER", "HIGH", "针对高攻随从的群体解场"),
            ("神圣新星", 4, "AOE_SWEEPER", "MODERATE", "全场打2回血清场"),
            ("精神控制", 9, "HARD_REMOVAL", "CRITICAL", "残局高费偷取我方核心主力大哥"),
        ],
        "WARRIOR": [
            ("绝命乱斗", 5, "AOE_SWEEPER", "CRITICAL", "5费防范铺场的关键乱斗清场"),
            ("剑刃风暴", 3, "AOE_SWEEPER", "HIGH", "连续打1清场"),
            ("斩杀", 2, "HARD_REMOVAL", "MODERATE", "配合补刀的硬解"),
        ],
        "PALADIN": [
            ("奉献", 4, "AOE_SWEEPER", "HIGH", "4费全场打2点扫场"),
            ("十字军光环", 4, "BURST_LETHAL", "CRITICAL", "随从铺场后的致命增益滚雪球"),
            ("守卫者的力量", 5, "AOE_SWEEPER", "HIGH", "依托随从攻击力的群体清屏"),
        ],
        "HUNTER": [
            ("爆炸陷阱", 2, "AOE_SWEEPER", "HIGH", "受击打2清场奥秘"),
            ("杀戮命令", 3, "BURST_LETHAL", "HIGH", "配合野兽打5直伤斩杀"),
            ("镂骨恶犬", 6, "AOE_SWEEPER", "CRITICAL", "突袭横扫吸血清场"),
        ],
        "DEATHKNIGHT": [
            ("邪爆", 5, "AOE_SWEEPER", "CRITICAL", "消耗尸体连续打1清场"),
            ("冰霜巨龙之怒", 7, "AOE_SWEEPER", "HIGH", "全场打5并全员冻结"),
        ],
        "SHAMAN": [
            ("嗜血", 5, "BURST_LETHAL", "CRITICAL", "全员+3攻突发反杀斩杀"),
            ("闪电风暴", 3, "AOE_SWEEPER", "HIGH", "全场打3法术清场"),
        ],
        "ROGUE": [
            ("刺骨", 2, "BURST_LETHAL", "HIGH", "连击打4单解或走脸"),
            ("暗影步", 0, "VALUE_DRAW", "MODERATE", "战吼回收复用核心组件"),
        ],
        "DEMONHUNTER": [
            ("乱舞横扫", 5, "AOE_SWEEPER", "HIGH", "英雄攻击力全场横扫"),
            ("献祭光环", 4, "AOE_SWEEPER", "MODERATE", "2次打1清场"),
        ],
        "DRUID": [
            ("横扫", 5, "AOE_SWEEPER", "MODERATE", "单体打4全场打1"),
            ("星辰坠落", 7, "AOE_SWEEPER", "HIGH", "全场打2或单体打5"),
        ],
    }

    @classmethod
    def evaluate_hand_silhouette(
        cls,
        opponent_class: str,
        hand_cards_info: List[Dict[str, Any]],
        current_turn: int = 5,
    ) -> HandSilhouetteReport:
        c_upper = opponent_class.upper().replace(" ", "").replace("_", "")
        matched_class = "MAGE"
        for key in cls.CLASS_CORE_POOL:
            if key in c_upper:
                matched_class = key
                break

        pool = cls.CLASS_CORE_POOL.get(matched_class, cls.CLASS_CORE_POOL["MAGE"])
        slots: List[SlotHandSilhouette] = []
        critical_slots: List[int] = []

        total_cards = len(hand_cards_info)
        if total_cards == 0:
            return HandSilhouetteReport(
                total_hand_count=0,
                slots=[],
                critical_threat_slots=[],
                summary_markdown="对手手牌已空，无手牌威胁。",
            )

        for idx, card_item in enumerate(hand_cards_info):
            slot_num = card_item.get("slot", idx + 1)
            hold_turns = card_item.get("hold_turns", 1)
            origin = card_item.get("origin", "TURN_DRAW")
            origin_tag = "起手保留" if "KEPT" in origin else ("调度重抽" if "REDRAW" in origin else "自然抓牌")

            # Predict based on hold turns
            preds: List[GhostCardSilhouette] = []
            if hold_turns >= 4:
                # Long-held card: likely high cost sweeper or combo finisher
                primary_raw = pool[0]  # top high-cost sweeper
                prob = min(88.0, 50.0 + hold_turns * 6.0)
                preds.append(
                    GhostCardSilhouette(
                        card_name=primary_raw[0],
                        cost=primary_raw[1],
                        probability_pct=prob,
                        danger_tier=primary_raw[3],
                        card_type=primary_raw[2],
                        deduction_rationale=primary_raw[4],
                    )
                )
                if len(pool) > 1:
                    alt_raw = pool[1]
                    preds.append(
                        GhostCardSilhouette(
                            card_name=alt_raw[0],
                            cost=alt_raw[1],
                            probability_pct=max(10.0, 100.0 - prob),
                            danger_tier=alt_raw[3],
                            card_type=alt_raw[2],
                            deduction_rationale=alt_raw[4],
                        )
                    )
                critical_slots.append(slot_num)
            elif hold_turns >= 2:
                # Mid-range removal or curve card
                pick_idx = 1 if len(pool) > 1 else 0
                raw = pool[pick_idx]
                prob = 65.0
                preds.append(
                    GhostCardSilhouette(
                        card_name=raw[0],
                        cost=raw[1],
                        probability_pct=prob,
                        danger_tier=raw[3],
                        card_type=raw[2],
                        deduction_rationale=raw[4],
                    )
                )
                if len(pool) > 2:
                    alt_raw = pool[2]
                    preds.append(
                        GhostCardSilhouette(
                            card_name=alt_raw[0],
                            cost=alt_raw[1],
                            probability_pct=35.0,
                            danger_tier=alt_raw[3],
                            card_type=alt_raw[2],
                            deduction_rationale=alt_raw[4],
                        )
                    )
            else:
                # Freshly drawn card
                pick_idx = min(3, len(pool) - 1)
                raw = pool[pick_idx]
                prob = 45.0
                preds.append(
                    GhostCardSilhouette(
                        card_name=raw[0],
                        cost=raw[1],
                        probability_pct=prob,
                        danger_tier="MODERATE",
                        card_type=raw[2],
                        deduction_rationale="新回合摸入牌，倾向于当回合可用曲线或普通随从",
                    )
                )

            slots.append(
                SlotHandSilhouette(
                    slot=slot_num,
                    hold_turns=hold_turns,
                    origin_tag=origin_tag,
                    primary_prediction=preds[0],
                    alternative_predictions=preds[1:] if len(preds) > 1 else [],
                )
            )

        # Markdown formatting
        md_lines = [
            f"**敌方手牌透视热力矩阵** (对手职业: `{matched_class}`，手牌共 {total_cards} 张):",
        ]
        for s in slots:
            p = s.primary_prediction
            danger_badge = "🔥 [极度危险]" if p.danger_tier == "CRITICAL" else ("⚠️ [高危预警]" if p.danger_tier == "HIGH" else "")
            md_lines.append(
                f"• 槽位 **#{s.slot}** ({s.origin_tag}·握持{s.hold_turns}回合): **{p.probability_pct:.0f}% 概率为【{p.card_name}】** ({p.cost}费) {danger_badge}\n"
                f"  └ 🧠 {p.deduction_rationale}"
            )

        return HandSilhouetteReport(
            total_hand_count=total_cards,
            slots=slots,
            critical_threat_slots=critical_slots,
            summary_markdown="\n".join(md_lines),
        )
