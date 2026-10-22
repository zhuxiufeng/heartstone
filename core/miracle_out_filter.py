"""
MiracleOutFilter: Miracle Out Inversion Filter & Clutch Draw Odds (绝境神抽逆转抽滤雷达).
Identifies game-saving topdecks in the remaining deck during critical/losing states,
computing exact draw probabilities and pivoting tactical directives toward miracle lines.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("MiracleOutFilter")


@dataclass
class MiracleOutCard:
    card_name: str
    out_type: str                  # "LETHAL_OUT", "BOARD_WIPE_OUT", "SURVIVAL_OUT"
    out_type_cn: str
    copies_remaining: int
    draw_probability_pct: float
    impact_description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_name": self.card_name,
            "out_type": self.out_type,
            "out_type_cn": self.out_type_cn,
            "copies_remaining": self.copies_remaining,
            "draw_probability_pct": self.draw_probability_pct,
            "impact_description": self.impact_description,
        }


@dataclass
class MiracleOutReport:
    is_in_miracle_mode: bool
    total_miracle_probability_pct: float
    miracle_outs: List[MiracleOutCard] = field(default_factory=list)
    banner_text: str = ""
    tactical_callout: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_in_miracle_mode": self.is_in_miracle_mode,
            "total_miracle_probability_pct": self.total_miracle_probability_pct,
            "miracle_outs": [o.to_dict() for o in self.miracle_outs],
            "banner_text": self.banner_text,
            "tactical_callout": self.tactical_callout,
        }


KNOWN_LETHAL_OUTS = {
    "火球术": 6, "杀戮命令": 5, "横扫": 4, "刺骨": 4, "神圣惩击": 3,
    "闪电箭": 3, "熔岩爆裂": 5, "暗影箭": 4, "吸血鬼之血": 5, "火车王里诺艾": 6,
    "库卡隆精英卫士": 4, "真银圣剑": 4, "风暴战斧": 3,
}

KNOWN_WIPE_OUTS = {
    "烈焰风暴", "绝命乱斗", "扭曲虚空", "暴风雪", "地狱烈焰", "混乱新星", "神圣新星",
    "血液沸腾", "暗言术：毁",
}

KNOWN_SURVIVAL_OUTS = {
    "雷诺·杰克逊", "冰霜新星", "暂避锋芒", "淤泥喷射者", "恐狼先锋", "阿古斯防御者",
}


class MiracleOutFilter:
    """Filters deck for clutch outs and computes hypergeometric draw probabilities."""

    @classmethod
    def evaluate_miracle_outs(
        cls,
        winrate_pct: float,
        remaining_cards: List[Tuple[Any, int]],
        player_hp: int,
        enemy_hp: int,
        friendly_board_atk: int,
        enemy_board_atk: int,
    ) -> MiracleOutReport:
        # Miracle mode triggers when behind (winrate < 40%) or facing lethal board
        is_facing_death = enemy_board_atk >= player_hp and player_hp > 0
        if winrate_pct >= 40.0 and not is_facing_death:
            return MiracleOutReport(
                is_in_miracle_mode=False,
                total_miracle_probability_pct=0.0,
                miracle_outs=[],
                banner_text="",
                tactical_callout="当前局势正常，按常规价值交换展开。",
            )

        total_cards_left = sum(count for _, count in remaining_cards)
        if total_cards_left <= 0:
            return MiracleOutReport(
                is_in_miracle_mode=True,
                total_miracle_probability_pct=0.0,
                miracle_outs=[],
                banner_text="⚠️ 牌库已耗尽，无神抽可能",
                tactical_callout="牌库已空，全力走脸打光手牌拼最后一搏！",
            )

        hp_deficit = enemy_hp - friendly_board_atk
        miracle_cards: List[MiracleOutCard] = []

        # Scan remaining cards
        for card_obj, count in remaining_cards:
            c_name = getattr(card_obj, "name", str(card_obj))
            prob_pct = round((count / total_cards_left) * 100.0, 1)

            # 1. Lethal Out
            if c_name in KNOWN_LETHAL_OUTS and KNOWN_LETHAL_OUTS[c_name] >= hp_deficit:
                dmg = KNOWN_LETHAL_OUTS[c_name]
                miracle_cards.append(
                    MiracleOutCard(
                        card_name=c_name,
                        out_type="LETHAL_OUT",
                        out_type_cn="🎯 斩杀神抽",
                        copies_remaining=count,
                        draw_probability_pct=prob_pct,
                        impact_description=f"直伤打出 {dmg} 点直接绝杀对手",
                    )
                )
            # 2. Board Wipe Out
            elif c_name in KNOWN_WIPE_OUTS and is_facing_death:
                miracle_cards.append(
                    MiracleOutCard(
                        card_name=c_name,
                        out_type="BOARD_WIPE_OUT",
                        out_type_cn="🛡️ 清场救赎",
                        copies_remaining=count,
                        draw_probability_pct=prob_pct,
                        impact_description="全场清场化解敌方致命场攻威胁",
                    )
                )
            # 3. Survival Out
            elif c_name in KNOWN_SURVIVAL_OUTS and is_facing_death:
                miracle_cards.append(
                    MiracleOutCard(
                        card_name=c_name,
                        out_type="SURVIVAL_OUT",
                        out_type_cn="💖 续命护脸",
                        copies_remaining=count,
                        draw_probability_pct=prob_pct,
                        impact_description="筑起防线避免当回合猝死",
                    )
                )

        if not miracle_cards:
            return MiracleOutReport(
                is_in_miracle_mode=True,
                total_miracle_probability_pct=0.0,
                miracle_outs=[],
                banner_text="⚠️ 牌库无可直接逆转的标志单卡",
                tactical_callout="局势落后，尽量走脸给压力，等待对手失误。",
            )

        # Cumulative probability: 1 - product(1 - p_i)
        miss_prob = 1.0
        for out in miracle_cards:
            miss_prob *= (1.0 - (out.copies_remaining / total_cards_left))
        cum_prob_pct = round((1.0 - miss_prob) * 100.0, 1)

        out_summary = " | ".join(f"【{o.card_name}】({o.draw_probability_pct}%)" for o in miracle_cards[:2])
        banner = f"🔥 绝境逆转抽滤雷达: {len(miracle_cards)} 张救赎牌 · 累计翻盘概率 {cum_prob_pct}% ({out_summary})"
        directive = (
            f"局势落后 (胜率仅 {winrate_pct:.1f}%)！常规随从交换必败！"
            f"战术指令：全员弃防走脸，下回合以 {cum_prob_pct}% 概率赌神抽 {miracle_cards[0].card_name} 翻盘！"
        )

        return MiracleOutReport(
            is_in_miracle_mode=True,
            total_miracle_probability_pct=cum_prob_pct,
            miracle_outs=miracle_cards,
            banner_text=banner,
            tactical_callout=directive,
        )
