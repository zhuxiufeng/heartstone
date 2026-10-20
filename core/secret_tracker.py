"""
SecretTracker: Tracks opponent secrets and eliminates candidates based on in-game actions.
Zero memory injection: Relies entirely on event triggers (log events or user testing).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from .card_db import CardDatabase, CardInfo

logger = logging.getLogger("SecretTracker")


class TriggerType(str, Enum):
    ATTACK_HERO = "ATTACK_HERO"          # Minion/Hero attacks opponent hero
    ATTACK_MINION = "ATTACK_MINION"      # Minion attacks opponent minion
    PLAY_MINION = "PLAY_MINION"          # Friendly minion played from hand
    CAST_SPELL = "CAST_SPELL"            # Friendly spell cast
    HERO_POWER = "HERO_POWER"            # Friendly hero power used
    MINION_DIES = "MINION_DIES"          # Friendly or enemy minion died
    PLAY_CARD_COUNT = "PLAY_CARD_COUNT"  # 3rd card played in turn
    TURN_END = "TURN_END"                # Turn ended


@dataclass
class SecretDefinition:
    name: str
    hero_class: str
    triggers: List[TriggerType]
    description: str
    mana_cost: int
    card_id: str = ""


# Standard Secret Pool by Class
KNOWN_SECRETS: List[SecretDefinition] = [
    # Mage Secrets (3 Mana)
    SecretDefinition("寒冰屏障", "MAGE", [TriggerType.ATTACK_HERO], "受到致命伤害时免疫一回合", 3, "EX1_295"),
    SecretDefinition("寒冰护体", "MAGE", [TriggerType.ATTACK_HERO], "英雄被攻击时获得8点护甲", 3, "EX1_289"),
    SecretDefinition("蒸发", "MAGE", [TriggerType.ATTACK_HERO], "随从攻击英雄时将其消灭", 3, "EX1_594"),
    SecretDefinition("绿洲盟友", "MAGE", [TriggerType.ATTACK_HERO], "随从攻击英雄时召唤3/6嘲讽水元素", 3, "BAR_546"),
    SecretDefinition("法术反制", "MAGE", [TriggerType.CAST_SPELL], "施放法术时法术无效化", 3, "EX1_612"),
    SecretDefinition("净天圣步", "MAGE", [TriggerType.CAST_SPELL], "施放法术时召唤随机4费随从", 3, "BT_003"),
    SecretDefinition("镜像实体", "MAGE", [TriggerType.PLAY_MINION], "打出随从时复制该随从", 3, "EX1_294"),
    SecretDefinition("爆炸符文", "MAGE", [TriggerType.PLAY_MINION], "打出随从时对其造成6点伤害溢出给脸", 3, "LOOT_101"),
    SecretDefinition("异议", "MAGE", [TriggerType.PLAY_MINION], "打出随从时反制并消灭该随从", 3, "REV_829"),

    # Hunter Secrets (2 Mana)
    SecretDefinition("爆炸陷阱", "HUNTER", [TriggerType.ATTACK_HERO], "英雄受到攻击时全场敌方打2", 2, "EX1_610"),
    SecretDefinition("误导", "HUNTER", [TriggerType.ATTACK_HERO], "英雄受到攻击时使攻击者随机攻击另一目标", 2, "EX1_533"),
    SecretDefinition("游荡怪物", "HUNTER", [TriggerType.ATTACK_HERO], "英雄受到攻击时召唤随机3费随从代为承受", 2, "LOOT_079"),
    SecretDefinition("冰冻陷阱", "HUNTER", [TriggerType.ATTACK_HERO, TriggerType.ATTACK_MINION], "敌方随从攻击时移回手牌且费用+2", 2, "EX1_611"),
    SecretDefinition("毒蛇陷阱", "HUNTER", [TriggerType.ATTACK_MINION], "随从受到攻击时召唤三条1/1蛇", 2, "EX1_554"),
    SecretDefinition("狙击", "HUNTER", [TriggerType.PLAY_MINION], "打出随从时对其造成4点伤害", 2, "EX1_609"),
    SecretDefinition("压制", "HUNTER", [TriggerType.CAST_SPELL], "施放法术后随机消灭一个敌方随从", 2, "ULD_152"),
    SecretDefinition("冰霜陷阱", "HUNTER", [TriggerType.CAST_SPELL], "施放法术时将其移回手牌且费用+1", 2, "AV_224"),
    SecretDefinition("捕鼠陷阱", "HUNTER", [TriggerType.PLAY_CARD_COUNT], "单回合打出3张牌后召唤6/6老鼠", 2, "GIL_577"),

    # Paladin Secrets (1 Mana)
    SecretDefinition("崇高牺牲", "PALADIN", [TriggerType.ATTACK_HERO, TriggerType.ATTACK_MINION], "敌人攻击时召唤2/1挡刀", 1, "EX1_130"),
    SecretDefinition("救赎", "PALADIN", [TriggerType.MINION_DIES], "随从死亡时复活并具有1点生命值", 1, "EX1_136"),
    SecretDefinition("复仇", "PALADIN", [TriggerType.MINION_DIES], "随从死亡时使另一个随机友方随从+3/+2", 1, "FP1_020"),
    SecretDefinition("忏悔", "PALADIN", [TriggerType.PLAY_MINION], "打出随从时其生命值降为1", 1, "EX1_379"),
    SecretDefinition("审判", "PALADIN", [TriggerType.PLAY_MINION], "场上有3个随从打出随从时将其消灭", 1, "LOE_027"),
    SecretDefinition("永不屈服", "PALADIN", [TriggerType.CAST_SPELL], "施放法术时友方随从+2生命值", 1, "DAL_570"),
    SecretDefinition("古神在上", "PALADIN", [TriggerType.CAST_SPELL], "施放法术时随机变成同费法术", 1, "DMF_236"),
    SecretDefinition("迅捷救援", "PALADIN", [TriggerType.PLAY_CARD_COUNT], "单回合打出3张牌后召唤3/4圣盾步兵", 1, "BAR_550"),

    # Rogue Secrets (2 Mana)
    SecretDefinition("闪避", "ROGUE", [TriggerType.ATTACK_HERO], "英雄受到伤害后本回合获得免疫", 2, "LOOT_214"),
    SecretDefinition("伏击", "ROGUE", [TriggerType.PLAY_MINION], "打出随从时召唤2/3剧毒潜行随从", 2, "BT_707"),
    SecretDefinition("邪恶交易", "ROGUE", [TriggerType.CAST_SPELL], "施放法术后对手抽两张牌", 2, "BT_709"),
    SecretDefinition("匿踪", "ROGUE", [TriggerType.ATTACK_MINION], "随从受到攻击时将其随机变形为+1费随从", 2, "BT_701"),
    SecretDefinition("抄袭", "ROGUE", [TriggerType.TURN_END], "回合结束时复制对手打出的所有卡牌", 2, "SCH_706"),
]


@dataclass
class ActiveSecret:
    secret_id: int
    hero_class: str
    turn_played: int
    eliminated_names: Set[str] = field(default_factory=set)


class SecretTracker:
    """Manages active secrets for the opponent and performs Bayesian-style rule elimination."""

    def __init__(self, card_db: Optional[CardDatabase] = None) -> None:
        self.card_db = card_db or CardDatabase.get_instance()
        self.active_secrets: List[ActiveSecret] = []
        self._secret_counter = 0

    def reset(self) -> None:
        """Clear all secret tracking state."""
        self.active_secrets.clear()
        self._secret_counter = 0
        logger.info("Secret tracker state reset.")

    def add_opponent_secret(self, hero_class: str, turn: int = 1) -> int:
        """Called when opponent plays an unknown secret."""
        self._secret_counter += 1
        secret = ActiveSecret(
            secret_id=self._secret_counter,
            hero_class=hero_class.upper(),
            turn_played=turn,
            eliminated_names=set(),
        )
        self.active_secrets.append(secret)
        logger.info(f"Added secret #{secret.secret_id} for {hero_class} at turn {turn}")
        return secret.secret_id

    def remove_secret(self, secret_id: int) -> None:
        """Called when a secret triggers or is revealed/destroyed."""
        self.active_secrets = [s for s in self.active_secrets if s.secret_id != secret_id]
        logger.info(f"Removed secret #{secret_id}")

    def on_game_action(self, trigger: TriggerType, context: Optional[Dict] = None) -> None:
        """
        Record a gameplay action that DID NOT trigger any secrets.
        All secrets with this trigger type are eliminated from the possible candidate set.
        """
        for secret in self.active_secrets:
            candidates = [s for s in KNOWN_SECRETS if s.hero_class == secret.hero_class]
            for cand in candidates:
                if trigger in cand.triggers:
                    secret.eliminated_names.add(cand.name)
                    logger.debug(f"Secret #{secret.secret_id}: Eliminated {cand.name} via {trigger.value}")

    def get_possible_secrets(self, secret_id: Optional[int] = None) -> Dict[int, List[SecretDefinition]]:
        """
        Returns surviving possible secrets for each active secret.
        """
        results: Dict[int, List[SecretDefinition]] = {}
        for s in self.active_secrets:
            if secret_id is not None and s.secret_id != secret_id:
                continue
            all_for_class = [cand for cand in KNOWN_SECRETS if cand.hero_class == s.hero_class]
            surviving = [cand for cand in all_for_class if cand.name not in s.eliminated_names]
            results[s.secret_id] = surviving
        return results

    def get_summary_text(self) -> str:
        """Returns user-readable markdown text for overlay display."""
        if not self.active_secrets:
            return "当前敌方头上无奥秘。"

        lines = [f"**敌方当前挂有 {len(self.active_secrets)} 个奥秘:**"]
        possible_map = self.get_possible_secrets()
        for s in self.active_secrets:
            surviving = possible_map.get(s.secret_id, [])
            cand_names = [f"`{c.name}`" for c in surviving]
            if not cand_names:
                lines.append(f"• 奥秘 #{s.secret_id} ({s.hero_class}): 未知新版奥秘")
            else:
                lines.append(f"• 奥秘 #{s.secret_id} ({s.hero_class}) 可能为: {', '.join(cand_names)}")
                if s.eliminated_names:
                    lines.append(f"  *(已排除: {', '.join(list(s.eliminated_names)[:5])})*")
        return "\n".join(lines)
