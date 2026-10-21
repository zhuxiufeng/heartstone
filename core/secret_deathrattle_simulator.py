"""
SecretDeathrattleSimulator: Multi-Secret Trigger Priority & Deathrattle Cascade Resolver.
Simulates complex Hearthstone interactions: multi-secret simultaneous triggers,
action redirections/cancellations, and multi-death deathrattle cascade chain reactions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("SecretDeathrattleSimulator")


@dataclass
class SecretTriggerEvent:
    secret_name: str
    trigger_rule: str
    impact_type: str            # "REDIRECT", "DAMAGE", "CANCEL", "SUMMON", "BUFF"
    description: str
    damage_to_friendly_hero: int = 0
    damage_to_friendly_board: int = 0
    target_redirected_to: Optional[str] = None


@dataclass
class SecretProbingPlan:
    action_type: str            # "ATTACK_HERO", "ATTACK_MINION", "PLAY_MINION", "CAST_SPELL"
    action_label: str
    tested_secrets: List[str]
    safety_score_pct: float     # 0.0 to 100.0%
    worst_case_punish: str
    recommended_minion_used: str
    tactical_directive: str


@dataclass
class DeathrattleCascadeResult:
    dying_minions: List[str]
    spawned_tokens: List[str]
    total_aoe_damage: int
    surviving_friendly_minions: List[Dict[str, Any]]
    surviving_enemy_minions: List[Dict[str, Any]]
    cascade_log: List[str]
    summary_markdown: str


@dataclass
class SecretCascadeReport:
    active_secrets: List[str]
    probing_plans: List[SecretProbingPlan]
    best_probing_plan: SecretProbingPlan
    deathrattle_simulation: Optional[DeathrattleCascadeResult]
    summary_markdown: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_secrets": self.active_secrets,
            "best_probing_plan": {
                "action_type": self.best_probing_plan.action_type,
                "action_label": self.best_probing_plan.action_label,
                "tested_secrets": self.best_probing_plan.tested_secrets,
                "safety_score_pct": round(self.best_probing_plan.safety_score_pct, 1),
                "worst_case_punish": self.best_probing_plan.worst_case_punish,
                "recommended_minion_used": self.best_probing_plan.recommended_minion_used,
                "tactical_directive": self.best_probing_plan.tactical_directive,
            },
            "probing_plans": [
                {
                    "action_type": p.action_type,
                    "action_label": p.action_label,
                    "tested_secrets": p.tested_secrets,
                    "safety_score_pct": round(p.safety_score_pct, 1),
                    "worst_case_punish": p.worst_case_punish,
                    "directive": p.tactical_directive,
                }
                for p in self.probing_plans
            ],
            "deathrattle": {
                "dying_minions": self.deathrattle_simulation.dying_minions,
                "spawned_tokens": self.deathrattle_simulation.spawned_tokens,
                "total_aoe_damage": self.deathrattle_simulation.total_aoe_damage,
                "cascade_log": self.deathrattle_simulation.cascade_log,
            } if self.deathrattle_simulation else None,
            "summary_markdown": self.summary_markdown,
        }


class SecretDeathrattleSimulator:
    """Simulates multi-secret trigger cascades and deathrattle chains."""

    SECRET_DATABASE = {
        # Hunter
        "爆炸陷阱": {"trigger": "ATTACK_HERO", "impact": "DAMAGE", "hero_dmg": 2, "board_dmg": 2, "desc": "敌方英雄受击时，对所有敌方角色造成2点伤害"},
        "冰冻陷阱": {"trigger": "ATTACK_ANY", "impact": "REDIRECT", "desc": "攻击的随从移回所有者手牌，费用增加(2)点"},
        "游荡怪物": {"trigger": "ATTACK_HERO", "impact": "SUMMON", "desc": "英雄受击时，召唤一个随机3费随从成为新目标"},
        "狙击": {"trigger": "PLAY_MINION", "impact": "DAMAGE", "board_dmg": 4, "desc": "下随从时对其造成4点伤害"},
        "误导": {"trigger": "ATTACK_HERO", "impact": "REDIRECT", "desc": "攻击英雄时，随机重新指向另一个角色"},

        # Mage
        "法术反制": {"trigger": "CAST_SPELL", "impact": "CANCEL", "desc": "施放法术时，反制并取消该法术"},
        "异议": {"trigger": "PLAY_MINION", "impact": "CANCEL", "desc": "使用随从时，反制并直接消灭该随从"},
        "蒸发": {"trigger": "ATTACK_HERO", "impact": "CANCEL", "desc": "随从攻击英雄时，直接消灭该随从"},
        "绿洲盟友": {"trigger": "CAST_SPELL", "impact": "SUMMON", "desc": "施放法术后召唤一个3/6具有嘲讽的水元素"},

        # Paladin
        "崇高牺牲": {"trigger": "ATTACK_ANY", "impact": "SUMMON", "desc": "敌人攻击时，召唤一个2/1防御者成为新目标"},
        "救赎": {"trigger": "MINION_DEATH", "impact": "SUMMON", "desc": "友方随从死亡时复活为1血"},
        "复仇": {"trigger": "MINION_DEATH", "impact": "BUFF", "desc": "友方随从死亡时，使另一个友方随从获得+3/+2"},

        # Rogue
        "伏击": {"trigger": "PLAY_MINION", "impact": "SUMMON", "desc": "使用随从后召唤一个2/3剧毒潜行随从"},
        "作弊游戏": {"trigger": "ATTACK_HERO", "impact": "CANCEL", "desc": "受到致命伤害时免疫本回合伤害并抽牌"},
    }

    @classmethod
    def evaluate_probing_order(
        cls,
        active_secrets: List[str],
        friendly_minions: List[Dict[str, Any]],
        friendly_hand: List[Dict[str, Any]],
        friendly_hp: int,
    ) -> SecretCascadeReport:
        if not active_secrets:
            dummy_plan = SecretProbingPlan(
                action_type="NONE",
                action_label="无奥秘",
                tested_secrets=[],
                safety_score_pct=100.0,
                worst_case_punish="无风险",
                recommended_minion_used="任意",
                tactical_directive="对手场上无奥秘，按常规战术展开攻击与下怪即可。",
            )
            return SecretCascadeReport(
                active_secrets=[],
                probing_plans=[dummy_plan],
                best_probing_plan=dummy_plan,
                deathrattle_simulation=None,
                summary_markdown="场上无活跃奥秘。",
            )

        # Sort friendly minions by attack ascending (lowest attack/token first)
        sorted_minions = sorted(friendly_minions, key=lambda m: (m.get("attack", 1), -m.get("health", 1)))
        cheapest_minion_name = sorted_minions[0].get("name", "低攻杂兵") if sorted_minions else "英雄技能或武器"

        # Check lowest cost spell and minion in hand
        hand_spells = [c for c in friendly_hand if c.get("type") == "SPELL"]
        hand_minions = [c for c in friendly_hand if c.get("type") == "MINION"]
        cheapest_spell = min(hand_spells, key=lambda c: c.get("cost", 99)).get("name", "硬币/低费法术") if hand_spells else "低费法术"
        cheapest_hand_minion = min(hand_minions, key=lambda c: c.get("cost", 99)).get("name", "低费杂鱼") if hand_minions else "低费随从"

        plans: List[SecretProbingPlan] = []

        # Plan 1: Probe Hero Attack
        tested_hero_secrets = [s for s in active_secrets if cls.SECRET_DATABASE.get(s, {}).get("trigger") in ("ATTACK_HERO", "ATTACK_ANY")]
        has_freeze = "冰冻陷阱" in active_secrets
        has_vaporize = "蒸发" in active_secrets
        has_explosive = "爆炸陷阱" in active_secrets
        has_noble = "崇高牺牲" in active_secrets or "游荡怪物" in active_secrets

        hero_safety = 85.0
        punish_desc = "无明显严厉惩罚"
        if has_vaporize:
            hero_safety -= 35.0
            punish_desc = f"若为【蒸发】，将直接秒杀攻击的随从！严禁用主力大哥走脸"
        elif has_freeze:
            hero_safety -= 20.0
            punish_desc = f"若为【冰冻陷阱】，攻击随从将被回手并加2费"
        elif has_explosive:
            if friendly_hp <= 2:
                hero_safety = 0.0
                punish_desc = "致命危险！若为【爆炸陷阱】将直接打脸斩杀我方英雄！"
            else:
                hero_safety -= 15.0
                punish_desc = "若为【爆炸陷阱】，全场随从及英雄将承受2点AOE伤害"

        plans.append(
            SecretProbingPlan(
                action_type="ATTACK_HERO",
                action_label="杂毛探脸 (Attack Face)",
                tested_secrets=tested_hero_secrets,
                safety_score_pct=max(5.0, hero_safety),
                worst_case_punish=punish_desc,
                recommended_minion_used=cheapest_minion_name,
                tactical_directive=f"使用【{cheapest_minion_name}】先行攻击敌方英雄，防范蒸发/冰冻/爆炸/游荡怪物。",
            )
        )

        # Plan 2: Probe Minion Play
        tested_play_secrets = [s for s in active_secrets if cls.SECRET_DATABASE.get(s, {}).get("trigger") == "PLAY_MINION"]
        play_safety = 80.0
        play_punish = "无"
        if "异议" in active_secrets:
            play_safety -= 40.0
            play_punish = f"若为【异议】，打出的第一个随从将被直接反制消灭！"
        elif "狙击" in active_secrets:
            play_safety -= 20.0
            play_punish = "若为【狙击】，打出的随从将立即承受4点单体伤害"

        plans.append(
            SecretProbingPlan(
                action_type="PLAY_MINION",
                action_label="垫杂毛下怪 (Play Minion)",
                tested_secrets=tested_play_secrets,
                safety_score_pct=max(10.0, play_safety),
                worst_case_punish=play_punish,
                recommended_minion_used=cheapest_hand_minion,
                tactical_directive=f"使用手牌最低费的【{cheapest_hand_minion}】先行垫刀，排查异议/狙击/伏击。",
            )
        )

        # Plan 3: Probe Spell Cast
        tested_spell_secrets = [s for s in active_secrets if cls.SECRET_DATABASE.get(s, {}).get("trigger") == "CAST_SPELL"]
        spell_safety = 90.0
        spell_punish = "无"
        if "法术反制" in active_secrets:
            spell_safety -= 45.0
            spell_punish = "若为【法术反制】，第一张施放的法术将彻底失效被吃！"

        plans.append(
            SecretProbingPlan(
                action_type="CAST_SPELL",
                action_label="垫法术破反制 (Cast Spell)",
                tested_secrets=tested_spell_secrets,
                safety_score_pct=max(10.0, spell_safety),
                worst_case_punish=spell_punish,
                recommended_minion_used=cheapest_spell,
                tactical_directive=f"优先使用【{cheapest_spell}】先行破法反，保护后续高费关键法术。",
            )
        )

        # Pick best probing plan
        # If Mage secrets present and Counterspell probable, test spell first or minion first
        plans.sort(key=lambda p: -p.safety_score_pct)
        best_plan = plans[0]

        # Markdown summary
        md_lines = [
            f"**奥秘触发链推演**（检测到敌方已挂 `{len(active_secrets)}` 个奥秘: {', '.join(active_secrets)}）:",
            f"• **最优试探顺序**: **{best_plan.action_label}** (安全指数 {best_plan.safety_score_pct:.0f}%)",
            f"• **推荐操作**: {best_plan.tactical_directive}",
            f"• ⚠️ **极端惩罚预警**: {best_plan.worst_case_punish}",
        ]

        return SecretCascadeReport(
            active_secrets=active_secrets,
            probing_plans=plans,
            best_probing_plan=best_plan,
            deathrattle_simulation=None,
            summary_markdown="\n".join(md_lines),
        )

    @classmethod
    def simulate_deathrattle_cascade(
        cls,
        dying_minions: List[Dict[str, Any]],
        board_friendly: List[Dict[str, Any]],
        board_enemy: List[Dict[str, Any]],
    ) -> DeathrattleCascadeResult:
        """Simulates simultaneous deathrattle triggers and tokens."""
        logs = []
        spawned = []
        aoe_dmg = 0

        for m in dying_minions:
            name = m.get("name", "随从")
            logs.append(f"随从死亡结算: 【{name}】")
            # Common deathrattle archetypes
            if "自爆绵羊" in name or "憎恶" in name:
                aoe_dmg += 2
                logs.append(f"  → 触发亡语: 对全场所有随从造成 2 点伤害！")
            elif "鬼灵爬行者" in name:
                spawned.extend(["1/1 鬼灵蜘蛛", "1/1 鬼灵蜘蛛"])
                logs.append(f"  → 触发亡语: 召唤 2 只 1/1 鬼灵蜘蛛")
            elif "淤泥喷射者" in name:
                spawned.append("1/2 泥浆怪(嘲讽)")
                logs.append(f"  → 触发亡语: 召唤 1 只 1/2 具有嘲讽的泥浆怪")
            elif "虚空领主" in name:
                spawned.extend(["1/3 虚空行者(嘲讽)"] * 3)
                logs.append(f"  → 触发亡语: 召唤 3 只 1/3 虚空行者")
            elif "亡语" in m.get("text", ""):
                spawned.append(f"衍生物({name})")
                logs.append(f"  → 触发未知/通用亡语生成场面衍生物")

        # Resulting surviving friendly minions after aoe
        survived_friendly = []
        for m in board_friendly:
            rem_hp = m.get("health", 1) - aoe_dmg
            if rem_hp > 0:
                m_copy = dict(m)
                m_copy["health"] = rem_hp
                survived_friendly.append(m_copy)

        survived_enemy = []
        for m in board_enemy:
            rem_hp = m.get("health", 1) - aoe_dmg
            if rem_hp > 0:
                m_copy = dict(m)
                m_copy["health"] = rem_hp
                survived_enemy.append(m_copy)

        md = (
            f"**亡语连环结算完成**: {len(dying_minions)} 只随从阵亡，产生 {aoe_dmg} 点亡语AOE，"
            f"生成衍生单位: {', '.join(spawned) if spawned else '无'}。"
        )

        return DeathrattleCascadeResult(
            dying_minions=[m.get("name", "随从") for m in dying_minions],
            spawned_tokens=spawned,
            total_aoe_damage=aoe_dmg,
            surviving_friendly_minions=survived_friendly,
            surviving_enemy_minions=survived_enemy,
            cascade_log=logs,
            summary_markdown=md,
        )
