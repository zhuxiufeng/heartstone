"""
Cross-TCG Universal Theory Engine (跨界卡牌博弈哲学与通用元定理迁移)
- Synthesizes foundational axioms across Magic: The Gathering (MTG), Yu-Gi-Oh!, and Shadowverse.
- Tripartite TCG Axioms:
  1. Tempo Initiative Axiom (先攻节奏权公理 - MTG): Board initiative compounds quadratically.
  2. Card Entropy Axiom (卡牌资源熵增模型 - Yu-Gi-Oh!): Differential card advantage determines inevitability.
  3. Life as Resource Axiom (生命资源代偿公理 - Shadowverse/MTG): Any health > 0 is purely fuel for tempo.
- Transforms raw Hearthstone board states into master-class philosophical strategy directives.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class TCGAxiomType(str, Enum):
    TEMPO_INITIATIVE = "TEMPO_INITIATIVE"        # 先攻节奏权公理 (来自万智牌)
    CARD_ENTROPY = "CARD_ENTROPY"                # 卡牌资源熵增模型 (来自游戏王)
    LIFE_AS_RESOURCE = "LIFE_AS_RESOURCE"        # 生命资源代偿公理 (来自影之诗/万智牌)


@dataclass
class UniversalTheoryReport:
    dominant_axiom: TCGAxiomType
    axiom_title: str
    origin_game: str
    tempo_vs_value_balance: float  # -1.0 (纯节奏抢攻) ~ +1.0 (纯资源熵增)
    life_as_fuel_efficiency: float # 0.0 ~ 1.0
    philosophical_doctrine: str
    tactical_execution_directive: str
    summary_markdown: str


class UniversalTcgTheoryEngine:
    """
    Applies universal competitive trading-card meta-theorems to Hearthstone play.
    """

    @classmethod
    def evaluate_board_philosophy(
        cls,
        player_hp: int,
        enemy_hp: int,
        my_board_mana_value: int,
        enemy_board_mana_value: int,
        my_hand_count: int,
        enemy_hand_count: int,
    ) -> UniversalTheoryReport:
        """
        Calculates the underlying meta-philosophical posture of the current board.
        """
        # Board mana advantage (Tempo)
        tempo_diff = my_board_mana_value - enemy_board_mana_value
        # Hand card advantage (Value)
        card_diff = my_hand_count - enemy_hand_count

        # Compute balance: -1.0 (pure tempo rush) to +1.0 (pure resource value)
        balance = round((card_diff * 0.2) - (tempo_diff * 0.15), 2)
        balance = max(-1.0, min(1.0, balance))

        # Life as fuel: if HP > 15, life can be aggressively used to buy board/cards
        life_fuel = round(min(1.0, max(0.0, (player_hp - 10) / 20.0)), 2)

        # Classify dominant axiom
        if tempo_diff >= 4 or enemy_hp <= 15:
            axiom = TCGAxiomType.TEMPO_INITIATIVE
            title = "⚡ 先攻节奏权公理 (Tempo Initiative Axiom)"
            origin = "万智牌 (Magic: The Gathering)"
            doctrine = "“先攻支配战场，费用转化为场攻的效率，决定了生死的钟摆。”"
            directive = (
                f"我方场面战力价值领先对手 {tempo_diff} 费！"
                "当前对局重心为【节奏压迫】：切勿为了贪图过牌而放弃站场，全速将场攻转化为对敌方血线的终结压力。"
            )
        elif player_hp >= 20 and card_diff <= -2:
            axiom = TCGAxiomType.LIFE_AS_RESOURCE
            title = "🩸 生命资源代偿公理 (Life as Resource Axiom)"
            origin = "影之诗 / 万智牌经典黑塔哲学"
            doctrine = "“30点生命与1点生命在本质上无异，只要未至斩杀，血量便是换取卡牌与场面的廉价燃料。”"
            directive = (
                f"我方生命值高达 {player_hp} 血，处于安全防区。"
                "当前战略重心为【卖血换牌】：可用英雄脸部主动接下敌方小伤害，留存关键解牌与法力，换取后续长线资源翻盘。"
            )
        else:
            axiom = TCGAxiomType.CARD_ENTROPY
            title = "📜 卡牌资源熵增模型 (Card Entropy Axiom)"
            origin = "游戏王 (Yu-Gi-Oh! +1 Card Advantage)"
            doctrine = "“一切场面皆可被重置，唯有绝对手牌净差，方能在资源消耗的终局奠定必然胜势。”"
            directive = (
                f"当前手牌差为 {card_diff:+d} 张。"
                "当前战略重心为【卡差置换】：优先执行 1 换 2 或白吃互换，诱导对手过度铺场进入我方解牌射程。"
            )

        md = (
            f"**跨界 TCG 元定理通用哲学博弈报告**:\n"
            f"• **主导公理**: **{title}** (源自: {origin})\n"
            f"• **博弈箴言**: *{doctrine}*\n"
            f"• **宏观平衡度**: 节奏抢占 vs 资源熵增 = {balance:+.2f} | 卖血代偿指数: {life_fuel:.2f}\n"
            f"• **战略哲学指引**: {directive}"
        )

        return UniversalTheoryReport(
            dominant_axiom=axiom,
            axiom_title=title,
            origin_game=origin,
            tempo_vs_value_balance=balance,
            life_as_fuel_efficiency=life_fuel,
            philosophical_doctrine=doctrine,
            tactical_execution_directive=directive,
            summary_markdown=md,
        )
