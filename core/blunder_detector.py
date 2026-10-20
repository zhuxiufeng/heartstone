"""
BlunderDetector: Match Replay Analyzer & Tactical Blunder Detection Engine.
Detects missed lethals, unnecessary mana floating, and overextension into predicted AOEs.
Generates comprehensive post-mortem match reviews and grades.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BlunderDetector")


@dataclass
class TurnSnapshot:
    turn_number: int
    mana_available: int
    friendly_hp: int
    enemy_hp: int
    had_lethal: bool = False
    lethal_damage: int = 0
    aoe_threat_warning: str = ""
    suggested_play: str = ""
    played_card_count: int = 0
    posture_mode: str = "BALANCED"


@dataclass
class BlunderItem:
    turn_number: int
    blunder_type: str        # "MISSED_LETHAL", "OVEREXTEND_AOE", "MANA_WASTAGE", "BURST_VULNERABILITY"
    severity: str            # "CRITICAL", "MAJOR", "MINOR"
    description: str
    impact: str


@dataclass
class MatchReviewReport:
    result: str              # "WIN" or "LOSS"
    total_turns: int
    match_grade: str         # "S (完美对局)", "A (优秀发挥)", "B (存在瑕疵)", "C (重大伏笔)"
    blunders: List[BlunderItem] = field(default_factory=list)
    key_turning_point: str = ""
    mvp_performance: str = ""
    markdown_summary: str = ""


class BlunderDetector:
    """Analyzes a match timeline to identify tactical blunders and generate reviews."""

    @classmethod
    def evaluate_match(
        cls,
        result: str,
        friendly_hero: str,
        opponent_hero: str,
        turn_history: List[TurnSnapshot],
    ) -> MatchReviewReport:
        blunders: List[BlunderItem] = []
        is_win = result.upper() == "WIN"

        total_turns = len(turn_history)
        if total_turns == 0:
            return MatchReviewReport(
                result=result,
                total_turns=0,
                match_grade="S (无数据)",
                key_turning_point="对局过短或无回合记录",
                mvp_performance="--",
                markdown_summary="暂无对局历史记录。",
            )

        # 1. Detect Missed Lethal
        for idx, snap in enumerate(turn_history):
            if snap.had_lethal:
                # If this turn had lethal but game continued for more turns or resulted in loss
                if idx < total_turns - 1 or not is_win:
                    blunders.append(BlunderItem(
                        turn_number=snap.turn_number,
                        blunder_type="MISSED_LETHAL",
                        severity="CRITICAL",
                        description=f"回合 {snap.turn_number} 错失斩杀！AI 测算出最高伤害可达 {snap.lethal_damage} 点，敌方仅余 {snap.enemy_hp} 血。",
                        impact="本可直接获胜，错失致胜良机",
                    ))

        # 2. Detect Overextension into Predicted AOE
        for idx in range(total_turns - 1):
            curr = turn_history[idx]
            nxt = turn_history[idx + 1]
            if curr.aoe_threat_warning and curr.played_card_count >= 3:
                # If player dumped 3+ cards directly into an AOE warning turn
                blunders.append(BlunderItem(
                    turn_number=curr.turn_number,
                    blunder_type="OVEREXTEND_AOE",
                    severity="MAJOR",
                    description=f"回合 {curr.turn_number} 顶着敌方高危 AOE 警报（{curr.aoe_threat_warning}）盲目铺满随从，导致手牌消耗过大。",
                    impact="场面被对手廉价返场清空，陷入资源被动",
                ))

        # 3. Grade Computation
        critical_count = sum(1 for b in blunders if b.severity == "CRITICAL")
        major_count = sum(1 for b in blunders if b.severity == "MAJOR")

        if critical_count > 0:
            grade = "C (存在致命伏笔)"
        elif major_count >= 2:
            grade = "B (节奏存在瑕疵)"
        elif major_count == 1:
            grade = "A (发挥优良)"
        else:
            grade = "S (神级发挥 / 零伏笔)"

        # 4. Turning Point Detection
        if blunders:
            first_crit = next((b for b in blunders if b.severity == "CRITICAL"), blunders[0])
            turning_point = f"第 {first_crit.turn_number} 回合：{first_crit.description}"
        elif is_win:
            turning_point = f"第 {max(1, total_turns - 2)} 回合：牢牢掌控场面与节奏，稳健推进至斩杀线。"
        else:
            turning_point = f"第 {max(1, total_turns // 2)} 回合：未能有效化解对手攻势，场面逐渐失控。"

        mvp = "稳健场面压制" if is_win else "防守顽强推演"

        # Generate Markdown Summary
        res_emoji = "🏆 胜利 (VICTORY)" if is_win else "💔 惜败 (DEFEAT)"
        md_lines = [
            f"### ⚔️ 竞技场对局复盘战报：{res_emoji}",
            f"- **对战双方**: 我方 【{friendly_hero}】 vs 敌方 【{opponent_hero}】",
            f"- **总回合数**: 共激战 {total_turns} 回合",
            f"- **综合战局评级**: **{grade}**",
            f"- **关键转折点**: {turning_point}",
            "",
            "#### 🔍 伏笔与失误推演 (Blunders Detected):",
        ]

        if not blunders:
            md_lines.append("🎉 **完美！本局未检测到任何明显伏笔与资源浪费。**")
        else:
            for b in blunders:
                badge = "🔴 [致命伏笔]" if b.severity == "CRITICAL" else "🟡 [严重失误]"
                md_lines.append(f"• **T{b.turn_number}** {badge} {b.description} *(后果: {b.impact})*")

        md_summary = "\n".join(md_lines)

        return MatchReviewReport(
            result=result,
            total_turns=total_turns,
            match_grade=grade,
            blunders=blunders,
            key_turning_point=turning_point,
            mvp_performance=mvp,
            markdown_summary=md_summary,
        )
