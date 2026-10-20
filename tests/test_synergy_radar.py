from core.card_db import CardInfo
from core.synergy_radar import SynergyRadar


def test_synergy_radar_empty():
    rep = SynergyRadar.analyze_deck([])
    assert rep.overall_balance_score == 0.0
    assert "构筑起步" in rep.archetype_title


def test_synergy_radar_with_deck():
    c1 = CardInfo(id="1", name="叫嚣的矮人", cost=1, attack=2, health=1, text="战吼：使一个随从获得+2攻击力", card_type="MINION")
    c2 = CardInfo(id="2", name="烈焰风暴", cost=7, text="对所有敌方随从造成5点伤害", card_type="SPELL")
    c3 = CardInfo(id="3", name="刺杀", cost=5, text="消灭一个敌方随从", card_type="SPELL")
    c4 = CardInfo(id="4", name="奥术智慧", cost=3, text="抽两张牌", card_type="SPELL")
    c5 = CardInfo(id="5", name="火球术", cost=4, text="对任意目标造成6点伤害", card_type="SPELL")

    rep = SynergyRadar.analyze_deck([c1, c2, c3, c4, c5])
    assert rep.early_tempo_score > 0
    assert rep.board_clear_score > 0
    assert rep.hard_removal_score > 0
    assert rep.card_draw_score > 0
    assert rep.reach_burst_score > 0
    assert rep.overall_balance_score > 0
    assert len(rep.archetype_title) > 0
