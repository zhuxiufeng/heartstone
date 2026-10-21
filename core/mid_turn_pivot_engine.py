"""
MidTurnPivotEngine: Real-Time Dynamic Mid-Turn Re-Planning Engine.
Dynamically re-evaluates and pivots remaining turn steps upon mid-turn entropy:
new card draws (e.g., from Lifetap/Arcane Intellect), RNG missile resolutions, or Discovery picks.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .master_copilot import CoPilotStep, CoPilotStepType, CoPilotTurnPlan

logger = logging.getLogger("MidTurnPivotEngine")


class MidTurnPivotEngine:
    """Modifies remaining steps on the fly without wiping turn history."""

    @classmethod
    def evaluate_pivot(
        cls,
        plan: CoPilotTurnPlan,
        event_type: str,            # "CARD_DRAWN", "RNG_RESOLVED", "DISCOVER_PICKED"
        drawn_card_name: str = "",
        drawn_card_damage: int = 0,
        enemy_hp: int = 30,
        friendly_board_attack: int = 0,
        available_mana: int = 0,
    ) -> CoPilotTurnPlan:
        if plan.is_completed:
            return plan

        current_idx = plan.active_step_index
        # Check if the newly drawn card or RNG resolution unlocks immediate lethal
        total_potential_damage = friendly_board_attack + drawn_card_damage
        if total_potential_damage >= enemy_hp and enemy_hp > 0:
            # PIVOT TO LETHAL!
            logger.info(f"Mid-turn pivot triggered: Immediate lethal unlocked via {drawn_card_name}!")
            new_remaining_steps: List[CoPilotStep] = []
            step_num = current_idx + 1

            if drawn_card_damage > 0:
                new_remaining_steps.append(
                    CoPilotStep(
                        step_number=step_num,
                        step_type=CoPilotStepType.PLAY_SPELL,
                        action_text=f"使用【{drawn_card_name}】直接打脸 ({drawn_card_damage}伤)",
                        source_label="手牌",
                        target_label="敌方英雄",
                        conversational_voice=f"神抽抓到了【{drawn_card_name}】！变更战术，直接甩脸！",
                        status="IN_PROGRESS",
                        ar_coords={"start_x": 0.5, "start_y": 0.88, "end_x": 0.5, "end_y": 0.2},
                        tactical_purpose="终结比赛",
                        is_critical_micro=True,
                    )
                )
                step_num += 1

            new_remaining_steps.append(
                CoPilotStep(
                    step_number=step_num,
                    step_type=CoPilotStepType.ATTACK_FACE,
                    action_text="全员随从走脸斩杀！",
                    source_label="我方战场",
                    target_label="敌方英雄",
                    conversational_voice="绝杀战机已现！全部战力全力走脸斩杀！",
                    status="PENDING",
                    ar_coords={"start_x": 0.5, "start_y": 0.58, "end_x": 0.5, "end_y": 0.2},
                    tactical_purpose="终结比赛",
                    is_critical_micro=True,
                )
            )

            # Preserve completed past steps, replace remaining
            completed_steps = plan.steps[:current_idx]
            plan.steps = completed_steps + new_remaining_steps
            plan.is_lethal_turn = True
            plan.macro_voice_overview = f"计划紧急修正：由于抽到【{drawn_card_name}】，直接转入斩杀流程！"
            plan.summary_markdown += f"\n\n⚡ **回合中战术修正**: 摸到 `{drawn_card_name}`，立即转入终结斩杀！"
            return plan

        # Default: if card drawn is playable and not lethal, append/adjust
        return plan
