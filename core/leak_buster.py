"""
LeakBuster: Professional Tactical Blunder & Play-Order Leak Audit Engine.
Detects micro-blunders across turns: missed lethals, suboptimal draw orders,
premature attacks before aura buffs, divine shield trade inefficiencies, and excessive mana floating.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("LeakBuster")


class LeakType(str, Enum):
    MISSED_LETHAL = "MISSED_LETHAL"
    SUBOPTIMAL_DRAW_ORDER = "SUBOPTIMAL_DRAW_ORDER"
    AURA_SEQUENCE_ERROR = "AURA_SEQUENCE_ERROR"
    DIVINE_SHIELD_WASTE = "DIVINE_SHIELD_WASTE"
    AOE_OVEREXTEND = "AOE_OVEREXTEND"
    MANA_FLOAT = "MANA_FLOAT"


@dataclass
class LeakItem:
    turn: int
    leak_type: LeakType
    severity: str                 # "CRITICAL", "MAJOR", "MINOR"
    title: str
    explanation: str
    estimated_winrate_loss_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn": self.turn,
            "leak_type": self.leak_type.value,
            "severity": self.severity,
            "title": self.title,
            "explanation": self.explanation,
            "estimated_winrate_loss_pct": round(self.estimated_winrate_loss_pct, 1),
        }


@dataclass
class LeakAuditSummary:
    total_leaks: int
    leak_score: float             # 0 to 100 scale (100 = flawless play)
    leak_grade: str               # "S 宗师无暇", "A 卓越发挥", "B 存在漏洞", "C 严重伏笔"
    leaks: List[LeakItem] = field(default_factory=list)
    radar_scores: Dict[str, float] = field(default_factory=dict)
    top_actionable_fixes: List[str] = field(default_factory=list)
    summary_markdown: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_leaks": self.total_leaks,
            "leak_score": round(self.leak_score, 1),
            "leak_grade": self.leak_grade,
            "leaks": [l.to_dict() for l in self.leaks],
            "radar_scores": {k: round(v, 1) for k, v in self.radar_scores.items()},
            "top_actionable_fixes": self.top_actionable_fixes,
            "summary_markdown": self.summary_markdown,
        }


class LeakBuster:
    """Audits player turn logs to expose subtle tactical flaws and sequencing mistakes."""

    AURA_BUFF_KEYWORDS = [
        "暴风城勇士", "十字军光环", "嗜血", "野蛮咆哮", "火舌图腾",
        "战歌指挥官", "团队领袖", "恐狼先锋", "全体获得+", "随从获得+"
    ]

    DRAW_CARD_KEYWORDS = [
        "奥术智慧", "滋养", "疾跑", "严正警戒", "痛苦诅咒", "抽一张牌",
        "抽两张牌", "过牌", "追踪术", "感知恶魔", "生命分流"
    ]

    @classmethod
    def audit_turn(
        cls,
        turn: int,
        action_sequence: List[Dict[str, Any]],
        start_mana: int,
        spent_mana: int,
        enemy_hp: int,
        board_total_lethal_damage: int = 0,
        opponent_has_aoe_next_turn: bool = False,
        minions_on_board_count: int = 0,
    ) -> List[LeakItem]:
        leaks: List[LeakItem] = []

        # 1. Missed Lethal Audit
        if board_total_lethal_damage >= enemy_hp and enemy_hp > 0:
            # Check if game ended or if user made trades / ended turn
            went_face_for_kill = False
            for act in action_sequence:
                if act.get("type") == "ATTACK" and act.get("target") == "HERO":
                    if act.get("damage", 0) >= enemy_hp:
                        went_face_for_kill = True
            if not went_face_for_kill:
                leaks.append(
                    LeakItem(
                        turn=turn,
                        leak_type=LeakType.MISSED_LETHAL,
                        severity="CRITICAL",
                        title=f"第 {turn} 回合错失直接斩杀",
                        explanation=f"当前场面与手牌总伤害为 {board_total_lethal_damage} 点，敌方血量仅为 {enemy_hp} 点，本可直接终结比赛！",
                        estimated_winrate_loss_pct=85.0,
                    )
                )

        # 2. Sequencing Audit: Draw Order
        first_draw_idx = -1
        first_card_play_idx = -1

        for idx, act in enumerate(action_sequence):
            card_name = act.get("name", "")
            if any(k in card_name for k in cls.DRAW_CARD_KEYWORDS):
                if first_draw_idx == -1:
                    first_draw_idx = idx
            elif act.get("type") == "PLAY_CARD":
                if first_card_play_idx == -1:
                    first_card_play_idx = idx

        if first_draw_idx != -1 and first_card_play_idx != -1 and first_card_play_idx < first_draw_idx:
            leaks.append(
                LeakItem(
                    turn=turn,
                    leak_type=LeakType.SUBOPTIMAL_DRAW_ORDER,
                    severity="MAJOR",
                    title=f"第 {turn} 回合下牌顺序伏笔（未先过牌）",
                    explanation="在出随从/法术之后才进行过牌。过牌应优先执行，以便根据抓到的新牌做出最合理的战术决策。",
                    estimated_winrate_loss_pct=15.0,
                )
            )

        # 3. Sequencing Audit: Aura Buff before Attacks
        buff_play_idx = -1
        first_attack_idx = -1

        for idx, act in enumerate(action_sequence):
            card_name = act.get("name", "")
            if any(k in card_name for k in cls.AURA_BUFF_KEYWORDS) and act.get("type") == "PLAY_CARD":
                buff_play_idx = idx
            elif act.get("type") == "ATTACK" and first_attack_idx == -1:
                first_attack_idx = idx

        if buff_play_idx != -1 and first_attack_idx != -1 and first_attack_idx < buff_play_idx:
            leaks.append(
                LeakItem(
                    turn=turn,
                    leak_type=LeakType.AURA_SEQUENCE_ERROR,
                    severity="MAJOR",
                    title=f"第 {turn} 回合光环随从后置伏笔",
                    explanation="在随从发动攻击后才打出群体增益/光环卡牌，导致先攻随从未能享受攻击力加成，白白浪费场面输出。",
                    estimated_winrate_loss_pct=18.0,
                )
            )

        # 4. Divine Shield Trade Inefficiency
        for act in action_sequence:
            if act.get("type") == "ATTACK" and act.get("target_has_divine_shield", False):
                attacker_atk = act.get("attacker_attack", 0)
                if attacker_atk >= 4:
                    leaks.append(
                        LeakItem(
                            turn=turn,
                            leak_type=LeakType.DIVINE_SHIELD_WASTE,
                            severity="MINOR",
                            title=f"第 {turn} 回合高攻撞圣盾损耗",
                            explanation=f"使用 {attacker_atk} 攻高战力生物强破圣盾。推荐优先用英雄技能点射、低费法术或1攻杂兵先破圣盾。",
                            estimated_winrate_loss_pct=8.0,
                        )
                    )

        # 5. Overextend into heavy AOE
        if opponent_has_aoe_next_turn and minions_on_board_count >= 5:
            minions_played_this_turn = sum(1 for a in action_sequence if a.get("type") == "PLAY_CARD" and a.get("card_type") == "MINION")
            if minions_played_this_turn >= 2:
                leaks.append(
                    LeakItem(
                        turn=turn,
                        leak_type=LeakType.AOE_OVEREXTEND,
                        severity="MAJOR",
                        title=f"第 {turn} 回合防AOE纪律缺失（过度铺场）",
                        explanation=f"在对手即将迎来关键AOE回合且场上已有多只随从的情况下继续连铺2只生物，极易被单卡团灭导致资源枯竭。",
                        estimated_winrate_loss_pct=22.0,
                    )
                )

        # 6. Severe Mana Floating
        unspent_mana = start_mana - spent_mana
        if unspent_mana >= 3 and turn >= 4:
            leaks.append(
                LeakItem(
                    turn=turn,
                    leak_type=LeakType.MANA_FLOAT,
                    severity="MINOR",
                    title=f"第 {turn} 回合严重空余法力水晶 ({unspent_mana}费)",
                    explanation=f"本回合剩余 {unspent_mana} 点法力水晶未被利用，打乱了法力曲线节奏。",
                    estimated_winrate_loss_pct=6.0,
                )
            )

        return leaks

    @classmethod
    def audit_match(
        cls,
        turns_data: List[Dict[str, Any]],
        result: str = "WIN",
    ) -> LeakAuditSummary:
        all_leaks: List[LeakItem] = []

        for t_info in turns_data:
            turn_num = t_info.get("turn", 1)
            actions = t_info.get("actions", [])
            start_mana = t_info.get("start_mana", turn_num)
            spent_mana = t_info.get("spent_mana", start_mana)
            enemy_hp = t_info.get("enemy_hp", 30)
            lethal_dmg = t_info.get("board_lethal_damage", 0)
            opp_aoe = t_info.get("has_aoe_next_turn", False)
            board_count = t_info.get("board_minions_count", 0)

            t_leaks = cls.audit_turn(
                turn=turn_num,
                action_sequence=actions,
                start_mana=start_mana,
                spent_mana=spent_mana,
                enemy_hp=enemy_hp,
                board_total_lethal_damage=lethal_dmg,
                opponent_has_aoe_next_turn=opp_aoe,
                minions_on_board_count=board_count,
            )
            all_leaks.extend(t_leaks)

        # Calculate Leak Score (100 base, deductions based on severity)
        deduction = 0.0
        for l in all_leaks:
            if l.severity == "CRITICAL":
                deduction += 35.0
            elif l.severity == "MAJOR":
                deduction += 15.0
            else:
                deduction += 5.0

        leak_score = max(0.0, min(100.0, 100.0 - deduction))

        # Grade
        if leak_score >= 90.0:
            grade = "S 宗师无暇"
        elif leak_score >= 75.0:
            grade = "A 卓越发挥"
        elif leak_score >= 60.0:
            grade = "B 存在漏洞"
        else:
            grade = "C 严重伏笔"

        # Radar Dimensions (0-100)
        has_missed_lethal = any(l.leak_type == LeakType.MISSED_LETHAL for l in all_leaks)
        has_seq_err = any(l.leak_type in [LeakType.SUBOPTIMAL_DRAW_ORDER, LeakType.AURA_SEQUENCE_ERROR] for l in all_leaks)
        has_mana_float = any(l.leak_type == LeakType.MANA_FLOAT for l in all_leaks)
        has_aoe_leak = any(l.leak_type == LeakType.AOE_OVEREXTEND for l in all_leaks)
        has_trade_leak = any(l.leak_type == LeakType.DIVINE_SHIELD_WASTE for l in all_leaks)

        radar = {
            "Sequencing": 60.0 if has_seq_err else 95.0,
            "LethalAwareness": 20.0 if has_missed_lethal else 98.0,
            "ResourcePacing": 65.0 if has_mana_float else 90.0,
            "AntiSweeperDiscipline": 50.0 if has_aoe_leak else 92.0,
            "ValueTrading": 70.0 if has_trade_leak else 94.0,
        }

        # Actionable fixes
        fixes: List[str] = []
        if has_missed_lethal:
            fixes.append("斩杀警觉度：每回合开始前先心算场面攻击力+直伤+法术，避免错斩痛失好局。")
        if has_seq_err:
            fixes.append("出牌次序纪律：坚决遵循【先抽牌、再打光环/增益、最后发动攻击】的基本原则。")
        if has_aoe_leak:
            fixes.append("防AOE防过度投资：当场面已有绝对压制力时，手牌保留关键续航生物，勿将所有鸡蛋放一个篮子。")
        if has_trade_leak:
            fixes.append("圣盾破除细节：优先使用英雄技能或1点低伤频率破盾，切勿使用主力大怪强行消耗。")
        if not fixes:
            fixes.append("对局发挥近乎完美！继续保持严谨的出牌顺序与精准的打脸/控场节奏。")

        # Markdown summary
        md_lines = [
            f"**伏笔盲区审计评分**: **{leak_score:.1f}** 分 (评级: `{grade}`)",
            f"• **检测到伏笔瑕疵**: 共 {len(all_leaks)} 处 (致命 {sum(1 for l in all_leaks if l.severity == 'CRITICAL')} / 重大 {sum(1 for l in all_leaks if l.severity == 'MAJOR')} / 轻微 {sum(1 for l in all_leaks if l.severity == 'MINOR')})",
        ]
        for f in fixes[:2]:
            md_lines.append(f"• 💡 **改进建议**: {f}")

        return LeakAuditSummary(
            total_leaks=len(all_leaks),
            leak_score=leak_score,
            leak_grade=grade,
            leaks=all_leaks,
            radar_scores=radar,
            top_actionable_fixes=fixes,
            summary_markdown="\n".join(md_lines),
        )
