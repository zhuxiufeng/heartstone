"""
TokenInspector: High-Definition Tokens, Titan Abilities, and Derivative Cards Inspector.
Allows players to hover or query tokens, appendages, and signatures for complex cards in Arena.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("TokenInspector")


@dataclass
class TokenInfo:
    name: str
    cost: int
    attack: Optional[int]
    health: Optional[int]
    card_type: str              # "MINION", "SPELL", "TITAN_ABILITY", "WEAPON"
    text: str
    token_category: str         # "TITAN", "COLOSSAL", "TOKEN", "FORGE"


# Signature Titan Abilities and Major Colossals / Token generators
SIGNATURE_TOKENS: Dict[str, List[TokenInfo]] = {
    # 阿曼苏尔 (Aman'Thul) - Priest Titan
    "TTN_903": [
        TokenInfo("清除异端", 0, None, None, "TITAN_ABILITY", "选择两个非泰坦敌方随从，将其移出对战。", "TITAN"),
        TokenInfo("塑造生命", 0, None, None, "TITAN_ABILITY", "发现一张传说随从牌。使其获得+2/+2并具有吸血。", "TITAN"),
        TokenInfo("目睹创生", 0, None, None, "TITAN_ABILITY", "召唤一个具有嘲讽的6/6并复制阿曼苏尔。", "TITAN"),
    ],
    # 萨格拉斯，毁灭者 (Sargeras, the Destroyer) - Warlock Titan
    "TTN_960": [
        TokenInfo("送入虚空", 0, None, None, "TITAN_ABILITY", "将所有其他随从送入扭曲虚空。", "TITAN"),
        TokenInfo("地狱火！", 0, None, None, "TITAN_ABILITY", "从扭曲虚空中召唤两个6/6的地狱火。", "TITAN"),
        TokenInfo("军团入侵！", 0, None, None, "TITAN_ABILITY", "在每个回合结束时从扭曲虚空中召唤两个3/2并具有突袭的小鬼。", "TITAN"),
    ],
    # 诺甘农 (Norgannon) - Mage Titan
    "TTN_075": [
        TokenInfo("原初奥秘", 0, None, None, "TITAN_ABILITY", "施放1个随机法师奥秘（本局每用过一次技能翻倍）。", "TITAN"),
        TokenInfo("古代知识", 0, None, None, "TITAN_ABILITY", "下回合敌方所有手牌法力消耗增加(1)点（每次技能翻倍）。", "TITAN"),
        TokenInfo("无尽潜能", 0, None, None, "TITAN_ABILITY", "造成5点伤害（每次技能翻倍）。", "TITAN"),
    ],
    # 兵主 (The Primus) - Death Knight Titan
    "TTN_737": [
        TokenInfo("符文凋零", 0, None, None, "TITAN_ABILITY", "消灭一个敌方随从。兵主与友方英雄获得其生命值。", "TITAN"),
        TokenInfo("冰霜之触", 0, None, None, "TITAN_ABILITY", "造成3点伤害，随机冻结3个敌方随从，抽一张牌。", "TITAN"),
        TokenInfo("鲜血之沸", 0, None, None, "TITAN_ABILITY", "使所有敌方随从获得-2/-2，恢复等量生命值。", "TITAN"),
    ],
    # 阿格拉玛，复仇者 (Aggramar, the Avenger) - Hunter Titan
    "TTN_092": [
        TokenInfo("迅捷斩击", 0, None, None, "TITAN_ABILITY", "泰坦之剑获得+2攻击力，你的英雄进行攻击时不承受伤害。", "TITAN"),
        TokenInfo("坚守战线", 0, None, None, "TITAN_ABILITY", "泰坦之剑获得+1生命值，召唤一个3/3具有嘲讽的石像。", "TITAN"),
        TokenInfo("全力突击", 0, None, None, "TITAN_ABILITY", "泰坦之剑获得+2攻击力，抽一张牌。", "TITAN"),
    ],
    # 奈利，巨鲸号 (Nellie, the Great Thresher) - Warrior Colossal
    "TSC_660": [
        TokenInfo("奈利的船尾", 1, 5, 5, "COLOSSAL", "巨型+1。亡语：将奈利的海盗加入手牌，其法力值消耗减少(1)点。", "COLOSSAL"),
    ],
    # 可拉巴托亚 (Crabatoa) - Rogue Colossal
    "TSC_086": [
        TokenInfo("可拉巴托亚的巨螯 (左)", 1, 2, 1, "COLOSSAL", "巨型+2。亡语：为可拉巴托亚装备2/1大鳌武器。", "COLOSSAL"),
        TokenInfo("可拉巴托亚的巨螯 (右)", 1, 2, 1, "COLOSSAL", "巨型+2。亡语：可拉巴托亚获得+2攻击力。", "COLOSSAL"),
    ],
    # 盖亚，机械巨龙 (Gaia, the Techtonic) - Mage Colossal
    "TSC_029": [
        TokenInfo("盖亚的钻头", 2, 2, 3, "COLOSSAL", "巨型+2。突袭。机械随从攻击后对所有敌人造成1点伤害。", "COLOSSAL"),
    ],
}


class TokenInspector:
    """Inspector providing fast O(1) lookup of token and titan sub-cards."""

    @classmethod
    def get_tokens(cls, card_id: str, card_name: str = "") -> List[TokenInfo]:
        """Returns tokens for card by ID or name matching."""
        if card_id in SIGNATURE_TOKENS:
            return SIGNATURE_TOKENS[card_id]

        # Name fallback heuristics
        name_lower = card_name.lower()
        if "阿曼苏尔" in name_lower:
            return SIGNATURE_TOKENS["TTN_903"]
        if "萨格拉斯" in name_lower:
            return SIGNATURE_TOKENS["TTN_960"]
        if "诺甘农" in name_lower:
            return SIGNATURE_TOKENS["TTN_075"]
        if "兵主" in name_lower:
            return SIGNATURE_TOKENS["TTN_737"]
        if "阿格拉玛" in name_lower:
            return SIGNATURE_TOKENS["TTN_092"]
        if "奈利" in name_lower:
            return SIGNATURE_TOKENS["TSC_660"]
        if "可拉巴托亚" in name_lower:
            return SIGNATURE_TOKENS["TSC_086"]
        if "盖亚" in name_lower:
            return SIGNATURE_TOKENS["TSC_029"]

        return []

    @classmethod
    def format_token_summary(cls, card_id: str, card_name: str = "") -> str:
        """Returns compact multi-line summary of tokens."""
        tokens = cls.get_tokens(card_id, card_name)
        if not tokens:
            return ""

        lines = [f"🌟 【衍生物/技能推演 ({len(tokens)})】:"]
        for t in tokens:
            stats = f" ({t.attack}/{t.health})" if t.attack is not None else ""
            lines.append(f"• **{t.name}**{stats} [{t.token_category}]: {t.text}")
        return "\n".join(lines)
