"""
OpponentArchetypeClassifier: Real-time Opponent Archetype and Deck Identification.
Tracks cards played by the opponent during combat to classify their arena deck archetype
and formulate real-time counter-strategies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

logger = logging.getLogger("ArchetypeClassifier")


@dataclass
class ArchetypeMatchReport:
    archetype_name: str
    confidence_pct: int
    tactical_profile: str
    strategic_counter: str
    key_cards_seen: List[str] = field(default_factory=list)
    posterior_probabilities: Dict[str, float] = field(default_factory=dict)
    aoe_threat_probability_pct: int = 35
    burn_threat_probability_pct: int = 30
    removal_threat_probability_pct: int = 40
    bayesian_dossier_text: str = ""


# Archetype definitions for all 11 classes with signature keywords and card names
CLASS_ARCHETYPES: Dict[str, List[Dict]] = {
    "MAGE": [
        {
            "name": "法强直伤法 (Spell Burn)",
            "keywords": ["法术伤害", "火球", "寒冰箭", "制造余震", "奥术箭袋", "奥术飞弹", "烈焰风暴", "法力浮龙"],
            "profile": "依赖法强随从与直伤法术斩杀，随从防守能力偏弱",
            "counter": "时刻保持血量 ≥ 15，优先清理敌方法强随从，全员铺场抢先击杀！",
        },
        {
            "name": "元素铺场法 (Elemental Tempo)",
            "keywords": ["元素", "熔岩", "自燃", "火元素", "流水"],
            "profile": "每回合按费连环拍元素生物，依靠场面滚雪球",
            "counter": "每回合断其元素随从节奏，不留杂毛，迫使其断连击！",
        },
        {
            "name": "控制资源法 (Control Resource)",
            "keywords": ["暴风雪", "变形术", "深度冻结", "巅峰无限", "倒带", "远古雕文"],
            "profile": "携带多张高费大解与资源衍生牌，擅长拖入大后期",
            "counter": "切忌被动拖后期，分散铺场防单解，压低其血量逼其空过交大招！",
        },
    ],
    "PALADIN": [
        {
            "name": "圣盾铺场骑 (Divine Shield Aggro)",
            "keywords": ["圣盾", "报告", "白银之手", "十字军光环", "正义保护者", "战马训练师"],
            "profile": "前期高频制造杂毛圣盾随从，中期依靠光环 Buff 一波斩杀",
            "counter": "优先用小怪或补刀破除圣盾，必须清理全部报告兵防十字军光环！",
        },
        {
            "name": "污手节奏骑 (Handbuff Midrange)",
            "keywords": ["手牌中的", "获得+", "亮石技师", "肌肉", "装甲"],
            "profile": "前期蓄能给手牌随从贴身材，中期连拍巨型身材随从",
            "counter": "抓住其前期下身材较亏的空档，全力抢脸施压，不要给其中期从容反扑的机会！",
        },
        {
            "name": "控制圣骑 (Control Paladin)",
            "keywords": ["生而平等", "奉献", "守日者", "圣光术", "提里奥"],
            "profile": "拥有经典双卡清场与高质量嘲讽大哥",
            "counter": "防范平等奉献一波清场，保留续航手牌，避免一波梭哈！",
        },
    ],
    "PRIEST": [
        {
            "name": "快攻暗牧 (Aggro Shadow Priest)",
            "keywords": ["暗影", "暗影形态", "心灵震爆", "虚触扈从", "亡语"],
            "profile": "前期 1-3 费高攻随从疯狂走脸，依靠技能每回合打 2-3 直伤",
            "counter": "全力架嘲讽随从，控住场面后立刻回血，逼其将技能打向随从！",
        },
        {
            "name": "控场龙牧 (Dragon Control)",
            "keywords": ["龙", "圣光炸弹", "精神控制", "暗言术", "真言术"],
            "profile": "优质龙族协同身材与单体大解，后期拉大哥翻盘",
            "counter": "随从攻击力保持 4 攻防灭，注意防范 6 费圣光炸弹！",
        },
    ],
    "WARLOCK": [
        {
            "name": "快攻动物园 (Zoo Swarm)",
            "keywords": ["烈焰小鬼", "小鬼", "虚空行者", "叫嚣", "恐狼", "残暴"],
            "profile": "低费随从快速铺满场面，配合增益卡以小换大",
            "counter": "严控敌方随从数量，即使亏身材也要清干净杂毛，防其贴皮增益！",
        },
        {
            "name": "控制恶魔术 (Control Demon)",
            "keywords": ["地狱烈焰", "亵渎", "扭曲虚空", "恶魔", "末日守卫"],
            "profile": "自残换手牌优势，拥有多阶全场清场法术",
            "counter": "随从血量做成不连续阶梯防亵渎，压制其血量使其不敢肆意分流抽牌！",
        },
    ],
    "DEATHKNIGHT": [
        {
            "name": "邪恶快攻死骑 (Unholy Swarm DK)",
            "keywords": ["残骸", "亡者大军", "尸体", "食尸鬼", "疫病"],
            "profile": "超高频铺杂毛，消耗残骸造成全场爆发与场面扩张",
            "counter": "优先解掉产尸生物，算准残骸消耗量，防范一波爆发斩杀！",
        },
        {
            "name": "鲜血控制死骑 (Blood Control DK)",
            "keywords": ["鲜血", "吸血", "莫格莱尼", "窒息", "吞噬"],
            "profile": "超强回血与解场能力，后期单卡质量极高",
            "counter": "抢脸节奏必须果断，不给其拖入血量上限提升的大后期！",
        },
    ],
    "HUNTER": [
        {
            "name": "野兽快攻猎 (Beast Face Hunter)",
            "keywords": ["野兽", "杀戮", "放狗", "关门放狗", "雷象", "突袭"],
            "profile": "所有资源专注于走脸压血，回合时钟极快",
            "counter": "优先架嘲讽护脸，清理野兽防杀戮命令 5 伤斩杀！",
        },
    ],
    "WARRIOR": [
        {
            "name": "激怒节奏战 (Enrage Tempo)",
            "keywords": ["受伤", "激怒", "暴乱狂战士", "旋风斩", "苦痛寺僧"],
            "profile": "随从受伤时触发高额攻击力或过牌收益",
            "counter": "不要给其随从留残血！若攻击必须一击必杀，切忌留下 1 血随从！",
        },
        {
            "name": "护甲防战 (Armor Control)",
            "keywords": ["护甲", "绝命乱斗", "盾牌猛击", "重击", "盾牌格挡"],
            "profile": "超高护甲积累，依靠乱斗与单解拖死对手",
            "counter": "保留 2-3 个核心攻击点即可，切勿全下防乱斗，持续制造每回合输出压力！",
        },
    ],
}


class OpponentArchetypeClassifier:
    """Classifies opponent's deck archetype based on observed plays."""

    def __init__(self, opponent_class: str = "UNKNOWN") -> None:
        self.opponent_class = opponent_class.upper().strip()
        self.played_cards: List[str] = []
        self._matched_archetype: Optional[ArchetypeMatchReport] = None

    def reset(self, opponent_class: str = "UNKNOWN") -> None:
        self.opponent_class = opponent_class.upper().strip()
        self.played_cards.clear()
        self._matched_archetype = None

    def record_card_played(self, card_name: str, card_text: str = "") -> None:
        """Records a card played by opponent to refine archetype classification."""
        if not card_name:
            return
        self.played_cards.append(card_name)

        # Re-evaluate archetype matching
        self._matched_archetype = self._evaluate_archetype()

    def _evaluate_archetype(self) -> ArchetypeMatchReport:
        c_key = "UNKNOWN"
        for k in CLASS_ARCHETYPES.keys():
            if k in self.opponent_class or self.opponent_class in k:
                c_key = k
                break

        if c_key == "UNKNOWN" or len(self.played_cards) < 2:
            return ArchetypeMatchReport(
                archetype_name="均势中速 (Midrange)",
                confidence_pct=45,
                tactical_profile="对局尚在初期，等待敌方展现构筑核心特征",
                strategic_counter="按费平滑拍怪，保持场面主动权与随从交换优势",
                key_cards_seen=list(self.played_cards),
                posterior_probabilities={"均势中速": 0.45, "其他流派": 0.55},
                aoe_threat_probability_pct=35,
                burn_threat_probability_pct=30,
                removal_threat_probability_pct=40,
                bayesian_dossier_text="样本不足(已出卡<2张)，采用竞技场基准中速先验分布。",
            )

        candidates = CLASS_ARCHETYPES[c_key]
        num_cands = len(candidates)
        # Uniform initial prior
        priors = [1.0 / num_cands] * num_cands
        likelihoods = [1.0] * num_cands

        all_text = " ".join(self.played_cards)

        matched_seen_map = {}
        for idx, cand in enumerate(candidates):
            c_name = cand["name"]
            matched_seen = []
            for card in self.played_cards:
                # Check if this card matches candidate's keywords
                matches = any(kw in card for kw in cand["keywords"])
                if matches:
                    likelihoods[idx] *= 0.85
                    matched_seen.append(card)
                else:
                    likelihoods[idx] *= 0.25
            matched_seen_map[c_name] = matched_seen

        # Compute unnormalized posterior
        unnorm = [priors[i] * likelihoods[i] for i in range(num_cands)]
        total_p = sum(unnorm)
        if total_p <= 0:
            posteriors = priors
        else:
            posteriors = [p / total_p for p in unnorm]

        # Find best candidate
        best_idx = max(range(num_cands), key=lambda i: posteriors[i])
        best_cand = candidates[best_idx]
        best_post = posteriors[best_idx]
        conf = max(40, min(98, int(best_post * 100)))

        post_dict = {candidates[i]["name"]: round(posteriors[i], 3) for i in range(num_cands)}

        # Archetype threat profiles (AOE, Burn, Removal)
        # Infer threat weights from archetype name & profile
        aoe_accum = 0.0
        burn_accum = 0.0
        removal_accum = 0.0
        for i, cand in enumerate(candidates):
            weight = posteriors[i]
            c_prof = cand["name"] + " " + cand["profile"]
            # AOE
            if "控制" in c_prof or "清场" in c_prof:
                aoe_accum += weight * 0.80
            elif "直伤" in c_prof or "中速" in c_prof:
                aoe_accum += weight * 0.35
            else:
                aoe_accum += weight * 0.15
            # Burn
            if "直伤" in c_prof or "快攻" in c_prof:
                burn_accum += weight * 0.85
            elif "节奏" in c_prof:
                burn_accum += weight * 0.40
            else:
                burn_accum += weight * 0.15
            # Removal
            if "控制" in c_prof:
                removal_accum += weight * 0.75
            elif "中速" in c_prof or "节奏" in c_prof:
                removal_accum += weight * 0.45
            else:
                removal_accum += weight * 0.20

        aoe_pct = min(95, max(10, int(aoe_accum * 100)))
        burn_pct = min(95, max(10, int(burn_accum * 100)))
        rem_pct = min(95, max(10, int(removal_accum * 100)))

        post_desc = " | ".join(f"{k.split(' ')[0]}: {int(v*100)}%" for k, v in post_dict.items())
        dossier = (
            f"贝叶斯流派后验分布: [{post_desc}] ➔ 判定为【{best_cand['name']}】(置信度 {conf}%)\n"
            f"动态威胁感知: AOE清场概率 {aoe_pct}% | 直伤斩杀概率 {burn_pct}% | 硬解威胁概率 {rem_pct}%"
        )

        return ArchetypeMatchReport(
            archetype_name=best_cand["name"],
            confidence_pct=conf,
            tactical_profile=best_cand["profile"],
            strategic_counter=best_cand["counter"],
            key_cards_seen=matched_seen_map.get(best_cand["name"], [])[:3],
            posterior_probabilities=post_dict,
            aoe_threat_probability_pct=aoe_pct,
            burn_threat_probability_pct=burn_pct,
            removal_threat_probability_pct=rem_pct,
            bayesian_dossier_text=dossier,
        )

    def get_current_report(self) -> ArchetypeMatchReport:
        if self._matched_archetype is None:
            self._matched_archetype = self._evaluate_archetype()
        return self._matched_archetype
