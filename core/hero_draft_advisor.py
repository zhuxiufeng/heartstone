"""
HeroDraftAdvisor: Current-patch Arena Hero Tier Engine.
Evaluates 1-out-of-3 opening Hero choices based on latest patch Arena leaderboard win rates,
hero power strength, and ease of high-win drafting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("HeroDraftAdvisor")


@dataclass
class HeroTierInfo:
    class_name: str
    class_cn: str
    tier: str                      # "T0", "T1", "T2", "T3"
    winrate: float                 # e.g., 56.4
    power_rating: int              # 1-100
    hero_power_rating: str         # e.g., "⭐⭐⭐⭐⭐ (极强补刀与尸体滚雪球)"
    recommended_archetype: str     # e.g., "冰霜死骑 / 残骸控制"
    core_strengths: List[str]      # e.g., ["高频发现", "解场返场一体"]
    draft_priority_advice: str    # Detailed advice for drafting this hero


# Latest Arena Meta Tier List for all 11 classes
ARENA_HERO_TIERS: Dict[str, Dict[str, Any]] = {
    "DEATHKNIGHT": {
        "class_cn": "死亡骑士",
        "tier": "T0",
        "winrate": 56.8,
        "power_rating": 96,
        "hero_power_rating": "⭐⭐⭐⭐⭐ (冲锋1/1造尸体，残骸资源无限滚雪球)",
        "recommended_archetype": "彩虹控制 / 鲜血冰霜消耗",
        "core_strengths": ["最强职业发现池", "残骸机制零损耗返场", "优质突袭与吸血生物"],
        "draft_priority_advice": "当前版本绝对霸主！优先抓取采矿事故、冰霜打击与尸体消耗牌，后期无解。",
    },
    "DEMONHUNTER": {
        "class_cn": "恶魔猎手",
        "tier": "T0",
        "winrate": 55.6,
        "power_rating": 94,
        "hero_power_rating": "⭐⭐⭐⭐⭐ (1费灵活变身补刀，节奏掌控者)",
        "recommended_archetype": "快攻走脸 / 突袭节奏轴",
        "core_strengths": ["1费技能绝不卡费", "超高频突袭与抽牌", "极易打出前4回合压制"],
        "draft_priority_advice": "前4费压死对手的最佳选择！多选低费突袭与流放过牌，绝不可选厚重慢速牌。",
    },
    "MAGE": {
        "class_cn": "法师",
        "tier": "T1",
        "winrate": 53.9,
        "power_rating": 89,
        "hero_power_rating": "⭐⭐⭐⭐ (无伤过嘲讽点火，补刀王者)",
        "recommended_archetype": "法术发现 / 元素控场",
        "core_strengths": ["无视嘲讽2点补刀", "暴风雪/烈焰风暴强控", "奥术发现源源不断"],
        "draft_priority_advice": "容错率极高。重点选优质法术发现与全场清场，控制场面拖入后期即胜。",
    },
    "PALADIN": {
        "class_cn": "圣骑士",
        "tier": "T1",
        "winrate": 53.2,
        "power_rating": 87,
        "hero_power_rating": "⭐⭐⭐⭐ (每回合稳定报告兵，圣盾赖场)",
        "recommended_archetype": "十字军光环中速 / 圣盾Buff滚雪球",
        "core_strengths": ["报告兵配合光环爆发极高", "圣盾随从白吃换怪", "贴Buff即时抢先手"],
        "draft_priority_advice": "铺场即正义。只要抓到十字军光环或优质Buff，铺满场面即可在5-6费叫杀。",
    },
    "ROGUE": {
        "class_cn": "潜行者",
        "tier": "T1",
        "winrate": 52.8,
        "power_rating": 86,
        "hero_power_rating": "⭐⭐⭐⭐ (2费转刀管两轮，单卡赚节奏)",
        "recommended_archetype": "连击节奏 / 机械海盗快攻",
        "core_strengths": ["一把匕首管2回合", "连击解场返场极快", "微调费用润滑"],
        "draft_priority_advice": "高手上限最高的职业。需要精准规划连击与武器耐久，控住前期节奏必胜。",
    },
    "WARLOCK": {
        "class_cn": "术士",
        "tier": "T1",
        "winrate": 52.1,
        "power_rating": 84,
        "hero_power_rating": "⭐⭐⭐⭐ (自残换手牌，手牌永远不竭)",
        "recommended_archetype": "手牌资源控场 / 恶魔铺场",
        "core_strengths": ["自带抽牌防断续航", "地狱烈焰清场", "大型恶魔单卡质量"],
        "draft_priority_advice": "血量就是资源。优先抓取回血/吸血随从以抵消技能自残，手牌优势直接压垮对手。",
    },
    "HUNTER": {
        "class_cn": "猎人",
        "tier": "T2",
        "winrate": 50.8,
        "power_rating": 79,
        "hero_power_rating": "⭐⭐⭐ (每回合稳打脸2点，抢血时钟)",
        "recommended_archetype": "极限走脸 / 野兽突袭",
        "core_strengths": ["全英雄最强终结时钟", "直伤法术防不胜防", "野兽滚雪球"],
        "draft_priority_advice": "打脸是唯一信仰。压制曲线在1-4费，禁止抓取高费笨重大哥，6费前打崩对手。",
    },
    "SHAMAN": {
        "class_cn": "萨满祭司",
        "tier": "T2",
        "winrate": 50.2,
        "power_rating": 77,
        "hero_power_rating": "⭐⭐⭐ (随机图腾提供场攻/法强/嘲讽)",
        "recommended_archetype": "嗜血斩杀 / 过载图腾节奏",
        "core_strengths": ["嗜血全员走脸暴毙", "闪电风暴清场", "优质战吼随从"],
        "draft_priority_advice": "依赖嗜血终结。选牌需要保证充足的低费铺场生物，有场面就有嗜血翻盘几率。",
    },
    "DRUID": {
        "class_cn": "德鲁伊",
        "tier": "T2",
        "winrate": 49.3,
        "power_rating": 74,
        "hero_power_rating": "⭐⭐⭐ (1点攻击+1点护甲，灵活补刀)",
        "recommended_archetype": "抉择跳费中速 / 嘲讽大怪",
        "core_strengths": ["跳费提前出大哥", "抉择应对多变", "群体Buff扫场"],
        "draft_priority_advice": "前期容易亏节奏。务必补充足够的2-3费过渡随从，否则容易未到高费即被打残。",
    },
    "PRIEST": {
        "class_cn": "牧师",
        "tier": "T3",
        "winrate": 47.5,
        "power_rating": 68,
        "hero_power_rating": "⭐⭐ (依赖随从站场才能回血，空场白给)",
        "recommended_archetype": "亡语复活 / 偷牌发现消耗",
        "core_strengths": ["高血随从贴贴无限白吃", "群体狂乱单卡翻盘", "资源偷取"],
        "draft_priority_advice": "吃牌序极严重。空场时英雄技能毫无意义，必须拼死抓取超模1-3费随从保住场面。",
    },
    "WARRIOR": {
        "class_cn": "战士",
        "tier": "T3",
        "winrate": 46.2,
        "power_rating": 64,
        "hero_power_rating": "⭐⭐ (叠甲对场面零帮助，前期极度被动)",
        "recommended_archetype": "护甲大控场 / 嘲讽受伤体系",
        "core_strengths": ["绝命乱斗全场翻盘", "优质武器控场", "叠甲抗疲劳"],
        "draft_priority_advice": "当前版本弱势。除非有大量极品武器与乱斗，否则不建议首选，极易前期被快攻冲垮。",
    },
}


class HeroDraftAdvisor:
    """
    Ranks 3 hero candidates at the start of an Arena run.
    """

    @classmethod
    def evaluate_hero_choices(cls, hero_names: List[str]) -> List[HeroTierInfo]:
        """
        Takes 3 hero names (English or Chinese) and returns sorted tier analysis.
        """
        results: List[HeroTierInfo] = []

        for name in hero_names:
            matched_key = None
            clean = name.strip().upper().replace(" ", "").replace("_", "")

            # Exact match or substring
            for k, data in ARENA_HERO_TIERS.items():
                if k == clean or data["class_cn"] in name:
                    matched_key = k
                    break

            if not matched_key:
                # Fallback search
                for k, data in ARENA_HERO_TIERS.items():
                    if k in clean or clean in k:
                        matched_key = k
                        break

            if matched_key:
                d = ARENA_HERO_TIERS[matched_key]
                results.append(HeroTierInfo(
                    class_name=matched_key,
                    class_cn=d["class_cn"],
                    tier=d["tier"],
                    winrate=d["winrate"],
                    power_rating=d["power_rating"],
                    hero_power_rating=d["hero_power_rating"],
                    recommended_archetype=d["recommended_archetype"],
                    core_strengths=d["core_strengths"],
                    draft_priority_advice=d["draft_priority_advice"],
                ))
            else:
                results.append(HeroTierInfo(
                    class_name=name,
                    class_cn=name,
                    tier="T2",
                    winrate=50.0,
                    power_rating=75,
                    hero_power_rating="⭐⭐⭐",
                    recommended_archetype="标准中速",
                    core_strengths=["随从站场"],
                    draft_priority_advice="保持健康平滑法力曲线。",
                ))

        # Sort by power rating descending
        results.sort(key=lambda h: h.power_rating, reverse=True)
        return results

    @classmethod
    def get_best_hero(cls, hero_names: List[str]) -> Optional[HeroTierInfo]:
        evals = cls.evaluate_hero_choices(hero_names)
        return evals[0] if evals else None
