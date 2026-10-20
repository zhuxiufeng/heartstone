"""
ActionTreeSearch: 1-Ply forward branch action tree exploration.
Evaluates competing play options (Tempo Development vs Control Clear vs Face Rush)
and computes Net Expected Value (EV Score) to discover non-obvious master lines.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .card_db import CardInfo

logger = logging.getLogger("ActionTreeSearch")


@dataclass
class ActionBranch:
    plan_name: str                 # "方案A: 节奏站场 (Tempo)", "方案B: 稳健控场 (Control)", "方案C: 全力抢脸 (Rush)"
    action_sequence: List[str]     # e.g., ["打出【淡水鳄】", "使用【英雄技能】", "随从走脸"]
    mana_spent: int
    floating_mana: int
    damage_to_face: int
    projected_board_attack: int
    projected_board_health: int
    surviving_enemy_attack: int
    ev_score: float                # Net Expected Value Score
    tactical_intent: str
    floor_ev: float = 0.0          # 下限稳健值 (Worst-case floor under AOE/clear)
    ceiling_ev: float = 0.0        # 上限爆发值 (High-roll ceiling)
    opp_response_threat: str = ""  # 敌方下回合最高威胁响应预测
    board_survival_rate: float = 1.0 # 敌方反打后随从存活率
    curve_synergy_advice: str = "" # 连续两回合曲线协同度评价
    projected_winrate: float = 50.0 # 预计执行后全局胜率百分比 (%)
    positioning_slot_advice: str = "" # 随从下怪几何插槽推荐
    curve_foresight_text: str = ""    # 双回合费用曲线平滑前瞻
    variance_policy: str = ""         # 随机性方差博弈倾向评估
    resilience_score: int = 50        # 抗灭韧性评分 (0 to 100)
    resilience_badge: str = ""        # 抗灭韧性气泡


@dataclass
class ActionTreeResult:
    best_branch: ActionBranch
    alternative_branches: List[ActionBranch] = field(default_factory=list)
    comparison_summary: str = ""


class ActionTreeSearch:
    """
    Simulates branch game outcomes to mathematically rank the top candidate plays.
    Includes Transposition Table memoization, symmetry reduction, and lethal short-circuiting.
    """

    _memo_cache: Dict[Tuple, ActionTreeResult] = {}

    @classmethod
    def clear_cache(cls) -> None:
        cls._memo_cache.clear()

    @staticmethod
    def _compute_state_signature(
        friendly_minions: List[Dict[str, Any]],
        enemy_minions: List[Dict[str, Any]],
        hand_cards: List[CardInfo],
        available_mana: int,
        friendly_hp: int,
        enemy_hp: int,
        opponent_class: str,
    ) -> Tuple:
        f_sig = tuple(sorted(
            (m.get("name", ""), m.get("atk", m.get("attack", 0)), m.get("health", m.get("hp", 0)), bool(m.get("can_attack", True)), bool(m.get("taunt", False)))
            for m in friendly_minions
        ))
        e_sig = tuple(sorted(
            (m.get("name", ""), m.get("atk", m.get("attack", 0)), m.get("health", m.get("hp", 0)), bool(m.get("taunt", False)))
            for m in enemy_minions
        ))
        h_sig = tuple(getattr(c, "id", str(c)) for c in hand_cards)
        return (f_sig, e_sig, h_sig, available_mana, friendly_hp, enemy_hp, opponent_class.upper())

    @staticmethod
    def _get_atk(m: Dict[str, Any]) -> int:
        return m.get("atk", m.get("attack", 0))

    @staticmethod
    def _get_hp(m: Dict[str, Any]) -> int:
        return m.get("health", m.get("hp", 0))

    @classmethod
    def search_optimal_branch(
        cls,
        friendly_minions: List[Dict[str, Any]],  # [{"name": str, "atk": int, "health": int, "can_attack": bool}]
        enemy_minions: List[Dict[str, Any]],     # [{"name": str, "atk": int, "health": int, "taunt": bool}]
        hand_cards: List[CardInfo],
        available_mana: int,
        friendly_hp: int = 30,
        enemy_hp: int = 30,
        opponent_class: str = "MAGE",
    ) -> ActionTreeResult:
        """
        Explores candidate play branches and evaluates their resultant EV score.
        Uses Zobrist-like state memoization to return cached results in <0.01ms.
        """
        state_key = cls._compute_state_signature(
            friendly_minions, enemy_minions, hand_cards, available_mana, friendly_hp, enemy_hp, opponent_class
        )
        if state_key in cls._memo_cache:
            return cls._memo_cache[state_key]

        branches: List[ActionBranch] = []

        ready_f_minions = [m for m in friendly_minions if m.get("can_attack", True)]
        total_f_atk = sum(cls._get_atk(m) for m in ready_f_minions)
        enemy_taunts = [m for m in enemy_minions if m.get("taunt", False)]
        taunt_hp = sum(cls._get_hp(m) for m in enemy_taunts)

        # Early Lethal Short-Circuit (Instant win check)
        is_direct_face_lethal = (not enemy_taunts and total_f_atk >= enemy_hp and total_f_atk > 0)

        # -------------------------------------------------------------------------
        # Branch 1: Tempo Development (节奏展开)
        # -------------------------------------------------------------------------
        playable_cards = [c for c in hand_cards if c.cost <= available_mana]
        playable_cards.sort(key=lambda c: (c.cost, getattr(c, "attack", 0) or 0), reverse=True)

        tempo_actions: List[str] = []
        tempo_spent = 0
        tempo_minions_played = []

        for c in playable_cards:
            if tempo_spent + c.cost <= available_mana:
                txt = getattr(c, "clean_text", "") or ""
                if ("叫嚣" in c.name or "获得+" in txt) and ready_f_minions:
                    target = ready_f_minions[0].get("name", "友方随从")
                    tempo_actions.append(f"打出: 【{c.name}】 → 战吼增益我方【{target}】(+攻)")
                elif ("DAMAGE" in (getattr(c, "text", "") or "").upper() or "伤害" in txt) and enemy_minions:
                    e_tgt = enemy_minions[0].get("name", "敌方随从")
                    tempo_actions.append(f"打出: 【{c.name}】 → 定向打击敌方【{e_tgt}】")
                else:
                    tempo_actions.append(f"打出: 【{c.name}】 ({c.cost}费)")
                tempo_spent += c.cost
                tempo_minions_played.append(c)

        rem_mana_tempo = available_mana - tempo_spent
        if rem_mana_tempo >= 2:
            tempo_actions.append("使用【英雄技能】压制/补刀")
            tempo_spent += 2
            rem_mana_tempo -= 2

        # Minions clear taunts first, remainder goes to face
        face_dmg_tempo = max(0, total_f_atk - taunt_hp)
        if taunt_hp > 0:
            tempo_actions.append(f"场上随从集火清理敌方嘲讽 ({taunt_hp}血)")
        if face_dmg_tempo > 0:
            tempo_actions.append(f"余下随从全员走脸造成 {face_dmg_tempo} 点伤害")

        proj_atk_tempo = sum(cls._get_atk(m) for m in friendly_minions) + sum(getattr(c, "attack", 0) or 0 for c in tempo_minions_played)
        proj_hp_tempo = sum(cls._get_hp(m) for m in friendly_minions) + sum(getattr(c, "health", 0) or 0 for c in tempo_minions_played)
        surv_e_atk_tempo = sum(cls._get_atk(m) for m in enemy_minions if not m.get("taunt", False))

        ev_tempo = (
            (proj_atk_tempo * 2.0) +
            (proj_hp_tempo * 1.0) +
            (face_dmg_tempo * 1.5) -
            (rem_mana_tempo * 2.5) -
            (surv_e_atk_tempo * 1.2)
        )

        branches.append(ActionBranch(
            plan_name="方案A: 节奏展开 (Tempo)",
            action_sequence=tempo_actions or ["挂机或转技能"],
            mana_spent=tempo_spent,
            floating_mana=rem_mana_tempo,
            damage_to_face=face_dmg_tempo,
            projected_board_attack=proj_atk_tempo,
            projected_board_health=proj_hp_tempo,
            surviving_enemy_attack=surv_e_atk_tempo,
            ev_score=round(ev_tempo, 1),
            tactical_intent="最大化法力水晶利用率，铺场展开并兼顾血量施压",
        ))

        # -------------------------------------------------------------------------
        # Branch 2: Control & Value Trades (稳健控场)
        # -------------------------------------------------------------------------
        ctrl_actions: List[str] = []
        enemy_total_hp = sum(cls._get_hp(m) for m in enemy_minions)
        face_dmg_ctrl = max(0, total_f_atk - enemy_total_hp)

        if enemy_minions:
            ctrl_actions.append(f"全员优先随从交换，清理敌方 {len(enemy_minions)} 个场上随从")
        if face_dmg_ctrl > 0:
            ctrl_actions.append(f"扫清场面后剩余场攻走脸 {face_dmg_ctrl} 点")

        ctrl_spent = 0
        for c in playable_cards:
            if ctrl_spent + c.cost <= available_mana:
                txt = getattr(c, "clean_text", "") or ""
                if ("叫嚣" in c.name or "获得+" in txt) and ready_f_minions:
                    target = ready_f_minions[0].get("name", "友方随从")
                    ctrl_actions.append(f"打出: 【{c.name}】 → 战吼增益我方【{target}】完成优势交换")
                elif ("DAMAGE" in (getattr(c, "text", "") or "").upper() or "伤害" in txt) and enemy_minions:
                    e_tgt = enemy_minions[0].get("name", "敌方随从")
                    ctrl_actions.append(f"法术解场: 【{c.name}】 → 消灭敌方【{e_tgt}】")
                else:
                    ctrl_actions.append(f"后置下怪补足场面: 【{c.name}】")
                ctrl_spent += c.cost

        rem_mana_ctrl = available_mana - ctrl_spent
        surviving_e_atk_ctrl = max(0, sum(cls._get_atk(m) for m in enemy_minions) - total_f_atk)

        ev_ctrl = (
            (proj_atk_tempo * 1.6) +
            (proj_hp_tempo * 1.2) +
            (face_dmg_ctrl * 1.0) -
            (rem_mana_ctrl * 2.0) -
            (surviving_e_atk_ctrl * 2.5)  # Huge reward for 0 enemy board
        )

        branches.append(ActionBranch(
            plan_name="方案B: 稳健控场 (Control)",
            action_sequence=ctrl_actions or ["控场交换"],
            mana_spent=ctrl_spent,
            floating_mana=rem_mana_ctrl,
            damage_to_face=face_dmg_ctrl,
            projected_board_attack=proj_atk_tempo,
            projected_board_health=proj_hp_tempo,
            surviving_enemy_attack=surviving_e_atk_ctrl,
            ev_score=round(ev_ctrl, 1),
            tactical_intent="彻底剥夺敌方场面与攻击频率，规避被Buff或嗜血偷鸡",
        ))

        # -------------------------------------------------------------------------
        # Branch 3: All-in Face Rush (全力走脸抢血)
        # -------------------------------------------------------------------------
        rush_actions: List[str] = []
        if taunt_hp > 0:
            rush_actions.append(f"用最小代价破开嘲讽 ({taunt_hp}血)")
        rush_face_dmg = max(0, total_f_atk - taunt_hp)
        rush_actions.append(f"全员全力打脸造成 {rush_face_dmg} 点伤害")

        # Hand burn
        hand_burn = 0
        rush_spent = 0
        for c in playable_cards:
            if "DAMAGE" in (c.text or "").upper() or "伤害" in (c.text or ""):
                rush_actions.append(f"直伤抢脸: 【{c.name}】")
                rush_spent += c.cost
                hand_burn += 3

        total_rush_dmg = rush_face_dmg + hand_burn
        rem_enemy_hp = enemy_hp - total_rush_dmg

        face_urgency_bonus = 25.0 if rem_enemy_hp <= 8 else (10.0 if rem_enemy_hp <= 15 else -5.0)
        ev_rush = (
            (total_rush_dmg * 2.2) +
            face_urgency_bonus -
            (sum(cls._get_atk(m) for m in enemy_minions) * 1.8)
        )

        branches.append(ActionBranch(
            plan_name="方案C: 全力突击 (Rush)",
            action_sequence=rush_actions,
            mana_spent=rush_spent or tempo_spent,
            floating_mana=rem_mana_tempo,
            damage_to_face=total_rush_dmg,
            projected_board_attack=total_f_atk,
            projected_board_health=sum(cls._get_hp(m) for m in friendly_minions),
            surviving_enemy_attack=sum(cls._get_atk(m) for m in enemy_minions),
            ev_score=round(ev_rush, 1),
            tactical_intent=f"全员无视非嘲讽走脸，将敌方压至 {rem_enemy_hp} 血绝杀线",
        ))

        # Compute Advanced Forecasting: Opponent Next-Turn Response & Curve Synergy
        c_upper = opponent_class.upper().strip()
        if "MAGE" in c_upper or "法师" in c_upper:
            aoe_threat_name = "烈焰风暴 / 暴风雪"
            est_aoe_dmg = 4
        elif "WARLOCK" in c_upper or "术士" in c_upper:
            aoe_threat_name = "地狱烈焰 / 亵渎"
            est_aoe_dmg = 3
        elif "PRIEST" in c_upper or "牧师" in c_upper:
            aoe_threat_name = "圣光炸弹 / 神圣新星"
            est_aoe_dmg = 3
        elif "PALADIN" in c_upper or "骑士" in c_upper:
            aoe_threat_name = "奉献"
            est_aoe_dmg = 2
        elif "SHAMAN" in c_upper or "萨满" in c_upper:
            aoe_threat_name = "闪电风暴"
            est_aoe_dmg = 3
        else:
            aoe_threat_name = "常规解牌/AOE"
            est_aoe_dmg = 2

        next_turn_mana = min(10, available_mana + 1)
        hand_costs = [c.cost for c in hand_cards]

        for b in branches:
            surv_count = 0
            total_m = max(len(friendly_minions), 1)
            for m in friendly_minions:
                if cls._get_hp(m) > est_aoe_dmg:
                    surv_count += 1
            surv_rate = round(surv_count / total_m, 2)
            b.board_survival_rate = surv_rate
            b.opp_response_threat = f"防【{aoe_threat_name}】存活率 {int(surv_rate * 100)}%"
            b.floor_ev = round(b.ev_score * (0.5 + 0.5 * surv_rate), 1)
            b.ceiling_ev = round(b.ev_score + (b.damage_to_face * 1.2) + (b.projected_board_attack * 0.4), 1)

            rem_costs = list(hand_costs)
            if next_turn_mana in rem_costs:
                b.curve_synergy_advice = f"完美衔接 T{next_turn_mana} 费用曲线 (0水晶浪费)"
            elif any(c1 + c2 == next_turn_mana for i, c1 in enumerate(rem_costs) for c2 in rem_costs[i+1:]):
                b.curve_synergy_advice = f"双卡平滑衔接 T{next_turn_mana} 水晶"
            else:
                b.curve_synergy_advice = f"T{next_turn_mana} 存在水晶空隙，建议提前过牌"

            # Calculate concrete projected win rate % for this branch
            try:
                from .winrate_estimator import WinRateEstimator
                rem_e_hp = max(0, enemy_hp - b.damage_to_face)
                win_rep = WinRateEstimator.calculate_winrate(
                    friendly_hp=friendly_hp,
                    enemy_hp=rem_e_hp,
                    friendly_board_atk=b.projected_board_attack,
                    enemy_board_atk=b.surviving_enemy_attack,
                    friendly_minion_count=len(friendly_minions),
                    enemy_minion_count=len(enemy_minions),
                    friendly_hand_count=max(1, len(hand_cards) - 1),
                    enemy_hand_count=4,
                    current_turn=available_mana,
                    has_immediate_lethal=(rem_e_hp <= 0),
                )
                b.projected_winrate = win_rep.winrate_pct
            except Exception:
                b.projected_winrate = 50.0

            # 1. 2-Turn Curve Smoothing Foresight
            try:
                from .mana_efficiency import ManaEfficiencyOptimizer
                eff_plan = ManaEfficiencyOptimizer.calculate_2turn_efficiency(hand_cards, available_mana, next_turn_mana)
                if eff_plan:
                    b.curve_foresight_text = eff_plan.advice_text
            except Exception:
                pass

            # 2. Positioning Slot Advice for deployed minion
            try:
                from .positioning_geometry import PositioningGeometry
                board_objs = [
                    {"name": cls._get_name(m), "atk": cls._get_atk(m), "health": cls._get_hp(m),
                     "divine_shield": False, "deathrattle": False, "taunt": False, "is_mech": False}
                    for m in friendly_minions
                ]
                incoming_minion = {"name": "新增随从", "atk": 3, "health": 3, "divine_shield": False, "deathrattle": False, "taunt": False, "is_magnetic": False}
                for c in playable_cards:
                    if (c.attack or 0) > 0 and c.name in " ".join(b.action_sequence):
                        incoming_minion = {
                            "name": c.name,
                            "atk": c.attack or 2,
                            "health": c.health or 2,
                            "divine_shield": "圣盾" in (c.text or ""),
                            "deathrattle": "亡语" in (c.text or ""),
                            "taunt": "嘲讽" in (c.text or ""),
                            "is_magnetic": "磁力" in (c.text or ""),
                        }
                        break
                pos_advice = PositioningGeometry.calculate_optimal_placement(board_objs, incoming_minion, opponent_class)
                b.positioning_slot_advice = f"{pos_advice.slot_description} ({pos_advice.strategic_rationale})"
            except Exception:
                pass

            # 3. Variance Evaluator Policy
            try:
                from .variance_evaluator import VarianceEvaluator
                var_report = VarianceEvaluator.evaluate_risk_policy(b.projected_winrate, b.action_sequence)
                b.variance_policy = f"{var_report.policy_badge}: {var_report.variance_directive}"
            except Exception:
                pass

        # If direct lethal was detected, ensure Rush branch is ranked #1 with absolute certainty
        if is_direct_face_lethal:
            for b in branches:
                if "Rush" in b.plan_name or "突击" in b.plan_name:
                    b.ev_score = 999.0
                    b.projected_winrate = 100.0
                    b.tactical_intent = f"【🔥100%直接斩杀】敌方无嘲讽且仅剩 {enemy_hp} 血，全员集火走脸直接取胜！"

        # Sort branches by net EV score descending
        branches.sort(key=lambda b: b.ev_score, reverse=True)
        best = branches[0]
        alts = branches[1:]

        comparison = (
            f"🌲 动作树最优解: 【{best.plan_name}】(期望值EV: {best.ev_score}) | "
            f"备选: {alts[0].plan_name}(EV: {alts[0].ev_score})"
        )

        result = ActionTreeResult(
            best_branch=best,
            alternative_branches=alts,
            comparison_summary=comparison,
        )

        if len(cls._memo_cache) > 256:
            cls._memo_cache.clear()
        cls._memo_cache[state_key] = result
        return result
