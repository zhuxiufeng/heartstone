"""
BurstDamageGuard: Opponent Burst Damage Threshold & Lethal Defense Guard for Hearthstone Arena.
Calculates opponent's maximum burst potential (empty-board spells/weapons/hero power + field attack)
on their upcoming turn and generates high-priority survival directives.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("BurstDamageGuard")


# Approximate empty-board maximum realistic burst damage by Class and Mana available in Arena
# Includes typical direct burn spells, weapons, charge/rush buffs, and hero power
CLASS_BURST_CURVES: Dict[str, Dict[int, int]] = {
    "MAGE": {
        1: 1,   # 技能点脸/奥术飞弹
        2: 2,   # 寒冰箭/技能
        3: 3,   # 寒冰箭+技能
        4: 6,   # 火球术
        5: 7,   # 火球+技能
        6: 9,   # 火球+寒冰箭
        7: 10,  # 火球+寒冰箭+技能
        8: 12,  # 双火球
        9: 13,  # 双火球+技能
        10: 16, # 炎爆术+火球/双火球+寒冰箭
    },
    "HUNTER": {
        1: 2,   # 奥术射击/技能
        2: 2,   # 稳固射击技能
        3: 5,   # 杀戮命令 (野兽在场)
        4: 5,   # 杀戮命令/武器
        5: 7,   # 杀戮命令 + 技能点脸
        6: 7,   # 杀戮 + 鹰角弓
        7: 9,   # 杀戮 + 奥术射击 + 技能
        8: 10,  # 双杀戮
        9: 11,  # 暴龙王克鲁什(8) + 技能(2) ~ 10-11
        10: 12, # 暴龙王 + 杀戮
    },
    "SHAMAN": {
        1: 3,   # 闪电箭
        2: 3,   # 闪电箭/熔岩震击
        3: 5,   # 熔岩爆裂
        4: 8,   # 闪电箭 + 熔岩爆裂
        5: 8,   # 嗜血基础点/熔岩爆裂
        6: 9,   # 双熔岩爆裂 / 嗜血爆发
        7: 11,  # 双熔岩 + 闪电箭
        8: 11,  # 闪电箭双发+熔岩
        9: 14,  # 三重过载直伤
        10: 14,
    },
    "ROGUE": {
        1: 2,   # 匕首+毒药
        2: 3,   # 影袭/刺骨
        3: 4,   # 刺骨连击
        4: 7,   # 刺骨(4) + 影袭(3)
        5: 8,   # 刺骨 + 刀油/毒刃
        6: 10,  # 连击刺骨 + 火车王/冷血
        7: 10,
        8: 12,  # 斩杀连击
        9: 12,
        10: 14,
    },
    "WARLOCK": {
        1: 4,   # 灵魂之火 (丢牌)
        2: 4,   # 灵魂之火
        3: 4,   # 灵魂火/吸血
        4: 7,   # 地狱烈焰(3) + 灵魂之火(4)
        5: 8,   # 力量代价 + 灵魂火
        6: 9,   # 末日守卫(5) + 灵魂火(4)
        7: 9,
        8: 11,  # 双灵魂火 + 恶魔
        9: 11,
        10: 13,
    },
    "PALADIN": {
        1: 1,
        2: 2,
        3: 3,
        4: 4,   # 真银圣剑 (4点斩杀)
        5: 4,
        6: 6,   # 复仇之怒随机 / 奉献+真银
        7: 6,
        8: 8,   # 提里奥弗丁 / 军备大剑
        9: 8,
        10: 10,
    },
    "WARRIOR": {
        1: 2,
        2: 3,   # 英雄打击(+4)
        3: 3,   # 炽炎战斧
        4: 5,   # 库卡隆精英卫士(4) / 英打+武器
        5: 6,   # 奥金斧(5) + 技能
        6: 7,   # 奥金斧(5) + 英雄打击(4) 拆分
        7: 9,   # 奥金斧 + 英雄打击
        8: 9,   # 格罗玛什地狱咆哮激怒(10)
        9: 12,  # 吼爹激怒(10) + 怒火中烧
        10: 12,
    },
    "DRUID": {
        1: 1,   # 技能点脸
        2: 2,   # 愤怒/爪击
        3: 3,   # 爪击+技能
        4: 4,   # 横扫点脸
        5: 5,   # 横扫+技能
        6: 6,   # 星火术(5) / 横扫+爪击
        7: 6,
        8: 8,   # 双横扫
        9: 10,  # 自然之力 + 野性咆哮斩杀线
        10: 12,
    },
    "DEMONHUNTER": {
        1: 1,   # 技能点脸(1费打1)
        2: 3,   # 混乱打击(+2) + 技能
        3: 4,   # 协调打击/战刃
        4: 6,   # 刃缚精魂(4) + 技能
        5: 7,   # 恶魔变形单发
        6: 8,   # 恶魔变形 + 冲锋突袭
        7: 8,
        8: 10,
        9: 10,
        10: 12,
    },
    "DEATHKNIGHT": {
        1: 1,
        2: 3,   # 冰霜打击
        3: 4,   # 寒冬号角+直伤
        4: 5,   # 萨萨里安突袭走脸
        5: 6,   # 骨髓操纵者
        6: 7,   # 冰霜巨龙之怒(5点冻结直伤)
        7: 8,   # 冰龙之怒 + 技能
        8: 10,
        9: 10,
        10: 12,
    },
    "PRIEST": {
        1: 0,
        2: 2,   # 神圣惩击
        3: 3,
        4: 5,   # 心灵震爆(5)
        5: 5,
        6: 6,   # 神圣新星+惩击
        7: 7,   # 心灵震爆 + 惩击
        8: 8,
        9: 10,  # 双心爆
        10: 10,
    },
}


@dataclass
class BurstThreatReport:
    opponent_class: str
    opponent_mana: int
    opponent_field_atk: int
    empty_board_burst: int
    total_projected_damage: int
    friendly_hp: int
    friendly_armor: int
    friendly_taunt_hp: int
    effective_hp: int
    lethal_deficit: int              # Damage exceeding friendly HP (>0 means LETHAL threat!)
    safety_margin: int               # HP remaining after surviving burst (<=0 means dead)
    threat_tier: str                 # "CRITICAL_LETHAL", "HIGH_DANGER", "MODERATE", "SAFE"
    danger_badge: str
    survival_directive: str
    threat_breakdown: List[str] = field(default_factory=list)


class BurstDamageGuard:
    """Evaluates opponent lethal damage thresholds and generates survival directives."""

    @classmethod
    def evaluate_threat(
        cls,
        opponent_class: str,
        current_turn: int,
        opponent_board_atk: int,
        friendly_hp: int,
        friendly_armor: int = 0,
        friendly_taunt_hp: int = 0,
        opponent_has_coin: bool = False,
    ) -> BurstThreatReport:
        norm_class = opponent_class.upper().strip()
        # Fallback to MAGE curve if unknown
        burst_table = CLASS_BURST_CURVES.get(norm_class, CLASS_BURST_CURVES["MAGE"])

        # Opponent's mana on their next turn
        next_mana = min(10, current_turn + 1)
        if opponent_has_coin:
            next_mana = min(10, next_mana + 1)

        empty_burst = burst_table.get(next_mana, burst_table.get(10, 10))

        # Taunts soak board minion damage first
        effective_board_damage = max(0, opponent_board_atk - friendly_taunt_hp)
        total_dmg = effective_board_damage + empty_burst

        effective_hp = friendly_hp + friendly_armor
        deficit = total_dmg - effective_hp
        margin = effective_hp - total_dmg

        breakdown = [
            f"敌方场攻威胁: {opponent_board_atk} 点 (我方嘲讽吸收 {friendly_taunt_hp} 点，有效走脸: {effective_board_damage} 点)",
            f"敌方空场直伤爆发: ~{empty_burst} 点 ({norm_class} {next_mana}费极限法术/技能斩杀线)",
            f"下回合总斩杀威胁: {total_dmg} 点 vs 我方总生命: {effective_hp} 点",
        ]

        if deficit >= 0:
            tier = "CRITICAL_LETHAL"
            badge = f"🚨 敌方绝杀预警 (缺口 {deficit} 点)"
            directive = (
                f"【生死决断·防绝杀】敌方下回合预计拥有 {next_mana} 费，总爆发高达 {total_dmg} 点！"
                f"我方生命仅 {effective_hp} 点（处于斩杀死区，伤害溢出 {deficit} 点）！"
                f"必须优先击杀敌方高攻随从，或打出嘲讽/叠甲抬血，否则下回合必遭斩杀！"
            )
        elif margin <= 3:
            tier = "HIGH_DANGER"
            badge = f"⚠️ 斩杀濒危边缘 (仅余 {margin} 血)"
            directive = (
                f"【濒危血线防范】下回合敌方总爆发可达 {total_dmg} 点，我方仅余 {margin} 点容错空间！"
                f"随时可能因敌方神抽直伤崩盘，建议稳健控场清怪，避免走脸贪伤害。"
            )
        elif margin <= 8:
            tier = "MODERATE"
            badge = f"🛡️ 处于安全阈值 (容差 {margin} 点)"
            directive = f"敌方下回合斩杀线约为 {total_dmg} 点，我方血量处于安全范围，可在控场与适度走脸间灵活抉择。"
        else:
            tier = "SAFE"
            badge = f"✅ 血线高枕无忧 (容差 {margin} 点)"
            directive = "敌方爆发完全无法威胁我方生命，可放心铺场提速施压！"

        return BurstThreatReport(
            opponent_class=norm_class,
            opponent_mana=next_mana,
            opponent_field_atk=opponent_board_atk,
            empty_board_burst=empty_burst,
            total_projected_damage=total_dmg,
            friendly_hp=friendly_hp,
            friendly_armor=friendly_armor,
            friendly_taunt_hp=friendly_taunt_hp,
            effective_hp=effective_hp,
            lethal_deficit=deficit,
            safety_margin=margin,
            threat_tier=tier,
            danger_badge=badge,
            survival_directive=directive,
            threat_breakdown=breakdown,
        )

    @classmethod
    def get_next_turn_key_cards(cls, opponent_class: str, next_mana: int) -> List[Dict[str, str]]:
        """Returns the Top 3 key Arena threat cards the opponent can play on their upcoming mana turn."""
        norm_class = opponent_class.upper().strip()
        threat_db = {
            "MAGE": {
                2: [{"name": "寒冰箭", "cost": 2, "effect": "3伤+冻结", "counter": "防单体打3控大怪"}],
                3: [{"name": "奥术智慧", "cost": 3, "effect": "过2张牌", "counter": "敌方补资源拐点"}],
                4: [{"name": "火球术", "cost": 4, "effect": "6点高额直伤", "counter": "血线务必保持6以上"}],
                5: [{"name": "冰锥术", "cost": 5, "effect": "冻结3目标+1伤", "counter": "大随从置于两翼"}],
                6: [{"name": "暴风雪", "cost": 6, "effect": "全场2伤+全部冻结", "counter": "控制随从铺场数量"}],
                7: [
                    {"name": "烈焰风暴", "cost": 7, "effect": "全场打4清场", "counter": "优先做5血以上随从"},
                    {"name": "火焰之地传送门", "cost": 7, "effect": "打5+召随机5费", "counter": "留解牌防大怪反场"},
                ],
                8: [{"name": "创世之力", "cost": 8, "effect": "发现双6费突袭", "counter": "留强解应付双大怪"}],
                10: [{"name": "炎爆术", "cost": 10, "effect": "10点终结斩杀", "counter": "血量必须维持10以上"}],
            },
            "PALADIN": {
                2: [{"name": "护盾机器人", "cost": 2, "effect": "圣盾抢场面", "counter": "小随从破盾交换"}],
                4: [
                    {"name": "奉献", "cost": 4, "effect": "全场打2", "counter": "随从血量提升至3以上"},
                    {"name": "真银圣剑", "cost": 4, "effect": "4攻提刀回血", "counter": "架嘲讽挡脸挡刀"},
                    {"name": "王者祝福", "cost": 4, "effect": "+4/+4超强滚雪球", "counter": "务必清理全部杂毛"},
                ],
                6: [{"name": "正义防御", "cost": 3, "effect": "偷取最大攻击力", "counter": "避免单个超高攻单核"}],
                8: [{"name": "提里奥·弗丁", "cost": 8, "effect": "圣盾嘲讽+5/3灰烬", "counter": "保留沉默或变形术"}],
            },
            "HUNTER": {
                2: [{"name": "爆炸陷阱", "cost": 2, "effect": "全场打2奥秘", "counter": "先用小怪打脸试探"}],
                3: [{"name": "杀戮命令", "cost": 3, "effect": "5点野兽直伤", "counter": "绝对清光所有野兽"}],
                5: [{"name": "狂踏的犀牛", "cost": 5, "effect": "突袭践踏直伤", "counter": "低血怪主动送掉防穿甲"}],
                6: [{"name": "长鬃草原狮", "cost": 6, "effect": "6/5亡语双土狼", "counter": "留变形或先抢脸压死"}],
            },
            "WARRIOR": {
                3: [{"name": "炽炎战斧", "cost": 3, "effect": "3/2提刀控场", "counter": "防3血核心被白砍"}],
                5: [
                    {"name": "绝命乱斗", "cost": 5, "effect": "全场仅留1怪生还", "counter": "避免孤注一掷全铺"},
                    {"name": "奥金斧", "cost": 5, "effect": "5/2高伤战斧", "counter": "架嘲讽保核心血线"},
                ],
            },
            "PRIEST": {
                4: [{"name": "暗影狂乱", "cost": 4, "effect": "借小怪内讧相撞", "counter": "防亡语小怪被抓"}],
                5: [{"name": "群体狂乱", "cost": 5, "effect": "全场随从互相撞击", "counter": "控制随从攻血差"}],
                6: [
                    {"name": "神圣新星", "cost": 3, "effect": "全场打2敌方回血", "counter": "随从血量堆到3以上"},
                    {"name": "圣光炸弹", "cost": 6, "effect": "攻击力反伤自爆", "counter": "高攻低血随从极危"},
                ],
            },
            "WARLOCK": {
                4: [{"name": "地狱烈焰", "cost": 4, "effect": "全场打3包英雄", "counter": "随从血量抬到4血以上"}],
                5: [{"name": "末日守卫", "cost": 5, "effect": "5/7冲锋突袭", "counter": "防5血冲脸斩杀"}],
                8: [{"name": "扭曲虚空", "cost": 8, "effect": "彻底消灭所有随从", "counter": "保留手牌后续返场"}],
            },
            "SHAMAN": {
                3: [{"name": "闪电风暴", "cost": 3, "effect": "全场打3过载2", "counter": "做4血随从安全存活"}],
                5: [{"name": "嗜血", "cost": 5, "effect": "全体随从+3攻击", "counter": "清光一切随从与图腾"}],
            },
            "ROGUE": {
                2: [{"name": "刺骨", "cost": 2, "effect": "4点连击斩杀", "counter": "防4血斩杀线"}],
                5: [{"name": "邪脊刺杀者", "cost": 5, "effect": "连击直接消灭单体", "counter": "分散战力莫全押单怪"}],
            },
            "DRUID": {
                4: [{"name": "横扫", "cost": 4, "effect": "主目标打4其余打1", "counter": "主怪防4其余防1"}],
                8: [{"name": "终极感染", "cost": 10, "effect": "打5抽5回5召5/5", "counter": "提速走脸尽快终结"}],
            },
            "DEATHKNIGHT": {
                5: [{"name": "尸爆", "cost": 5, "effect": "连续死尸全场连炸", "counter": "控制死尸数量"}],
                6: [{"name": "侏儒嚼嚼怪", "cost": 6, "effect": "5/6突袭吸血", "counter": "防大怪被吸血反超"}],
            },
            "DEMONHUNTER": {
                3: [{"name": "眼棱", "cost": 3, "effect": "打3吸血流放0费", "counter": "防残血怪被吸血"}],
                5: [{"name": "刃缚精锐", "cost": 5, "effect": "4点直伤斩杀/解场", "counter": "提防空场打4爆发"}],
            },
        }

        class_pool = threat_db.get(norm_class, threat_db.get("MAGE", {}))
        # Look for exact mana match or nearby highest danger
        exact_match = class_pool.get(next_mana, [])
        if exact_match:
            return exact_match[:3]

        # Find closest mana threat
        candidates = []
        for m_cost, cards in sorted(class_pool.items(), key=lambda x: abs(x[0] - next_mana)):
            if m_cost <= next_mana + 1:
                candidates.extend(cards)
                if len(candidates) >= 3:
                    break
        return candidates[:3] if candidates else [
            {"name": "通用强力随从", "cost": f"{next_mana}费", "effect": "按费拍怪站场", "counter": "保持场面优势主动交换"}
        ]
