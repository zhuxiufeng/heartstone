"""
WhatIfSandbox: Parallel Reality Simulation & Alternative Decision Tree Explorer.
Branches off any turn to simulate how an alternative decision (e.g. face vs trade, holding resource)
would have evolved across 3 future turns compared to the actual baseline play line.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("WhatIfSandbox")


@dataclass
class HorizonState:
    turn_offset: int            # +1, +2, +3
    friendly_hp: int
    enemy_hp: int
    friendly_board_attack: int
    enemy_board_attack: int
    projected_winrate_pct: float


@dataclass
class BranchProjection:
    branch_name: str            # "基准实战打法 (Actual/Baseline)" vs "平行时空抉择 (What-If)"
    action_description: str
    horizon_states: List[HorizonState]
    terminal_winrate_pct: float
    tactical_summary: str


@dataclass
class WhatIfSimulationReport:
    branching_turn: int
    alternative_action_hypothesized: str
    baseline_branch: BranchProjection
    what_if_branch: BranchProjection
    winrate_delta_pct: float    # positive means what-if is better
    verdict: str                # "PARALLEL_SUPERIOR", "PARALLEL_INFERIOR", "EQUAL"
    verdict_label: str
    comparison_table_ascii: str
    summary_markdown: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branching_turn": self.branching_turn,
            "alternative_action": self.alternative_action_hypothesized,
            "winrate_delta_pct": round(self.winrate_delta_pct, 1),
            "verdict": self.verdict,
            "verdict_label": self.verdict_label,
            "baseline": {
                "name": self.baseline_branch.branch_name,
                "action": self.baseline_branch.action_description,
                "winrate": round(self.baseline_branch.terminal_winrate_pct, 1),
            },
            "what_if": {
                "name": self.what_if_branch.branch_name,
                "action": self.what_if_branch.action_description,
                "winrate": round(self.what_if_branch.terminal_winrate_pct, 1),
            },
            "comparison_table": self.comparison_table_ascii,
            "summary_markdown": self.summary_markdown,
        }


class WhatIfSandbox:
    """Simulates 3-turn forward projection for alternative play lines."""

    @classmethod
    def simulate_what_if(
        cls,
        turn: int,
        actual_action_desc: str,
        what_if_action_desc: str,
        start_friendly_hp: int,
        start_enemy_hp: int,
        start_friendly_board_atk: int,
        start_enemy_board_atk: int,
        opponent_has_aoe_next_turn: bool = False,
    ) -> WhatIfSimulationReport:
        # 1. Project Baseline (Actual play)
        # Assume actual play: e.g. played all-in face or traded
        base_h1_fhp = max(1, start_friendly_hp - start_enemy_board_atk)
        base_h1_ehp = max(0, start_enemy_hp - start_friendly_board_atk)
        base_h1_fatk = start_friendly_board_atk
        base_h1_eatk = start_enemy_board_atk

        # If opponent has AoE at T+1, baseline suffers if full board
        if opponent_has_aoe_next_turn and "全铺" in actual_action_desc:
            base_h1_fatk = max(1, base_h1_fatk // 3)

        base_h2_fatk = base_h1_fatk + 3
        base_h2_ehp = max(0, base_h1_ehp - base_h1_fatk)
        base_h2_fhp = max(1, base_h1_fhp - base_h1_eatk)

        base_h3_wr = 70.0 if base_h2_ehp <= 5 else (50.0 if base_h2_fhp > 10 else 35.0)

        baseline_states = [
            HorizonState(1, base_h1_fhp, base_h1_ehp, base_h1_fatk, base_h1_eatk, 52.0),
            HorizonState(2, base_h2_fhp, base_h2_ehp, base_h2_fatk, base_h1_eatk, 55.0),
            HorizonState(3, base_h2_fhp, base_h2_ehp, base_h2_fatk, base_h1_eatk, base_h3_wr),
        ]
        base_branch = BranchProjection(
            branch_name="基准实战打法",
            action_description=actual_action_desc,
            horizon_states=baseline_states,
            terminal_winrate_pct=base_h3_wr,
            tactical_summary="原路线按部就班推演",
        )

        # 2. Project What-If Branch
        # Check if alternative is defensive trade or holding resource
        is_defensive = any(k in what_if_action_desc for k in ["解场", "白吃", "防守", "控场", "防AOE"])
        if is_defensive:
            # Enemy board attack reduced, enemy takes less damage initially, but player survives better
            alt_h1_eatk = max(0, start_enemy_board_atk - 4)
            alt_h1_fhp = max(1, start_friendly_hp - alt_h1_eatk)
            alt_h1_ehp = start_enemy_hp
            alt_h1_fatk = max(1, start_friendly_board_atk - 2)
            alt_h2_fatk = alt_h1_fatk + 4
            alt_h2_ehp = max(0, alt_h1_ehp - alt_h1_fatk)
            alt_h2_fhp = max(1, alt_h1_fhp - alt_h1_eatk)
            alt_h3_wr = 68.0 if alt_h1_fhp >= 15 else 48.0
        else:
            # Aggressive all-in face
            alt_h1_ehp = max(0, start_enemy_hp - start_friendly_board_atk - 3)
            alt_h1_fhp = max(1, start_friendly_hp - start_enemy_board_atk)
            alt_h1_fatk = start_friendly_board_atk
            alt_h1_eatk = start_enemy_board_atk
            alt_h2_ehp = max(0, alt_h1_ehp - alt_h1_fatk)
            alt_h2_fhp = max(0, alt_h1_fhp - alt_h1_eatk)
            alt_h3_wr = 85.0 if alt_h2_ehp <= 0 else (60.0 if alt_h2_ehp <= 6 else 30.0)

        what_if_states = [
            HorizonState(1, alt_h1_fhp, alt_h1_ehp, alt_h1_fatk, start_enemy_board_atk, 54.0),
            HorizonState(2, alt_h2_fhp, alt_h2_ehp, alt_h2_fatk, start_enemy_board_atk, 60.0),
            HorizonState(3, alt_h2_fhp, alt_h2_ehp, alt_h2_fatk, start_enemy_board_atk, alt_h3_wr),
        ]
        what_if_branch = BranchProjection(
            branch_name="平行时空抉择",
            action_description=what_if_action_desc,
            horizon_states=what_if_states,
            terminal_winrate_pct=alt_h3_wr,
            tactical_summary="假想分支路线模拟",
        )

        wr_delta = alt_h3_wr - base_h3_wr
        if wr_delta >= 5.0:
            verdict = "PARALLEL_SUPERIOR"
            v_label = f"🌟 平行时空更优 (胜率预期 +{wr_delta:.1f}%)"
        elif wr_delta <= -5.0:
            verdict = "PARALLEL_INFERIOR"
            v_label = f"⚠️ 实战打法更优 (平行抉择亏损 {abs(wr_delta):.1f}% 胜率)"
        else:
            verdict = "EQUAL"
            v_label = "⚖️ 两条路线各有千秋 (胜率差异 < 5%)"

        # Comparison table
        ascii_table = (
            "+------------------+------------+------------+------------+------------+\n"
            "| 对比维度         | T+1 友方血 | T+1 敌方血 | T+2 场攻   | 3回合胜率  |\n"
            "+------------------+------------+------------+------------+------------+\n"
            f"| 实战基准打法     | {base_h1_fhp:>10} | {base_h1_ehp:>10} | {base_h2_fatk:>10} | {base_h3_wr:>9.1f}% |\n"
            f"| 平行时空假想     | {alt_h1_fhp:>10} | {alt_h1_ehp:>10} | {alt_h2_fatk:>10} | {alt_h3_wr:>9.1f}% |\n"
            "+------------------+------------+------------+------------+------------+"
        )

        md = (
            f"**第 {turn} 回合平行时空推演沙盘**:\n"
            f"• **实战操作**: {actual_action_desc}\n"
            f"• **假想操作**: {what_if_action_desc}\n"
            f"• **推演结论**: **{v_label}**\n\n"
            f"```text\n{ascii_table}\n```"
        )

        return WhatIfSimulationReport(
            branching_turn=turn,
            alternative_action_hypothesized=what_if_action_desc,
            baseline_branch=base_branch,
            what_if_branch=what_if_branch,
            winrate_delta_pct=wr_delta,
            verdict=verdict,
            verdict_label=v_label,
            comparison_table_ascii=ascii_table,
            summary_markdown=md,
        )
