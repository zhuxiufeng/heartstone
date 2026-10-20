"""
HandTracker: Tracks opponent hand slots, cards held duration, mulligan keeps, and card origins (discoveries/coins).
Zero memory injection: Relies on Power.log entity state transitions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .card_db import CardDatabase, CardInfo

logger = logging.getLogger("HandTracker")


CLASS_ARENA_THREATS: Dict[str, List[Dict[str, Any]]] = {
    "MAGE": [
        {"name": "烈焰风暴", "cost": 7, "role": "7费全场清场"},
        {"name": "暴风雪", "cost": 6, "role": "6费全场冰冻AOE"},
        {"name": "变形术", "cost": 4, "role": "单体变羊硬解"},
        {"name": "巅峰无限", "cost": 4, "role": "无限资源"},
        {"name": "火球术", "cost": 4, "role": "6点斩杀直伤"},
    ],
    "PRIEST": [
        {"name": "精神控制", "cost": 10, "role": "10费拉大哥"},
        {"name": "圣光炸弹", "cost": 6, "role": "攻血清场"},
        {"name": "暗言术:灭", "cost": 2, "role": "单解高攻"},
        {"name": "真言术:宴", "cost": 2, "role": "随从滚雪球"},
    ],
    "WARLOCK": [
        {"name": "扭曲虚空", "cost": 8, "role": "全场硬消灭"},
        {"name": "地狱烈焰", "cost": 4, "role": "全场打3"},
        {"name": "亵渎", "cost": 2, "role": "阶梯连环全清"},
        {"name": "吸取灵魂", "cost": 2, "role": "打3吸血"},
    ],
    "PALADIN": [
        {"name": "守日者塔林姆", "cost": 6, "role": "全场变3/3逆转"},
        {"name": "奉献", "cost": 4, "role": "全场打2"},
        {"name": "生而平等", "cost": 2, "role": "配合解场"},
        {"name": "王者祝福", "cost": 4, "role": "核心贴皮爆发"},
    ],
    "HUNTER": [
        {"name": "暴龙王克鲁什", "cost": 9, "role": "8点冲锋绝杀"},
        {"name": "杀戮命令", "cost": 3, "role": "5点直伤终结"},
        {"name": "爆炸射击", "cost": 5, "role": "打5溅射打2"},
        {"name": "关门放狗", "cost": 3, "role": "突袭返场"},
    ],
    "DEATHKNIGHT": [
        {"name": "邪爆", "cost": 5, "role": "全场尸爆连清"},
        {"name": "绝望之线", "cost": 2, "role": "微型连环亡语清场"},
        {"name": "吸血鬼之血", "cost": 2, "role": "超上限巨额抬血"},
        {"name": "解冻", "cost": 2, "role": "极速过牌"},
    ],
    "WARRIOR": [
        {"name": "绝命乱斗", "cost": 5, "role": "翻盘乱斗"},
        {"name": "盾牌猛击", "cost": 1, "role": "高甲单解"},
        {"name": "斩杀", "cost": 2, "role": "消灭受伤随从"},
    ],
    "SHAMAN": [
        {"name": "闪电风暴", "cost": 3, "role": "全场打3过载"},
        {"name": "妖术", "cost": 4, "role": "单体变青蛙"},
        {"name": "潮汐奔涌", "cost": 4, "role": "单解打4回4"},
        {"name": "嗜血", "cost": 5, "role": "全场+3攻猝死爆发"},
    ],
    "ROGUE": [
        {"name": "刺杀", "cost": 4, "role": "单体消灭"},
        {"name": "闷棍", "cost": 2, "role": "大怪回手崩节奏"},
        {"name": "刀扇", "cost": 3, "role": "全场打1过牌"},
    ],
    "DRUID": [
        {"name": "横扫", "cost": 4, "role": "定向打4全场打1"},
        {"name": "滋养", "cost": 5, "role": "跳费/抽3张牌"},
        {"name": "自然平衡", "cost": 1, "role": "1费硬解"},
    ],
    "DEMONHUNTER": [
        {"name": "恶魔变形", "cost": 6, "role": "双回合10点直伤"},
        {"name": "刃缚精魂", "cost": 4, "role": "全场打4直伤"},
        {"name": "混乱打击", "cost": 2, "role": "攻击过牌"},
    ],
}


CN_TO_ENG_CLASS = {
    "法师": "MAGE",
    "牧师": "PRIEST",
    "术士": "WARLOCK",
    "圣骑士": "PALADIN",
    "骑士": "PALADIN",
    "猎人": "HUNTER",
    "潜行者": "ROGUE",
    "盗贼": "ROGUE",
    "德鲁伊": "DRUID",
    "萨满": "SHAMAN",
    "萨满祭司": "SHAMAN",
    "战士": "WARRIOR",
    "死亡骑士": "DEATHKNIGHT",
    "死骑": "DEATHKNIGHT",
    "恶魔猎手": "DEMONHUNTER",
    "瞎子": "DEMONHUNTER",
    "HERO_01": "WARRIOR",
    "HERO_02": "SHAMAN",
    "HERO_03": "ROGUE",
    "HERO_04": "PALADIN",
    "HERO_05": "HUNTER",
    "HERO_06": "DRUID",
    "HERO_07": "WARLOCK",
    "HERO_08": "MAGE",
    "HERO_09": "PRIEST",
    "HERO_10": "DEMONHUNTER",
    "HERO_11": "DEATHKNIGHT",
}


@dataclass
class OpponentHandCard:
    slot: int                       # 1-indexed hand position
    entity_id: int                  # Hearthstone internal entity ID
    turn_added: int                 # Turn when card entered hand
    turns_held: int = 0             # How many turns card has been held
    is_mulligan_keep: bool = False  # Kept through mulligan
    is_coin: bool = False           # Is this the Coin?
    creator_card: Optional[str] = None  # Name or ID of generator card (e.g. "暗影视界")
    card_info: Optional[CardInfo] = None # Known card if revealed
    deduction_label: str = ""       # Inferred role (e.g. "大概率高费解牌/大哥")
    unplayed_manas: List[int] = field(default_factory=list) # Available mana values when opponent held this card
    excluded_roles: List[str] = field(default_factory=list) # Categories 100% ruled out
    negative_deduction_note: str = "" # Formatted deduction summary


class HandTracker:
    """Manages opponent hand state, identifying cards kept from start and derived resources."""

    def __init__(self, card_db: Optional[CardDatabase] = None) -> None:
        self.card_db = card_db or CardDatabase.get_instance()
        self.cards: List[OpponentHandCard] = []
        self.current_turn: int = 1
        self.opponent_class: str = "UNKNOWN"
        self._next_virtual_id: int = 1000

    def set_opponent_class(self, opp_class: str) -> None:
        """Sets opponent class for targeted archetype and suspected card inference."""
        if opp_class:
            clean = str(opp_class).strip()
            upper = clean.upper()
            if upper in CLASS_ARENA_THREATS:
                self.opponent_class = upper
            elif clean in CN_TO_ENG_CLASS:
                self.opponent_class = CN_TO_ENG_CLASS[clean]
            elif upper in CN_TO_ENG_CLASS:
                self.opponent_class = CN_TO_ENG_CLASS[upper]
            else:
                self.opponent_class = upper

            # Refresh deductions
            for c in self.cards:
                c.deduction_label = self._deduce_card_role(c)

    def reset(self) -> None:
        """Reset match tracking."""
        self.cards.clear()
        self.current_turn = 1
        self.opponent_class = "UNKNOWN"
        logger.info("HandTracker state reset.")

    def set_turn(self, turn: int, opponent_mana: Optional[int] = None) -> None:
        """Updates current turn and recalculates turns_held and deduction labels for all cards."""
        self.current_turn = turn
        if opponent_mana is not None:
            self.record_turn_mana_passed(opponent_mana)
        for c in self.cards:
            c.turns_held = max(0, self.current_turn - c.turn_added)
            self._update_negative_deduction(c)
            c.deduction_label = self._deduce_card_role(c)

    def record_turn_mana_passed(self, available_mana: int) -> None:
        """
        Negative Deduction Trigger:
        Records that opponent had available_mana, yet chose not to play cards currently in hand.
        Eliminates on-curve proactive minions mathematically.
        """
        for c in self.cards:
            if not c.is_coin and available_mana not in c.unplayed_manas:
                c.unplayed_manas.append(available_mana)
                self._update_negative_deduction(c)

    def _update_negative_deduction(self, card: OpponentHandCard) -> None:
        """Computes mathematical exclusions based on turns and mana points passed."""
        if card.is_coin or card.creator_card:
            return

        exclusions = []
        manas = sorted(card.unplayed_manas)
        if 2 in manas:
            exclusions.append("2费站场随从")
        if 3 in manas:
            exclusions.append("3费站场随从")
        if 4 in manas:
            exclusions.append("4费单体生物")
        if 5 in manas:
            exclusions.append("5费主力随从")

        card.excluded_roles = exclusions

        if card.is_mulligan_keep and len(manas) >= 2:
            max_passed = max(manas) if manas else 0
            if max_passed >= 4:
                card.negative_deduction_note = f"🚫 100%排除 2~{max_passed} 费节奏生物 ➔ 锁定高费大哥(5+费)或AOE/硬解"
            elif max_passed >= 2:
                card.negative_deduction_note = f"🚫 排除前期 2~3 费节奏随从 ➔ 偏向功能法术/高费解牌"
        elif card.turns_held >= 3 and exclusions:
            card.negative_deduction_note = f"🚫 排除: {', '.join(exclusions[:2])}"

    def get_negative_deductions(self) -> List[Dict[str, Any]]:
        """Returns structured negative deduction cards for UI and AI evaluation."""
        results = []
        for c in self.cards:
            if c.negative_deduction_note:
                results.append({
                    "slot": c.slot,
                    "turns_held": c.turns_held,
                    "deduction": c.negative_deduction_note,
                    "excluded_roles": c.excluded_roles,
                })
        return results

    def _deduce_card_role(self, card: OpponentHandCard) -> str:
        """Infer probable identity of an opponent card based on holding duration and context."""
        if card.is_coin:
            return "🪙 幸运币"
        if card.creator_card:
            return f"🔮 衍生: 来自【{card.creator_card}】"

        # Class-specific threat inference
        opp_threats = CLASS_ARENA_THREATS.get(getattr(self, "opponent_class", "UNKNOWN"), [])
        suspected_names = []
        if opp_threats:
            for t in opp_threats:
                if t["cost"] <= self.current_turn + 1:
                    suspected_names.append(t["name"])
        suspected_str = f"，疑似【{'】/【'.join(suspected_names[:3])}】" if suspected_names else ""

        if card.turns_held >= 5 and card.is_mulligan_keep:
            return f"👑 起手死捏 {card.turns_held} 轮: 高费核心/大解{suspected_str}"
        if card.turns_held >= 4:
            return f"⏳ 蓄力 {card.turns_held} 轮: 蓄能大解/高费生物{suspected_str}"
        if card.turns_held <= 0:
            return "⚡ 本轮新抽卡"
        return f"捏牌 {card.turns_held} 轮"

    def init_opening_hand(self, card_count: int, has_coin: bool) -> None:
        """Called when opening hands are finalized after mulligan."""
        self.cards.clear()
        for idx in range(card_count):
            slot = idx + 1
            is_coin = has_coin and (slot == card_count)
            self._next_virtual_id += 1
            card = OpponentHandCard(
                slot=slot,
                entity_id=self._next_virtual_id,
                turn_added=1,
                turns_held=0,
                is_mulligan_keep=not is_coin,
                is_coin=is_coin,
                creator_card="幸运币" if is_coin else None,
            )
            self.cards.append(card)
        logger.info(f"Initialized opponent opening hand: {card_count} cards (Coin={has_coin})")

    def record_card_drawn(self, entity_id: Optional[int] = None, creator: Optional[str] = None) -> OpponentHandCard:
        """Called when opponent draws or generates a card into hand."""
        ent_id = entity_id or self._next_virtual_id + 1
        self._next_virtual_id = max(self._next_virtual_id, ent_id)

        slot = len(self.cards) + 1
        new_card = OpponentHandCard(
            slot=slot,
            entity_id=ent_id,
            turn_added=self.current_turn,
            turns_held=0,
            is_mulligan_keep=False,
            is_coin=False,
            creator_card=creator,
        )
        self.cards.append(new_card)
        logger.info(f"Opponent added card to slot #{slot} (created by: {creator})")
        return new_card

    def record_card_played(self, entity_id: Optional[int] = None, slot: Optional[int] = None) -> Optional[OpponentHandCard]:
        """Called when opponent plays a card from hand."""
        if not self.cards:
            return None

        target_card: Optional[OpponentHandCard] = None
        if entity_id:
            for c in self.cards:
                if c.entity_id == entity_id:
                    target_card = c
                    break
        elif slot and 1 <= slot <= len(self.cards):
            target_card = self.cards[slot - 1]

        if not target_card and self.cards:
            # Default to removing the latest or first card if slot not specified
            target_card = self.cards[-1]

        if target_card in self.cards:
            self.cards.remove(target_card)
            # Re-index remaining slots
            for idx, c in enumerate(self.cards):
                c.slot = idx + 1
            logger.info(f"Opponent played card from slot #{target_card.slot} (held {target_card.turns_held} turns)")

        return target_card

    def get_summary(self) -> Dict[str, Any]:
        """Returns statistical overview for overlay display."""
        total = len(self.cards)
        mulligan_keeps = sum(1 for c in self.cards if c.is_mulligan_keep)
        created_cards = [c for c in self.cards if c.creator_card and not c.is_coin]
        coin_present = any(c.is_coin for c in self.cards)

        # Longest held card
        longest_held = max((c.turns_held for c in self.cards), default=0)

        return {
            "total_count": total,
            "mulligan_keeps": mulligan_keeps,
            "created_count": len(created_cards),
            "created_details": [f"#{c.slot} 来自【{c.creator_card}】" for c in created_cards],
            "has_coin": coin_present,
            "longest_held_turns": longest_held,
            "cards": list(self.cards),
        }

    def get_display_text(self) -> str:
        """Formatted markdown for overlay UI."""
        summary = self.get_summary()
        total = summary["total_count"]
        if total == 0:
            return "敌方手牌: 0 张"

        lines = [f"**敌方手牌: {total} 张**"]
        if summary["mulligan_keeps"] > 0:
            lines.append(f"• 🚨 **{summary['mulligan_keeps']} 张起手留牌** (已蓄力 {summary['longest_held_turns']} 回合，谨防核心大解/变身)")
        if summary["created_count"] > 0:
            lines.append(f"• 🔮 **{summary['created_count']} 张额外衍生牌**: {', '.join(summary['created_details'])}")
        if summary["has_coin"]:
            lines.append("• 🪙 **保留幸运币** (注意防范突发跳费)")

        # Detailed card slot badges
        if self.cards:
            lines.append("\n**手牌明细与逆向推断:**")
            for c in self.cards[:7]:  # show up to 7 cards
                label = c.deduction_label or f"捏牌 {c.turns_held} 轮"
                lines.append(f"• `#{c.slot}` {label}")

        return "\n".join(lines)

    def has_long_held_cards(self, min_turns: int = 4) -> bool:
        """Returns True if opponent is holding cards for min_turns or longer."""
        return any(c.turns_held >= min_turns for c in self.cards)

    def get_threat_warnings(self) -> List[str]:
        """Provides concise actionable tactical warnings for AI strategic injection."""
        warnings = []
        opp_threats = CLASS_ARENA_THREATS.get(getattr(self, "opponent_class", "UNKNOWN"), [])
        suspected = [t["name"] for t in opp_threats if t["cost"] <= self.current_turn + 1]
        suspected_hint = f" (重点防范: 【{'】/【'.join(suspected[:2])}】)" if suspected else ""

        for c in self.cards:
            if c.is_mulligan_keep and c.turns_held >= 5:
                warnings.append(f"对手起手留牌(槽位#{c.slot})已屯{c.turns_held}回合未出，极大概率是关键高费大解或终结斩杀！{suspected_hint}")
            elif c.creator_card and not c.is_coin:
                warnings.append(f"对手槽位#{c.slot}为【{c.creator_card}】衍生牌，需防范特定非常规解牌！")
        return warnings

    def get_hand_reading_matrix(self) -> List[Dict[str, Any]]:
        """
        Calculates an advanced probability matrix for opponent held cards,
        estimating concrete card likelihoods based on mulligan holding and class rotation data.
        """
        matrix: List[Dict[str, Any]] = []
        opp_class = getattr(self, "opponent_class", "UNKNOWN")
        threats = CLASS_ARENA_THREATS.get(opp_class, [])

        for card in self.cards:
            if card.is_coin:
                matrix.append({
                    "slot": card.slot,
                    "turns_held": card.turns_held,
                    "label": "🪙 幸运币",
                    "inferred_card": "幸运币",
                    "probability_pct": 100.0,
                    "threat_level": "INFO",
                    "advice": "防范对手当回合或下回合提前1费跳费拍出关键大怪/清场！",
                })
            elif card.creator_card:
                matrix.append({
                    "slot": card.slot,
                    "turns_held": card.turns_held,
                    "label": f"🔮 衍生: 【{card.creator_card}】",
                    "inferred_card": f"【{card.creator_card}】衍生物",
                    "probability_pct": 90.0,
                    "threat_level": "WARNING",
                    "advice": "对手额外衍生物资源，可能包含跨职业技能或针对性解牌。",
                })
            elif card.is_mulligan_keep and card.turns_held >= 3:
                # High-value held card
                affordable = [t for t in threats if t["cost"] <= self.current_turn + 1]
                top_names = [t["name"] for t in affordable[:2]] if affordable else ["核心大解", "终结斩杀"]
                prob = min(88.0, 50.0 + card.turns_held * 8.0)
                matrix.append({
                    "slot": card.slot,
                    "turns_held": card.turns_held,
                    "label": f"🎯 起手留牌 (已捏 {card.turns_held} 回合)",
                    "inferred_card": " / ".join(top_names),
                    "probability_pct": prob,
                    "threat_level": "DANGER" if card.turns_held >= 5 else "WARNING",
                    "advice": f"持有{card.turns_held}回合未打，极大概率在等待时机打出【{' / '.join(top_names)}】！切勿全仓梭哈压场！",
                    "negative_deduction": card.negative_deduction_note,
                })
        return matrix

    def get_reading_matrix_text(self) -> str:
        """Returns concise formatted text of the hand reading matrix."""
        matrix = self.get_hand_reading_matrix()
        if not matrix:
            return "对手手牌均属于正常新抽牌，暂无高危沉淀留牌。"
        lines = []
        for item in matrix:
            neg_str = f" [{item['negative_deduction']}]" if item.get("negative_deduction") else ""
            lines.append(f"• 槽位#{item['slot']} [{item['label']}]: {item['inferred_card']} (研判概率 ~{item['probability_pct']:.0f}%){neg_str} ➔ {item['advice']}")
        return "\n".join(lines)
