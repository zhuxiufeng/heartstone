"""
MatchHistoryLearner: Local match repository & adaptive reinforcement learner.
Records game outcomes to customize personal card weights and pinpoint loss root causes.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MatchHistoryLearner")


def get_default_history_file() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "cache" / "match_history.json"


MATCH_HISTORY_FILE = get_default_history_file()


@dataclass
class MatchRecord:
    result: str                     # "WIN" or "LOSS"
    friendly_hero: str
    opponent_hero: str
    turn_count: int
    deck_card_ids: List[str] = field(default_factory=list)
    loss_reason: str = ""           # e.g., "MANA_STALL", "BURST_BURNOUT", "AOE_WIPE"
    timestamp: float = 0.0


class MatchHistoryLearner:
    """
    Learns personalized card performance adjustments from historical local games.
    """

    def __init__(self, history_file: Path = MATCH_HISTORY_FILE) -> None:
        self.history_file = history_file
        self.matches: List[MatchRecord] = []
        self._load()

    def _load(self) -> None:
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.matches = [
                            MatchRecord(
                                result=m.get("result", "UNKNOWN"),
                                friendly_hero=m.get("friendly_hero", "UNKNOWN"),
                                opponent_hero=m.get("opponent_hero", "UNKNOWN"),
                                turn_count=m.get("turn_count", 0),
                                deck_card_ids=m.get("deck_card_ids", []),
                                loss_reason=m.get("loss_reason", ""),
                                timestamp=m.get("timestamp", 0.0),
                            )
                            for m in data
                        ]
                        logger.info(f"Loaded {len(self.matches)} match records.")
                        # Sync to DuckDB
                        try:
                            from .duckdb_manager import DuckDBManager
                            db = DuckDBManager.get_instance()
                            if db.is_available() and db.query_scalar("SELECT count(*) FROM match_events") == 0:
                                for m in self.matches:
                                    db.record_match_event(
                                        match_id=f"M_{int(m.timestamp)}",
                                        timestamp=m.timestamp,
                                        result=m.result,
                                        friendly_hero=m.friendly_hero,
                                        opponent_hero=m.opponent_hero,
                                        turn_count=m.turn_count,
                                        loss_reason=m.loss_reason,
                                        deck_cards=m.deck_card_ids,
                                    )
                        except Exception as ex:
                            logger.debug(f"DuckDB match history sync on load: {ex}")
            except Exception as e:
                logger.warning(f"Failed to load match history: {e}")

    def save(self) -> None:
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([asdict(m) for m in self.matches], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save match history: {e}")

    def record_match(
        self,
        result: str,
        friendly_hero: str,
        opponent_hero: str,
        turn_count: int,
        deck_card_ids: Optional[List[str]] = None,
        loss_reason: str = "",
    ) -> None:
        import time
        rec = MatchRecord(
            result=result.upper(),
            friendly_hero=friendly_hero.upper(),
            opponent_hero=opponent_hero.upper(),
            turn_count=turn_count,
            deck_card_ids=deck_card_ids or [],
            loss_reason=loss_reason,
            timestamp=time.time(),
        )
        self.matches.append(rec)
        self.save()
        try:
            from .duckdb_manager import DuckDBManager
            db = DuckDBManager.get_instance()
            if db.is_available():
                db.record_match_event(
                    match_id=f"M_{int(rec.timestamp)}",
                    timestamp=rec.timestamp,
                    result=rec.result,
                    friendly_hero=rec.friendly_hero,
                    opponent_hero=rec.opponent_hero,
                    turn_count=rec.turn_count,
                    loss_reason=rec.loss_reason,
                    deck_cards=rec.deck_card_ids,
                )
        except Exception as e:
            logger.debug(f"DuckDB record_match_event sync: {e}")
        logger.info(f"Recorded match: {result} ({friendly_hero} vs {opponent_hero})")

    def get_card_winrate_adjustment(self, card_id: str) -> float:
        """
        Calculates personal dynamic bonus or penalty based on historical deck inclusion win-rates.
        """
        if not self.matches:
            return 0.0

        times_included = 0
        times_won = 0

        for m in self.matches:
            if card_id in m.deck_card_ids:
                times_included += 1
                if m.result == "WIN":
                    times_won += 1

        # Minimum sample size of 5 games
        if times_included < 5:
            return 0.0

        personal_winrate = times_won / times_included
        if personal_winrate >= 0.75:
            return 5.0
        elif personal_winrate >= 0.65:
            return 3.0
        elif personal_winrate <= 0.30:
            return -5.0
        elif personal_winrate <= 0.40:
            return -3.0

        return 0.0

    def get_summary_stats(self) -> Dict[str, Any]:
        """Returns aggregate win rate and stats."""
        total = len(self.matches)
        if total == 0:
            return {"total_matches": 0, "win_rate": 0.0, "wins": 0, "losses": 0}

        wins = sum(1 for m in self.matches if m.result == "WIN")
        losses = total - wins
        wr = round((wins / total) * 100, 1)

        return {
            "total_matches": total,
            "wins": wins,
            "losses": losses,
            "win_rate": wr,
        }
