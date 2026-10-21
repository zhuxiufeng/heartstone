"""
MasterCoPilot: Real-Time Every-Step Grandmaster Co-Pilot Engine.
Deconstructs turn plans into discrete, sequential atomic steps,
provides companion conversational voice whispering, and guides player actions step-by-step.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("MasterCoPilot")


class CoPilotStepType(str, Enum):
    DRAW_FIRST = "DRAW_FIRST"          # 优先过牌探路
    AURA_BUFF = "AURA_BUFF"            # 先下光环/群体增益随从
    HERO_POWER = "HERO_POWER"          # 英雄技能点杀/补刀
    TRADE_MINION = "TRADE_MINION"      # 随从白吃/解场交换
    PLAY_SPELL = "PLAY_SPELL"          # 施放法术解场/清场
    PLAY_MINION = "PLAY_MINION"        # 随从按费站场
    ATTACK_FACE = "ATTACK_FACE"        # 全力打脸走脸/斩杀
    END_TURN = "END_TURN"              # 结束回合


@dataclass
class CoPilotStep:
    step_number: int
    step_type: CoPilotStepType
    action_text: str
    source_label: str
    target_label: str
    conversational_voice: str
    status: str                        # "PENDING", "IN_PROGRESS", "COMPLETED", "SKIPPED"
    ar_coords: Dict[str, float] = field(default_factory=dict)
    tactical_purpose: str = ""
    is_critical_micro: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "step_type": self.step_type.value,
            "action_text": self.action_text,
            "source_label": self.source_label,
            "target_label": self.target_label,
            "conversational_voice": self.conversational_voice,
            "status": self.status,
            "ar_coords": self.ar_coords,
            "tactical_purpose": self.tactical_purpose,
            "is_critical_micro": self.is_critical_micro,
        }


@dataclass
class CoPilotTurnPlan:
    turn_number: int
    active_step_index: int             # 0-based index of current pending step
    steps: List[CoPilotStep]
    macro_voice_overview: str
    is_lethal_turn: bool = False
    is_completed: bool = False
    summary_markdown: str = ""

    def to_dict(self) -> Dict[str, Any]:
        active_step = self.get_active_step()
        return {
            "turn_number": self.turn_number,
            "active_step_index": self.active_step_index,
            "is_lethal_turn": self.is_lethal_turn,
            "is_completed": self.is_completed,
            "macro_voice_overview": self.macro_voice_overview,
            "active_step": active_step.to_dict() if active_step else None,
            "steps": [s.to_dict() for s in self.steps],
            "summary_markdown": self.summary_markdown,
        }

    def get_active_step(self) -> Optional[CoPilotStep]:
        if 0 <= self.active_step_index < len(self.steps):
            return self.steps[self.active_step_index]
        return None

    def advance(self) -> Optional[CoPilotStep]:
        if 0 <= self.active_step_index < len(self.steps):
            self.steps[self.active_step_index].status = "COMPLETED"
            self.active_step_index += 1
            if self.active_step_index < len(self.steps):
                self.steps[self.active_step_index].status = "IN_PROGRESS"
                return self.steps[self.active_step_index]
            else:
                self.is_completed = True
                return None
        return None


class MasterCoPilotEngine:
    """Orchestrates step-by-step master guidance and real-time execution flow."""

    _instance: Optional[MasterCoPilotEngine] = None

    def __init__(self) -> None:
        self.current_plan: Optional[CoPilotTurnPlan] = None
        self.executed_actions_history: List[str] = []

    @classmethod
    def get_instance(cls) -> MasterCoPilotEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def build_step_plan(
        cls,
        action_sequence: List[str],
        trading_plan: str = "",
        had_lethal: bool = False,
        friendly_hp: int = 30,
        enemy_hp: int = 30,
        mana: int = 1,
        turn: int = 1,
    ) -> CoPilotTurnPlan:
        steps: List[CoPilotStep] = []
        step_counter = 1

        # 1. Macro Voice Tone
        if had_lethal:
            macro_speech = f"绝杀战机已出现！敌方仅剩 {enemy_hp} 血，本回合直取敌将首级！"
        elif "打脸" in trading_plan or "抢脸" in trading_plan:
            macro_speech = "本回合我们时钟领先，主要任务是高效控场的同时最大化压制敌方血线。"
        elif "防守" in trading_plan or "稳健" in trading_plan:
            macro_speech = "当前血线偏低，严禁贪脸，务必优先完成随从白吃解场化解危机。"
        else:
            macro_speech = "按费平滑展开，稳扎稳打建立场面与手牌双重优势。"

        # 2. Deconstruct actions into atomic micro steps
        # Check for draw actions first
        draw_actions = [a for a in action_sequence if any(k in a for k in ["抽牌", "智慧", "生命分流", "追踪术", "过牌"])]
        attack_actions = [a for a in action_sequence if any(k in a for k in ["攻击", "打脸", "撞", "解掉", "交换"])]
        play_actions = [a for a in action_sequence if a not in draw_actions and a not in attack_actions]

        # Order: 1. Draw -> 2. Aura -> 3. Trades -> 4. Minion plays -> 5. Face -> 6. End Turn
        for da in draw_actions:
            steps.append(
                CoPilotStep(
                    step_number=step_counter,
                    step_type=CoPilotStepType.DRAW_FIRST,
                    action_text=da,
                    source_label="手牌/技能",
                    target_label="牌库",
                    conversational_voice="先出这个过牌，看看摸到什么牌再做下一步决定。",
                    status="PENDING",
                    ar_coords={"start_x": 0.45, "start_y": 0.88, "end_x": 0.5, "end_y": 0.5},
                    tactical_purpose="获取更多卡牌信息以拓展后续最优分支",
                    is_critical_micro=True,
                )
            )
            step_counter += 1

        for aa in attack_actions:
            is_face = any(k in aa for k in ["打脸", "英雄", "走脸"])
            stype = CoPilotStepType.ATTACK_FACE if is_face else CoPilotStepType.TRADE_MINION
            voice = "全部随从全力走脸，直接斩杀！" if had_lethal else ("随从走脸压低血线。" if is_face else f"用这个随从稳健白吃，化解敌方威胁。")
            steps.append(
                CoPilotStep(
                    step_number=step_counter,
                    step_type=stype,
                    action_text=aa,
                    source_label="我方战场",
                    target_label="敌方英雄" if is_face else "敌方随从",
                    conversational_voice=voice,
                    status="PENDING",
                    ar_coords={"start_x": 0.5, "start_y": 0.58, "end_x": 0.5, "end_y": 0.2 if is_face else 0.42},
                    tactical_purpose="终结比赛" if had_lethal else ("血线压制" if is_face else "场面控场"),
                    is_critical_micro=had_lethal,
                )
            )
            step_counter += 1

        for pa in play_actions:
            is_spell = any(k in pa for k in ["法术", "火球", "横扫", "愤怒", "奉献", "暴风雪", "药水"])
            stype = CoPilotStepType.PLAY_SPELL if is_spell else CoPilotStepType.PLAY_MINION
            voice = f"使用这发法术解场。" if is_spell else f"下这个随从站场，按费打满节奏。"
            steps.append(
                CoPilotStep(
                    step_number=step_counter,
                    step_type=stype,
                    action_text=pa,
                    source_label="手牌",
                    target_label="目标随从" if is_spell else "棋盘空位",
                    conversational_voice=voice,
                    status="PENDING",
                    ar_coords={"start_x": 0.5, "start_y": 0.88, "end_x": 0.5, "end_y": 0.58},
                    tactical_purpose="解场控场" if is_spell else "建立前场攻击频率",
                )
            )
            step_counter += 1

        # Fallback if empty
        if not steps:
            steps.append(
                CoPilotStep(
                    step_number=1,
                    step_type=CoPilotStepType.END_TURN,
                    action_text="结束回合",
                    source_label="结束按钮",
                    target_label="结束按钮",
                    conversational_voice="场面已处理完毕，可以直接点击结束回合。",
                    status="PENDING",
                    ar_coords={"start_x": 0.85, "start_y": 0.48, "end_x": 0.85, "end_y": 0.48},
                    tactical_purpose="等待敌方行动",
                )
            )

        # Mark first step as IN_PROGRESS
        steps[0].status = "IN_PROGRESS"

        # Markdown summary
        md_lines = [
            f"**全知大师副驾 · 回合 {turn} 步进导航** ({macro_speech}):",
        ]
        for s in steps:
            badge = "🔥 [斩杀]" if s.is_critical_micro else ""
            mark = "▶" if s.status == "IN_PROGRESS" else " "
            md_lines.append(f"  {mark} **步骤 {s.step_number}**: {s.action_text} ({s.conversational_voice}) {badge}")

        summary_md = "\n".join(md_lines)

        return CoPilotTurnPlan(
            turn_number=turn,
            active_step_index=0,
            steps=steps,
            macro_voice_overview=macro_speech,
            is_lethal_turn=had_lethal,
            is_completed=False,
            summary_markdown=summary_md,
        )

    def load_turn_plan(self, plan: CoPilotTurnPlan) -> None:
        self.current_plan = plan
        self.executed_actions_history.clear()

    def advance_current_step(self) -> Optional[CoPilotStep]:
        if self.current_plan:
            return self.current_plan.advance()
        return None

    def get_active_voice(self) -> str:
        if not self.current_plan or self.current_plan.is_completed:
            return "回合已完成，稳健等待对手出牌。"
        cur_step = self.current_plan.get_active_step()
        if cur_step:
            return cur_step.conversational_voice
        return "请进行下一步操作。"
