"""
Tactical Setup & Baiting Planner (做局诱敌与两回合前置战术规划器)
- Damage Preparation Lines (修血铺垫): pre-damaging high-health minions to align with next turn's sweepers/burn.
- Removal Baiting Lines (钓鱼诱解): deliberately deploying high-threat pseudo-cores to extract hard removals before key Titans/finishers.
- Multi-turn payoff sequencing.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class SetupCategory(str, Enum):
    DAMAGE_PREPARATION = "DAMAGE_PREPARATION"  # 修血铺垫: 提前压低血量契合下回合AOE/法术
    BAIT_REMOVAL = "BAIT_REMOVAL"              # 钓鱼诱解: 伪核骗解，为下回合核心大哥铺路
    MANA_BANK_SETUP = "MANA_BANK_SETUP"        # 费用储备: 留币或蓄力为下回合高爆发做局


@dataclass
class SetupStep:
    turn_offset: int  # 0: 本回合 (T0), 1: 下回合 (T+1)
    action_type: str  # ATTACK, PLAY_CARD, HOLD_COIN
    card_or_minion_name: str
    target_name: Optional[str] = None
    intent: str = ""


@dataclass
class TacticalSetupPlan:
    category: SetupCategory
    name: str
    confidence_score: float
    t0_action_description: str
    t1_payoff_description: str
    expected_tempo_gain: float
    steps: List[SetupStep] = field(default_factory=list)
    summary_markdown: str = ""


class TacticalSetupPlanner:
    """
    Identifies 2-turn proactive tactical setup lines.
    """

    KNOWN_SWEEPERS = {
        "烈焰风暴": {"dmg": 4, "cost": 7, "target": "ALL_ENEMY"},
        "横扫": {"dmg": 4, "cost": 4, "target": "SINGLE_PLUS_SPLASH"},
        "奉献": {"dmg": 2, "cost": 4, "target": "ALL_ENEMY"},
        "地狱烈焰": {"dmg": 3, "cost": 4, "target": "ALL"},
        "暴风雪": {"dmg": 2, "cost": 6, "target": "ALL_ENEMY"},
        "神圣新星": {"dmg": 2, "cost": 4, "target": "ALL_ENEMY"},
        "闪电风暴": {"dmg": 3, "cost": 3, "target": "ALL_ENEMY"},
    }

    BAIT_TARGETS = {
        "布莱恩·铜须", "火妖", "拍卖师", "贪婪的伴侣", "加基森拍卖师",
        "奥能水母", "末日预言者", "随从军官"
    }

    CORE_FINISHERS = {
        "阿曼苏尔", "提里奥·弗丁", "萨弗拉斯", "艾萨拉女王", "灭世者萨格拉斯",
        "生命阿莱克丝塔萨", "泰坦", "巨型", "尤格-萨隆"
    }

    @classmethod
    def plan_setup_lines(
        cls,
        friendly_board: List[Dict[str, Any]],
        enemy_board: List[Dict[str, Any]],
        friendly_hand: List[str],
        current_mana: int,
        next_turn_mana: int,
    ) -> List[TacticalSetupPlan]:
        """
        Scans board and hand to construct high-EV multi-turn setup lines.
        """
        plans: List[TacticalSetupPlan] = []

        # 1. Damage Preparation Lines (修血铺垫)
        # Check if hand has a sweeper/burst playable next turn
        for card in friendly_hand:
            for sweeper_name, info in cls.KNOWN_SWEEPERS.items():
                if sweeper_name in card and next_turn_mana >= info["cost"]:
                    sweeper_dmg = info["dmg"]
                    # Find enemy minions with health > sweeper_dmg but <= sweeper_dmg + friendly_attack
                    for em in enemy_board:
                        e_hp = em.get("health", 0)
                        e_name = em.get("name", "敌方随从")
                        if sweeper_dmg < e_hp <= (sweeper_dmg + 3):
                            needed_chip = e_hp - sweeper_dmg
                            # Check if friendly minion can chip without dying or with minimal trade
                            for fm in friendly_board:
                                f_atk = fm.get("attack", 0)
                                f_name = fm.get("name", "我方随从")
                                if f_atk >= needed_chip and fm.get("can_attack", True):
                                    plan = TacticalSetupPlan(
                                        category=SetupCategory.DAMAGE_PREPARATION,
                                        name=f"修血做局：【{f_name}】压制【{e_name}】契合下回合【{sweeper_name}】",
                                        confidence_score=88.0,
                                        t0_action_description=f"使用【{f_name}】攻击【{e_name}】打掉 {f_atk} 点血量，将其修至 {e_hp - f_atk} 血。",
                                        t1_payoff_description=f"下回合准时打出【{sweeper_name}】（造成 {sweeper_dmg} 点伤害），即可完美清场不留残余！",
                                        expected_tempo_gain=4.5,
                                        steps=[
                                            SetupStep(
                                                turn_offset=0,
                                                action_type="ATTACK",
                                                card_or_minion_name=f_name,
                                                target_name=e_name,
                                                intent=f"修血铺垫，使敌方血量降至 {e_hp - f_atk} 血",
                                            ),
                                            SetupStep(
                                                turn_offset=1,
                                                action_type="PLAY_CARD",
                                                card_or_minion_name=sweeper_name,
                                                target_name="全场/主目标",
                                                intent="准时收割清场",
                                            ),
                                        ],
                                        summary_markdown=f"🎯 **提前两回合修血做局**：当前用【{f_name}】打掉【{e_name}】血量，下回合【{sweeper_name}】全清收割！",
                                    )
                                    plans.append(plan)
                                    break

        # 2. Bait Removal Lines (钓鱼诱解)
        # Check if we have a core finisher in hand for next turn, and a bait minion in hand for this turn
        finisher_in_hand = [c for c in friendly_hand if any(k in c for k in cls.CORE_FINISHERS)]
        bait_in_hand = [c for c in friendly_hand if any(k in c for k in cls.BAIT_TARGETS)]

        if finisher_in_hand and bait_in_hand and current_mana >= 2:
            f_card = finisher_in_hand[0]
            b_card = bait_in_hand[0]
            plan = TacticalSetupPlan(
                category=SetupCategory.BAIT_REMOVAL,
                name=f"诱敌做局：先下【{b_card}】骗解，为核心【{f_card}】扫清障碍",
                confidence_score=84.0,
                t0_action_description=f"本回合打出高仇恨伪核随从【{b_card}】，迫使对手交出硬解/沉默/伤害法术。",
                t1_payoff_description=f"下回合对手解牌空竭，安全打出核心【{f_card}】确立绝对胜势！",
                expected_tempo_gain=5.0,
                steps=[
                    SetupStep(
                        turn_offset=0,
                        action_type="PLAY_CARD",
                        card_or_minion_name=b_card,
                        target_name="我方场面",
                        intent="高威胁钓鱼伪核，诱骗敌方解牌",
                    ),
                    SetupStep(
                        turn_offset=1,
                        action_type="PLAY_CARD",
                        card_or_minion_name=f_card,
                        target_name="我方场面",
                        intent="对手解牌耗尽后安全打出核心大哥",
                    ),
                ],
                summary_markdown=f"🎣 **诱敌做局战术**：先下【{b_card}】钓出对手解牌，下回合核心【{f_card}】安全降临！",
            )
            plans.append(plan)

        # 3. Mana Bank Setup (留币垫费)
        if any("幸运币" in c for c in friendly_hand) and current_mana in (5, 6, 7):
            high_cost_finishers = [c for c in friendly_hand if any(k in c for k in cls.CORE_FINISHERS)]
            if high_cost_finishers:
                target_card = high_cost_finishers[0]
                plan = TacticalSetupPlan(
                    category=SetupCategory.MANA_BANK_SETUP,
                    name=f"控费做局：暂留【幸运币】，下回合跳费准时启动【{target_card}】",
                    confidence_score=80.0,
                    t0_action_description="本回合不贪图小额节奏交币，保留幸运币。",
                    t1_payoff_description=f"下回合拥有 {next_turn_mana + 1} 点法力水晶，提前 1 回合拍出终极核心【{target_card}】！",
                    expected_tempo_gain=3.5,
                    steps=[
                        SetupStep(
                            turn_offset=0,
                            action_type="HOLD_COIN",
                            card_or_minion_name="幸运币",
                            target_name=None,
                            intent="蓄力留费，避免低效跳费",
                        ),
                        SetupStep(
                            turn_offset=1,
                            action_type="PLAY_CARD",
                            card_or_minion_name=target_card,
                            target_name="我方场面",
                            intent="跳费降临核心随从",
                        ),
                    ],
                    summary_markdown=f"💎 **蓄费做局**：本回合按费运营保留硬币，下回合跳币准时出【{target_card}】！",
                )
                plans.append(plan)

        return plans
