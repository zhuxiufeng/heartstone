"""
LiveDiscoverAdvisor: Real-Time Tactical Discover & Adapt Priority Advisor for Hearthstone.
Dynamically calculates the most urgent tactical need (Survival, Board Clear, Finisher, Value)
based on active health, board attack, and hand exhaustion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from .card_db import CardDatabase, CardInfo

logger = logging.getLogger("LiveDiscoverAdvisor")


@dataclass
class DiscoverCardEvaluation:
    name: str
    card_id: str
    cost: int
    tier: str                  # "S", "A", "B", "C"
    tier_badge: str            # "🔥 S级首选", "⭐ A级优质", "🔹 B级可用", "⚠️ C级下选"
    score: float               # 0.0 ~ 100.0
    reason: str
    tactical_synergy: str
    is_best_pick: bool = False


@dataclass
class DiscoverTriPickResult:
    guidance: DiscoverGuidance
    evaluations: List[DiscoverCardEvaluation]
    best_card: Optional[DiscoverCardEvaluation]
    lead_margin: float
    verdict_directive: str


@dataclass
class DiscoverGuidance:
    priority_tier: str              # "SURVIVAL", "BOARD_CLEAR", "BURST_FINISH", "VALUE_REFILL", "TEMPO_DEVELOP"
    priority_badge: str
    guidance_text: str
    recommended_card_types: List[str] = field(default_factory=list)
    avoid_card_types: List[str] = field(default_factory=list)


class LiveDiscoverAdvisor:
    """Evaluates in-game board state and prescribes precise discover picking directives."""

    @classmethod
    def evaluate_discover_need(
        cls,
        friendly_hp: int,
        enemy_hp: int,
        friendly_board_atk: int,
        enemy_board_atk: int,
        hand_size: int,
        is_facing_lethal: bool = False,
    ) -> DiscoverGuidance:
        # 1. Emergency Survival (Facing lethal or HP <= 10 with enemy field pressure)
        if is_facing_lethal or (friendly_hp <= 10 and enemy_board_atk >= 5):
            return DiscoverGuidance(
                priority_tier="SURVIVAL",
                priority_badge="🚨 紧急求生·优先保命",
                guidance_text="当前生命已触碰危险红线！三选一必须绝对优先抓取【嘲讽随从 / 深度冻结 / 抬血保命 / 护甲 / 冰箱】！",
                recommended_card_types=["嘲讽随从", "高额回血/叠甲", "冰冻全场/单控", "潜行/保命奥秘"],
                avoid_card_types=["纯过牌", "纯抽卡衍生物", "无嘲讽白板大哥"],
            )

        # 2. Burst Finisher (Enemy is low and can be finished soon)
        if enemy_hp <= 12 and friendly_board_atk >= 3:
            return DiscoverGuidance(
                priority_tier="BURST_FINISH",
                priority_badge="🔥 绝杀封喉·优先直伤",
                guidance_text=f"敌方仅剩 {enemy_hp} 血！绝佳斩杀窗口已开，三选一优先抓取【高爆发直伤法术 / 冲锋突袭 / 强攻武器】直接终结比赛！",
                recommended_card_types=["直伤法术", "冲锋随从", "武器直伤", "攻击力咆哮/光环Buff"],
                avoid_card_types=["慢速控场牌", "防御型嘲讽"],
            )

        # 3. Board Clear (Enemy board attack is more than 2x friendly board attack)
        if enemy_board_atk >= friendly_board_atk + 5 and enemy_board_atk >= 7:
            return DiscoverGuidance(
                priority_tier="BOARD_CLEAR",
                priority_badge="⚡ 绝境返场·优先AOE与硬解",
                guidance_text="敌方场攻占据压倒性优势！三选一优先寻找【全场AOE清场 / 单体硬解 / 突袭复数返场】夺回主动权！",
                recommended_card_types=["全场AOE清场", "单体消灭/变形硬解", "突袭/吸血随从"],
                avoid_card_types=["高费纯资源牌", "低节奏过牌"],
            )

        # 4. Value Refill (Hand is empty <= 2 cards)
        if hand_size <= 2:
            return DiscoverGuidance(
                priority_tier="VALUE_REFILL",
                priority_badge="💎 资源续航·优先过牌补充",
                guidance_text="我方手牌枯竭！三选一优先抓取【多张过牌 / 无限资源复制 / 亡语高质量大卡】以防后续回合断粮！",
                recommended_card_types=["大量过牌法术", "亡语/衍生手牌随从", "英雄牌/泰坦核心"],
                avoid_card_types=["低效单解", "一次性亏卡法术"],
            )

        # 5. Tempo Development (Default / Ahead)
        return DiscoverGuidance(
            priority_tier="TEMPO_DEVELOP",
            priority_badge="⚔️ 节奏站场·优先超模身材",
            guidance_text="当前战局处于可控节奏中，三选一优先抓取【符合法力曲线的超模随从 / 优质身材战力】持续滚雪球施压！",
            recommended_card_types=["身材超模随从", "单体控场", "圣盾/魔免随从"],
            avoid_card_types=["过窄特化针对牌"],
        )

    @classmethod
    def evaluate_tri_pick(
        cls,
        candidate_cards: List[Union[str, CardInfo]],
        friendly_hp: int,
        enemy_hp: int,
        friendly_board_atk: int,
        enemy_board_atk: int,
        hand_size: int,
        available_mana: int = 10,
        card_db: Optional[CardDatabase] = None,
        is_facing_lethal: bool = False,
    ) -> DiscoverTriPickResult:
        """
        Ranks in-match Discover 3-card choices against active tactical needs,
        mana constraints, and arena tier values.
        """
        guidance = cls.evaluate_discover_need(
            friendly_hp=friendly_hp,
            enemy_hp=enemy_hp,
            friendly_board_atk=friendly_board_atk,
            enemy_board_atk=enemy_board_atk,
            hand_size=hand_size,
            is_facing_lethal=is_facing_lethal,
        )

        db = card_db or CardDatabase.get_instance()
        evaluations: List[DiscoverCardEvaluation] = []

        for item in candidate_cards:
            if isinstance(item, CardInfo):
                c = item
            else:
                c = None
                if db and hasattr(db, "get_by_name"):
                    c = db.get_by_name(str(item))
                if not c:
                    c = CardInfo(id="", name=str(item), cost=3)

            name = c.name
            cost = c.cost
            text = getattr(c, "text", "") or ""
            c_type = getattr(c, "card_type", "") or ""
            atk = getattr(c, "attack", 0) or 0
            hp = getattr(c, "health", 0) or 0
            rarity = getattr(c, "rarity", "COMMON") or "COMMON"

            # 1. Base Score
            if rarity in ("LEGENDARY", "EPIC"):
                base_score = 75.0
            elif rarity == "RARE":
                base_score = 68.0
            else:
                base_score = 64.0

            # 2. Tactical Fit Bonus / Malus based on priority_tier
            bonus = 0.0
            reason_parts: List[str] = []
            tier_need = guidance.priority_tier

            if tier_need == "SURVIVAL":
                if any(k in name or k in text for k in ["嘲讽", "恢复", "治疗", "护甲", "冰冻", "潜行", "无法成为目标", "圣盾"]):
                    bonus += 25.0
                    reason_parts.append("契合保命防守需求")
                elif cost >= 7 and "嘲讽" not in text:
                    bonus -= 18.0
                    reason_parts.append("高费笨重无防守战力")
            elif tier_need == "BURST_FINISH":
                if any(k in name or k in text for k in ["造成", "伤害", "直伤", "火球", "冲锋", "斩杀", "射击", "风怒"]):
                    bonus += 26.0
                    reason_parts.append("契合斩杀窗口直伤终结")
                elif atk >= 6:
                    bonus += 14.0
                    reason_parts.append("高攻随从快速压血")
                elif any(k in text for k in ["恢复", "抽牌"]):
                    bonus -= 10.0
            elif tier_need == "BOARD_CLEAR":
                if any(k in name or k in text for k in ["所有", "全场", "消灭", "AOE", "暴风雪", "烈焰风暴", "横扫", "奉献", "剧毒"]):
                    bonus += 28.0
                    reason_parts.append("关键全场清算解场牌")
                elif any(k in text for k in ["突袭", "造成"]):
                    bonus += 15.0
                    reason_parts.append("即时突袭返场战力")
            elif tier_need == "VALUE_REFILL":
                if any(k in text for k in ["抽", "发现", "置入", "复制", "亡语"]):
                    bonus += 24.0
                    reason_parts.append("核心续航资源补给")
            else:  # TEMPO_DEVELOP
                if atk + hp >= cost * 2 and cost > 0:
                    bonus += 18.0
                    reason_parts.append("超模身材站场施压")
                if "突袭" in text or "圣盾" in text or "战吼" in text:
                    bonus += 12.0

            # 3. Mana Usability
            if cost <= available_mana:
                bonus += 8.0
                reason_parts.append("当回合可立即打出")
            elif cost == available_mana + 1:
                bonus += 4.0
                reason_parts.append("下回合准时压制")

            final_score = max(25.0, min(99.0, base_score + bonus))

            # Tier classification
            if final_score >= 82.0:
                tier = "S"
                tier_badge = "🔥 S级首选"
            elif final_score >= 70.0:
                tier = "A"
                tier_badge = "⭐ A级优质"
            elif final_score >= 58.0:
                tier = "B"
                tier_badge = "🔹 B级可用"
            else:
                tier = "C"
                tier_badge = "⚠️ C级下选"

            evaluations.append(
                DiscoverCardEvaluation(
                    name=name,
                    card_id=c.id,
                    cost=cost,
                    tier=tier,
                    tier_badge=tier_badge,
                    score=round(final_score, 1),
                    reason=" · ".join(reason_parts) if reason_parts else "常规战力抓取",
                    tactical_synergy=f"{tier_badge} ({final_score:.1f}分)",
                )
            )

        # Sort descending by score
        evaluations.sort(key=lambda e: e.score, reverse=True)
        best_card = evaluations[0] if evaluations else None
        if best_card:
            best_card.is_best_pick = True

        lead_margin = 0.0
        if len(evaluations) >= 2:
            lead_margin = round(evaluations[0].score - evaluations[1].score, 1)

        if best_card:
            verdict = (
                f"【实战发现首选: {best_card.name}】{best_card.tier_badge} (领先 +{lead_margin:.1f} 分) · "
                f"{best_card.reason}"
            )
        else:
            verdict = "无有效发现候选卡牌"

        return DiscoverTriPickResult(
            guidance=guidance,
            evaluations=evaluations,
            best_card=best_card,
            lead_margin=lead_margin,
            verdict_directive=verdict,
        )
