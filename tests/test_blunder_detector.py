from core.blunder_detector import BlunderDetector, TurnSnapshot


def test_blunder_detector_clean_win():
    history = [
        TurnSnapshot(turn_number=1, mana_available=1, friendly_hp=30, enemy_hp=30),
        TurnSnapshot(turn_number=2, mana_available=2, friendly_hp=30, enemy_hp=28),
        TurnSnapshot(turn_number=3, mana_available=3, friendly_hp=30, enemy_hp=20, had_lethal=True, lethal_damage=22),
    ]
    report = BlunderDetector.evaluate_match(
        result="WIN",
        friendly_hero="法师",
        opponent_hero="猎人",
        turn_history=history,
    )
    assert report.result == "WIN"
    assert "S" in report.match_grade
    assert len(report.blunders) == 0


def test_blunder_detector_missed_lethal():
    history = [
        TurnSnapshot(turn_number=1, mana_available=1, friendly_hp=30, enemy_hp=30),
        TurnSnapshot(turn_number=2, mana_available=2, friendly_hp=30, enemy_hp=5, had_lethal=True, lethal_damage=6),
        TurnSnapshot(turn_number=3, mana_available=3, friendly_hp=10, enemy_hp=5),  # Continued game after lethal
    ]
    report = BlunderDetector.evaluate_match(
        result="LOSS",
        friendly_hero="法师",
        opponent_hero="猎人",
        turn_history=history,
    )
    assert report.result == "LOSS"
    assert "C" in report.match_grade
    assert len(report.blunders) >= 1
    assert any(b.blunder_type == "MISSED_LETHAL" for b in report.blunders)
