"""
LogListener: High-performance Hearthstone log file tailer and event dispatcher.
Monitors Arena.log and Power.log as a background QThread.
Extracts arena drafting actions (MakePick, draft choices), game turns, and card plays.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from PyQt5.QtCore import QObject, QThread, pyqtSignal
except ImportError:
    class QThread:  # type: ignore
        def __init__(self, parent=None): pass
        def start(self): pass
        def quit(self): pass
        def wait(self): pass
    def pyqtSignal(*args):  # type: ignore
        class _Signal:
            def connect(self, fn): pass
            def emit(self, *a, **kw): pass
        return _Signal()

from .card_db import CardDatabase, CardInfo, get_class_cn

logger = logging.getLogger("LogListener")

# Precompiled regex patterns for zero-overhead parsing
RE_HERO = re.compile(r"CardID=(HERO_\d+[a-z]?)")
RE_TURN = re.compile(r"TAG_CHANGE Entity=GameEntity tag=TURN value=(\d+)")
RE_RESOURCES = re.compile(r"tag=RESOURCES value=(\d+)")
RE_RESOURCES_USED = re.compile(r"tag=RESOURCES_USED value=(\d+)")
RE_CARD_ID = re.compile(r"CardID=([A-Za-z0-9_]+)")


class LogListener(QThread):
    """Watches Hearthstone Arena.log and Power.log in real time without blocking."""

    # Draft Signals
    draft_hero_selected = pyqtSignal(str)          # Hero class (e.g. "MAGE", "PALADIN")
    draft_choices_updated = pyqtSignal(list)       # List of 3 candidate CardInfo
    card_picked = pyqtSignal(dict)                 # {"card_id": str, "slot": int, "card": CardInfo}
    card_previewed = pyqtSignal(object)            # CardInfo when hovered in draft
    draft_finished = pyqtSignal(list)              # List of picked CardInfo (up to 30)

    # Play Mode Signals
    game_started = pyqtSignal(dict)                # {"player": str, "opponent": str}
    turn_active = pyqtSignal(dict)                 # {"turn": int, "is_player_turn": bool}
    card_played = pyqtSignal(dict)                 # {"player": str, "card_id": str, "card": CardInfo}
    play_state_updated = pyqtSignal(dict)          # {"turn": int, "mana": int, "max_mana": int, "hand": list, "friendly_board": list, "enemy_board": list, "opponent_hero": str}
    game_over = pyqtSignal(dict)                   # {"won": bool}

    # Diagnostics
    log_status = pyqtSignal(str)

    def __init__(
        self,
        log_dir: str,
        card_db: Optional[CardDatabase] = None,
        poll_interval_sec: float = 0.25,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.log_dir = Path(log_dir).resolve()
        self.card_db = card_db or CardDatabase.get_instance()
        self.poll_interval = poll_interval_sec

        self._running = False
        self._arena_pos = 0
        self._power_pos = 0

        # Draft state tracking
        self.current_hero: str = "UNKNOWN"
        self.current_deck: List[CardInfo] = []
        self.current_choices: List[CardInfo] = []

        # Play state tracking
        self.in_game = False
        self.turn_count = 1
        self.is_my_turn = True
        self.current_mana = 1
        self.max_mana = 1
        self.player_hand: List[CardInfo] = []
        self.friendly_board: List[str] = []
        self.enemy_board: List[str] = []
        self.opponent_hero: str = "法师"

    def update_log_dir(self, new_dir: str) -> None:
        """Dynamically update log directory."""
        self.log_dir = Path(new_dir).resolve()
        self._arena_pos = 0
        self._power_pos = 0
        logger.info(f"Log directory updated to: {self.log_dir}")

    def reset_draft(self) -> None:
        """Clear current draft state."""
        self.current_deck.clear()
        self.current_choices.clear()
        self.current_hero = "UNKNOWN"

    def stop(self) -> None:
        """Request clean termination."""
        self._running = False

    def _find_active_log_dir(self) -> Path:
        """Finds active log directory, either self.log_dir or the latest Hearthstone session subdirectory."""
        if not self.log_dir.exists():
            return self.log_dir

        try:
            subdirs = [d for d in self.log_dir.iterdir() if d.is_dir() and d.name.startswith("Hearthstone_")]
            if subdirs:
                # Sort by timestamp in directory name descending
                subdirs.sort(key=lambda d: d.name, reverse=True)
                return subdirs[0]
        except Exception as e:
            logger.debug(f"Error enumerating subdirs in {self.log_dir}: {e}")

        return self.log_dir

    def run(self) -> None:
        """Worker loop reading new lines appended to Arena.log and Power.log."""
        self._running = True
        logger.info(f"LogListener thread started, watching base: {self.log_dir}")
        self.log_status.emit(f"日志监听已就绪: {self.log_dir.name}")

        active_dir = self._find_active_log_dir()
        logger.info(f"LogListener active session dir: {active_dir}")

        arena_file = active_dir / "Arena.log"
        power_file = active_dir / "Power.log"

        # For active arena draft session, parse from start to recover current hero & picks
        self._arena_pos = 0

        if power_file.exists():
            try:
                self._power_pos = power_file.stat().st_size
            except OSError:
                self._power_pos = 0

        last_dir_check_time = time.time()

        while self._running:
            try:
                # Every 2 seconds, check if Hearthstone created a newer session directory
                now = time.time()
                if now - last_dir_check_time > 2.0:
                    last_dir_check_time = now
                    newest_dir = self._find_active_log_dir()
                    if newest_dir != active_dir:
                        logger.info(f"Detected new Hearthstone session folder: {newest_dir.name}")
                        active_dir = newest_dir
                        arena_file = active_dir / "Arena.log"
                        power_file = active_dir / "Power.log"
                        self._arena_pos = 0
                        self._power_pos = 0
                        self.log_status.emit(f"已切换新会话日志: {active_dir.name}")

                # Check files in active session folder, with fallback to base log_dir
                af = arena_file if arena_file.exists() else (self.log_dir / "Arena.log")
                pf = power_file if power_file.exists() else (self.log_dir / "Power.log")

                self._check_file(af, is_arena=True)
                self._check_file(pf, is_arena=False)
            except Exception as e:
                logger.error(f"Error reading log file: {e}", exc_info=True)
                self.log_status.emit(f"日志读取警告: {e}")

            time.sleep(self.poll_interval)

        logger.info("LogListener thread finished.")

    def _check_file(self, file_path: Path, is_arena: bool) -> None:
        if not file_path.exists():
            return

        current_size = file_path.stat().st_size
        last_pos = self._arena_pos if is_arena else self._power_pos

        # File was truncated or recreated
        if current_size < last_pos:
            last_pos = 0

        if current_size > last_pos:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(last_pos)
                    lines = f.readlines()
                    new_pos = f.tell()

                if is_arena:
                    is_preload = (last_pos == 0)
                    self._arena_pos = new_pos
                    for line in lines:
                        self._parse_arena_line(line, is_preload=is_preload)
                else:
                    self._power_pos = new_pos
                    for line in lines:
                        self._parse_power_line(line)
            except Exception as e:
                logger.debug(f"File read error on {file_path}: {e}")

    # ==========================
    # Arena.log Parser
    # ==========================
    def _parse_arena_line(self, line: str, is_preload: bool = False) -> None:
        line_clean = line.strip()
        if not line_clean:
            return

        # 1. Detect Pick: "MakePick - Chosen Card: CORE_CS2_039 Slot: 12" or similar
        # Regex covers multiple variants across HS patch logs
        pick_match = re.search(r"MakePick.*?Chosen Card:\s*([A-Za-z0-9_]+)(?:.*?Slot:\s*(\d+))?", line_clean)
        if not pick_match:
            pick_match = re.search(r"MakePick\s*slot=(\d+)\s*cardId=([A-Za-z0-9_]+)", line_clean)
            if pick_match:
                slot = int(pick_match.group(1))
                card_id = pick_match.group(2)
            else:
                slot, card_id = None, None
        else:
            card_id = pick_match.group(1)
            slot = int(pick_match.group(2)) if pick_match.group(2) else len(self.current_deck) + 1

        if card_id:
            card_info = self.card_db.get_by_id(card_id) or CardInfo(id=card_id, name=card_id)
            self.current_deck.append(card_info)
            logger.info(f"Draft Pick detected: Slot {slot} -> {card_info.name} ({card_id})")

            payload = {
                "card_id": card_id,
                "slot": slot or len(self.current_deck),
                "card": card_info,
                "total_picked": len(self.current_deck),
            }
            if not is_preload:
                self.card_picked.emit(payload)
                self.log_status.emit(f"第 {len(self.current_deck)}/30 抓: {card_info.name}")

            if len(self.current_deck) >= 30 and not is_preload:
                logger.info("Arena draft finished with 30 cards.")
                self.draft_finished.emit(list(self.current_deck))
            return

        # 2. Hero selection or draft init (e.g. "hero=HERO_11", "Client chooses: ... (HERO_11)", "Hero: HERO_11")
        hero_match = re.search(r"(?:Hero:\s*|hero=|\(HERO_)(HERO_\d+[a-z]?|[A-Za-z0-9_]+)", line_clean, re.IGNORECASE)
        if hero_match:
            hero_raw = hero_match.group(1).upper()
            if not hero_raw.startswith("HERO_") and "HERO_" in line_clean.upper():
                m_sub = re.search(r"(HERO_\d+[a-z]?)", line_clean, re.IGNORECASE)
                if m_sub:
                    hero_raw = m_sub.group(1).upper()

            hero_id_map = {
                "HERO_01": "WARRIOR", "HERO_02": "SHAMAN", "HERO_03": "ROGUE",
                "HERO_04": "PALADIN", "HERO_05": "HUNTER", "HERO_06": "DRUID",
                "HERO_07": "WARLOCK", "HERO_08": "MAGE", "HERO_09": "PRIEST",
                "HERO_10": "DEMONHUNTER", "HERO_11": "DEATHKNIGHT"
            }
            card = self.card_db.get_by_id(hero_raw)
            hero_class = card.card_class if card else hero_id_map.get(hero_raw, hero_raw)
            class_cn_map = {
                "DEATHKNIGHT": "死亡骑士", "DEMONHUNTER": "恶魔猎手", "DRUID": "德鲁伊",
                "HUNTER": "猎人", "MAGE": "法师", "PALADIN": "圣骑士",
                "PRIEST": "牧师", "ROGUE": "潜行者", "SHAMAN": "萨满祭司",
                "WARLOCK": "术士", "WARRIOR": "战士",
                "HERO_01": "战士", "HERO_02": "萨满祭司", "HERO_03": "潜行者",
                "HERO_04": "圣骑士", "HERO_05": "猎人", "HERO_06": "德鲁伊",
                "HERO_07": "术士", "HERO_08": "法师", "HERO_09": "牧师",
                "HERO_10": "恶魔猎手", "HERO_11": "死亡骑士"
            }
            hero_name = class_cn_map.get(hero_class, class_cn_map.get(hero_raw, hero_class))
            if self.current_hero != hero_name and self.current_hero != hero_class:
                self.current_hero = hero_name
                self.draft_hero_selected.emit(hero_name)
                logger.info(f"Arena Hero selected: {hero_name} ({hero_raw})")

        # 3. Detect client card choice: "Client chooses: 弗林特·枪臂 (WW_379)"
        choose_match = re.search(r"Client chooses:\s*(.*?)\s*\(([A-Za-z0-9_]+)\)", line_clean)
        if choose_match:
            c_name = choose_match.group(1).strip()
            c_id = choose_match.group(2).strip()
            if not c_id.startswith("HERO_"):
                c_info = self.card_db.get_by_id(c_id)
                if not c_info:
                    c_info = self.card_db.fuzzy_match_card(c_name) or CardInfo(id=c_id, name=c_name)
                if not is_preload:
                    self.current_deck.append(c_info)
                    logger.info(f"Draft card chosen: {c_info.name} ({c_id})")
                    self.card_picked.emit({
                        "card_id": c_id,
                        "slot": len(self.current_deck),
                        "card": c_info,
                        "card_name": c_info.name,
                        "total_picked": len(self.current_deck),
                    })

        # 4. Draft choices logged (e.g. ClientRequestDraftChoicesAndContents)
        if "DraftManager.OnChoicesAndContents" in line_clean:
            self.current_choices = []
            self.draft_choices_updated.emit([])

        if "DraftChoices" in line_clean or "Choices:" in line_clean:
            ids = re.findall(r"([A-Za-z0-9_]{4,30})", line_clean)
            valid_cards = []
            for cid in ids:
                c = self.card_db.get_by_id(cid)
                if c and c.collectible:
                    valid_cards.append(c)
            if len(valid_cards) == 3:
                self.current_choices = valid_cards
                self.draft_choices_updated.emit(valid_cards)

    # ==========================
    # Power.log Parser
    # ==========================
    def _parse_power_line(self, line: str) -> None:
        line_clean = line.strip()
        if not line_clean:
            return

        # Ultra-fast path pre-filter: Skip 95%+ non-action log lines before regex
        if not ("TAG_CHANGE" in line_clean or "BlockType=PLAY" in line_clean or "ZONE" in line_clean or "CREATE_GAME" in line_clean or "CardID=HERO" in line_clean):
            return

        # Game start detection
        if "CREATE_GAME" in line_clean:
            self.in_game = True
            self.turn_count = 1
            self.current_mana = 1
            self.max_mana = 1
            self.player_hand.clear()
            self.friendly_board.clear()
            self.enemy_board.clear()
            self.game_started.emit({"turn": 1})
            self.log_status.emit("对局开始 (实战模式)")
            self._emit_play_state()
            return

        # Game end detection
        if "TAG_CHANGE Entity=GameEntity tag=STATE value=COMPLETE" in line_clean:
            self.in_game = False
            self.game_over.emit({"won": True})
            self.log_status.emit("对局结束")
            return

        # Opponent hero detection
        hero_match = RE_HERO.search(line_clean)
        if hero_match:
            hid = hero_match.group(1)
            hero_card = self.card_db.get_by_id(hid)
            if hero_card and hero_card.card_class != "NEUTRAL":
                self.opponent_hero = get_class_cn(hero_card.card_class)

        # Turn change detection
        turn_match = RE_TURN.search(line_clean)
        if turn_match:
            raw_turn = int(turn_match.group(1))
            self.turn_count = max(1, raw_turn // 2) if raw_turn > 1 else 1
            calculated_mana = min(10, self.turn_count)
            self.current_mana = calculated_mana
            self.max_mana = calculated_mana
            self.turn_active.emit({"turn": self.turn_count, "raw_turn": raw_turn, "is_player_turn": self.is_my_turn})
            self._emit_play_state()
            return

        # Mana resources detection
        mana_match = RE_RESOURCES.search(line_clean)
        if mana_match:
            self.max_mana = int(mana_match.group(1))
            self.current_mana = self.max_mana

        mana_used_match = RE_RESOURCES_USED.search(line_clean)
        if mana_used_match:
            used = int(mana_used_match.group(1))
            self.current_mana = max(0, self.max_mana - used)
            self._emit_play_state()

        # Hand card tracking: SHOW_ENTITY or TAG_CHANGE to HAND
        if "tag=ZONE value=HAND" in line_clean or "zone=HAND" in line_clean:
            cid_match = RE_CARD_ID.search(line_clean)
            if cid_match:
                cid = cid_match.group(1)
                c_info = self.card_db.get_by_id(cid)
                if c_info and c_info.collectible and not any(h.id == cid for h in self.player_hand):
                    self.player_hand.append(c_info)
                    self._emit_play_state()

        # Card play detection: BlockType=PLAY
        if "BlockType=PLAY" in line_clean:
            card_match = RE_CARD_ID.search(line_clean)
            if card_match:
                cid = card_match.group(1)
                c_info = self.card_db.get_by_id(cid) or CardInfo(id=cid, name=cid)
                # Deduct from hand if present
                for idx, h in enumerate(self.player_hand):
                    if h.id == cid:
                        self.player_hand.pop(idx)
                        self.current_mana = max(0, self.current_mana - h.cost)
                        break
                self.card_played.emit({"card_id": cid, "card": c_info})
                self._emit_play_state()

    def _emit_play_state(self) -> None:
        """Dispatches live board and hand payload for real-time play suggestions."""
        payload = {
            "turn": self.turn_count,
            "mana": self.current_mana,
            "max_mana": self.max_mana,
            "hand": list(self.player_hand),
            "friendly_board": list(self.friendly_board),
            "enemy_board": list(self.enemy_board),
            "opponent_hero": self.opponent_hero,
        }
        self.play_state_updated.emit(payload)
