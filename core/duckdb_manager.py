"""
DuckDBManager: High-Performance Embedded OLAP Analytics Engine for Hearthstone Arena AI.
Provides sub-millisecond vectorized SQL querying for:
1. In-process Card Metadata Search & Complex Multi-Filter Aggregations.
2. Arena Career Vault Multi-Dimensional OLAP (Winrates, Hero Matchup Matrix, Trophy Aggregations).
3. Match History Event Lake & Loss Reason Attribution Analysis.
4. HSReplay & Firestone Meta Analytics Query Engine.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("DuckDBManager")

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    duckdb = None  # type: ignore
    DUCKDB_AVAILABLE = False
    logger.warning("DuckDB is not installed. Analytics will use in-memory fallbacks.")


def get_default_duckdb_path() -> Path:
    """Locates or creates default duckdb storage file across frozen exe and source environments."""
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    cache_dir = base_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "arena_analytics.duckdb"


class DuckDBManager:
    """
    Singleton DuckDB manager orchestrating local vectorized analytics.
    Thread-safe connection handling with automatic schema migrations and graceful fallbacks.
    """

    _instance: Optional[DuckDBManager] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None, in_memory: bool = False) -> None:
        self.in_memory = in_memory
        self.db_path = ":memory:" if in_memory else str(db_path or get_default_duckdb_path())
        self._con: Optional[duckdb.DuckDBPyConnection] = None  # type: ignore
        self._op_lock = threading.RLock()
        self._initialized_tables = False

        if DUCKDB_AVAILABLE:
            self._connect()
            self._init_schemas()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None, in_memory: bool = False) -> DuckDBManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = DuckDBManager(db_path=db_path, in_memory=in_memory)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (useful for isolated testing)."""
        with cls._lock:
            if cls._instance and cls._instance._con:
                try:
                    cls._instance._con.close()
                except Exception:
                    pass
            cls._instance = None

    def is_available(self) -> bool:
        """Returns True if DuckDB is installed and connection is active."""
        return DUCKDB_AVAILABLE and self._con is not None

    def _connect(self) -> None:
        """Initializes duckdb connection with fallback to in-memory on disk errors."""
        try:
            self._con = duckdb.connect(database=self.db_path, read_only=False)
            logger.info(f"DuckDB connection established successfully at: {self.db_path}")
        except Exception as e:
            logger.warning(f"Failed to open DuckDB at {self.db_path}: {e}. Falling back to in-memory database.")
            try:
                self._con = duckdb.connect(database=":memory:", read_only=False)
                self.in_memory = True
            except Exception as ex2:
                logger.error(f"Failed to initialize in-memory DuckDB: {ex2}")
                self._con = None

    def _init_schemas(self) -> None:
        """Creates tables and indexes for card DB, career runs, match events, and meta cache."""
        if not self._con:
            return

        with self._op_lock:
            try:
                # 1. Cards Table
                self._con.execute("""
                    CREATE TABLE IF NOT EXISTS cards (
                        id VARCHAR PRIMARY KEY,
                        name VARCHAR,
                        cost INT,
                        card_type VARCHAR,
                        card_class VARCHAR,
                        attack INT,
                        health INT,
                        rarity VARCHAR,
                        text VARCHAR,
                        mechanics VARCHAR
                    );
                    CREATE INDEX IF NOT EXISTS idx_cards_cost ON cards(cost);
                    CREATE INDEX IF NOT EXISTS idx_cards_class ON cards(card_class);
                    CREATE INDEX IF NOT EXISTS idx_cards_type ON cards(card_type);
                """)

                # 2. Career Runs Table
                self._con.execute("""
                    CREATE TABLE IF NOT EXISTS career_runs (
                        run_id VARCHAR PRIMARY KEY,
                        timestamp DOUBLE,
                        hero_class VARCHAR,
                        wins INT,
                        losses INT,
                        deck_cards VARCHAR,
                        mvp_card VARCHAR,
                        is_twelve_wins BOOLEAN
                    );
                    CREATE INDEX IF NOT EXISTS idx_career_hero ON career_runs(hero_class);
                    CREATE INDEX IF NOT EXISTS idx_career_wins ON career_runs(wins);
                """)

                # 3. Match Events Table (Individual Games)
                self._con.execute("""
                    CREATE TABLE IF NOT EXISTS match_events (
                        match_id VARCHAR,
                        timestamp DOUBLE,
                        result VARCHAR,
                        friendly_hero VARCHAR,
                        opponent_hero VARCHAR,
                        turn_count INT,
                        loss_reason VARCHAR,
                        deck_cards VARCHAR
                    );
                    CREATE INDEX IF NOT EXISTS idx_match_result ON match_events(result);
                    CREATE INDEX IF NOT EXISTS idx_match_opp ON match_events(opponent_hero);
                """)

                # 4. Card Meta Analytics Table
                self._con.execute("""
                    CREATE TABLE IF NOT EXISTS card_meta (
                        card_id VARCHAR PRIMARY KEY,
                        card_name VARCHAR,
                        tier VARCHAR,
                        deck_winrate DOUBLE,
                        played_winrate DOUBLE,
                        inclusion_rate DOUBLE,
                        score_delta DOUBLE,
                        synergy_tag VARCHAR
                    );
                """)
                self._initialized_tables = True
            except Exception as e:
                logger.error(f"Error initializing DuckDB schemas: {e}", exc_info=True)

    # -------------------------------------------------------------------------
    # Generic SQL Execution
    # -------------------------------------------------------------------------
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> None:
        if not self._con:
            return
        with self._op_lock:
            try:
                cursor = self._con.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
            except Exception as e:
                logger.error(f"DuckDB execute error: {e} | SQL: {sql}")
                raise

    def query(self, sql: str, params: Optional[List[Any]] = None) -> List[Tuple]:
        if not self._con:
            return []
        with self._op_lock:
            try:
                cursor = self._con.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                return cursor.fetchall()
            except Exception as e:
                logger.error(f"DuckDB query error: {e} | SQL: {sql}")
                return []

    def query_dicts(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        if not self._con:
            return []
        with self._op_lock:
            try:
                cursor = self._con.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                logger.error(f"DuckDB query_dicts error: {e} | SQL: {sql}")
                return []

    def query_scalar(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        if not self._con:
            return None
        with self._op_lock:
            try:
                cursor = self._con.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                row = cursor.fetchone()
                return row[0] if row else None
            except Exception as e:
                logger.error(f"DuckDB query_scalar error: {e} | SQL: {sql}")
                return None

    # -------------------------------------------------------------------------
    # Card Database Vectorized Operations
    # -------------------------------------------------------------------------
    def ingest_cards_from_json(self, json_path: Path) -> int:
        """Vectorized single-SQL bulk ingestion from cards.json (sub-second for 36,000+ cards)."""
        if not self._con or not json_path.exists():
            return 0
        with self._op_lock:
            try:
                # Use duckdb's native read_json_auto for blazing speed
                escaped_path = str(json_path.resolve()).replace("\\", "/")
                self._con.execute(f"""
                    INSERT OR REPLACE INTO cards (id, name, cost, card_type, card_class, attack, health, rarity, text, mechanics)
                    SELECT 
                        id, 
                        name, 
                        coalesce(cost, 0) as cost, 
                        coalesce(type, '') as card_type, 
                        coalesce(cardClass, 'NEUTRAL') as card_class, 
                        attack, 
                        health, 
                        coalesce(rarity, 'COMMON') as rarity, 
                        coalesce(text, '') as text, 
                        to_json(mechanics) as mechanics
                    FROM read_json_auto('{escaped_path}')
                """)
                count = self.query_scalar("SELECT count(*) FROM cards") or 0
                logger.info(f"Directly ingested {count} cards from JSON into DuckDB in one shot.")
                return count
            except Exception as e:
                logger.error(f"Error ingesting cards from JSON file {json_path}: {e}", exc_info=True)
                return 0

    def ingest_cards(self, cards_data: List[Any]) -> int:
        """Bulk ingests or updates card records into the DuckDB cards table (supports dicts and CardInfo)."""
        if not self._con or not cards_data:
            return 0
        with self._op_lock:
            try:
                rows = []
                for c in cards_data:
                    if isinstance(c, dict):
                        cid = c.get("id") or c.get("cardId") or ""
                        if not cid:
                            continue
                        rows.append((
                            cid, c.get("name", ""), c.get("cost", 0) or 0,
                            c.get("type") or c.get("card_type") or "",
                            c.get("cardClass") or c.get("card_class") or "NEUTRAL",
                            c.get("attack"), c.get("health"), c.get("rarity", "COMMON"),
                            c.get("text", "") or "", json.dumps(c.get("mechanics", []))
                        ))
                    else:
                        cid = getattr(c, "id", "")
                        if not cid:
                            continue
                        rows.append((
                            cid, getattr(c, "name", ""), getattr(c, "cost", 0) or 0,
                            getattr(c, "card_type", ""), getattr(c, "card_class", "NEUTRAL"),
                            getattr(c, "attack", None), getattr(c, "health", None),
                            getattr(c, "rarity", "COMMON"), getattr(c, "text", "") or "",
                            json.dumps(getattr(c, "mechanics", []))
                        ))

                cursor = self._con.cursor()
                cursor.executemany("""
                    INSERT OR REPLACE INTO cards 
                    (id, name, cost, card_type, card_class, attack, health, rarity, text, mechanics)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows)
                logger.info(f"Ingested {len(rows)} cards into DuckDB.")
                return len(rows)
            except Exception as e:
                logger.error(f"Error ingesting cards into DuckDB: {e}", exc_info=True)
                return 0

    def filter_cards(
        self,
        cost: Optional[int] = None,
        min_cost: Optional[int] = None,
        max_cost: Optional[int] = None,
        card_type: Optional[str] = None,
        card_class: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Executes fast multi-attribute query against cards table."""
        if not self._con:
            return []
        where_clauses = ["1=1"]
        params: List[Any] = []

        if cost is not None:
            where_clauses.append("cost = ?")
            params.append(cost)
        if min_cost is not None:
            where_clauses.append("cost >= ?")
            params.append(min_cost)
        if max_cost is not None:
            where_clauses.append("cost <= ?")
            params.append(max_cost)
        if card_type:
            where_clauses.append("card_type = ?")
            params.append(card_type.upper())
        if card_class:
            where_clauses.append("card_class = ?")
            params.append(card_class.upper())
        if keyword:
            where_clauses.append("(name LIKE ? OR text LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        sql = f"""
            SELECT id, name, cost, card_type, card_class, attack, health, rarity, text
            FROM cards
            WHERE {' AND '.join(where_clauses)}
            ORDER BY cost ASC, attack DESC
            LIMIT {int(limit)}
        """
        return self.query_dicts(sql, params)

    # -------------------------------------------------------------------------
    # Arena Career Vault OLAP Analytics
    # -------------------------------------------------------------------------
    def record_career_run(
        self,
        run_id: str,
        timestamp: float,
        hero_class: str,
        wins: int,
        losses: int,
        deck_cards: List[str],
        mvp_card: str = "",
        is_twelve_wins: bool = False,
    ) -> None:
        """Inserts or updates arena career run in DuckDB."""
        if not self._con:
            return
        with self._op_lock:
            try:
                cards_json = json.dumps(deck_cards, ensure_ascii=False)
                self._con.execute("""
                    INSERT OR REPLACE INTO career_runs
                    (run_id, timestamp, hero_class, wins, losses, deck_cards, mvp_card, is_twelve_wins)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [run_id, timestamp, hero_class, wins, losses, cards_json, mvp_card, is_twelve_wins])
            except Exception as e:
                logger.error(f"Error recording career run in DuckDB: {e}")

    def aggregate_career_summary(self) -> Dict[str, Any]:
        """Calculates career totals, averages, trophies, and hero breakdowns in single vectorized pass."""
        if not self._con:
            return {
                "total_runs": 0, "total_wins": 0, "total_losses": 0,
                "overall_winrate_pct": 0.0, "average_wins_per_run": 0.0,
                "twelve_win_trophies": 0, "best_hero_class": "NONE",
                "best_hero_winrate_pct": 0.0, "hero_breakdown": {},
            }
        with self._op_lock:
            try:
                # Overall totals
                totals = self.query("""
                    SELECT 
                        count(*) as total_runs,
                        coalesce(sum(wins), 0) as total_wins,
                        coalesce(sum(losses), 0) as total_losses,
                        coalesce(avg(wins), 0.0) as avg_wins,
                        coalesce(sum(case when is_twelve_wins or wins >= 12 then 1 else 0 end), 0) as twelve_wins
                    FROM career_runs
                """)
                if not totals or totals[0][0] == 0:
                    return {
                        "total_runs": 0, "total_wins": 0, "total_losses": 0,
                        "overall_winrate_pct": 0.0, "average_wins_per_run": 0.0,
                        "twelve_win_trophies": 0, "best_hero_class": "NONE",
                        "best_hero_winrate_pct": 0.0, "hero_breakdown": {},
                    }

                t_runs, t_wins, t_losses, avg_wins, t_twelve = totals[0]
                t_total_games = t_wins + t_losses
                overall_wr = round((t_wins / t_total_games) * 100.0, 1) if t_total_games > 0 else 0.0

                # Per hero breakdown
                breakdown_rows = self.query("""
                    SELECT 
                        hero_class,
                        count(*) as runs,
                        sum(wins) as wins,
                        sum(losses) as losses,
                        avg(wins) as avg_wins,
                        sum(case when is_twelve_wins or wins >= 12 then 1 else 0 end) as twelve_wins
                    FROM career_runs
                    GROUP BY hero_class
                    ORDER BY wins DESC
                """)

                hero_dict: Dict[str, Dict[str, Any]] = {}
                best_hero = "NONE"
                best_wr = 0.0

                for r in breakdown_rows:
                    h_class, h_runs, h_wins, h_losses, h_avg, h_12 = r
                    h_games = h_wins + h_losses
                    h_wr = round((h_wins / h_games) * 100.0, 1) if h_games > 0 else 0.0
                    hero_dict[h_class] = {
                        "runs": h_runs,
                        "wins": h_wins,
                        "losses": h_losses,
                        "winrate_pct": h_wr,
                        "avg_wins": round(float(h_avg), 1),
                        "twelve_wins": h_12,
                    }
                    if h_wr > best_wr and h_runs >= 1:
                        best_wr = h_wr
                        best_hero = h_class

                return {
                    "total_runs": t_runs,
                    "total_wins": t_wins,
                    "total_losses": t_losses,
                    "overall_winrate_pct": overall_wr,
                    "average_wins_per_run": round(float(avg_wins), 1),
                    "twelve_win_trophies": t_twelve,
                    "best_hero_class": best_hero,
                    "best_hero_winrate_pct": best_wr,
                    "hero_breakdown": hero_dict,
                }
            except Exception as e:
                logger.error(f"Error computing career summary with DuckDB: {e}", exc_info=True)
                return {}

    # -------------------------------------------------------------------------
    # Match History & Loss Reason Diagnostics
    # -------------------------------------------------------------------------
    def record_match_event(
        self,
        match_id: str,
        timestamp: float,
        result: str,
        friendly_hero: str,
        opponent_hero: str,
        turn_count: int,
        loss_reason: str = "",
        deck_cards: Optional[List[str]] = None,
    ) -> None:
        """Records single combat game outcome into match_events table."""
        if not self._con:
            return
        with self._op_lock:
            try:
                cards_json = json.dumps(deck_cards or [], ensure_ascii=False)
                self._con.execute("""
                    INSERT INTO match_events 
                    (match_id, timestamp, result, friendly_hero, opponent_hero, turn_count, loss_reason, deck_cards)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [match_id, timestamp, result, friendly_hero, opponent_hero, turn_count, loss_reason, cards_json])
            except Exception as e:
                logger.error(f"Error recording match event in DuckDB: {e}")

    def aggregate_loss_reasons(self) -> List[Dict[str, Any]]:
        """Returns distribution and frequencies of failure modes across matches."""
        sql = """
            SELECT 
                loss_reason,
                count(*) as count,
                round(count(*) * 100.0 / sum(count(*)) over (), 1) as percentage
            FROM match_events
            WHERE result = 'LOSS' AND loss_reason IS NOT NULL AND loss_reason != ''
            GROUP BY loss_reason
            ORDER BY count DESC
        """
        return self.query_dicts(sql)

    def aggregate_opponent_matchups(self) -> List[Dict[str, Any]]:
        """Computes winrates and average game duration against each opponent class."""
        sql = """
            SELECT 
                opponent_hero,
                count(*) as total_games,
                sum(case when result = 'WIN' then 1 else 0 end) as wins,
                round(sum(case when result = 'WIN' then 1 else 0 end) * 100.0 / count(*), 1) as winrate_pct,
                round(avg(turn_count), 1) as avg_turns
            FROM match_events
            GROUP BY opponent_hero
            ORDER BY total_games DESC
        """
        return self.query_dicts(sql)

    # -------------------------------------------------------------------------
    # HSReplay Meta Analytics Operations
    # -------------------------------------------------------------------------
    def bulk_upsert_card_meta(self, records: List[Tuple]) -> int:
        """Upserts card meta analytics into card_meta table."""
        if not self._con or not records:
            return 0
        with self._op_lock:
            try:
                cursor = self._con.cursor()
                cursor.executemany("""
                    INSERT OR REPLACE INTO card_meta
                    (card_id, card_name, tier, deck_winrate, played_winrate, inclusion_rate, score_delta, synergy_tag)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, records)
                return len(records)
            except Exception as e:
                logger.error(f"Error bulk upserting card meta: {e}")
                return 0

    def get_meta_rankings(
        self,
        tier: Optional[str] = None,
        min_winrate: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Queries card meta rankings with optional tier and winrate filters."""
        where = ["1=1"]
        params: List[Any] = []
        if tier:
            where.append("tier = ?")
            params.append(tier.upper())
        if min_winrate is not None:
            where.append("deck_winrate >= ?")
            params.append(min_winrate)

        sql = f"""
            SELECT card_id, card_name, tier, deck_winrate, played_winrate, inclusion_rate, score_delta, synergy_tag
            FROM card_meta
            WHERE {' AND '.join(where)}
            ORDER BY deck_winrate DESC, inclusion_rate DESC
            LIMIT {int(limit)}
        """
        return self.query_dicts(sql, params)
