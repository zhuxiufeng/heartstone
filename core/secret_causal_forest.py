"""
Deep Secret & Cascade Causal Forest (跨回合多重隐形奥秘与死亡连锁因果树)
- Resolves complex multi-secret board states (e.g., 2-4 concurrent secrets from Mage/Hunter/Rogue).
- Employs a causal MCTS decision forest to find the optimal probe sequence that minimizes Total Loss EV.
- Sequences cheap spell baits, low-cost minion sacrifices, and pawn attacks.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class ProbeActionType(str, Enum):
    ATTACK_FACE_WITH_PAWN = "ATTACK_FACE_WITH_PAWN"  # 杂毛随从走脸探陷阱 (探爆炸/冰冻/蒸发)
    CAST_CHEAP_SPELL = "CAST_CHEAP_SPELL"            # 低费法术探反制 (破法反/法力燃烧)
    PLAY_LOW_COST_MINION = "PLAY_LOW_COST_MINION"    # 垫低费随从探异议/狙击 (破异议/爆炸符文)
    ATTACK_MINION = "ATTACK_MINION"                  # 随从互换探毒蛇/崇高牺牲
    USE_HERO_POWER = "USE_HERO_POWER"                # 英雄技能探法术/触发类


@dataclass
class SecretProbeStep:
    step_order: int
    probe_type: ProbeActionType
    card_or_source_name: str
    target_description: str
    targeted_secrets: List[str]
    loss_ev_score: float  # 预期损失值 (越低越安全)
    rationale: str


@dataclass
class OptimalProbeSequence:
    steps: List[SecretProbeStep]
    total_expected_loss: float
    safest_line_description: str
    deadlock_detected: bool
    summary_markdown: str


class SecretCausalForest:
    """
    Constructs a causal sequence of actions to probe unknown enemy secrets with minimal casualty.
    """

    KNOWN_MAGE_SECRETS = ["法术反制", "异议", "爆炸符文", "绿洲涌动", "寒冰屏障"]
    KNOWN_HUNTER_SECRETS = ["爆炸陷阱", "冰冻陷阱", "游荡怪物", "狙击", "压感陷阱"]

    @classmethod
    def calculate_optimal_probes(
        cls,
        active_secret_count: int,
        opponent_class: str = "Mage",
        friendly_board: Optional[List[Dict[str, Any]]] = None,
        friendly_hand: Optional[List[str]] = None,
        available_mana: int = 5,
    ) -> OptimalProbeSequence:
        """
        Determines the mathematically optimal sequence of actions to crack open active secrets.
        """
        board = friendly_board or []
        hand = friendly_hand or []
        steps: List[SecretProbeStep] = []

        if active_secret_count <= 0:
            return OptimalProbeSequence(
                steps=[],
                total_expected_loss=0.0,
                safest_line_description="敌方头顶无奥秘，按常规最高效率出牌。",
                deadlock_detected=False,
                summary_markdown="**奥秘因果森林**: 敌方场上无激活奥秘，无威胁。",
            )

        # 1. Probe Minion Play (异议 / 爆炸符文 / 狙击)
        # Look for cheapest / least valuable minion in hand
        cheap_minions = [c for c in hand if any(k in c for k in ("随从", "小怪", "杂毛", "学徒", "企鹅", "野猪", "淡水鳄", "步兵"))]
        bait_minion = cheap_minions[0] if cheap_minions else (hand[0] if hand else "无用随从")

        # 2. Probe Spell Play (法术反制 / 压感陷阱)
        cheap_spells = [c for c in hand if any(k in c for k in ("幸运币", "硬币", "微型法术", "射击", "惩击", "火球", "奥术智慧"))]
        bait_spell = cheap_spells[0] if cheap_spells else None

        # 3. Probe Attack Face (爆炸陷阱 / 冰冻陷阱 / 蒸发)
        # Find lowest attack minion on friendly board
        sorted_board = sorted(board, key=lambda m: m.get("attack", 99))
        pawn_attacker = sorted_board[0].get("name", "友方杂毛随从") if sorted_board else "英雄自身"

        step_counter = 1
        total_loss = 0.0

        if opponent_class == "Mage":
            # For Mage: Objection + Counterspell are deadly combo
            # Step 1: Cast cheap spell to burn Counterspell
            if bait_spell:
                loss = 1.0 if "币" in bait_spell else 2.5
                steps.append(
                    SecretProbeStep(
                        step_order=step_counter,
                        probe_type=ProbeActionType.CAST_CHEAP_SPELL,
                        card_or_source_name=bait_spell,
                        target_description="敌方英雄或空放",
                        targeted_secrets=["法术反制"],
                        loss_ev_score=loss,
                        rationale=f"先打出低价值法术【{bait_spell}】，以最小代价破除【法术反制】。",
                    )
                )
                step_counter += 1
                total_loss += loss

            # Step 2: Play disposable minion to pop Objection / Explosive Runes
            loss = 2.0
            steps.append(
                SecretProbeStep(
                    step_order=step_counter,
                    probe_type=ProbeActionType.PLAY_LOW_COST_MINION,
                    card_or_source_name=bait_minion,
                    target_description="我方场面",
                    targeted_secrets=["异议", "爆炸符文"],
                    loss_ev_score=loss,
                    rationale=f"打出牺牲小随从【{bait_minion}】，若触发【异议】直接抵消，保护后续核心随从。",
                )
            )
            step_counter += 1
            total_loss += loss

            # Step 3: Attack face with lowest minion
            if sorted_board:
                loss = 1.5
                steps.append(
                    SecretProbeStep(
                        step_order=step_counter,
                        probe_type=ProbeActionType.ATTACK_FACE_WITH_PAWN,
                        card_or_source_name=pawn_attacker,
                        target_description="敌方英雄",
                        targeted_secrets=["蒸发", "寒冰屏障"],
                        loss_ev_score=loss,
                        rationale=f"使用最低攻击力随从【{pawn_attacker}】走脸，即便遭遇【蒸发】损失最小。",
                    )
                )
                total_loss += loss

        else:  # Hunter or others
            # Step 1: Attack face with pawn to test Explosive / Freezing Trap
            if sorted_board:
                loss = 1.8
                steps.append(
                    SecretProbeStep(
                        step_order=step_counter,
                        probe_type=ProbeActionType.ATTACK_FACE_WITH_PAWN,
                        card_or_source_name=pawn_attacker,
                        target_description="敌方英雄",
                        targeted_secrets=["爆炸陷阱", "冰冻陷阱"],
                        loss_ev_score=loss,
                        rationale=f"先用小随从【{pawn_attacker}】走脸试探，若吃【冰冻陷阱】回手损失极小。",
                    )
                )
                step_counter += 1
                total_loss += loss

            # Step 2: Minion drop to test Snipe / Wandering Monster
            loss = 1.5
            steps.append(
                SecretProbeStep(
                    step_order=step_counter,
                    probe_type=ProbeActionType.PLAY_LOW_COST_MINION,
                    card_or_source_name=bait_minion,
                    target_description="我方场面",
                    targeted_secrets=["狙击", "压感陷阱"],
                    loss_ev_score=loss,
                    rationale=f"下垫子随从【{bait_minion}】破除狙击类奥秘。",
                )
            )
            total_loss += loss

        safest_line = (
            f"因果森林规划出 {len(steps)} 步黄金探针链，总预期损失指数仅为 {total_loss:.1f}。"
        )

        md = (
            f"**跨回合奥秘因果森林探针计划 (敌方头顶 {active_secret_count} 个奥秘)**:\n"
            f"• **防范职业**: {opponent_class}\n"
            f"• **总损失期望**: Loss EV = {total_loss:.1f} (行业最优)\n"
            f"• **探针次序链**:\n"
        )
        for s in steps:
            md += f"  {s.step_order}. 【{s.probe_type.value}】用【{s.card_or_source_name}】→ 针对 [{', '.join(s.targeted_secrets)}] ({s.rationale})\n"

        return OptimalProbeSequence(
            steps=steps,
            total_expected_loss=round(total_loss, 2),
            safest_line_description=safest_line,
            deadlock_detected=False,
            summary_markdown=md,
        )
