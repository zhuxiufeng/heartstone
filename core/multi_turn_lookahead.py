"""
MultiTurnLookahead: Multi-Turn Horizon Simulation & Counter-Response Forecasting.
Projects friendly board survival across Turns T+1 and T+2 against opponent class counters,
evaluates worst-case punishes, and recommends defensive Anti-Punish Plan B.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("MultiTurnLookahead")


@dataclass
class CandidatePlayOutcome:
    play_strategy: str               # "SWARM_EXPAND", "TEMPO_DEVELOP", "DEFENSIVE_TRADE"
    strategy_label: str              # "激进全铺场", "稳健节奏站场", "控场白吃防守"
    projected_t1_surviving_minions: float
    projected_t1_surviving_attack: int
    projected_t1_friendly_hp: int
    t1_opponent_counter_card: str
    t1_opponent_counter_desc: str
    t2_projected_board_value: float
    risk_level: str                  # "SAFE", "MODERATE", "RISKY", "CRITICAL"
    survival_score_pct: float        # 0.0 - 100.0%
    is_recommended: bool = False
    tactical_rationale: str = ""


@dataclass
class LookaheadForecastReport:
    current_turn: int
    opponent_class: str
    best_strategy: str
    recommended_outcome: CandidatePlayOutcome
    candidate_outcomes: List[CandidatePlayOutcome] = field(default_factory=list)
    anti_punish_plan_b: str = ""
    forecast_table_ascii: str = ""
    summary_markdown: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_turn": self.current_turn,
            "opponent_class": self.opponent_class,
            "best_strategy": self.best_strategy,
            "anti_punish_plan_b": self.anti_punish_plan_b,
            "forecast_table_ascii": self.forecast_table_ascii,
            "summary_markdown": self.summary_markdown,
            "candidates": [
                {
                    "strategy": c.play_strategy,
                    "label": c.strategy_label,
                    "surviving_minions": round(c.projected_t1_surviving_minions, 1),
                    "surviving_attack": c.projected_t1_surviving_attack,
                    "friendly_hp": c.projected_t1_friendly_hp,
                    "counter_card": c.t1_opponent_counter_card,
                    "counter_desc": c.t1_opponent_counter_desc,
                    "risk_level": c.risk_level,
                    "survival_pct": round(c.survival_score_pct, 1),
                    "is_recommended": c.is_recommended,
                    "rationale": c.tactical_rationale,
                }
                for c in self.candidate_outcomes
            ],
        }


class MultiTurnLookahead:
    """Simulates opponent's 2-turn counter responses and board survival horizons."""

    # Top class counter sweeps by class and turn
    CLASS_PUNISH_MAP: Dict[str, Dict[int, Tuple[str, int, str]]] = {
        "MAGE": {
            3: ("回荡混响", 0, "复制并弱化单个核心大怪"),
            4: ("火球术", 6, "单卡点杀6血核心"),
            6: ("暴风雪", 2, "全场打2并全部冻结"),
            7: ("烈焰风暴", 5, "全场打5强力清屏"),
            9: ("夕阳漫游者", 10, "随机打10并站场大怪"),
        },
        "PALADIN": {
            4: ("奉献", 2, "全场打2清理低血杂兵"),
            5: ("守卫者的力量", 3, "全场AOE清屏"),
            6: ("剑龙骑术", 0, "制造高血量亡语嘲讽"),
        },
        "WARRIOR": {
            3: ("剑刃风暴", 1, "全场连续打1直到随从死亡"),
            4: ("余震", 3, "全场连续打3次1点伤害"),
            5: ("绝命乱斗", 99, "消灭除1只随从外的所有随从"),
            8: ("清理污染", 5, "高护甲全场高伤清场"),
        },
        "PRIEST": {
            4: ("暗言术: 毁", 0, "消灭所有5攻以上随从"),
            4: ("神圣新星", 2, "全场打2并回血2点"),
            6: ("群体狂乱", 0, "所有随从互相攻击"),
            8: ("漩涡净场", 99, "沉默并消灭全场随从"),
        },
        "WARLOCK": {
            2: ("亵渎", 1, "递增连环全场打1"),
            4: ("地狱烈焰", 3, "全场打3伤害"),
            4: ("掀桌子", 3, "全场打3伤害"),
            8: ("扭曲虚空", 99, "消灭全场所有随从"),
        },
        "DEATHKNIGHT": {
            5: ("邪爆", 1, "消耗尸体连续打1直到清场"),
            7: ("冰霜巨龙之怒", 5, "全场打5并全员冻结"),
            8: ("兵主", 0, "单解偷取属性并召唤护卫"),
        },
        "SHAMAN": {
            3: ("闪电风暴", 3, "全场打3法术清场"),
            5: ("嗜血", 0, "全员+3攻突发反杀斩杀"),
            6: ("陨石术", 6, "单体打6并顺劈相邻随从打3"),
        },
        "HUNTER": {
            4: ("爆炸陷阱", 2, "受到攻击时全场打2"),
            6: ("镂骨恶犬", 3, "突袭横扫吸血清场"),
        },
        "DEMONHUNTER": {
            4: ("献祭光环", 2, "全场打2次1点伤害"),
            5: ("乱舞横扫", 4, "英雄攻击力全场打4"),
        },
        "DRUID": {
            5: ("横扫", 4, "单体打4并全场打1"),
            7: ("星辰坠落", 5, "全场打2或单体打5"),
        },
        "ROGUE": {
            2: ("刺骨", 4, "连击打4单解"),
            5: ("暗影步连击狂潮", 0, "资源爆发高攻解场"),
        },
    }

    @classmethod
    def evaluate_horizon(
        cls,
        friendly_minions: List[Dict[str, Any]],
        enemy_minions: List[Dict[str, Any]],
        friendly_hp: int,
        enemy_hp: int,
        opponent_class: str,
        current_turn: int,
        friendly_hand_count: int = 4,
    ) -> LookaheadForecastReport:
        c_upper = opponent_class.upper().replace(" ", "").replace("_", "")
        matched_class = "MAGE"
        for key in cls.CLASS_PUNISH_MAP:
            if key in c_upper:
                matched_class = key
                break

        t1_turn = current_turn + 1
        t2_turn = current_turn + 2

        class_punishes = cls.CLASS_PUNISH_MAP.get(matched_class, {})
        punish_info = class_punishes.get(t1_turn)
        if not punish_info:
            # Fallback to closest available punish
            available_turns = sorted(class_punishes.keys())
            next_turns = [t for t in available_turns if t >= t1_turn]
            if next_turns:
                punish_info = class_punishes[next_turns[0]]
            elif available_turns:
                punish_info = class_punishes[available_turns[-1]]
            else:
                punish_info = ("常规解牌/随从站场", 2, "敌方进行随从交换或普通点杀")

        counter_card, aoe_dmg, counter_desc = punish_info

        # Baseline friendly stats
        base_count = len(friendly_minions)
        base_atk = sum(m.get("attack", 0) for m in friendly_minions)
        base_hp_pool = sum(m.get("health", 0) for m in friendly_minions)
        enemy_board_atk = sum(m.get("attack", 0) for m in enemy_minions)

        candidates: List[CandidatePlayOutcome] = []

        # Candidate 1: Swarm & Expand (Full commitment to board)
        c1_count = base_count + 2
        c1_atk = base_atk + 5
        # If opponent has AoE
        if aoe_dmg >= 99:
            c1_surv_count = 1.0
            c1_surv_atk = max(1, c1_atk // 4)
        elif aoe_dmg > 0:
            survived = [m for m in friendly_minions if m.get("health", 1) > aoe_dmg]
            # Newly played minions assumed 2-3 hp, largely wiped by heavy AOE
            new_survived = 1 if aoe_dmg <= 2 else 0
            c1_surv_count = max(0.5, float(len(survived) + new_survived))
            c1_surv_atk = sum(m.get("attack", 0) for m in survived) + (2 if new_survived else 0)
        else:
            c1_surv_count = max(1.0, float(c1_count - 1))
            c1_surv_atk = max(0, c1_atk - 3)

        c1_surv_pct = min(100.0, max(10.0, (c1_surv_atk / max(1, c1_atk)) * 100.0))
        c1_hp = max(0, friendly_hp - max(0, enemy_board_atk - 2))
        c1_risk = "CRITICAL" if c1_surv_pct < 30 else ("RISKY" if c1_surv_pct < 60 else "MODERATE")

        candidates.append(
            CandidatePlayOutcome(
                play_strategy="SWARM_EXPAND",
                strategy_label="激进全铺场",
                projected_t1_surviving_minions=c1_surv_count,
                projected_t1_surviving_attack=c1_surv_atk,
                projected_t1_friendly_hp=c1_hp,
                t1_opponent_counter_card=counter_card,
                t1_opponent_counter_desc=counter_desc,
                t2_projected_board_value=float(c1_surv_atk * 1.5),
                risk_level=c1_risk,
                survival_score_pct=c1_surv_pct,
                tactical_rationale=f"遭遇 {counter_card} 清场将损失大量频率，仅留存 {c1_surv_count:.0f} 只随从。",
            )
        )

        # Candidate 2: Tempo Develop (Moderate development, holding 1-2 resources)
        c2_count = base_count + 1
        c2_atk = base_atk + 3
        if aoe_dmg >= 99:
            c2_surv_count = 1.0
            c2_surv_atk = max(1, c2_atk // 3)
        elif aoe_dmg > 0:
            survived = [m for m in friendly_minions if m.get("health", 1) > aoe_dmg]
            c2_surv_count = max(1.0, float(len(survived) + 1))
            c2_surv_atk = sum(m.get("attack", 0) for m in survived) + 3
        else:
            c2_surv_count = max(1.0, float(c2_count - 0.5))
            c2_surv_atk = max(0, c2_atk - 2)

        c2_surv_pct = min(100.0, max(20.0, (c2_surv_atk / max(1, c2_atk)) * 100.0))
        c2_hp = max(0, friendly_hp - max(0, enemy_board_atk - 3))
        c2_risk = "SAFE" if c2_surv_pct >= 65 else ("MODERATE" if c2_surv_pct >= 45 else "RISKY")

        candidates.append(
            CandidatePlayOutcome(
                play_strategy="TEMPO_DEVELOP",
                strategy_label="稳健节奏站场",
                projected_t1_surviving_minions=c2_surv_count,
                projected_t1_surviving_attack=c2_surv_atk,
                projected_t1_friendly_hp=c2_hp,
                t1_opponent_counter_card=counter_card,
                t1_opponent_counter_desc=counter_desc,
                t2_projected_board_value=float(c2_surv_atk * 2.0),
                risk_level=c2_risk,
                survival_score_pct=c2_surv_pct,
                tactical_rationale=f"保留手牌续航，承受 {counter_card} 后仍有充裕返场资本。",
            )
        )

        # Candidate 3: Defensive Trade (Full trade, clearing opponent threats)
        c3_count = max(0, base_count - len(enemy_minions) // 2)
        c3_atk = max(0, base_atk - enemy_board_atk // 2)
        c3_surv_count = max(0.5, float(c3_count))
        c3_surv_atk = max(1, c3_atk)
        c3_surv_pct = 75.0 if enemy_board_atk > 0 else 60.0
        c3_hp = friendly_hp  # zero damage taken due to full trades
        c3_risk = "SAFE"

        candidates.append(
            CandidatePlayOutcome(
                play_strategy="DEFENSIVE_TRADE",
                strategy_label="控场白吃防守",
                projected_t1_surviving_minions=c3_surv_count,
                projected_t1_surviving_attack=c3_surv_atk,
                projected_t1_friendly_hp=c3_hp,
                t1_opponent_counter_card=counter_card,
                t1_opponent_counter_desc="对手场面已空，仅能单下随从无从连环反制",
                t2_projected_board_value=float(c3_surv_atk * 1.8),
                risk_level=c3_risk,
                survival_score_pct=c3_surv_pct,
                tactical_rationale="剥夺对手场面攻击频率，最大化英雄血线安全。",
            )
        )

        # Determine best strategy
        # If player can close game (enemy hp low), prefer Swarm
        # If severe AoE turn upcoming (e.g. Turn 7 Mage Flamestrike or Turn 5 Brawl) and player has good board, prefer Tempo Develop or Trade
        if enemy_hp <= base_atk + 4 and c1_hp > 5:
            best_idx = 0  # SWARM_EXPAND
        elif aoe_dmg >= 3 and len(friendly_minions) >= 3:
            best_idx = 1  # TEMPO_DEVELOP (Don't overextend)
        elif enemy_board_atk >= friendly_hp * 0.6:
            best_idx = 2  # DEFENSIVE_TRADE (Protect face)
        else:
            best_idx = 1  # TEMPO_DEVELOP

        candidates[best_idx].is_recommended = True
        best_candidate = candidates[best_idx]

        # Defensive Anti-Punish Plan B
        if best_idx == 0:
            anti_plan_b = f"防反制保底：若对手手牌充足（≥4张），建议转为【稳健节奏站场】，手牌留1张优质生物防 {counter_card}。"
        elif best_idx == 1:
            anti_plan_b = f"防反制保底：注意将随从血量分散在 {aoe_dmg + 1} 点以上（防 {counter_card} 阈值）。"
        else:
            anti_plan_b = f"防反制保底：解场优先用低攻随从补刀，保留高攻大哥的血量以抵御随从强换。"

        # Generate ASCII table
        ascii_lines = [
            "+------------------+------------+------------+---------------+----------+",
            "| 战术方案         | T+1存活率  | 存活场攻   | 对手最高反制  | 风险评级 |",
            "+------------------+------------+------------+---------------+----------+",
        ]
        for c in candidates:
            rec_mark = "★ " if c.is_recommended else "  "
            line = (
                f"| {rec_mark}{c.strategy_label:<8} | {c.survival_score_pct:>8.1f}%  | "
                f"{c.projected_t1_surviving_attack:>8}点  | {c.t1_opponent_counter_card:<11} | {c.risk_level:<8} |"
            )
            ascii_lines.append(line)
        ascii_lines.append("+------------------+------------+------------+---------------+----------+")
        ascii_table = "\n".join(ascii_lines)

        # Markdown summary
        md_summary = (
            f"**多回合前瞻推演**（下回合 T{t1_turn} 对手预测惩罚: `{counter_card}`）:\n"
            f"• **推荐路线**: **{best_candidate.strategy_label}** (存活期望率 {best_candidate.survival_score_pct:.1f}%)\n"
            f"• **反制预警**: {counter_desc}\n"
            f"• **{anti_plan_b}**"
        )

        return LookaheadForecastReport(
            current_turn=current_turn,
            opponent_class=matched_class,
            best_strategy=best_candidate.play_strategy,
            recommended_outcome=best_candidate,
            candidate_outcomes=candidates,
            anti_punish_plan_b=anti_plan_b,
            forecast_table_ascii=ascii_table,
            summary_markdown=md_summary,
        )
