"""
GamePhaseMachine: Adaptive Multi-Stage Tactical Transition State Machine.
Dynamically tracks match evolution across Mulligan, Early, Mid, Late, and Fatigue phases,
adaptively adjusting objective function weights for tempo, value, face pressure, and survival.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger("GamePhaseMachine")


class GamePhase(str, Enum):
    MULLIGAN = "MULLIGAN"
    EARLY_GAME = "EARLY_GAME"
    MID_GAME = "MID_GAME"
    LATE_GAME = "LATE_GAME"
    FATIGUE = "FATIGUE"


@dataclass
class GamePhaseState:
    phase: GamePhase
    phase_name_zh: str
    phase_name_en: str
    turn: int
    tempo_weight: float           # Relative importance of spending mana and establishing board
    card_advantage_weight: float  # Relative importance of drawing and preserving hand cards
    face_pressure_weight: float   # Relative importance of pushing enemy hero damage
    survival_weight: float        # Relative importance of defensive healing/armor/taunt
    strategic_directive: str      # Core strategic guideline for current phase
    curve_target: str             # Key mana bracket to utilize
    summary_markdown: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "phase_name_zh": self.phase_name_zh,
            "phase_name_en": self.phase_name_en,
            "turn": self.turn,
            "weights": {
                "tempo": round(self.tempo_weight, 2),
                "card_advantage": round(self.card_advantage_weight, 2),
                "face_pressure": round(self.face_pressure_weight, 2),
                "survival": round(self.survival_weight, 2),
            },
            "strategic_directive": self.strategic_directive,
            "curve_target": self.curve_target,
            "summary_markdown": self.summary_markdown,
        }


class GamePhaseMachine:
    """Manages adaptive phase transitions and dynamic heuristic weights."""

    PHASE_METADATA = {
        GamePhase.MULLIGAN: {
            "zh": "起手调度阶段",
            "en": "Mulligan Phase",
            "directive": "重点寻找1-3费平滑曲线生物，后手保留优质解牌或双3费跳币链。",
            "curve_target": "1~3 费先手铺垫",
            "base_weights": (1.9, 0.4, 0.3, 1.0),
        },
        GamePhase.EARLY_GAME: {
            "zh": "前期节奏争夺",
            "en": "Early Game (T1-T4)",
            "directive": "每回合最大化消耗法力水晶，强保场面控制权，严禁空过或裸抽英雄技能。",
            "curve_target": "2~4 费高效随从站场",
            "base_weights": (1.8, 0.6, 0.5, 0.9),
        },
        GamePhase.MID_GAME: {
            "zh": "中期资源与场面交换",
            "en": "Mid Game (T5-T7)",
            "directive": "权衡场面攻防与手牌续航，防范对手对位高费关键AOE，展开价值交换。",
            "curve_target": "5~7 费高质量生物与解场",
            "base_weights": (1.3, 1.1, 1.0, 1.1),
        },
        GamePhase.LATE_GAME: {
            "zh": "残局斩杀冲刺",
            "en": "Late Game (T8+)",
            "directive": "精算双方打脸斩杀时钟，将手牌资源转化为直接斩杀或压倒性终结场面。",
            "curve_target": "8+ 费高费大哥与终结技",
            "base_weights": (0.7, 1.4, 1.8, 1.5),
        },
        GamePhase.FATIGUE: {
            "zh": "疲劳决战时刻",
            "en": "Fatigue Showdown",
            "directive": "牌库见底，严格禁止盲目过牌，全力压制对手血线以疲劳倒计时决胜。",
            "curve_target": "最大化伤害与护脸",
            "base_weights": (0.4, 0.3, 2.2, 2.0),
        },
    }

    @classmethod
    def evaluate(
        cls,
        current_turn: int,
        available_mana: int = 1,
        remaining_deck_count: int = 20,
        friendly_hp: int = 30,
        enemy_hp: int = 30,
    ) -> GamePhaseState:
        # Determine Phase
        if current_turn <= 0:
            phase = GamePhase.MULLIGAN
        elif remaining_deck_count <= 2:
            phase = GamePhase.FATIGUE
        elif current_turn <= 4:
            phase = GamePhase.EARLY_GAME
        elif current_turn <= 7:
            phase = GamePhase.MID_GAME
        else:
            phase = GamePhase.LATE_GAME

        meta = cls.PHASE_METADATA[phase]
        base_tempo, base_card, base_face, base_surv = meta["base_weights"]

        # Dynamic survival modifier: if friendly HP is low, spike survival weight
        if friendly_hp <= 12:
            survival_mult = 1.0 + (13 - friendly_hp) * 0.1
            base_surv *= survival_mult
            base_face *= 0.8
        elif friendly_hp >= 25 and enemy_hp <= 15:
            # Enemy low, our HP high -> spike face pressure
            base_face *= 1.4
            base_tempo *= 1.2

        summary_md = (
            f"**当前战术阶段**: **{meta['zh']}** ({meta['en']})\n"
            f"• **核心战术指标**: {meta['directive']}\n"
            f"• **自适应权重**: 节奏控场 `{base_tempo:.1f}` | 手牌价值 `{base_card:.1f}` | 打脸斩杀 `{base_face:.1f}` | 生命防守 `{base_surv:.1f}`"
        )

        return GamePhaseState(
            phase=phase,
            phase_name_zh=meta["zh"],
            phase_name_en=meta["en"],
            turn=max(0, current_turn),
            tempo_weight=base_tempo,
            card_advantage_weight=base_card,
            face_pressure_weight=base_face,
            survival_weight=base_surv,
            strategic_directive=meta["directive"],
            curve_target=meta["curve_target"],
            summary_markdown=summary_md,
        )
