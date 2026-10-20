"""
TurnReplayerEngine: Chess.com-Style Turn-by-Turn Replay and Accuracy% Analyzer for Hearthstone.
Analyzes every turn snapshot of a completed match, grades every decision:
★ 妙手 (Brilliant)
✅ 最佳 (Best)
⚖️ 良好 (Good)
⚠️ 疑问手 (Inaccuracy)
❌ 严重伏笔 (Blunder)
Computes overall Game Decision Accuracy percentage (0-100%) and provides turn-by-turn navigation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TurnReplayer")


@dataclass
class TurnReviewNode:
    turn_number: int
    mana: int
    max_mana: int
    friendly_hp: int
    enemy_hp: int
    friendly_board: List[str] = field(default_factory=list)
    enemy_board: List[str] = field(default_factory=list)
    hand_cards: List[str] = field(default_factory=list)
    ai_best_plan: List[str] = field(default_factory=list)
    ai_ev: float = 0.0
    ai_winrate: float = 50.0
    player_actual_plays: List[str] = field(default_factory=list)
    had_lethal: bool = False
    lethal_damage: int = 0
    blunder_alerts: List[str] = field(default_factory=list)
    aoe_threat: str = ""
    floating_mana: int = 0
    # Evaluated scoring attributes
    action_grade: str = "✅ 最佳 (Best)"
    grade_color: str = "#10b981"
    score: int = 100
    analysis_comment: str = "出牌思路清晰，最大化法力水晶与场面收益。"


@dataclass
class MatchReplaySummary:
    result: str                    # "WIN" or "LOSS"
    total_turns: int
    overall_accuracy_pct: float    # e.g. 88.5 (%)
    grade_tier: str                # "S", "A", "B", "C"
    brilliant_count: int = 0
    best_count: int = 0
    good_count: int = 0
    inaccuracy_count: int = 0
    blunder_count: int = 0
    turn_nodes: List[TurnReviewNode] = field(default_factory=list)
    key_turning_turn: int = 1
    summary_markdown: str = ""


class TurnReplayerEngine:
    """Evaluates turn-by-turn accuracy and generates granular post-game reviews."""

    @classmethod
    def analyze_replay(
        cls,
        result: str,
        turn_snapshots: List[TurnReviewNode],
    ) -> MatchReplaySummary:
        is_win = result.upper() == "WIN"
        total_turns = len(turn_snapshots)

        if total_turns == 0:
            return MatchReplaySummary(
                result=result,
                total_turns=0,
                overall_accuracy_pct=100.0,
                grade_tier="S (无数据)",
            )

        brilliant_count = 0
        best_count = 0
        good_count = 0
        inaccuracy_count = 0
        blunder_count = 0

        first_blunder_turn = 1

        for idx, node in enumerate(turn_snapshots):
            # 1. Missed Lethal Evaluation
            if node.had_lethal and (not is_win or idx < total_turns - 1):
                node.action_grade = "❌ 严重伏笔 (Blunder)"
                node.grade_color = "#ef4444"
                node.score = 15
                node.analysis_comment = (
                    f"错失当回合斩杀绝杀机会！AI推演可造成 {node.lethal_damage} 点爆发伤害，"
                    f"敌方仅剩 {node.enemy_hp} 血，未能当回合终结对局导致战局被动拖后！"
                )
                blunder_count += 1
                if first_blunder_turn == 1:
                    first_blunder_turn = node.turn_number
                continue

            # 2. Lethal Execution Brilliant
            if node.had_lethal and is_win and idx == total_turns - 1:
                node.action_grade = "★ 妙手 (Brilliant)"
                node.grade_color = "#06b6d4"
                node.score = 100
                node.analysis_comment = f"算无遗策！精准计算并倾泻 {node.lethal_damage} 点斩杀伤害，一击穿透防线锁定胜局！"
                brilliant_count += 1
                continue

            # 3. Blunder Shield Operational Sequence Violations
            if node.blunder_alerts:
                node.action_grade = "❌ 严重伏笔 (Blunder)"
                node.grade_color = "#ef4444"
                node.score = 25
                node.analysis_comment = f"触犯核心操作时序禁忌：{node.blunder_alerts[0]}"
                blunder_count += 1
                if first_blunder_turn == 1:
                    first_blunder_turn = node.turn_number
                continue

            # 4. Inaccuracy - Heavy Mana Wastage (Floating Mana >= 3)
            if node.floating_mana >= 3 and len(node.hand_cards) >= 3:
                node.action_grade = "⚠️ 疑问手 (Inaccuracy)"
                node.grade_color = "#f97316"
                node.score = 45
                node.analysis_comment = (
                    f"法力利用率严重偏低，本回合白白浪费了 {node.floating_mana} 点法力水晶未打出可用手牌，"
                    f"节奏被动延后给对手喘息机会。"
                )
                inaccuracy_count += 1
                continue

            # 5. Brilliant Control or High Winrate Swing
            if node.ai_winrate >= 80.0 and node.ai_ev >= 25.0:
                node.action_grade = "★ 妙手 (Brilliant)"
                node.grade_color = "#06b6d4"
                node.score = 100
                node.analysis_comment = "全场压制推演！以极高期望值稳固场面主动，全局胜率攀升至80%以上！"
                brilliant_count += 1
                continue

            # 6. Best Play
            if (node.player_actual_plays and node.ai_best_plan and
                    any(node.player_actual_plays[0] in step for step in node.ai_best_plan[:2])):
                node.action_grade = "✅ 最佳 (Best)"
                node.grade_color = "#10b981"
                node.score = 100
                node.analysis_comment = "完全契合AI最优推演路线，精准控场换怪，兼顾法力利用与血量压制。"
                best_count += 1
                continue

            # 7. Good Play default
            node.action_grade = "⚖️ 良好 (Good)"
            node.grade_color = "#38bdf8"
            node.score = 80
            node.analysis_comment = "出牌平稳顺滑，维持了基本对攻与水晶倾泻节奏。"
            good_count += 1

        total_score = sum(n.score for n in turn_snapshots)
        avg_accuracy = round(total_score / max(total_turns, 1), 1)

        if avg_accuracy >= 90.0:
            tier = "S (大师水准)"
        elif avg_accuracy >= 78.0:
            tier = "A (优秀发挥)"
        elif avg_accuracy >= 65.0:
            tier = "B (良好·有瑕疵)"
        else:
            tier = "C (存在严重失误)"

        return MatchReplaySummary(
            result=result,
            total_turns=total_turns,
            overall_accuracy_pct=avg_accuracy,
            grade_tier=tier,
            brilliant_count=brilliant_count,
            best_count=best_count,
            good_count=good_count,
            inaccuracy_count=inaccuracy_count,
            blunder_count=blunder_count,
            turn_nodes=turn_snapshots,
            key_turning_turn=first_blunder_turn,
        )

    @classmethod
    def generate_sample_replay(cls) -> MatchReplaySummary:
        """Generates a realistic multi-turn sample match replay for testing and instant demonstration."""
        snapshots = [
            TurnReviewNode(
                turn_number=1,
                mana=1,
                max_mana=1,
                friendly_hp=30,
                enemy_hp=30,
                hand_cards=["叫嚣的中士", "恐狼先锋", "火球术"],
                friendly_board=[],
                enemy_board=[],
                ai_best_plan=["打出 叫嚣的中士 站场施压"],
                player_actual_plays=["打出 叫嚣的中士"],
                ai_ev=3.5,
                ai_winrate=52.0,
            ),
            TurnReviewNode(
                turn_number=2,
                mana=2,
                max_mana=2,
                friendly_hp=30,
                enemy_hp=28,
                hand_cards=["恐狼先锋", "寒冰箭", "火球术"],
                friendly_board=["叫嚣的中士 (2/1)"],
                enemy_board=["精灵弓箭手 (1/1)"],
                ai_best_plan=["叫嚣走脸 ➔ 打出 恐狼先锋 (占领中位)"],
                player_actual_plays=["叫嚣走脸", "使用 英雄技能 补刀精灵弓箭手"],
                ai_ev=5.2,
                ai_winrate=54.5,
            ),
            TurnReviewNode(
                turn_number=3,
                mana=3,
                max_mana=3,
                friendly_hp=30,
                enemy_hp=26,
                hand_cards=["寒冰箭", "麦田傀儡", "火球术"],
                friendly_board=["叫嚣的中士 (2/1)"],
                enemy_board=["淡水鳄 (2/3)"],
                floating_mana=3,
                ai_best_plan=["打出 麦田傀儡 扎实战场", "叫嚣解掉淡水鳄 (换怪保节奏)"],
                player_actual_plays=["空过回合"],
                ai_ev=2.0,
                ai_winrate=48.0,
            ),
            TurnReviewNode(
                turn_number=4,
                mana=4,
                max_mana=4,
                friendly_hp=28,
                enemy_hp=26,
                hand_cards=["寒冰箭", "水元素", "火球术"],
                friendly_board=[],
                enemy_board=["淡水鳄 (2/3)", "血沼黑嘴蜥 (3/2)"],
                blunder_alerts=["严禁在打出法术后再抽牌！时序错误将错失当回合解场最优解"],
                ai_best_plan=["打出 水元素 站场护脸"],
                player_actual_plays=["寒冰箭点脸", "抽牌"],
                ai_ev=4.0,
                ai_winrate=45.0,
            ),
            TurnReviewNode(
                turn_number=5,
                mana=5,
                max_mana=5,
                friendly_hp=25,
                enemy_hp=22,
                hand_cards=["火球术", "麦田傀儡", "寒冰箭"],
                friendly_board=["水元素 (3/6)"],
                enemy_board=["森金持盾卫士 (3/5 嘲讽)"],
                ai_best_plan=["水元素白吃森金 ➔ 打出 麦田傀儡"],
                player_actual_plays=["水元素白吃森金", "打出 麦田傀儡"],
                ai_ev=12.5,
                ai_winrate=62.0,
            ),
            TurnReviewNode(
                turn_number=6,
                mana=6,
                max_mana=6,
                friendly_hp=25,
                enemy_hp=10,
                hand_cards=["火球术", "寒冰箭", "冰枪术"],
                friendly_board=["水元素 (3/6)", "麦田傀儡 (2/3)"],
                enemy_board=[],
                had_lethal=True,
                lethal_damage=15,
                ai_best_plan=["火球术走脸 (6伤) ➔ 寒冰箭走脸 (3伤) ➔ 随从全军走脸 (5伤) ➔ 斩杀终结！"],
                player_actual_plays=["火球术走脸", "寒冰箭走脸", "全军走脸"],
                ai_ev=35.0,
                ai_winrate=100.0,
            ),
        ]
        return cls.analyze_replay(result="WIN", turn_snapshots=snapshots)
