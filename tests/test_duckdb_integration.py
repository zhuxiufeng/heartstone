"""
Tests for DuckDB Vectorized Embedded OLAP Engine Integration:
1. DuckDBManager Singleton & In-Memory Lifecycle
2. Card Ingestion & High-Speed Multi-Attribute SQL Filtering
3. Arena Career Vault OLAP Aggregation (Trophies, Hero Matrix, Win Rates)
4. Match History Event Lake & Failure Mode Breakdown
5. HSReplay Meta Analytics Bulk Query Engine
6. CardDatabase SQL Integration (query_sql & filter_cards_sql)
7. ArenaCareerVault & MatchHistoryLearner Automatic Sync
"""

import time
import pytest
from core.card_db import CardDatabase, CardInfo
from core.duckdb_manager import DuckDBManager
from core.arena_career_vault import ArenaCareerVault, ArenaRunRecord
from core.match_history_learner import MatchHistoryLearner, MatchRecord
from core.hsreplay_sync import HsreplaySync


@pytest.fixture(autouse=True)
def reset_duckdb():
    DuckDBManager.reset_instance()
    yield
    DuckDBManager.reset_instance()


def test_duckdb_manager_lifecycle():
    """Verify DuckDBManager initializes properly in-memory and verifies schema tables."""
    db = DuckDBManager(in_memory=True)
    assert db.is_available() is True
    assert db._initialized_tables is True

    # Test query scalar
    res = db.query_scalar("SELECT 42")
    assert res == 42


def test_duckdb_card_ingest_and_filter():
    """Verify bulk card ingestion and vectorized SQL filtering."""
    db = DuckDBManager(in_memory=True)

    sample_cards = [
        {"id": "C1", "name": "烈焰风暴", "cost": 7, "type": "SPELL", "cardClass": "MAGE", "text": "对所有敌方随从造成4点伤害。"},
        {"id": "C2", "name": "火球术", "cost": 4, "type": "SPELL", "cardClass": "MAGE", "text": "造成6点伤害。"},
        {"id": "C3", "name": "冰风雪人", "cost": 4, "type": "MINION", "cardClass": "NEUTRAL", "attack": 4, "health": 5, "text": ""},
        {"id": "C4", "name": "淡水鳄", "cost": 2, "type": "MINION", "cardClass": "NEUTRAL", "attack": 2, "health": 3, "text": ""},
        {"id": "C5", "name": "杀戮命令", "cost": 3, "type": "SPELL", "cardClass": "HUNTER", "text": "造成3点伤害。如果有野兽，造成5点伤害。"},
    ]

    count = db.ingest_cards(sample_cards)
    assert count == 5

    # Filter by cost
    cost4 = db.filter_cards(cost=4)
    assert len(cost4) == 2
    assert {c["name"] for c in cost4} == {"火球术", "冰风雪人"}

    # Filter by class and type
    mage_spells = db.filter_cards(card_class="MAGE", card_type="SPELL")
    assert len(mage_spells) == 2

    # Filter by keyword in text
    damage_cards = db.filter_cards(keyword="伤害")
    assert len(damage_cards) == 3


def test_duckdb_career_olap_aggregation():
    """Verify career summary aggregation correctly calculates runs, wins, trophies, and hero matrix."""
    db = DuckDBManager(in_memory=True)

    db.record_career_run("R1", 100.0, "MAGE", 12, 1, ["火球术", "烈焰风暴"], "火球术", True)
    db.record_career_run("R2", 200.0, "MAGE", 7, 3, ["火球术"], "火球术", False)
    db.record_career_run("R3", 300.0, "HUNTER", 5, 3, ["杀戮命令"], "杀戮命令", False)

    summary = db.aggregate_career_summary()

    assert summary["total_runs"] == 3
    assert summary["total_wins"] == 24
    assert summary["total_losses"] == 7
    assert summary["twelve_win_trophies"] == 1
    assert summary["average_wins_per_run"] == 8.0
    assert summary["best_hero_class"] == "MAGE"

    # Hero breakdown verification
    breakdown = summary["hero_breakdown"]
    assert "MAGE" in breakdown
    assert breakdown["MAGE"]["runs"] == 2
    assert breakdown["MAGE"]["wins"] == 19
    assert breakdown["MAGE"]["twelve_wins"] == 1
    assert breakdown["HUNTER"]["runs"] == 1
    assert breakdown["HUNTER"]["wins"] == 5


def test_duckdb_match_event_and_loss_reasons():
    """Verify match event recording and failure mode aggregation."""
    db = DuckDBManager(in_memory=True)

    db.record_match_event("M1", 10.0, "WIN", "MAGE", "HUNTER", 8)
    db.record_match_event("M2", 20.0, "LOSS", "MAGE", "HUNTER", 6, loss_reason="BURST_BURNOUT")
    db.record_match_event("M3", 30.0, "LOSS", "MAGE", "WARLOCK", 11, loss_reason="MANA_STALL")
    db.record_match_event("M4", 40.0, "LOSS", "MAGE", "HUNTER", 5, loss_reason="BURST_BURNOUT")

    # Failure mode distribution
    loss_stats = db.aggregate_loss_reasons()
    assert len(loss_stats) == 2
    assert loss_stats[0]["loss_reason"] == "BURST_BURNOUT"
    assert loss_stats[0]["count"] == 2

    # Opponent matchups
    matchups = db.aggregate_opponent_matchups()
    assert len(matchups) == 2
    hunter_m = next(m for m in matchups if m["opponent_hero"] == "HUNTER")
    assert hunter_m["total_games"] == 3
    assert hunter_m["wins"] == 1
    assert hunter_m["winrate_pct"] == 33.3


def test_duckdb_card_meta_analytics():
    """Verify HSReplay meta analytics table bulk upsert and query."""
    db = DuckDBManager(in_memory=True)

    records = [
        ("TTN_903", "阿曼苏尔", "S+", 68.5, 72.1, 85.0, 18.0, "泰坦控制核心"),
        ("CS2_032", "烈焰风暴", "S", 60.5, 64.2, 70.0, 10.0, "全场清场"),
        ("CS2_182", "冰风雪人", "B", 52.0, 53.0, 35.0, 3.0, "扎实站场"),
    ]
    upserted = db.bulk_upsert_card_meta(records)
    assert upserted == 3

    # Query rankings by tier
    s_tier = db.get_meta_rankings(tier="S+")
    assert len(s_tier) == 1
    assert s_tier[0]["card_name"] == "阿曼苏尔"

    # Query rankings with min winrate
    top_wr = db.get_meta_rankings(min_winrate=60.0)
    assert len(top_wr) == 2


def test_card_database_duckdb_sql_integration():
    """Verify CardDatabase.query_sql and filter_cards_sql interact with DuckDB."""
    card_db = CardDatabase.get_instance()
    card_db.load()

    # Test filter_cards_sql
    results = card_db.filter_cards_sql(cost=4, card_type="MINION", limit=5)
    assert len(results) > 0
    assert all(c.cost == 4 for c in results)

    # Test query_sql
    sql_res = card_db.query_sql("SELECT name, cost FROM cards WHERE cost = 2 LIMIT 3")
    assert len(sql_res) == 3
    assert all(r["cost"] == 2 for r in sql_res)


def test_arena_career_vault_and_match_history_sync(tmp_path):
    """Verify ArenaCareerVault and MatchHistoryLearner automatically sync records into DuckDB."""
    # Test ArenaCareerVault sync
    career_file = tmp_path / "test_career.json"
    vault = ArenaCareerVault(file_path=career_file)
    run_rec = vault.record_run(hero_class="WARRIOR", wins=9, losses=3, deck_card_names=["风暴战斧"], mvp_card="风暴战斧")
    assert run_rec.wins == 9

    summary = vault.get_duckdb_summary()
    assert summary is not None
    assert summary["total_runs"] >= 1

    # Test MatchHistoryLearner sync
    history_file = tmp_path / "test_history.json"
    learner = MatchHistoryLearner(history_file=history_file)
    learner.record_match(result="WIN", friendly_hero="MAGE", opponent_hero="PRIEST", turn_count=9)

    db = DuckDBManager.get_instance()
    match_count = db.query_scalar("SELECT count(*) FROM match_events WHERE opponent_hero = 'PRIEST'")
    assert match_count >= 1


def test_duckdb_ai_effectiveness_closedloop():
    """Verify DuckDB records turn advice outcomes and computes AI effectiveness metrics."""
    from core.turn_replayer import MatchReplaySummary, TurnReviewNode

    db = DuckDBManager(in_memory=True)

    # Match 1: Player strictly followed AI (high compliance), won the game
    node_m1_t1 = TurnReviewNode(
        turn_number=1, mana=1, max_mana=1, friendly_hp=30, enemy_hp=30,
        ai_best_plan=["法力浮龙"], player_actual_plays=["法力浮龙"], score=100, action_grade="✅ 最佳 (Best)"
    )
    node_m1_t2 = TurnReviewNode(
        turn_number=2, mana=2, max_mana=2, friendly_hp=30, enemy_hp=28,
        ai_best_plan=["寒冰箭走脸"], player_actual_plays=["寒冰箭走脸"], score=100, action_grade="✅ 最佳 (Best)",
        had_lethal=True, lethal_damage=6
    )
    summary_m1 = MatchReplaySummary(
        result="WIN", total_turns=2, overall_accuracy_pct=100.0, grade_tier="S",
        turn_nodes=[node_m1_t1, node_m1_t2]
    )
    ingested_m1 = db.record_match_replay(
        match_id="M_MATCH_1", timestamp=100.0, result="WIN", friendly_hero="MAGE", opponent_hero="HUNTER", summary=summary_m1
    )
    assert ingested_m1 == 2

    # Match 2: Player diverged from AI (blunders / missed lethal), lost the game
    node_m2_t1 = TurnReviewNode(
        turn_number=1, mana=1, max_mana=1, friendly_hp=30, enemy_hp=30,
        ai_best_plan=["转甲"], player_actual_plays=[], score=30, action_grade="❌ 严重伏笔 (Blunder)"
    )
    node_m2_t2 = TurnReviewNode(
        turn_number=2, mana=2, max_mana=2, friendly_hp=20, enemy_hp=5,
        ai_best_plan=["火球斩杀"], player_actual_plays=["转甲空过"], score=15, action_grade="❌ 严重伏笔 (Blunder)",
        had_lethal=True, lethal_damage=6
    )
    summary_m2 = MatchReplaySummary(
        result="LOSS", total_turns=2, overall_accuracy_pct=22.5, grade_tier="D",
        turn_nodes=[node_m2_t1, node_m2_t2]
    )
    ingested_m2 = db.record_match_replay(
        match_id="M_MATCH_2", timestamp=200.0, result="LOSS", friendly_hero="WARRIOR", opponent_hero="ROGUE", summary=summary_m2
    )
    assert ingested_m2 == 2

    # Run closedloop effectiveness query
    report = db.query_ai_effectiveness_report()

    assert report["total_matches_analyzed"] == 2
    assert report["total_turns_analyzed"] == 4
    assert report["winrate_when_followed"] == 100.0
    assert report["winrate_when_diverged"] == 0.0
    assert report["effectiveness_delta"] == 100.0
    assert report["lethal_conversion_pct"] == 50.0  # 1 won, 1 lost with lethal
    assert report["blunder_rate_per_game"] == 1.0   # 2 blunders across 2 games = 1.0/game
    assert len(report["grade_distribution"]) >= 2
