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
    ascii_board_map: str = ""      # Visual ASCII board showing slot placement
    defile_ladder_warning: Optional[str] = None # Warlock Defile ladder warning


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
    def _build_ascii_map(
        cls,
        board: List[Dict[str, Any]],
        new_minion_name: str,
        slot: int,
        is_magnetic: bool = False,
    ) -> str:
        """Constructs an ASCII board topology map showing where the new minion lands."""
        tokens = []
        board_len = len(board)
        for i in range(board_len):
            if i == slot:
                marker = f"[⚡磁力合体: {new_minion_name}⚡]" if is_magnetic else f"[★放入: {new_minion_name}★]"
                tokens.append(marker)
            m = board[i]
            m_name = m.get("name", f"随从{i+1}")
            m_atk = m.get("atk", 1)
            m_hp = m.get("health", 1)
            tokens.append(f"({m_name} {m_atk}/{m_hp})")
        if slot >= board_len:
            tokens.append(f"[★放入: {new_minion_name}★]")
        return " ➔ ".join(tokens)

    @classmethod
    def _check_defile_ladder(
        cls,
        board: List[Dict[str, Any]],
        new_minion: Dict[str, Any],
        opponent_class: str,
    ) -> Optional[str]:
        """Warns if adding this minion completes an unbroken 1..K health ladder for Warlock Defile."""
        if opponent_class.upper() != "WARLOCK":
            return None
        existing_hps = {m.get("health", 1) for m in board}
        incoming_hp = new_minion.get("health", 1)
        all_hps = existing_hps | {incoming_hp}
        # Check ladder from 1 upwards
        ladder_len = 0
        cur = 1
        while cur in all_hps:
            ladder_len += 1
            cur += 1
        if ladder_len >= 3 and incoming_hp <= ladder_len and incoming_hp not in existing_hps:
            return f"⚠️ 亵渎梯子警告：打出 {incoming_hp} 血随从将补齐 1~{ladder_len} 血链，术士 2 费亵渎可连续全清！"
        return None

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
        incoming_name = new_minion.get("name", "随从")
        defile_warn = cls._check_defile_ladder(board, new_minion, opponent_class)

        if board_len == 0:
            advice = PositioningAdvice(
                recommended_slot=0,
                slot_description="场上无随从，直接置于中场",
                strategic_rationale="先手首下随从",
                threat_mitigated="无",
                ascii_board_map=f"[★放入: {incoming_name}★]",
                defile_ladder_warning=defile_warn,
            )
            return advice

        name = incoming_name.upper()
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
                    ascii_board_map=cls._build_ascii_map(board, incoming_name, target_idx, is_magnetic=True),
                    defile_ladder_warning=defile_warn,
                )

        # 2. Adjacent Buff Minion (Dire Wolf / Defender of Argus / Flametongue)
        is_buffer = any(b in name for b in cls.ADJACENT_BUFF_NAMES)
        if is_buffer:
            best_idx = 1 if board_len >= 2 else 0
            left_name = board[max(0, best_idx - 1)].get("name", "左侧随从")
            right_name = board[min(board_len - 1, best_idx)].get("name", "右侧随从")
            return PositioningAdvice(
                recommended_slot=best_idx,
                slot_description=f"置于【{left_name}】与【{right_name}】之间 (Slot {best_idx})",
                strategic_rationale="最大化相邻随从攻击力/身材Buff覆盖",
                threat_mitigated="避免Buff只强化单侧",
                ascii_board_map=cls._build_ascii_map(board, incoming_name, best_idx),
                defile_ladder_warning=defile_warn,
            )

        # 3. Defensive Anti-Cleave / Anti-Betrayal / Anti-Meteor Geometry
        max_atk_idx = max(range(board_len), key=lambda i: board[i].get("atk", 0))

        if divine_shield or deathrattle:
            target_slot = max_atk_idx + 1
            flank_name = board[max_atk_idx].get("name", "主力随从")
            return PositioningAdvice(
                recommended_slot=target_slot,
                slot_description=f"置于主力【{flank_name}】右侧 (Slot {target_slot})",
                strategic_rationale="以圣盾/亡语随从充当缓冲盾，吸收锥形AOE、横扫和流星的溅射伤害",
                threat_mitigated="防流星/防横扫/防锥形伤害",
                ascii_board_map=cls._build_ascii_map(board, incoming_name, target_slot),
                defile_ladder_warning=defile_warn,
            )

        if atk >= 5:
            safe_slot = 1 if board_len >= 2 else 0
            neighbor_name = board[safe_slot].get("name", "护卫随从")
            return PositioningAdvice(
                recommended_slot=safe_slot,
                slot_description=f"置于内侧【{neighbor_name}】旁 (Slot {safe_slot})",
                strategic_rationale="大体型主力内置站位，两翼留小随从垫刀防致命射击/碾压墙",
                threat_mitigated="防碾压墙/防致命射击",
                ascii_board_map=cls._build_ascii_map(board, incoming_name, safe_slot),
                defile_ladder_warning=defile_warn,
            )

        return PositioningAdvice(
            recommended_slot=board_len,
            slot_description=f"置于最右翼外侧 (Slot {board_len})",
            strategic_rationale="小随从置于外翼，防背叛连环溅射，避免稀释主力随从的相邻Buff空间",
            threat_mitigated="防背叛/防连环溅射",
            ascii_board_map=cls._build_ascii_map(board, incoming_name, board_len),
            defile_ladder_warning=defile_warn,
        )
