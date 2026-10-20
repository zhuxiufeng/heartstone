"""
SynergyRadar: 6-Axis Deck Archetype Radar & Tribe Network Engine.
Evaluates in-progress or completed arena drafts across 6 critical competitive dimensions:
1. Early Tempo (1-3 drops, board init)
2. Board Clear (AOE wipes)
3. Hard Removal (Single target big threats elimination)
4. Card Draw (Card advantage & replenishment)
5. Reach & Burst (Direct burn & finisher reach)
6. Tribe Synergy (Elemental chain, Mech magnetism, Undead reborn, Dragon trigger)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from core.card_db import CardInfo
except (ImportError, ValueError):
    from .card_db import CardInfo

logger = logging.getLogger("SynergyRadar")


@dataclass
class SynergyRadarReport:
    early_tempo_score: float         # 0 - 100
    board_clear_score: float         # 0 - 100
    hard_removal_score: float        # 0 - 100
    card_draw_score: float           # 0 - 100
    reach_burst_score: float         # 0 - 100
    tribe_synergy_score: float       # 0 - 100
    overall_balance_score: float     # 0 - 100
    archetype_title: str             # e.g., "⚡ 极速节奏快攻", "🐉 龙族控场体系"
    strengths: List[str] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)
    tribe_counts: Dict[str, int] = field(default_factory=dict)


class SynergyRadar:
    """Computes multidimensional radar metrics for draft decks."""

    @classmethod
    def analyze_deck(cls, deck: List[CardInfo]) -> SynergyRadarReport:
        if not deck:
            return SynergyRadarReport(
                early_tempo_score=0.0,
                board_clear_score=0.0,
                hard_removal_score=0.0,
                card_draw_score=0.0,
                reach_burst_score=0.0,
                tribe_synergy_score=0.0,
                overall_balance_score=0.0,
                archetype_title="🌱 构筑起步",
                strengths=["正在选牌中..."],
                vulnerabilities=[],
            )

        early_drops = 0
        aoe_count = 0
        removal_count = 0
        draw_count = 0
        burst_count = 0
        tribes: Dict[str, int] = {}

        for card in deck:
            c_text = (card.clean_text or "").lower()
            c_cost = card.cost
            c_type = getattr(card, "card_type", getattr(card, "type", "MINION")).upper()

            # 1. Early Tempo: 1-3 cost minions
            if c_cost <= 3 and c_type == "MINION":
                early_drops += 1
            elif c_cost <= 2 and "造成" in c_text and c_type == "SPELL":
                early_drops += 0.5

            # 2. Board Clear: AOE
            if any(k in c_text for k in ["所有敌方随从", "所有随从", "全部敌人", "对每个随从", "伤害分配给所有敌方"]):
                aoe_count += 1

            # 3. Hard Removal
            if any(k in c_text for k in ["消灭一个", "沉默并消灭", "将其变形", "移出对战", "造成5点伤害", "造成6点伤害", "造成7点伤害", "造成8点伤害", "消灭敌方"]):
                removal_count += 1

            # 4. Card Draw
            if any(k in c_text for k in ["抽一张牌", "抽两张牌", "抽三张牌", "发现一张", "将一张", "抽牌"]):
                draw_count += 1

            # 5. Reach / Burst
            if any(k in c_text for k in ["对敌方英雄造成", "冲锋", "风怒", "嗜血", "本回合获得+3攻击力", "对任意目标造成"]):
                burst_count += 1

            # 6. Tribes
            race = (card.race or "").strip().upper()
            if race and race != "NONE":
                tribes[race] = tribes.get(race, 0) + 1

        # Normalize to 0 - 100 based on standard 30-card competitive benchmarks
        # Benchmarks: 8-10 early drops, 2-3 AOEs, 3-4 removals, 4-6 draws, 2-3 finishers
        deck_size = max(1, len(deck))
        scale = 30.0 / deck_size

        early_tempo = min(100.0, (early_drops * scale / 9.0) * 100.0)
        board_clear = min(100.0, (aoe_count * scale / 2.5) * 100.0)
        hard_removal = min(100.0, (removal_count * scale / 3.5) * 100.0)
        card_draw = min(100.0, (draw_count * scale / 5.0) * 100.0)
        reach_burst = min(100.0, (burst_count * scale / 2.5) * 100.0)

        # Max tribe synergy
        max_tribe_count = max(tribes.values()) if tribes else 0
        tribe_score = min(100.0, (max_tribe_count * scale / 5.0) * 100.0)

        overall = (early_tempo * 0.25 + board_clear * 0.15 + hard_removal * 0.15 + card_draw * 0.15 + reach_burst * 0.15 + tribe_score * 0.15)

        # Archetype title classification
        if tribe_score >= 60 and tribes:
            top_tribe = max(tribes, key=tribes.get)
            tribe_names = {"ELEMENTAL": "元素", "MECH": "机械", "DRAGON": "龙族", "BEAST": "野兽", "UNDEAD": "亡灵", "DEMON": "恶魔", "PIRATE": "海盗"}
            t_cn = tribe_names.get(top_tribe, top_tribe)
            title = f"🐉 {t_cn}连携体系"
        elif early_tempo >= 75 and reach_burst >= 60:
            title = "⚡ 极速突脸快攻 (Beatdown)"
        elif board_clear >= 70 and card_draw >= 60:
            title = "🛡️ 控场大核消耗 (Control)"
        elif early_tempo >= 65 and hard_removal >= 65:
            title = "⚖️ 扎实节奏中速 (Midrange Tempo)"
        else:
            title = "⚖️ 均势稳健体系"

        strengths = []
        if early_tempo >= 75:
            strengths.append(f"前中期曲线扎实 ({int(early_drops)}张低费前盘)")
        if board_clear >= 70:
            strengths.append(f"AOE 返场能力极强 ({aoe_count}张范围清场)")
        if hard_removal >= 70:
            strengths.append(f"单解充沛不惧大哥 ({removal_count}张大解)")
        if card_draw >= 70:
            strengths.append(f"手牌续航资源丰富 ({draw_count}张过牌补手)")

        vulnerabilities = []
        if early_tempo < 50:
            vulnerabilities.append("前期易卡手空过，急需补选 2-3 费优质站场随从")
        if card_draw < 40 and deck_size >= 15:
            vulnerabilities.append("中后期易打空手牌，建议补选过牌或优质发现")
        if board_clear < 35 and deck_size >= 15:
            vulnerabilities.append("缺少全场 AOE，失掉先手较难逆风翻盘")

        return SynergyRadarReport(
            early_tempo_score=round(early_tempo, 1),
            board_clear_score=round(board_clear, 1),
            hard_removal_score=round(hard_removal, 1),
            card_draw_score=round(card_draw, 1),
            reach_burst_score=round(reach_burst, 1),
            tribe_synergy_score=round(tribe_score, 1),
            overall_balance_score=round(overall, 1),
            archetype_title=title,
            strengths=strengths or ["攻防均衡"],
            vulnerabilities=vulnerabilities,
            tribe_counts=tribes,
        )
