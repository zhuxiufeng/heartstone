import pytest
from core.turn_replayer import TurnReplayerEngine, TurnReviewNode, MatchReplaySummary


def test_turn_replayer_sample_generation():
    summary = TurnReplayerEngine.generate_sample_replay()
    assert isinstance(summary, MatchReplaySummary)
    assert summary.total_turns == 6
    assert summary.result == "WIN"
    assert summary.overall_accuracy_pct > 0.0
    assert summary.brilliant_count >= 1
    assert summary.best_count >= 1
    assert summary.inaccuracy_count >= 1
    assert summary.blunder_count >= 1
    assert len(summary.turn_nodes) == 6


def test_missed_lethal_blunder():
    node = TurnReviewNode(
        turn_number=5,
        mana=5,
        max_mana=5,
        friendly_hp=20,
        enemy_hp=8,
        had_lethal=True,
        lethal_damage=12,
        player_actual_plays=["空过回合"],
    )
    summary = TurnReplayerEngine.analyze_replay(result="LOSS", turn_snapshots=[node])
    assert summary.blunder_count == 1
    assert node.action_grade == "❌ 严重伏笔 (Blunder)"
    assert node.score == 15
    assert "错失当回合斩杀" in node.analysis_comment


def test_blunder_shield_violation():
    node = TurnReviewNode(
        turn_number=3,
        mana=3,
        max_mana=3,
        friendly_hp=25,
        enemy_hp=25,
        blunder_alerts=["法术抽牌时序倒置！严禁先打伤害再抽牌"],
    )
    summary = TurnReplayerEngine.analyze_replay(result="WIN", turn_snapshots=[node])
    assert summary.blunder_count == 1
    assert node.action_grade == "❌ 严重伏笔 (Blunder)"
    assert node.score == 25
    assert "时序禁忌" in node.analysis_comment


def test_floating_mana_inaccuracy():
    node = TurnReviewNode(
        turn_number=4,
        mana=4,
        max_mana=4,
        friendly_hp=30,
        enemy_hp=30,
        hand_cards=["卡牌A", "卡牌B", "卡牌C"],
        floating_mana=3,
    )
    summary = TurnReplayerEngine.analyze_replay(result="WIN", turn_snapshots=[node])
    assert summary.inaccuracy_count == 1
    assert node.action_grade == "⚠️ 疑问手 (Inaccuracy)"
    assert node.score == 45
    assert "法力利用率严重偏低" in node.analysis_comment


def test_brilliant_lethal_win():
    node = TurnReviewNode(
        turn_number=7,
        mana=7,
        max_mana=7,
        friendly_hp=15,
        enemy_hp=10,
        had_lethal=True,
        lethal_damage=14,
    )
    summary = TurnReplayerEngine.analyze_replay(result="WIN", turn_snapshots=[node])
    assert summary.brilliant_count == 1
    assert node.action_grade == "★ 妙手 (Brilliant)"
    assert node.score == 100
    assert "精准计算" in node.analysis_comment
