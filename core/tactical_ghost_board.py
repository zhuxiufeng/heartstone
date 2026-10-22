"""
TacticalGhostBoard: Holographic Terminal Delta Simulation (鬼影实机沙盘预演).
Simulates post-turn board outcomes before any physical action is committed,
calculating exact surviving minion stats, remaining enemy threats, net face damage,
and mana expenditure efficiency.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("TacticalGhostBoard")


@dataclass
class SurvivingMinion:
    name: str
    attack: int
    health: int
    is_friendly: bool
    status_note: str = ""

    def __str__(self) -> str:
        return f"{self.name} ({self.attack}/{self.health})"


@dataclass
class GhostBoardSnapshot:
    """Pre-computed terminal board state after executing optimal turn sequence."""
    surviving_friendly: List[SurvivingMinion] = field(default_factory=list)
    surviving_enemies: List[SurvivingMinion] = field(default_factory=list)
    is_enemy_cleared: bool = False
    net_face_damage: int = 0
    enemy_hp_remaining: int = 30
    post_turn_board_attack: int = 0
    mana_spent: int = 0
    mana_remaining: int = 0
    holographic_summary_badge: str = ""
    terminal_delta_display: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "surviving_friendly": [str(m) for m in self.surviving_friendly],
            "surviving_enemies": [str(m) for m in self.surviving_enemies],
            "is_enemy_cleared": self.is_enemy_cleared,
            "net_face_damage": self.net_face_damage,
            "enemy_hp_remaining": self.enemy_hp_remaining,
            "post_turn_board_attack": self.post_turn_board_attack,
            "mana_spent": self.mana_spent,
            "mana_remaining": self.mana_remaining,
            "summary_badge": self.holographic_summary_badge,
        }


class TacticalGhostBoardSimulator:
    """Simulates physical end-of-turn board state from action and trade sequences."""

    @classmethod
    def simulate_turn_outcome(
        cls,
        friendly_minions: List[Dict[str, Any]],
        enemy_minions: List[Dict[str, Any]],
        played_minions: Optional[List[Dict[str, Any]]] = None,
        optimal_trades: Optional[List[str]] = None,
        face_damage: int = 0,
        current_mana: int = 1,
        spent_mana: int = 0,
        enemy_hp: int = 30,
    ) -> GhostBoardSnapshot:
        # Clone friendly and enemy minions
        f_list: List[Dict[str, Any]] = []
        for m in friendly_minions:
            name = m.get("name", "友方随从")
            atk = m.get("attack", m.get("atk", 2))
            hp = m.get("health", m.get("hp", 2))
            f_list.append({"name": name, "attack": atk, "health": hp, "acted": False})

        e_list: List[Dict[str, Any]] = []
        for m in enemy_minions:
            name = m.get("name", "敌方随从")
            atk = m.get("attack", m.get("atk", 2))
            hp = m.get("health", m.get("hp", 2))
            e_list.append({"name": name, "attack": atk, "health": hp})

        # Add played minions from hand this turn
        if played_minions:
            for pm in played_minions:
                name = pm.get("name", "入场随从")
                atk = pm.get("attack", pm.get("atk", 2))
                hp = pm.get("health", pm.get("hp", 2))
                f_list.append({"name": name, "attack": atk, "health": hp, "acted": True})

        # Process trades
        trades = optimal_trades or []
        for tr in trades:
            # Parse trade string like "随从A 换 随从B" or "以小换大: A -> B"
            if "换" in tr or "->" in tr or "撞" in tr:
                # Find matching friendly and enemy minion
                unacted_f = [m for m in f_list if not m.get("acted", False) and m["health"] > 0]
                alive_e = [m for m in e_list if m["health"] > 0]
                if unacted_f and alive_e:
                    f_m = unacted_f[0]
                    e_m = alive_e[0]
                    f_m["health"] -= e_m["attack"]
                    e_m["health"] -= f_m["attack"]
                    f_m["acted"] = True

        # Collect survivors
        surviving_f = [
            SurvivingMinion(
                name=m["name"],
                attack=m["attack"],
                health=m["health"],
                is_friendly=True,
            )
            for m in f_list if m["health"] > 0
        ]

        surviving_e = [
            SurvivingMinion(
                name=m["name"],
                attack=m["attack"],
                health=m["health"],
                is_friendly=False,
            )
            for m in e_list if m["health"] > 0
        ]

        is_cleared = len(surviving_e) == 0
        total_f_atk = sum(m.attack for m in surviving_f)
        rem_mana = max(0, current_mana - spent_mana)
        hp_rem = max(0, enemy_hp - face_damage)

        clear_tag = "敌方全清 (0随从)" if is_cleared else f"敌存 {len(surviving_e)} 随从"
        mana_tag = f"{spent_mana}/{current_mana}费(满费无损)" if rem_mana == 0 else f"{spent_mana}/{current_mana}费(余{rem_mana}费)"
        badge = f"🔮 战后预演: ⚔️场攻 {total_f_atk}点 · 走脸 {face_damage}伤 · {clear_tag} · {mana_tag}"

        # Markdown Terminal Delta
        f_names = ", ".join(f"{m.name}({m.attack}/{m.health})" for m in surviving_f) or "无随从存活"
        e_names = "全清" if is_cleared else ", ".join(f"{m.name}({m.attack}/{m.health})" for m in surviving_e)
        delta_display = (
            f"<b>🔮 战后终局沙盘预演:</b><br>"
            f"• <b>我方存活:</b> <span style='color: #34d399;'>{f_names}</span> (总场攻 {total_f_atk} 点)<br>"
            f"• <b>敌方残留:</b> <span style='color: {'#38bdf8' if is_cleared else '#f87171'};'>{e_names}</span><br>"
            f"• <b>敌方剩余血量:</b> {hp_rem} 点 (走脸压制 -{face_damage} 点) · 水晶利用: {mana_tag}"
        )

        return GhostBoardSnapshot(
            surviving_friendly=surviving_f,
            surviving_enemies=surviving_e,
            is_enemy_cleared=is_cleared,
            net_face_damage=face_damage,
            enemy_hp_remaining=hp_rem,
            post_turn_board_attack=total_f_atk,
            mana_spent=spent_mana,
            mana_remaining=rem_mana,
            holographic_summary_badge=badge,
            terminal_delta_display=delta_display,
        )
