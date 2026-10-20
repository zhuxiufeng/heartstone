"""
MulliganHandReader: Slot-level origin & holding duration inference engine.
Analyzes opponent's hand cards based on mulligan keep status and holding turns to deduce high-impact bombs vs situational cards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .hand_tracker import OpponentHandCard

logger = logging.getLogger("MulliganHandReader")


class CardOrigin(Enum):
    MULLIGAN_KEPT = "起手保留"
    TOPDECK = "回合抽牌"
    GENERATED = "额外衍生"
    COIN = "幸运币"


@dataclass
class SlotDeduction:
    slot: int
    origin: CardOrigin
    turns_held: int
    danger_level: str           # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    probable_card_type: str     # e.g., "高费全场大解或泰坦", "按费生物", "特定应对牌"
    inference_detail: str


@dataclass
class MulliganHandAnalysis:
    total_cards: int
    mulligan_kept_count: int
    bombs_in_hand_estimate: int
    slot_deductions: List[SlotDeduction] = field(default_factory=list)
    strategic_directive: str = ""


class MulliganHandReader:
    """
    Deduces exact card roles from hand position and time held.
    """

    @classmethod
    def analyze_opponent_hand(
        cls,
        cards: List[OpponentHandCard],
        current_turn: int,
        opponent_class: str = "MAGE",
    ) -> MulliganHandAnalysis:
        """
        Processes opponent hand cards to generate precise tactical reads.
        """
        deductions: List[SlotDeduction] = []
        bombs_count = 0
        mulligan_kept = 0

        for c in cards:
            turns = c.turns_held

            # 1. Coin check
            if c.is_coin:
                deductions.append(SlotDeduction(
                    slot=c.slot,
                    origin=CardOrigin.COIN,
                    turns_held=turns,
                    danger_level="LOW",
                    probable_card_type="幸运币",
                    inference_detail="提供1点额外水晶节奏跳费",
                ))
                continue

            # 2. Generated / Discovered check
            if c.creator_card:
                deductions.append(SlotDeduction(
                    slot=c.slot,
                    origin=CardOrigin.GENERATED,
                    turns_held=turns,
                    danger_level="MEDIUM",
                    probable_card_type=f"衍生资源 (来自【{c.creator_card}】)",
                    inference_detail=f"对手根据当时局势主动挑选的针对牌，大概率含解场或返场",
                ))
                continue

            # 3. Mulligan Keep
            if c.is_mulligan_keep:
                mulligan_kept += 1
                if current_turn >= 5 and turns >= 4:
                    # Grandmaster rule: No one holds a 2-drop for 5 turns. It's an end-game bomb or wipe!
                    bombs_count += 1
                    deductions.append(SlotDeduction(
                        slot=c.slot,
                        origin=CardOrigin.MULLIGAN_KEPT,
                        turns_held=turns,
                        danger_level="CRITICAL",
                        probable_card_type="高费全场清场(AOE)或终极泰坦",
                        inference_detail=(
                            f"第{c.slot}号位起手深捏{turns}回合未动！"
                            f"90%概率为{opponent_class}核心大解(如烈焰风暴/扭曲虚空/乱斗)或泰坦巨型，严禁倾泻所有手牌铺场！"
                        ),
                    ))
                elif current_turn <= 3:
                    deductions.append(SlotDeduction(
                        slot=c.slot,
                        origin=CardOrigin.MULLIGAN_KEPT,
                        turns_held=turns,
                        danger_level="LOW",
                        probable_card_type="前期黄金按费节奏牌",
                        inference_detail="起手保留的1-3费平滑生物或早期优质解牌",
                    ))
                else:
                    deductions.append(SlotDeduction(
                        slot=c.slot,
                        origin=CardOrigin.MULLIGAN_KEPT,
                        turns_held=turns,
                        danger_level="HIGH",
                        probable_card_type="中高费针对解牌或蓄势核心",
                        inference_detail=f"保留至第{current_turn}回合，随时准备在均势期翻盘",
                    ))
                continue

            # 4. Topdecked cards
            if turns == 0:
                deductions.append(SlotDeduction(
                    slot=c.slot,
                    origin=CardOrigin.TOPDECK,
                    turns_held=0,
                    danger_level="LOW",
                    probable_card_type="本回合即抽即打牌/随机过牌",
                    inference_detail="新抽入卡牌，尚未沉淀为长期对局威慑",
                ))
            else:
                deductions.append(SlotDeduction(
                    slot=c.slot,
                    origin=CardOrigin.TOPDECK,
                    turns_held=turns,
                    danger_level="MEDIUM",
                    probable_card_type="情境应对牌 (缺乏时机打出)",
                    inference_detail=f"抽入后保留{turns}回合，因费用或场面不符暂时待命",
                ))

        # Overall strategic directive
        if bombs_count > 0:
            directive = (
                f"⚠️ 读牌警报: 探测到对手手中存在 {bombs_count} 张起手深捏大核！"
                "绝非前期小怪，务必提防下回合大AOE清场或泰坦翻盘，保持可持续场面施压。"
            )
        elif mulligan_kept > 0 and current_turn <= 4:
            directive = f"ℹ️ 读牌提示: 对手手牌含 {mulligan_kept} 张起手保留卡，防对手按费下怪天胡展开。"
        else:
            directive = "✅ 读牌分析: 对手深捏手牌已被消耗殆尽，多为新抽或衍生牌，压迫感低可大胆控场。"

        return MulliganHandAnalysis(
            total_cards=len(cards),
            mulligan_kept_count=mulligan_kept,
            bombs_in_hand_estimate=bombs_count,
            slot_deductions=deductions,
            strategic_directive=directive,
        )
