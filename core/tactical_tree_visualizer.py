"""
TacticalDecisionTree: Multi-Branch Decision Topology Tree Visualizer.
Constructs interactive tree nodes modeling player choices (Plan A/B/C),
opponent counter-play distributions, and resulting winrate/resilience trajectories.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .action_tree_search import ActionBranch, ActionTreeResult

logger = logging.getLogger("TacticalDecisionTree")


@dataclass
class DecisionNode:
    node_id: str
    title: str
    detail: str
    ev_score: float
    winrate_pct: float
    node_type: str                  # "ROOT", "PLAYER_PLAN", "OPP_COUNTER", "OUTCOME"
    resilience_score: int = 50
    children: List[DecisionNode] = field(default_factory=list)


class TacticalDecisionTree:
    """Builds hierarchical decision tree for desktop and mobile companions."""

    @classmethod
    def build_tree(
        cls,
        action_tree_res: ActionTreeResult,
        current_mana: int,
        friendly_hp: int,
        enemy_hp: int,
        opponent_class: str = "法师",
    ) -> DecisionNode:
        root = DecisionNode(
            node_id="root",
            title=f"当前战场局面 (💎 {current_mana} 费)",
            detail=f"我方生命: {friendly_hp} vs 敌方: {enemy_hp} ({opponent_class})",
            ev_score=0.0,
            winrate_pct=50.0,
            node_type="ROOT",
        )

        all_branches = [action_tree_res.best_branch] + action_tree_res.alternative_branches
        for b_idx, branch in enumerate(all_branches):
            if not branch:
                continue
            plan_code = "A" if b_idx == 0 else ("B" if b_idx == 1 else "C")
            plan_node = DecisionNode(
                node_id=f"plan_{plan_code}",
                title=f"{branch.plan_name} (EV: {branch.ev_score:+0.1f})",
                detail=" ➔ ".join(branch.action_sequence[:3]) or "按费行动",
                ev_score=branch.ev_score,
                winrate_pct=branch.projected_winrate,
                resilience_score=branch.resilience_score,
                node_type="PLAYER_PLAN",
            )

            # Opponent Counter Responses
            if "突击" in branch.plan_name or "Rush" in branch.plan_name:
                opp_c1 = DecisionNode(
                    node_id=f"opp_{plan_code}_1",
                    title=f"敌方对冲走脸 (拼极限速度)",
                    detail=f"若敌方掏出直伤反斩杀，胜率波动剧烈",
                    ev_score=round(branch.ev_score - 4.0, 1),
                    winrate_pct=round(max(10.0, branch.projected_winrate - 15.0), 1),
                    node_type="OPP_COUNTER",
                )
                opp_c2 = DecisionNode(
                    node_id=f"opp_{plan_code}_2",
                    title=f"敌方被迫交解解场 (下风控局)",
                    detail=f"敌方手牌断水，我方下轮直接叫杀！",
                    ev_score=round(branch.ev_score + 6.0, 1),
                    winrate_pct=round(min(98.0, branch.projected_winrate + 12.0), 1),
                    node_type="OPP_COUNTER",
                )
                plan_node.children.extend([opp_c1, opp_c2])
            else:
                opp_c1 = DecisionNode(
                    node_id=f"opp_{plan_code}_1",
                    title=f"敌方交AOE/大解反扑 ({branch.opp_response_threat or '强解'})",
                    detail=f"受韧性评分影响，存活率 {int(branch.board_survival_rate * 100)}%",
                    ev_score=round(branch.ev_score - 2.5, 1),
                    winrate_pct=round(max(20.0, branch.projected_winrate - 8.0), 1),
                    node_type="OPP_COUNTER",
                )
                opp_c2 = DecisionNode(
                    node_id=f"opp_{plan_code}_2",
                    title=f"敌方补拍随从 (均势拉锯)",
                    detail=f"双回合平滑曲线压制，我方持续掌握主动权",
                    ev_score=round(branch.ev_score + 3.0, 1),
                    winrate_pct=round(min(95.0, branch.projected_winrate + 6.0), 1),
                    node_type="OPP_COUNTER",
                )
                plan_node.children.extend([opp_c1, opp_c2])

            root.children.append(plan_node)

        return root

    @classmethod
    def to_dict(cls, node: DecisionNode) -> Dict[str, Any]:
        return asdict(node)

    @classmethod
    def to_ascii_tree(cls, node: DecisionNode, prefix: str = "", is_last: bool = True) -> str:
        lines = []
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{node.title} [{node.node_type}]")
        child_prefix = prefix + ("    " if is_last else "│   ")
        for idx, child in enumerate(node.children):
            is_child_last = (idx == len(node.children) - 1)
            lines.append(cls.to_ascii_tree(child, child_prefix, is_child_last))
        return "\n".join(lines)
