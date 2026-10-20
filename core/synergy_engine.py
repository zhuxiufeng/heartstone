"""
SynergyEngine: Detects archetype and tribal synergies between candidate cards and the existing draft deck.
Calculates bonus points and partner cards for mechanics like Deathrattle, Spell Damage, Mechs, Dragons, Elementals, etc.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .card_db import CardDatabase, CardInfo

logger = logging.getLogger("SynergyEngine")


@dataclass
class SynergyEvaluation:
    card: CardInfo
    bonus_score: float             # Score bonus (0.0 to 20.0) based on synergy depth
    synergy_type: str              # e.g., "亡语配合", "法强联动", "龙族储备", "机械磁力"
    partner_cards: List[str]       # Names of cards in deck that form this synergy
    explanation: str               # Human-readable tactical rationale


class SynergyEngine:
    """Calculates dynamic synergy bonuses for arena draft picks."""

    TRIBAL_KEYWORDS = {
        "BEAST": "野兽",
        "MECHANICAL": "机械",
        "DRAGON": "龙",
        "ELEMENTAL": "元素",
        "MURLOC": "鱼人",
        "DEMON": "恶魔",
        "UNDEAD": "亡灵",
        "PIRATE": "海盗",
        "TOTEM": "图腾",
    }

    def __init__(self, card_db: Optional[CardDatabase] = None) -> None:
        self.card_db = card_db or CardDatabase.get_instance()

    def evaluate_synergies(
        self,
        candidate: CardInfo,
        deck: List[CardInfo],
    ) -> SynergyEvaluation:
        """
        Analyzes synergy potential of a candidate card with the cards currently in the draft deck.
        """
        if not deck:
            return SynergyEvaluation(
                card=candidate,
                bonus_score=0.0,
                synergy_type="基础战力",
                partner_cards=[],
                explanation="套牌初期，优先建立扎实的基础身材与曲线。",
            )

        text = candidate.text or ""
        race = (candidate.race or "").upper()
        races = [r.upper() for r in candidate.races] if candidate.races else ([race] if race else [])
        mechanics = [m.upper() for m in candidate.mechanics]
        c_type = getattr(candidate, "card_type", getattr(candidate, "type", "MINION")).upper()

        best_bonus = 0.0
        best_type = "标准战力"
        best_partners: List[str] = []
        best_expl = "无显著机制联动，按单卡模组评判。"

        # 1. Deathrattle Synergy (亡语)
        has_deathrattle = "DEATHRATTLE" in mechanics or "亡语" in text
        triggers_deathrattle = any(kw in text for kw in ["亡语", "触发", "复生", "消灭"]) and ("亡语" in text)
        deck_deathrattles = [
            c.name for c in deck
            if "DEATHRATTLE" in [m.upper() for m in c.mechanics] or "亡语" in (c.text or "")
        ]

        if triggers_deathrattle and deck_deathrattles:
            bonus = min(12.0, len(deck_deathrattles) * 2.5)
            if bonus > best_bonus:
                best_bonus = bonus
                best_type = "亡语联动"
                best_partners = deck_deathrattles[:3]
                best_expl = f"与套牌中 {len(deck_deathrattles)} 张亡语卡牌具有极强触发配合 (估算额外 +{bonus:.1f}分)。"
        elif has_deathrattle and len(deck_deathrattles) >= 3:
            bonus = 4.0
            if bonus > best_bonus:
                best_bonus = bonus
                best_type = "亡语体系"
                best_partners = deck_deathrattles[:3]
                best_expl = f"进一步充实亡语体系储备，提高场面粘性 (+{bonus:.1f}分)。"

        # 2. Spell Damage Synergy (法术强度)
        has_spell_dmg = "SPELLPOWER" in mechanics or "法术伤害" in text
        deck_burn_spells = [
            c.name for c in deck
            if getattr(c, "card_type", getattr(c, "type", "")).upper() == "SPELL"
            and any(kw in (c.text or "") for kw in ["伤害", "造成"])
        ]

        if has_spell_dmg and deck_burn_spells:
            bonus = min(10.0, len(deck_burn_spells) * 2.5)
            if bonus > best_bonus:
                best_bonus = bonus
                best_type = "法强联动"
                best_partners = deck_burn_spells[:3]
                best_expl = f"为牌库中 {len(deck_burn_spells)} 张直伤解场法术提供伤害加深 (+{bonus:.1f}分)。"

        # 3. Tribal Synergy (种族: 龙/野兽/机械/元素等)
        for t_key, t_name in self.TRIBAL_KEYWORDS.items():
            is_tribe = (t_key in races)
            synergy_with_tribe = (t_name in text) or (t_key.lower() in text.lower())

            matching_tribe_cards = [
                c.name for c in deck
                if (c.race and c.race.upper() == t_key) or (c.races and t_key in [r.upper() for r in c.races])
            ]

            if synergy_with_tribe and matching_tribe_cards:
                bonus = min(12.0, len(matching_tribe_cards) * 3.0)
                if bonus > best_bonus:
                    best_bonus = bonus
                    best_type = f"{t_name}配合"
                    best_partners = matching_tribe_cards[:3]
                    best_expl = f"手牌联动: 牌库已拥有 {len(matching_tribe_cards)} 张{t_name}牌，极易触发效果 (+{bonus:.1f}分)。"
            elif is_tribe and len(matching_tribe_cards) >= 3:
                bonus = min(6.0, len(matching_tribe_cards) * 1.5)
                if bonus > best_bonus:
                    best_bonus = bonus
                    best_type = f"{t_name}储备"
                    best_partners = matching_tribe_cards[:3]
                    best_expl = f"强化{t_name}种族池厚度 (+{bonus:.1f}分)。"

        # 4. Weapon Synergy (武器配合)
        is_weapon = c_type == "WEAPON"
        has_weapon_buff = any(kw in text for kw in ["武器", "攻击力", "耐久度"]) and ("武器" in text)
        deck_weapons = [
            c.name for c in deck
            if getattr(c, "card_type", getattr(c, "type", "")).upper() == "WEAPON"
        ]

        if has_weapon_buff and deck_weapons:
            bonus = min(8.0, len(deck_weapons) * 2.5)
            if bonus > best_bonus:
                best_bonus = bonus
                best_type = "武器淬炼"
                best_partners = deck_weapons[:2]
                best_expl = f"强化套牌中的武器耐久与输出 (+{bonus:.1f}分)。"

        # 5. Excavate Synergy & Dependency (发掘体系联动与缺失预警)
        requires_excavate = ("下次发掘" in text or "当你发掘" in text)
        gives_excavate = ("发掘" in text) and not requires_excavate
        deck_excavates = [
            c.name for c in deck
            if "发掘" in (c.text or "") and "下次发掘" not in (c.text or "")
        ]
        deck_excavate_payoffs = [
            c.name for c in deck
            if "下次发掘" in (c.text or "") or "当你发掘" in (c.text or "")
        ]

        if requires_excavate:
            if deck_excavates:
                bonus = min(12.0, len(deck_excavates) * 4.5)
                if bonus > best_bonus:
                    best_bonus = bonus
                    best_type = "发掘联动"
                    best_partners = deck_excavates[:3]
                    best_expl = f"已抓【{'/'.join(best_partners)}】等 {len(deck_excavates)} 张发掘卡，可稳定触发本卡亡语 (+{bonus:.0f}分)。"
            else:
                best_bonus = -5.0
                best_type = "缺发掘源"
                best_partners = []
                best_expl = f"需【发掘】才能触发复生召唤，但当前已抓 {len(deck)} 张牌中尚无发掘组件 (-5分)。"
        elif gives_excavate and (deck_excavates or deck_excavate_payoffs):
            partners = (deck_excavate_payoffs + deck_excavates)[:3]
            bonus = min(10.0, len(deck_excavates) * 2.5 + len(deck_excavate_payoffs) * 4.5)
            if bonus > best_bonus:
                best_bonus = bonus
                best_type = "发掘推进"
                best_partners = partners
                best_expl = f"推进宝藏进度并与已抓【{'/'.join(partners)}】形成发掘连锁 (+{bonus:.0f}分)。"

        # 6. Discover & Value Multiplier (发现与衍生手牌深度估值)
        is_discover = "DISCOVER" in mechanics or "发现" in text
        is_generation = any(kw in text for kw in ["随机获得", "置入你的手牌", "将一张"]) and not is_discover
        if is_discover and best_bonus >= 0:
            discover_bonus = 8.0
            if "法术" in text:
                discover_bonus += 3.0  # Spells discover exact situational outs
            if "龙" in text or "随从" in text:
                discover_bonus += 2.0
            if discover_bonus > best_bonus:
                best_bonus = discover_bonus
                best_type = "发现机制"
                best_partners = []
                best_expl = f"竞技场关键支点: 动态3选1对局针对卡，打破构筑限制解决场面危机 (+{discover_bonus:.1f}分)。"
        elif is_generation and len(deck) >= 10 and best_bonus >= 0:
            gen_bonus = 4.5
            if gen_bonus > best_bonus:
                best_bonus = gen_bonus
                best_type = "手牌扩充"
                best_partners = []
                best_expl = f"提供不消耗原始套牌的额外手牌厚度 (+{gen_bonus:.1f}分)。"

        return SynergyEvaluation(
            card=candidate,
            bonus_score=round(best_bonus, 1),
            synergy_type=best_type,
            partner_cards=best_partners,
            explanation=best_expl,
        )
