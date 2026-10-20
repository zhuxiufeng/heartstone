"""
PunishSimulator: Next-Turn Opponent Counter-Play & Worst-Case Punish Index.
Simulates opponent's most devastating on-curve class removals and calculates board survival resilience.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("PunishSimulator")


@dataclass
class PunishAssessment:
    punish_risk_level: str           # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    predicted_punish_card: str       # e.g. "烈焰风暴 (全场打5)"
    projected_surviving_minions: int
    projected_surviving_attack: int
    resilience_score: float          # 0.0 to 100.0 (%)
    tactical_advice: str


class PunishSimulator:
    """Evaluates friendly board state against opponent's next-turn maximum punish potentials."""

    # Key on-curve sweepers and punishes by class and mana
    CLASS_PUNISH_MATRIX: Dict[str, Dict[int, Tuple[str, int, str]]] = {
        # class: {turn: (card_name, aoe_damage_or_type, description)}
        "MAGE": {
            3: ("回荡混响", 0, "复制并削弱我方单个高费核心大怪"),
            4: ("火球术", 6, "单卡点杀我方 6 血以内核心战力"),
            6: ("暴风雪", 2, "全场打2并全部冻结"),
            7: ("烈焰风暴", 5, "全场打5彻底清屏"),
            9: ("夕阳漫游者", 10, "随机打10并召唤大号随从"),
        },
        "PALADIN": {
            4: ("奉献", 2, "全场打2荡平低血杂毛"),
            4: ("十字军光环", 0, "若对手有随从，每只攻击时全体+2/+1"),
            5: ("守卫者的力量", 3, "依自身随从攻击力造成全场AOE清场"),
            6: ("剑龙骑术", 0, "赋予敌方随从+2/+6与强力亡语嘲讽"),
        },
        "WARRIOR": {
            3: ("剑刃风暴", 1, "全场连续打1直到随从死亡，刮死同血量单位"),
            4: ("余震", 3, "全场连续造成3次1点伤害"),
            5: ("绝命乱斗", 99, "消灭除一只随从外的所有单位"),
            5: ("清理污染", 4, "根据护甲值造成全场高伤AOE"),
        },
        "PRIEST": {
            4: ("暗言术: 毁", 0, "消灭所有 5 攻以上随从"),
            4: ("神圣新星", 2, "全场打2并恢复英雄2血"),
            5: ("群体狂乱", 0, "令所有随从互相攻击至残局"),
            8: ("漩涡净场", 99, "沉默并消灭全场所有随从"),
        },
        "WARLOCK": {
            2: ("亵渎", 1, "全场打1，若有随从死亡则连环递增触发"),
            4: ("地狱烈焰", 3, "全场打3伤害"),
            4: ("掀桌子", 3, "全场打3伤害"),
            8: ("扭曲虚空", 99, "消灭全场所有随从"),
        },
        "HUNTER": {
            6: ("镂骨恶犬", 3, "突袭狂战斧横扫相邻随从并吸血回满"),
        },
        "SHAMAN": {
            3: ("闪电风暴", 3, "全场打3法术伤害"),
            5: ("嗜血", 0, "敌方全员+3攻击力发动突发斩杀"),
        },
        "DEATHKNIGHT": {
            5: ("邪爆", 1, "消耗尸体连续全场打1直至清屏"),
            7: ("冰霜巨龙之怒", 5, "全场打5并冻结敌方全体"),
        },
        "DEMONHUNTER": {
            4: ("献祭光环", 2, "全场打2次1点伤害"),
            5: ("乱舞解场", 4, "英雄攻击力横扫敌方场面"),
        },
    }

    @classmethod
    def evaluate_board_punish(
        cls,
        friendly_minions: List[Dict],
        opponent_class: str,
        current_turn: int,
    ) -> PunishAssessment:
        """
        Calculates how our proposed board fares against the opponent's next-turn punish.
        """
        next_turn = current_turn + 1
        c_upper = opponent_class.upper().replace(" ", "").replace("_", "")

        matched_class = "MAGE"
        for key in cls.CLASS_PUNISH_MATRIX:
            if key in c_upper:
                matched_class = key
                break

        class_punishes = cls.CLASS_PUNISH_MATRIX.get(matched_class, {})
        punish_info = class_punishes.get(next_turn, None)

        if not friendly_minions:
            return PunishAssessment(
                punish_risk_level="LOW",
                predicted_punish_card=punish_info[0] if punish_info else "无特定AOE",
                projected_surviving_minions=0,
                projected_surviving_attack=0,
                resilience_score=100.0,
                tactical_advice="空场无受惩罚单位。",
            )

        total_minions = len(friendly_minions)
        total_atk = sum(m.get("attack", 0) for m in friendly_minions)

        if not punish_info:
            return PunishAssessment(
                punish_risk_level="LOW",
                predicted_punish_card=f"【{matched_class}】下回合 ({next_turn}费) 无常见毁灭性AOE",
                projected_surviving_minions=total_minions,
                projected_surviving_attack=total_atk,
                resilience_score=95.0,
                tactical_advice="下回合对手无致命AOE费用，可放心投入战力压制场面！",
            )

        card_name, aoe_dmg, desc = punish_info

        # Simulate survival against aoe_dmg
        surviving_count = 0
        surviving_atk = 0

        for m in friendly_minions:
            hp = int(m.get("health", 1))
            atk = int(m.get("attack", 0))
            has_shield = bool(m.get("divine_shield", False))
            has_deathrattle = bool(m.get("deathrattle", False) or "亡语" in m.get("name", ""))

            # Hard destruction (Brawl, Nether, Whirlpool)
            if aoe_dmg >= 90:
                if has_deathrattle:
                    surviving_count += 1
                    surviving_atk += max(1, atk // 2)
            elif has_shield:
                surviving_count += 1
                surviving_atk += atk
            elif hp > aoe_dmg:
                surviving_count += 1
                surviving_atk += atk
            elif has_deathrattle:
                surviving_count += 1
                surviving_atk += 2

        survival_ratio = surviving_count / max(1, total_minions)
        resilience = (survival_ratio * 70.0) + min(30.0, (surviving_atk / max(1, total_atk)) * 30.0)

        if resilience <= 25.0:
            risk = "CRITICAL"
            advice = (
                f"🚨【极度高危惩罚】下回合对手拥有 {next_turn} 费【{card_name}】({desc})！"
                f"我方场上 {total_minions} 个随从将几乎全灭 (生存率 {survival_ratio*100:.0f}%)！"
                f"⚠️ 严禁继续盲目铺小随从！手里务必保留后续战力，或主动用随从以小换大消耗对手！"
            )
        elif resilience <= 55.0:
            risk = "HIGH"
            advice = (
                f"⚠️【防反手预警】谨防对手下回合拍出【{card_name}】！"
                f"预计仅有 {surviving_count}/{total_minions} 个单位存活。建议优先架圣盾或错开随从血线规避全清！"
            )
        else:
            risk = "LOW"
            advice = (
                f"🛡️【防反手韧性极佳 ({resilience:.0f}分)】我方拥有圣盾/亡语/高血量随从，"
                f"即便对手下回合准时打出【{card_name}】，我方仍能保有 {surviving_atk} 点反击场攻！"
            )

        return PunishAssessment(
            punish_risk_level=risk,
            predicted_punish_card=f"{card_name} ({next_turn}费)",
            projected_surviving_minions=surviving_count,
            projected_surviving_attack=surviving_atk,
            resilience_score=resilience,
            tactical_advice=advice,
        )
