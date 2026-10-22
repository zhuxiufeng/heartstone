"""
PostureEngine: Calculates the Beatdown Clock (turns to kill) and dynamic tactical posture (Aggro vs Control vs All-In).
Based on the classic "Who's the Beatdown?" theory adapted for Hearthstone Arena.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PostureEngine")


@dataclass
class BeatdownPivotAlert:
    has_pivoted: bool
    pivot_type: str            # "PIVOT_TO_OFFENSE", "PIVOT_TO_DEFENSE", "PIVOT_TO_ALL_IN", "STABLE"
    banner_badge: str          # e.g. "⚡【攻守易势·全面转攻】"
    action_directive: str      # Clear instruction for 3-second glanceability
    catalyst_reason: str       # What caused the flip
    previous_mode: str = ""
    current_mode: str = ""


@dataclass
class PostureAssessment:
    posture_mode: str          # "AGGRESSIVE" (全军突击抢脸), "CONTROL" (控场交换), "ALL_IN" (孤注一掷), "BALANCED" (稳健均势)
    friendly_clock_turns: int  # How many turns friendly board needs to kill opponent hero
    enemy_threat_turns: int    # How many turns enemy board needs to kill friendly hero
    tempo_score: float         # Positive means player is ahead on board tempo
    card_advantage: int        # Friendly hand count - Enemy hand count
    recommended_focus: str     # Main strategic direction
    detailed_reasoning: str    # Analytical breakdown
    pivot_alert: Optional[BeatdownPivotAlert] = None


class PostureEngine:
    """Evaluates match tempo, damage clocks, and determines whether to attack face or control board."""

    def __init__(self) -> None:
        pass

    def assess_posture(
        self,
        friendly_hp: int,
        enemy_hp: int,
        friendly_board_attack: int,
        enemy_board_attack: int,
        friendly_hand_count: int,
        enemy_hand_count: int,
        enemy_has_taunts: bool = False,
        current_turn: int = 1,
    ) -> PostureAssessment:
        """
        Computes the beatdown clock and strategic posture.
        """
        # 1. Clocks
        if friendly_board_attack > 0 and not enemy_has_taunts:
            friendly_clock = math.ceil(max(1, enemy_hp) / friendly_board_attack)
        elif friendly_board_attack > 0 and enemy_has_taunts:
            # Taunt absorbs time
            friendly_clock = math.ceil(max(1, enemy_hp) / friendly_board_attack) + 1
        else:
            friendly_clock = 99  # Zero board pressure

        if enemy_board_attack > 0:
            enemy_threat_turns = math.ceil(max(1, friendly_hp) / enemy_board_attack)
        else:
            enemy_threat_turns = 99

        card_advantage = friendly_hand_count - enemy_hand_count
        tempo_diff = friendly_board_attack - enemy_board_attack

        # 2. Strategic Posture Classification
        if friendly_clock <= 1:
            mode = "AGGRESSIVE"
            focus = "⚡ 斩杀冲刺！无视杂兵全力打脸，逼迫对手被动交解牌或直接赢下比赛"
            reason = f"我方场攻 ({friendly_board_attack}) 已进入终结射程，敌方血量剩余 {enemy_hp}，1回合斩杀。"
        elif friendly_clock <= 2 and enemy_threat_turns > 2:
            mode = "AGGRESSIVE"
            focus = "🔥 进攻压制 (Who's the Beatdown)！优先抢脸，将对手压入绝杀斩杀线"
            reason = f"我方 2 回合斩杀时钟已敲响，敌方无法在短期内反杀 (敌方斩杀时钟为 {enemy_threat_turns} 回合)。"
        elif friendly_hand_count <= 1 and enemy_hand_count >= 3 and enemy_hp <= 15:
            mode = "ALL_IN"
            focus = "⚔️ 孤注一掷 (All-in)！手牌续航见底，唯有以命搏命直接走脸抢胜机"
            reason = f"手牌资源差距已拉开 ({friendly_hand_count}张 vs {enemy_hand_count}张)，拖入后期必败，当前场面是唯一赢点。"
        elif enemy_threat_turns <= 2 and enemy_threat_turns < friendly_clock:
            mode = "CONTROL"
            focus = "🛡️ 稳固防守 (Control)！我方生命告急，严禁贪脸，务必优先解场与护脸"
            reason = f"我方生命值仅剩 {friendly_hp}，敌方拥有 {enemy_board_attack} 场攻，最快 {enemy_threat_turns} 回合致命！"
        elif tempo_diff >= 4 and card_advantage >= 0:
            mode = "BALANCED"
            focus = "⚖️ 滚雪球控场！通过优质白吃持续扩大场面，保持健康血量"
            reason = f"我方场面战力领先 {tempo_diff} 点，手牌资源充裕，稳扎稳打即可自然获胜。"
        else:
            mode = "CONTROL"
            focus = "🎯 伺机交换！化解敌方主要威胁随从，争取场面控制权"
            reason = f"当前处于均势博弈期，优先削减敌方高威胁生物以掌握主动权。"

        raw_assessment = PostureAssessment(
            posture_mode=mode,
            friendly_clock_turns=friendly_clock,
            enemy_threat_turns=enemy_threat_turns,
            tempo_score=float(tempo_diff),
            card_advantage=card_advantage,
            recommended_focus=focus,
            detailed_reasoning=reason,
        )

        # Detect dynamic pivot moment
        pivot_alert = DynamicPivotTracker.detect_pivot(
            current=raw_assessment,
            enemy_hand_count=enemy_hand_count,
            friendly_hp=friendly_hp,
            enemy_hp=enemy_hp,
        )
        raw_assessment.pivot_alert = pivot_alert
        return raw_assessment


class DynamicPivotTracker:
    """Tracks strategic role transitions and raises instant pivot alerts."""

    _last_mode: Optional[str] = None

    @classmethod
    def reset(cls) -> None:
        cls._last_mode = None

    @classmethod
    def detect_pivot(
        cls,
        current: PostureAssessment,
        enemy_hand_count: int = 4,
        friendly_hp: int = 30,
        enemy_hp: int = 30,
    ) -> BeatdownPivotAlert:
        prev_mode = cls._last_mode
        curr_mode = current.posture_mode
        cls._last_mode = curr_mode

        # Case 1: Switched to AGGRESSIVE (from non-AGGRESSIVE) or immediate critical offensive threshold
        if curr_mode == "AGGRESSIVE" and (prev_mode in ("CONTROL", "BALANCED", None) or enemy_hand_count <= 2 or current.friendly_clock_turns <= 2):
            if enemy_hand_count <= 2:
                catalyst = f"敌方手牌耗尽 (仅剩 {enemy_hand_count} 张)，已无续航手段"
            elif current.friendly_clock_turns <= 2:
                catalyst = f"我方斩杀时钟敲响 ({current.friendly_clock_turns} 回合)，敌方仅剩 {enemy_hp} 血"
            else:
                catalyst = f"我方场面战力压制 (领先 {current.tempo_score:.0f} 点)"

            return BeatdownPivotAlert(
                has_pivoted=True,
                pivot_type="PIVOT_TO_OFFENSE",
                banner_badge="⚡【攻守易势·全面转攻】",
                action_directive="【攻守易势】敌方资源耗尽，从防守全面转入抢脸终结阶段！",
                catalyst_reason=catalyst,
                previous_mode=prev_mode or "INITIAL",
                current_mode=curr_mode,
            )

        # Case 2: Switched to CONTROL (from AGGRESSIVE / BALANCED) or danger threshold
        if curr_mode == "CONTROL" and (prev_mode in ("AGGRESSIVE", "BALANCED") or friendly_hp <= 12):
            catalyst = f"我方生命滑落至警戒线 ({friendly_hp}血)，敌方最快 {current.enemy_threat_turns} 回合致命"
            return BeatdownPivotAlert(
                has_pivoted=True,
                pivot_type="PIVOT_TO_DEFENSE",
                banner_badge="🛡️【攻守易势·紧急筑防】",
                action_directive="【攻守易势】我方进入危险射程，停止冒进，全力稳健护脸！",
                catalyst_reason=catalyst,
                previous_mode=prev_mode or "INITIAL",
                current_mode=curr_mode,
            )

        # Case 3: ALL_IN pivot
        if curr_mode == "ALL_IN":
            return BeatdownPivotAlert(
                has_pivoted=True,
                pivot_type="PIVOT_TO_ALL_IN",
                banner_badge="⚔️【攻守易势·孤注一掷】",
                action_directive="【攻守易势】资源已脱节，拖入后期必败，抓住唯一窗口强行抢脸！",
                catalyst_reason="手牌见底，依靠当前场面抢死对手是数学唯一解",
                previous_mode=prev_mode or "INITIAL",
                current_mode=curr_mode,
            )

        return BeatdownPivotAlert(
            has_pivoted=False,
            pivot_type="STABLE",
            banner_badge="⚖️【战局平稳】",
            action_directive="维持当前战术节奏，按部就班推进",
            catalyst_reason="战术角色未发生剧烈跃迁",
            previous_mode=prev_mode or curr_mode,
            current_mode=curr_mode,
        )
