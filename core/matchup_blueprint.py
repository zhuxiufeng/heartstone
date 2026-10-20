"""
MatchupBlueprint: Comprehensive 11-class matchup tactical guide for Hearthstone Arena.
Covers modern expansion mechanics, class-specific hero power threats, danger turns, and counter-strategies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("MatchupBlueprint")


@dataclass
class MatchupStrategy:
    opponent_class_name: str
    core_gameplan: str               # 战略核心蓝图 (e.g. "防十字军光环/王者祝福，严控单只杂毛")
    turn_danger_alert: Optional[str] # 当回合高危卡牌预警 (e.g. "⚠️ 警戒 T4【守卫者的力量 / 十字军光环】")
    special_tactics: List[str]       # 战术避坑指南
    burst_danger_warning: str        # 空场/爆发斩杀预警
    ping_threat_active: bool         # 对手是否有 1 点补刀技能


class MatchupBlueprintEngine:
    """Delivers class-specific tactical master plans tailored to all 11 Hearthstone classes."""

    # 11 Classes with Ping Hero Powers
    PING_CLASSES = {
        "mage", "法师",
        "rogue", "潜行者", "盗贼",
        "druid", "德鲁伊",
        "demonhunter", "demon hunter", "恶魔猎手",
        "deathknight", "death knight", "死亡骑士",
    }

    # Archetype blueprints for each class
    BLUEPRINTS: Dict[str, Dict] = {
        "MAGE": {
            "name": "法师",
            "gameplan": "防冰系控场与高爆发直伤。场面交换务必保证残血随从 ≥ 2 血（防火冲补刀）。",
            "key_turns": {
                3: "小心【回荡混响】复制我方核心大怪；",
                4: "防范【火球术】点杀中坚随从；",
                6: "高危回合！严防【暴风雪】(全场打2冰冻)；",
                7: "极度危险！防范【烈焰风暴】(全场打5)；保留亡语或圣盾。",
                9: "防范【夕阳漫游者】(随机打10召唤大怪)。",
            },
            "tactics": [
                "随从交换后严禁留下 1 血残血（火冲无损补刀）",
                "高攻/核心随从尽量贴圣盾或避免单怪被【回荡混响】反打",
                "7 费前抢占场面并主动走脸压血，逼法师交解牌被动防守",
            ],
            "burst_base": 10, # Fireball (6) + Ping (1) + Spell (3)
        },
        "PALADIN": {
            "name": "圣骑士",
            "gameplan": "【宁解勿留杂毛】！圣骑士拥有极高单体 Buff 与光环翻盘能力，绝不给其留任何载体！",
            "key_turns": {
                4: "🚨 核心质变回合！严密防范【十字军光环】(+2/+1反冲) 与【王者祝福】(+4/+4)！",
                5: "防范【守卫者的力量】(依自身随从攻击力造成全场AOE)；",
                6: "防范【剑龙骑术 / 超凡力量】，严控对手场面单怪；",
                8: "防范【光铸凯瑞尔 / 圣盾大怪翻盘】。",
            },
            "tactics": [
                "【绝不留单怪】：宁愿用小随从破防对换，也必须清空圣骑士场面，杜绝光环滚雪球",
                "沉默与硬解必须捏死，只留给贴了王者/剑龙的大号身材怪",
                "防范【奉献】(打2)，避免一地图腾或杂毛被一锅端",
            ],
            "burst_base": 8,
        },
        "HUNTER": {
            "name": "猎人",
            "gameplan": "【倒计时生存蓝图】！猎人英雄技能射箭自带终局时钟，禁止慢性打消耗，必须速战速决抢回血线！",
            "key_turns": {
                3: "防范【星弦弓 / 动物伙伴】抢节奏；",
                4: "小心手牌【杀戮命令】(打5) 配合野兽直接斩杀；",
                6: "🚨 极度高危！严密防范【镂骨恶犬】(突袭+吸血+狂战斧扫场回满血)！随从必须拉开站位，大怪放两边！",
                7: "防范【阿格拉玛】泰坦突击。",
            },
            "tactics": [
                "我方血量低于 15 点时立刻转入全守姿态，防杀戮+射箭爆发",
                "防【镂骨恶犬】：低血随从不要与高攻随从相邻，防止猎人一脚吸回 15 血",
                "前期能争夺场面尽量争夺，逼迫猎人将伤害打在随从身上",
            ],
            "burst_base": 10,
        },
        "ROGUE": {
            "name": "潜行者",
            "gameplan": "【防背刺节奏反超】！潜行者连击爆发高但缺乏直伤奶量，通过高韧性随从逼其用脸卖血解场。",
            "key_turns": {
                1: "注意后手硬币【军情七处特工】打2抢节奏；",
                2: "我方 2 费下怪优先选择 2/3 身材，严禁裸下 3/2（防被 0 费背刺白吃）；",
                4: "防范【刺骨】连击打 4 与【影袭 / 街头摆摊】连环抢节奏；",
                6: "防范高攻随从配合【暗影步】双进双出。",
            },
            "tactics": [
                "起手与 2 费优先留 2/3 随从（避开背刺 2 点伤害阈值）",
                "随从交换后防范 1/2 匕首补刀",
                "潜行者无回复手段，将对手英雄血量压入 10 点内即可彻底锁死其卖脸能力",
            ],
            "burst_base": 8,
        },
        "PRIEST": {
            "name": "牧师",
            "gameplan": "防【暗言术】与血量滚雪球。严禁将我方随从交换到残血，防止对手北郡牧师/治疗白嫖手牌。",
            "key_turns": {
                4: "小心【暗言术: 毁】(消灭所有 5 攻以上随从) 与【神圣新星】(打2奶2)；",
                5: "防范【群体狂乱】，随从攻击力不要整齐一致；",
                7: "防范泰坦【阿曼苏尔】(移除两个随从或召唤大怪)；",
                8: "防范【漩涡净场】(全场沉默并消灭)。",
            },
            "tactics": [
                "控制随从攻击力在 4 攻黄金区间（避开灭与毁的杀伤线）",
                "严禁留下残血敌方随从，防止牧师真言术/技能奶满并触发战吼特效",
                "场面大优时防一手【暗言术: 毁】，不盲目下多张 5+ 攻大怪",
            ],
            "burst_base": 4,
        },
        "SHAMAN": {
            "name": "萨满祭司",
            "gameplan": "【控图腾防嗜血】！萨满的爆发完全依赖场面随从数量，即使是 0/2 基础图腾也能在 T5 变成 3 点斩杀！",
            "key_turns": {
                3: "防范【闪电风暴】(全场打3)；",
                5: "🚨 嗜血危险线！对手场面只要有 3 个怪即可输出 9+ 点爆发；",
                6: "防范泰坦【高戈奈斯】(打6过牌过载减费)；",
                8: "防范强力元素大怪连拍。",
            },
            "tactics": [
                "【见图腾就解】：绝不贪打脸留图腾，每留一个图腾就是送对手 3 点斩杀伤害",
                "随从血量尽量保持在 4 血以上，规避闪电风暴主杀伤区",
                "萨满过载下回合费用受限，抓住其过载回合疯狂反压场面",
            ],
            "burst_base": 12, # Bloodlust potential
        },
        "WARLOCK": {
            "name": "术士",
            "gameplan": "【破除亵渎阶梯】！术士具有最强群解但自身抽牌伤血，全力压制其血线破坏其抽牌节奏。",
            "key_turns": {
                2: "🚨 核心警戒：随从血量绝不能排布为 1、2、3 连续梯度，防止【亵渎】清全场！",
                4: "防范【地狱烈焰】(全场打3) 与【掀桌子】；",
                6: "防范【罪孽交响曲 / 大恶魔出动】；",
                8: "防范扭曲虚空等强力清场。",
            },
            "tactics": [
                "【破亵渎站位与血量】：通过合理交换让随从血量出现断档（如只有 2 血和 4 血，无 1 血与 3 血）",
                "术士卖血抽牌通常在 15 血以下危险，此时果断转为全员打脸压迫其不敢技能",
            ],
            "burst_base": 6,
        },
        "WARRIOR": {
            "name": "战士",
            "gameplan": "防【剑刃风暴】与【绝命乱斗】。战士叠甲能力强，但前期随从薄弱，利用优质前期随从稳步输出。",
            "key_turns": {
                3: "防范【剑刃风暴】：场上随从不要有相同低血量，避免被单卡连续刮死；",
                5: "🚨 乱斗警戒！防范【绝命乱斗】与【清理污染】(依护甲造成AOE)；",
                6: "防范高攻武器突击；",
                8: "防范【奥丁 / 泰坦卡兹格罗斯】。",
            },
            "tactics": [
                "随从血量错开分布，不给【剑刃风暴】连续清场的跳板",
                "场上有 3 个优质战力时停止铺杂毛，防范乱斗一发入魂",
            ],
            "burst_base": 6,
        },
        "DRUID": {
            "name": "德鲁伊",
            "gameplan": "防跳费与大树超展开。德鲁伊解大怪能力极弱，单个高攻高血大怪是德鲁伊无法逾越的天堑。",
            "key_turns": {
                3: "小心【横扫】(单体4其余1)；",
                5: "防范滋养跳费与优质嘲讽野兽；",
                7: "🚨 铺场爆发！防范【鼓圈】(召唤树人并全体 +2/+2 嘲讽)；",
                9: "防范巨型随从拍门。",
            },
            "tactics": [
                "【造大怪打脸】：德鲁伊没有刺杀和灭，造一个 6/6 或 8/8 大怪德鲁伊极难处理",
                "防横扫：低血杂毛避免在场，防止被横扫顺带清理",
            ],
            "burst_base": 6,
        },
        "DEMONHUNTER": {
            "name": "恶魔猎手",
            "gameplan": "【防 1 费恶魔之咬与突袭链】！恶魔猎手节奏极快，随从多带突袭，必须优先下高血嘲讽化解锋芒。",
            "key_turns": {
                1: "后手即可 1 费变脸打 1 补刀，严禁留下 1 血杂毛；",
                3: "防范【盲眼神射手】连环射击；",
                4: "小心流放特效爆发卡；",
                6: "防范恶魔大怪突袭解场。",
            },
            "tactics": [
                "恶魔猎手 1 费技能极度灵活，残血随从务必留在 2 血以上",
                "优先抓取并打出嘲讽随从，封锁其英雄攻击走脸",
            ],
            "burst_base": 8,
        },
        "DEATHKNIGHT": {
            "name": "死亡骑士",
            "gameplan": "【严防邪爆与残骸积累】！死骑综合实力全面，英雄技能 2 费召唤 1/1 突袭冲锋食尸鬼，自带补刀能力。",
            "key_turns": {
                2: "小心技能 1/1 食尸鬼突袭补刀；",
                5: "🚨 极度高危！严密防范【邪爆】(消耗尸体连续打1直至全场消灭)；",
                7: "防范【冰霜巨龙之怒】(全场打5冰冻)；",
                8: "防范【玛洛加尔领主】(消耗所有尸体召唤一地大骨头冲脸)。",
            },
            "tactics": [
                "随从交换后严禁留下 1 血随从（食尸鬼冲锋补刀并白赚 1 点尸体）",
                "若死骑尸体数量 ≥ 6，谨防【邪爆】清场，保留亡语随从作为赖场保险",
                "血量保持健康，防范冰霜死骑冰龙冰冻控场抢脸",
            ],
            "burst_base": 9,
        },
    }

    @classmethod
    def get_matchup_strategy(
        cls,
        opponent_class: str,
        current_turn: int,
        friendly_board: List[str],
        enemy_board: List[str],
        friendly_hp: int,
        enemy_hp: int,
    ) -> MatchupStrategy:
        """
        Synthesizes a deep strategic tactical blueprint for the current turn against opponent class.
        """
        # Normalize class name
        c_upper = opponent_class.upper().replace(" ", "").replace("_", "")
        # Lookup matching key
        matched_key = "MAGE"
        # Sort keys by length descending so "DEMONHUNTER" is matched before "HUNTER"
        sorted_keys = sorted(cls.BLUEPRINTS.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if key == c_upper or cls.BLUEPRINTS[key]["name"] == opponent_class:
                matched_key = key
                break
            if key in c_upper or cls.BLUEPRINTS[key]["name"] in opponent_class:
                matched_key = key
                break

        bp = cls.BLUEPRINTS[matched_key]
        opp_name = bp["name"]
        is_ping = (matched_key.lower() in cls.PING_CLASSES) or (opp_name in cls.PING_CLASSES)

        # Danger alert for current turn
        danger_alert = bp["key_turns"].get(current_turn, None)
        if not danger_alert and current_turn + 1 in bp["key_turns"]:
            danger_alert = f"下回合 ({current_turn + 1}费): " + bp["key_turns"][current_turn + 1]

        # Class specific lethal calculation (e.g. Shaman Bloodlust)
        burst_val = bp["burst_base"]
        burst_warning = f"【{opp_name}】基础空场爆发线约为 {burst_val} 点伤害。"
        if matched_key == "SHAMAN" and len(enemy_board) >= 2:
            bloodlust_potential = len(enemy_board) * 3
            burst_warning = f"🚨【嗜血警报】对手场上有 {len(enemy_board)} 个随从，若使用【嗜血】爆发可造成 +{bloodlust_potential} 点突发斩杀！"
        elif matched_key == "HUNTER" and friendly_hp <= 12:
            burst_warning = f"🚨【猎人斩杀线】我方血量已降至 {friendly_hp}，已在杀戮+射箭甚至直伤斩杀范围内！"

        return MatchupStrategy(
            opponent_class_name=opp_name,
            core_gameplan=bp["gameplan"],
            turn_danger_alert=danger_alert,
            special_tactics=bp["tactics"],
            burst_danger_warning=burst_warning,
            ping_threat_active=is_ping,
        )
