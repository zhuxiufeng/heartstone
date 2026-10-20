"""
Unit tests for HeroDraftAdvisor.
"""

from core.hero_draft_advisor import HeroDraftAdvisor, HeroTierInfo


def test_hero_tier_evaluation_t0_ranking():
    # Choices: Death Knight (T0), Hunter (T2), Warrior (T3)
    choices = ["死亡骑士", "猎人", "战士"]
    results = HeroDraftAdvisor.evaluate_hero_choices(choices)

    assert len(results) == 3
    # Top ranked must be Death Knight
    best = results[0]
    assert best.class_name == "DEATHKNIGHT"
    assert best.tier == "T0"
    assert best.winrate >= 56.0
    assert "采矿事故" in best.draft_priority_advice or "绝对霸主" in best.draft_priority_advice

    # Worst ranked must be Warrior
    worst = results[2]
    assert worst.class_name == "WARRIOR"
    assert worst.tier == "T3"


def test_get_best_hero():
    best = HeroDraftAdvisor.get_best_hero(["法师", "恶魔猎手", "牧师"])
    assert best is not None
    # Demon Hunter is T0 (power 94), Mage is T1 (power 89)
    assert best.class_name == "DEMONHUNTER"
