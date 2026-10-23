"""
ArenaCardStats: real arena card win-rate data from Firestone's public stats feed.

Source: https://static.zerotoheroes.com/api/arena/stats/cards/arena/{period}/{context}.gz.json
  - context: "global" or a lowercase class name ("mage", "demonhunter", ...)
  - each entry: cardId + counters (drawn, drawnThenWin, decksWithCard, decksWithCardThenWin, played, ...)

Metric used for drafting: "drawn win rate" (win rate of games in which the card was drawn),
shrunk toward the dataset baseline with a Bayesian prior so low-sample cards are not over-trusted.
Data is cached on disk (24h TTL) and refreshed in a background thread; when offline the cache is used,
and when no data exists at all the engine reports `None` (callers fall back to heuristics).
"""

from __future__ import annotations

import gzip
import json
import logging
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("ArenaCardStats")

STATS_URL = "https://static.zerotoheroes.com/api/arena/stats/cards/arena/{period}/{context}.gz.json"
DEFAULT_PERIOD = "last-patch"
CACHE_TTL_SEC = 24 * 3600
PRIOR_STRENGTH = 200          # pseudo-games pulling small samples toward the baseline
MIN_SAMPLE = 50               # below this many "drawn" games the card is treated as unknown
SCORE_PER_PP = 2.5            # draft score points per percentage point of win-rate delta
MAX_SCORE_DELTA = 25.0

CLASS_CONTEXT = {
    "DEATHKNIGHT": "deathknight", "DEMONHUNTER": "demonhunter", "DRUID": "druid",
    "HUNTER": "hunter", "MAGE": "mage", "PALADIN": "paladin", "PRIEST": "priest",
    "ROGUE": "rogue", "SHAMAN": "shaman", "WARLOCK": "warlock", "WARRIOR": "warrior",
}


def _default_cache_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "cache" / "arena_card_stats"


@dataclass
class CardWinrate:
    card_id: str
    context: str
    drawn_games: int
    drawn_winrate_pct: float        # raw
    adjusted_winrate_pct: float     # Bayesian-shrunk
    baseline_pct: float
    delta_pp: float                 # adjusted - baseline, percentage points
    score_delta: float              # draft score contribution
    played_winrate_pct: float
    deck_winrate_pct: float

    @property
    def label(self) -> str:
        sign = "+" if self.delta_pp >= 0 else ""
        return (f"📊 实战数据: 抽到胜率 {self.adjusted_winrate_pct:.1f}% "
                f"({sign}{self.delta_pp:.1f}pp, 样本 {self.drawn_games})")


class ArenaCardStats:
    _instance: Optional["ArenaCardStats"] = None
    _lock = threading.Lock()

    def __init__(self, cache_dir: Optional[Path] = None, period: str = DEFAULT_PERIOD,
                 auto_refresh: bool = True) -> None:
        self.cache_dir = cache_dir or _default_cache_dir()
        self.period = period
        self._data: Dict[str, Dict[str, Dict[str, Any]]] = {}   # context -> cardId -> stats
        self._baseline: Dict[str, float] = {}                   # context -> baseline drawn wr (0..1)
        self._updated: Dict[str, str] = {}
        self._fetching: set = set()
        self._data_lock = threading.RLock()
        self.auto_refresh = auto_refresh

    @classmethod
    def get_instance(cls) -> "ArenaCardStats":
        with cls._lock:
            if cls._instance is None:
                cls._instance = ArenaCardStats()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    # ------------------------------------------------------------------ loading
    def _cache_file(self, context: str) -> Path:
        return self.cache_dir / f"{self.period}_{context}.json"

    def load_payload(self, context: str, payload: Dict[str, Any]) -> int:
        """Index a raw Firestone payload ({lastUpdated, stats:[{cardId, stats}]})."""
        table: Dict[str, Dict[str, Any]] = {}
        wins = games = 0
        for entry in payload.get("stats", []):
            cid = entry.get("cardId")
            st = entry.get("stats") or {}
            if not cid:
                continue
            table[cid] = st
            wins += st.get("drawnThenWin", 0)
            games += st.get("drawn", 0)
        with self._data_lock:
            self._data[context] = table
            self._baseline[context] = (wins / games) if games else 0.5
            self._updated[context] = payload.get("lastUpdated", "")
        return len(table)

    def _load_from_cache(self, context: str) -> bool:
        f = self._cache_file(context)
        if not f.exists():
            return False
        try:
            self.load_payload(context, json.loads(f.read_text(encoding="utf-8")))
            return True
        except Exception as e:
            logger.warning(f"Corrupt arena stats cache {f}: {e}")
            return False

    def _fetch(self, context: str) -> bool:
        url = STATS_URL.format(period=self.period, context=context)
        try:
            req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip", "User-Agent": "HearthstoneArenaAI"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            payload = json.loads(raw.decode("utf-8"))
            n = self.load_payload(context, payload)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_file(context).write_text(json.dumps(payload), encoding="utf-8")
            logger.info(f"Fetched arena stats [{context}]: {n} cards, updated {payload.get('lastUpdated')}")
            return True
        except Exception as e:
            logger.warning(f"Arena stats fetch failed [{context}]: {e}")
            return False
        finally:
            self._fetching.discard(context)

    def _cache_is_stale(self, context: str) -> bool:
        f = self._cache_file(context)
        return (not f.exists()) or (time.time() - f.stat().st_mtime > CACHE_TTL_SEC)

    def ensure_context(self, context: str, blocking: bool = False) -> bool:
        """Make sure data for `context` is available; refresh in background when stale."""
        with self._data_lock:
            have = context in self._data
        if not have:
            have = self._load_from_cache(context)
        if self.auto_refresh and self._cache_is_stale(context) and context not in self._fetching:
            self._fetching.add(context)
            if blocking:
                return self._fetch(context) or have
            threading.Thread(target=self._fetch, args=(context,), daemon=True).start()
        return have

    def prefetch(self, hero_class: Optional[str] = None) -> None:
        """Non-blocking warm-up (call at app start / when hero is picked)."""
        self.ensure_context("global")
        ctx = CLASS_CONTEXT.get((hero_class or "").upper())
        if ctx:
            self.ensure_context(ctx)

    # ------------------------------------------------------------------ queries
    def has_data(self) -> bool:
        with self._data_lock:
            return bool(self._data)

    def last_updated(self, context: str = "global") -> str:
        return self._updated.get(context, "")

    def _lookup(self, context: str, card_id: str) -> Optional[Dict[str, Any]]:
        table = self._data.get(context)
        if not table:
            return None
        if card_id in table:
            return table[card_id]
        # Core-set reprints share stats with the original id and vice versa
        alt = card_id[5:] if card_id.startswith("CORE_") else f"CORE_{card_id}"
        return table.get(alt)

    def get_card_winrate(self, card_id: str, hero_class: Optional[str] = None) -> Optional[CardWinrate]:
        """Class-specific stats when the sample is large enough, else global. None if unknown."""
        if not card_id:
            return None
        contexts = []
        ctx = CLASS_CONTEXT.get((hero_class or "").upper())
        if ctx:
            self.ensure_context(ctx)
            contexts.append(ctx)
        self.ensure_context("global")
        contexts.append("global")

        with self._data_lock:
            for c in contexts:
                st = self._lookup(c, card_id)
                if not st or st.get("drawn", 0) < MIN_SAMPLE:
                    continue
                base = self._baseline.get(c, 0.5)
                n = st.get("drawn", 0)
                w = st.get("drawnThenWin", 0)
                raw = w / n
                adj = (w + PRIOR_STRENGTH * base) / (n + PRIOR_STRENGTH)
                delta_pp = (adj - base) * 100.0
                score = max(-MAX_SCORE_DELTA, min(MAX_SCORE_DELTA, delta_pp * SCORE_PER_PP))
                played = st.get("played", 0)
                decks = st.get("decksWithCard", 0)
                return CardWinrate(
                    card_id=card_id, context=c, drawn_games=n,
                    drawn_winrate_pct=raw * 100.0, adjusted_winrate_pct=adj * 100.0,
                    baseline_pct=base * 100.0, delta_pp=delta_pp, score_delta=score,
                    played_winrate_pct=(st.get("playedThenWin", 0) / played * 100.0) if played else 0.0,
                    deck_winrate_pct=(st.get("decksWithCardThenWin", 0) / decks * 100.0) if decks else 0.0,
                )
        return None
