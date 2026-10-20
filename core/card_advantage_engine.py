"""
CardAdvantageEngine: Hand Starvation, Resource Burn & Anti-Overextend Strategy.
Leverages hand differential to trigger Choke Out (forcing topdeck lethals) or Anti-Overextend protection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger("CardAdvantageEngine")


class ResourceState(Enum):
    CHOKE_OUT = "CHOKE_OUT"              # 对手断牌枯竭，全力打脸压死
    ANTI_OVEREXTEND = "ANTI_OVEREXTEND"  # 对手手牌充足，谨防全场被清
    BALANCED = "BALANCED"                # 资源均势


@dataclass
class ResourceAdvantagePlan:
    state: ResourceState
    friendly_hand: int
    enemy_hand: int
    hand_diff: int                       # friendly - enemy
    choke_pressure_active: bool
    anti_overextend_warning: bool
    strategic_directive: str


class CardAdvantageEngine:
    """Evaluates relative card advantage to direct tempo versus value commitments."""

    @classmethod
    def evaluate_resource_dynamics(
        cls,
        friendly_hand_count: int,
        enemy_hand_count: int,
        friendly_board_count: int,
        enemy_hp: int,
        turn_number: int,
    ) -> ResourceAdvantagePlan:
        """
        Assesses card advantage and switches tactical directives between Starvation Choke and Anti-Overextend.
        """
        diff = friendly_hand_count - enemy_hand_count

        # Scenario 1: Enemy is starved of cards (<= 2 cards in hand)
        if enemy_hand_count <= 2 and turn_number >= 4:
            directive = (
                f"📭【敌方手牌断档·断牌压迫】对手仅余 {enemy_hand_count} 张手牌！已丧失灵活战术应对能力！"
                f"严禁被动解场给对手喘息机会，果断全员走脸压低血线，迫使对手单靠右手第一张神抽来应对！"
            )
            return ResourceAdvantagePlan(
                state=ResourceState.CHOKE_OUT,
                friendly_hand=friendly_hand_count,
                enemy_hand=enemy_hand_count,
                hand_diff=diff,
                choke_pressure_active=True,
                anti_overextend_warning=False,
                strategic_directive=directive,
            )

        # Scenario 2: Enemy holds a full hand (>= 6 cards) while we already have 3+ minions on board
        if enemy_hand_count >= 6 and friendly_board_count >= 3:
            directive = (
                f"📦【防过度投资】对手手握 {enemy_hand_count} 张海量手牌，极大概率持有职业清场解牌！"
                f"场上已有 {friendly_board_count} 个战力，手牌中保留 1~2 张后续随从，切勿一次性铺光！"
            )
            return ResourceAdvantagePlan(
                state=ResourceState.ANTI_OVEREXTEND,
                friendly_hand=friendly_hand_count,
                enemy_hand=enemy_hand_count,
                hand_diff=diff,
                choke_pressure_active=False,
                anti_overextend_warning=True,
                strategic_directive=directive,
            )

        # Scenario 3: Standard value advantage
        if diff >= 3:
            directive = f"💎【卡差大幅领先 (+{diff}张)】我方手牌储备充裕，可以稳健以小换大磨死对手。"
        elif diff <= -3:
            directive = f"⚡【卡差落后 ({diff}张)】资源落后，拖入大后期必败，必须加快进攻节奏抢脸终结！"
        else:
            directive = f"⚖️【手牌均势】双方手牌持平 ({friendly_hand_count} vs {enemy_hand_count})，按费拍怪维持压制。"

        return ResourceAdvantagePlan(
            state=ResourceState.BALANCED,
            friendly_hand=friendly_hand_count,
            enemy_hand=enemy_hand_count,
            hand_diff=diff,
            choke_pressure_active=False,
            anti_overextend_warning=False,
            strategic_directive=directive,
        )
