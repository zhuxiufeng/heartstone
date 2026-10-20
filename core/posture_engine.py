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
class PostureAssessment:
    posture_mode: str          # "AGGRESSIVE" (全军突击抢脸), "CONTROL" (控场交换), "ALL_IN" (孤注一掷), "BALANCED" (稳健均势)
    friendly_clock_turns: int  # How many turns friendly board needs to kill opponent hero
    enemy_threat_turns: int    # How many turns enemy board needs to kill friendly hero
    tempo_score: float         # Positive means player is ahead on board tempo
    card_advantage: int        # Friendly hand count - Enemy hand count
    recommended_focus: str     # Main strategic direction
    detailed_reasoning: str    # Analytical breakdown


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

        return PostureAssessment(
            posture_mode=mode,
            friendly_clock_turns=friendly_clock,
            enemy_threat_turns=enemy_threat_turns,
            tempo_score=float(tempo_diff),
            card_advantage=card_advantage,
            recommended_focus=focus,
            detailed_reasoning=reason,
        )
