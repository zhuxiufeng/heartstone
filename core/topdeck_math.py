"""
TopdeckMath: Probabilistic survival and lethal calculator for clutch arena turns.
Quantifies draw odds (outs) when facing imminent defeat, guiding players between passive defeat and high-EV topdeck play lines.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .card_db import CardInfo
from .deck_tracker import DeckTracker

logger = logging.getLogger("TopdeckMath")


@dataclass
class TopdeckAdvice:
    remaining_deck_count: int
    lethal_outs_count: int
    survival_outs_count: int
    topdeck_lethal_prob: float      # e.g. 25.0 (%)
    topdeck_survival_prob: float   # e.g. 33.3 (%)
    recommended_line: str           # "ALL_IN_FACE" or "STABILIZE"
    advice_text: str                # Formatted markdown advice


class TopdeckMath:
    """Calculates hyper-geometric topdeck probabilities for arena endgames."""

    @staticmethod
    def calculate_endgame_odds(
        deck_tracker: DeckTracker,
        friendly_hp: int,
        enemy_hp: int,
        friendly_field_atk: int,
        enemy_field_atk: int,
        current_turn: int,
    ) -> Optional[TopdeckAdvice]:
        """
        Calculates exact odds of topdecking an out when in danger.
        """
        stats = deck_tracker.get_stats()
        total_remaining = stats.total_remaining
        if total_remaining <= 0:
            return None

        # Categorize remaining cards into outs
        lethal_outs = []
        survival_outs = []

        missing_damage = max(0, enemy_hp - friendly_field_atk)

        for card, count in stats.remaining_cards:
            # Check lethal out
            card_dmg = 0
            # Direct burn spells
            if card.card_type == "SPELL":
                if "造成" in card.text or "伤害" in card.text:
                    import re
                    m = re.search(r"(\d+)点伤害", card.clean_text)
                    if m:
                        card_dmg = int(m.group(1))
                    elif "造成$" in card.text:
                        card_dmg = 6  # e.g. Fireball
            elif card.card_type == "WEAPON":
                card_dmg = card.attack or 0
            elif "CHARGE" in card.mechanics:
                card_dmg = card.attack or 0

            if card_dmg >= missing_damage and missing_damage > 0:
                lethal_outs.extend([card] * count)

            # Check survival out (Taunt, Heal, Board Clear)
            is_survival = False
            if "TAUNT" in card.mechanics:
                is_survival = True
            elif "消灭所有" in card.clean_text or "对所有随从" in card.clean_text:
                is_survival = True
            elif "恢复" in card.clean_text and "生命值" in card.clean_text:
                is_survival = True

            if is_survival:
                survival_outs.extend([card] * count)

        lethal_count = len(lethal_outs)
        survival_count = len(survival_outs)

        prob_lethal = (lethal_count / total_remaining) * 100.0
        prob_survival = (survival_count / total_remaining) * 100.0

        # Assess if player is under fatal pressure
        is_fatal_danger = (friendly_hp <= enemy_field_atk) or (friendly_hp <= 12 and enemy_field_atk >= 7)

        if not is_fatal_danger and prob_lethal == 0:
            return None

        if is_fatal_danger:
            if prob_lethal > 0 and friendly_field_atk > 0:
                out_names = ", ".join(set(c.name for c in lethal_outs[:2]))
                advice = (
                    f"🎲【神抽搏命决策】敌方场攻 ({enemy_field_atk}) 已达我方濒死线！"
                    f"牌库剩余 {total_remaining} 张，抽中【{out_names}】直接斩杀的概率为 **{prob_lethal:.1f}%**！"
                    f"被动解场必败，**唯一获胜路线：全员打脸压血，下回合拼 {prob_lethal:.1f}% 绝境翻盘！**"
                )
                line = "ALL_IN_FACE"
            elif prob_survival > 0:
                out_names = ", ".join(set(c.name for c in survival_outs[:2]))
                advice = (
                    f"🛡️【绝境防守】敌方下回合场攻逼近斩杀！"
                    f"牌库尚有 {survival_count}/{total_remaining} 张关键护命牌【{out_names}】(抽中率 **{prob_survival:.1f}%**)，"
                    f"本回合尽力以小换大延缓伤害，等待救命神抽！"
                )
                line = "STABILIZE"
            else:
                advice = f"⚠️ 敌方场攻 ({enemy_field_atk}) 极高，尽可能优先清理敌方高攻随从护脸！"
                line = "STABILIZE"
        else:
            if prob_lethal >= 15.0:
                out_names = ", ".join(set(c.name for c in lethal_outs[:2]))
                advice = (
                    f"⚡【斩杀在即】敌方仅余 {enemy_hp} 血！我方牌库抽中斩杀卡【{out_names}】概率为 **{prob_lethal:.1f}%**，"
                    f"可开始全力走脸压缩敌方血线，营造一击必杀窗口！"
                )
                line = "ALL_IN_FACE"
            else:
                return None

        return TopdeckAdvice(
            remaining_deck_count=total_remaining,
            lethal_outs_count=lethal_count,
            survival_outs_count=survival_count,
            topdeck_lethal_prob=prob_lethal,
            topdeck_survival_prob=prob_survival,
            recommended_line=line,
            advice_text=advice,
        )
