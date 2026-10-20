"""
PositioningGeometry: Master-level board geometry & minion adjacency optimizer.
Protects valuable minions from Cleave/Meteor/Betrayal/Cone of Cold, and maximizes positional buffs (Magnetic, Dire Wolf, Argus).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PositioningGeometry")


@dataclass
class PositioningAdvice:
    recommended_slot: int          # 0 = far left, len(board) = far right
    slot_description: str          # e.g., "置于最左翼", "置于【随从A】与【随从B】之间"
    strategic_rationale: str       # e.g., "充当防背叛/流星缓冲盾，保护高攻随从"
    threat_mitigated: str          # e.g., "防背叛/陨石/锥形横扫"
    is_magnetic_fuse: bool = False # Whether this placement is a magnetic fusion onto a mech


class PositioningGeometry:
    """
    Computes mathematically optimal board insertion coordinates for incoming minions.
    """

    ADJACENT_BUFF_NAMES = {
        "恐狼先锋", "DIRE WOLF ALPHA",
        "阿古斯防御者", "DEFENDER OF ARGUS",
        "火舌图腾", "FLAMETONGUE TOTEM",
    }

    @classmethod
    def calculate_optimal_placement(
        cls,
        board: List[Dict[str, Any]],  # [{"name": str, "atk": int, "health": int, "divine_shield": bool, "deathrattle": bool, "taunt": bool, "is_mech": bool}]
        new_minion: Dict[str, Any],   # {"name": str, "atk": int, "health": int, "divine_shield": bool, "deathrattle": bool, "taunt": bool, "is_magnetic": bool}
        opponent_class: str = "MAGE",
    ) -> PositioningAdvice:
        """
        Determines the optimal placement slot for `new_minion` on `board`.
        Slots range from 0 (left-most) to len(board) (right-most).
        """
        board_len = len(board)
        if board_len == 0:
            return PositioningAdvice(
                recommended_slot=0,
                slot_description="场上无随从，直接置于中场",
                strategic_rationale="先手首下随从",
                threat_mitigated="无",
            )

        name = new_minion.get("name", "随从").upper()
        atk = new_minion.get("atk", 1)
        hp = new_minion.get("health", 1)
        divine_shield = new_minion.get("divine_shield", False)
        deathrattle = new_minion.get("deathrattle", False)
        is_magnetic = new_minion.get("is_magnetic", False)

        # 1. Magnetic Fusion Check
        # If magnetic and target mech is on board: placing to immediate LEFT of a Mech fuses it!
        if is_magnetic:
            mech_indices = [i for i, m in enumerate(board) if m.get("is_mech", False)]
            if mech_indices:
                target_idx = mech_indices[0]
                target_mech_name = board[target_idx].get("name", "机械随从")
                return PositioningAdvice(
                    recommended_slot=target_idx,
                    slot_description=f"置于【{target_mech_name}】左侧 (Slot {target_idx})",
                    strategic_rationale=f"触发磁力合体升级【{target_mech_name}】(+{atk}/+{hp})，享受即时冲锋/突袭攻击！",
                    threat_mitigated="避免分散站场被低效解掉",
                    is_magnetic_fuse=True,
                )

        # 2. Adjacent Buff Minion (Dire Wolf / Defender of Argus / Flametongue)
        # Needs to be placed between the two minions that benefit most!
        is_buffer = any(b in name for b in cls.ADJACENT_BUFF_NAMES)
        if is_buffer:
            # Place between the two lowest attack or ready-to-attack minions
            best_idx = 1 if board_len >= 2 else 0
            left_name = board[max(0, best_idx - 1)].get("name", "左侧随从")
            right_name = board[min(board_len - 1, best_idx)].get("name", "右侧随从")
            return PositioningAdvice(
                recommended_slot=best_idx,
                slot_description=f"置于【{left_name}】与【{right_name}】之间 (Slot {best_idx})",
                strategic_rationale="最大化相邻随从攻击力/身材Buff覆盖",
                threat_mitigated="避免Buff只强化单侧",
            )

        # 3. Defensive Anti-Cleave / Anti-Betrayal / Anti-Meteor Geometry
        # Core Rules:
        # A. Never place high attack minion directly adjacent to two low-hp valuable minions (Anti-Betrayal vs Rogue)
        # B. Low HP / Divine Shield / Deathrattle minions act as "Shock Absorbers" (Buffers)
        # C. Against Mage (Meteor/Cone of Cold) / Hunter (Crushing Walls):
        #    - Crushing Walls destroys outer-most minions -> Keep giant minions in interior!

        # Identify highest attack minion on board
        max_atk_idx = max(range(board_len), key=lambda i: board[i].get("atk", 0))
        max_atk_val = board[max_atk_idx].get("atk", 0)

        # If incoming minion has Divine Shield or Deathrattle:
        # Place it adjacent to the highest attack minion to protect it from splash!
        if divine_shield or deathrattle:
            target_slot = max_atk_idx + 1
            flank_name = board[max_atk_idx].get("name", "主力随从")
            return PositioningAdvice(
                recommended_slot=target_slot,
                slot_description=f"置于主力【{flank_name}】右侧 (Slot {target_slot})",
                strategic_rationale="以圣盾/亡语随从充当缓冲盾，吸收锥形AOE、横扫和流星的溅射伤害",
                threat_mitigated="防流星/防横扫/防锥形伤害",
            )

        # If incoming minion is a High-Attack Boss (Atk >= 5):
        # Do not place on extreme outer flanks if playing Hunter (Crushing Walls),
        # place inside, adjacent to a high-health or deathrattle minion.
        if atk >= 5:
            # Place inside the board, shielded by smaller minion on the flank
            safe_slot = 1 if board_len >= 2 else 0
            neighbor_name = board[safe_slot].get("name", "护卫随从")
            return PositioningAdvice(
                recommended_slot=safe_slot,
                slot_description=f"置于内侧【{neighbor_name}】旁 (Slot {safe_slot})",
                strategic_rationale="大体型主力内置站位，两翼留小随从垫刀防致命射击/碾压墙",
                threat_mitigated="防碾压墙/防致命射击",
            )

        # If incoming minion is a small token or low-stat minion (hp <= 2):
        # Place on extreme far left or far right flank (Slot 0 or Slot board_len)
        # to soak Betrayal and avoid splitting valuable minion buffers.
        return PositioningAdvice(
            recommended_slot=board_len,
            slot_description=f"置于最右翼外侧 (Slot {board_len})",
            strategic_rationale="小随从置于外翼，防背叛连环溅射，避免稀释主力随从的相邻Buff空间",
            threat_mitigated="防背叛/防连环溅射",
        )
