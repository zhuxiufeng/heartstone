"""
Unit tests for ArchetypeSpecializer (Draft Archetype Detection & Dynamic Synergy Specialization).
"""

from core.card_db import CardInfo
from core.archetype_specializer import ArchetypeSpecializer, ArchetypeType, ArchetypeProfile


def _make_card(id: str, name: str, cost: int, card_type: str = "MINION", text: str = "", race: str = None, mechanics: list = None) -> CardInfo:
    return CardInfo(
        id=id,
        name=name,
        cost=cost,
        attack=cost,
        health=cost,
        durability=None,
        card_class="NEUTRAL",
        card_type=card_type,
        rarity="COMMON",
        set_name="CORE",
        text=text,
        race=race,
        races=[race] if race else [],
        spell_school=None,
        mechanics=mechanics or [],
        collectible=True,
        raw_data={},
    )


def test_early_picks_undetermined():
    deck = [_make_card(f"c{i}", f"卡牌{i}", 2) for i in range(7)]
    prof = ArchetypeSpecializer.detect_archetype(deck)
    assert prof.archetype == ArchetypeType.UNDETERMINED


def test_aggro_archetype_detection_and_score_modifier():
    # 12 cards: 9 low cost (1-3 mana)
    low_cards = [_make_card(f"c{i}", f"低费{i}", 2) for i in range(9)]
    other_cards = [_make_card(f"c{i}", f"中费{i}", 4) for i in range(3)]
    deck = low_cards + other_cards

    prof = ArchetypeSpecializer.detect_archetype(deck)
    assert prof.archetype == ArchetypeType.AGGRO
    assert "极限快攻" in prof.name_cn

    # Aggro bonus for 2-drop
    card_2 = _make_card("c2", "淡水鳄", 2)
    score_2, desc_2 = ArchetypeSpecializer.evaluate_card_archetype_delta(card_2, prof)
    assert score_2 > 0
    assert "快攻契合" in desc_2

    # Aggro penalty for 7-drop
    card_7 = _make_card("c7", "暴风城勇士", 7)
    score_7, desc_7 = ArchetypeSpecializer.evaluate_card_archetype_delta(card_7, prof)
    assert score_7 < -15
    assert "流派冲突" in desc_7


def test_control_archetype_detection_and_score_modifier():
    # Heavy cards with board clears
    heavy_cards = [_make_card(f"c{i}", f"大怪{i}", 7) for i in range(5)]
    clears = [_make_card(f"clear{i}", f"清场{i}", 5, card_type="SPELL", text="对所有随从造成4点伤害。") for i in range(4)]
    mid_cards = [_make_card(f"mid{i}", f"中坚{i}", 4) for i in range(4)]
    deck = heavy_cards + clears + mid_cards

    prof = ArchetypeSpecializer.detect_archetype(deck)
    assert prof.archetype == ArchetypeType.CONTROL
    assert "资源控制" in prof.name_cn

    # Control bonus for AOE
    aoe_card = _make_card("flamestrike", "烈焰风暴", 7, card_type="SPELL", text="对所有敌方随从造成5点伤害。")
    score_aoe, desc_aoe = ArchetypeSpecializer.evaluate_card_archetype_delta(aoe_card, prof)
    assert score_aoe > 15
    assert "控制核心" in desc_aoe


def test_tribal_synergy_detection():
    dragons = [_make_card(f"d{i}", f"龙{i}", 4, race="Dragon") for i in range(6)]
    others = [_make_card(f"o{i}", f"杂项{i}", 3) for i in range(5)]
    deck = dragons + others

    prof = ArchetypeSpecializer.detect_archetype(deck)
    assert prof.archetype == ArchetypeType.TRIBAL_SYNERGY
    assert "Dragon" in prof.name_cn

    dragon_cand = _make_card("d_cand", "暮光幼龙", 4, race="Dragon")
    score_d, desc_d = ArchetypeSpecializer.evaluate_card_archetype_delta(dragon_cand, prof)
    assert score_d >= 20
    assert "种族联动" in desc_d
