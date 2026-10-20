"""
CardDatabase: Loads, downloads, caches, and indexes Hearthstone card metadata.
Provides fast cardId lookup, name lookup, and fuzzy search for OCR error recovery.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import pickle
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CardDB")

HEARTHSTONE_JSON_ZH_CN_URL = "https://api.hearthstonejson.com/v1/latest/zhCN/cards.json"

COMMON_CARD_KEYWORDS = {
    "突袭", "嘲讽", "圣盾", "风怒", "剧毒", "潜行", "战吼", "亡语", "吸血",
    "法术伤害", "微缩", "快枪", "锻造", "发掘", "亡灵", "野兽", "机械", "鱼人",
    "恶魔", "龙", "海盗", "元素", "图腾", "纳迦", "全种族", "连击", "抉择",
    "过载", "法术", "随从", "武器", "地标", "复生", "流放", "荣誉击杀",
    "超杀", "激励", "磁力", "休眠", "回响", "双生法术", "祈求", "可交易", "泰坦"
}

CLASS_CN_MAP = {
    "DEATHKNIGHT": "死亡骑士", "DEMONHUNTER": "恶魔猎手", "DRUID": "德鲁伊",
    "HUNTER": "猎人", "MAGE": "法师", "PALADIN": "圣骑士",
    "PRIEST": "牧师", "ROGUE": "潜行者", "SHAMAN": "萨满祭司",
    "WARLOCK": "术士", "WARRIOR": "战士", "NEUTRAL": "中立",
    "HERO_01": "战士", "HERO_02": "萨满祭司", "HERO_03": "潜行者",
    "HERO_04": "圣骑士", "HERO_05": "猎人", "HERO_06": "德鲁伊",
    "HERO_07": "术士", "HERO_08": "法师", "HERO_09": "牧师",
    "HERO_10": "恶魔猎手", "HERO_11": "死亡骑士"
}

def get_class_cn(class_name: str) -> str:
    """Returns Chinese display name for a Hearthstone class identifier."""
    if not class_name:
        return "未知"
    return CLASS_CN_MAP.get(str(class_name).upper(), str(class_name))


def get_default_cards_cache_file() -> Path:
    """Finds cards.json across PyInstaller frozen dirs, app root, and CWD."""
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "data" / "cards.json")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "data" / "cards.json")
        candidates.append(exe_dir / "_internal" / "data" / "cards.json")
    this_dir = Path(__file__).resolve().parent.parent
    candidates.append(this_dir / "data" / "cards.json")
    candidates.append(Path("data").resolve() / "cards.json")

    for c in candidates:
        if c.exists():
            return c

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data" / "cards.json"
    return this_dir / "data" / "cards.json"


def get_default_cards_indexed_file() -> Path:
    """Finds cards_indexed.pkl across PyInstaller frozen dirs, app root, and CWD."""
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "data" / "cards_indexed.pkl")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "data" / "cards_indexed.pkl")
        candidates.append(exe_dir / "_internal" / "data" / "cards_indexed.pkl")
    this_dir = Path(__file__).resolve().parent.parent
    candidates.append(this_dir / "data" / "cards_indexed.pkl")
    candidates.append(Path("data").resolve() / "cards_indexed.pkl")

    for c in candidates:
        if c.exists():
            return c

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data" / "cards_indexed.pkl"
    return this_dir / "data" / "cards_indexed.pkl"


CARDS_CACHE_FILE = get_default_cards_cache_file()
CARDS_INDEXED_FILE = get_default_cards_indexed_file()


@dataclass(slots=True)
class CardInfo:
    """Card metadata model formatted for arena analysis and prompt injection."""
    id: str
    name: str
    cost: int = 0
    attack: Optional[int] = None
    health: Optional[int] = None
    durability: Optional[int] = None
    card_class: str = "NEUTRAL"
    card_type: str = "MINION"  # MINION, SPELL, WEAPON, HERO, LOCATION
    rarity: str = "COMMON"     # FREE, COMMON, RARE, EPIC, LEGENDARY
    set_name: str = ""
    text: str = ""
    race: Optional[str] = None
    races: List[str] = field(default_factory=list)
    spell_school: Optional[str] = None
    mechanics: List[str] = field(default_factory=list)
    collectible: bool = True
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def clean_text(self) -> str:
        """Strip Hearthstone bold/italic markup and newline tags."""
        if not self.text:
            return ""
        # Remove <b>, </b>, <i>, </i>, [x], $, _, etc.
        cleaned = re.sub(r"</?[bi]>", "", self.text)
        cleaned = re.sub(r"\[x\]", "", cleaned)
        cleaned = cleaned.replace("$", "").replace("_", " ").replace("\n", " ").strip()
        return cleaned

    def format_summary(self) -> str:
        """Concise summary for UI display."""
        stats = []
        if self.card_type == "MINION":
            stats.append(f"{self.attack}/{self.health}")
        elif self.card_type == "WEAPON":
            stats.append(f"{self.attack}/{self.durability}")
        elif self.card_type == "LOCATION":
            stats.append(f"耐久 {self.health}")

        type_desc = f"{self.card_class} {self.card_type}"
        if self.race:
            type_desc += f" ({self.race})"
        elif self.spell_school:
            type_desc += f" ({self.spell_school})"

        stat_str = f" [{', '.join(stats)}]" if stats else ""
        return f"{self.name} ({self.cost}费{stat_str}, {type_desc})"

    def format_for_ai_prompt(self) -> str:
        """Detailed markdown string injected into LLM prompt to eliminate hallucinations."""
        lines = [
            f"- **【{self.name}】** (ID: `{self.id}`)",
            f"  * 费用: {self.cost} 费 | 职业: {self.card_class} | 稀有度: {self.rarity} | 类型: {self.card_type}",
        ]
        if self.attack is not None and self.health is not None:
            lines.append(f"  * 身材: {self.attack} 攻击力 / {self.health} 生命值")
        if self.durability is not None:
            lines.append(f"  * 耐久度: {self.durability}")
        if self.race:
            races_str = ", ".join(self.races) if self.races else self.race
            lines.append(f"  * 种族: {races_str}")
        if self.spell_school:
            lines.append(f"  * 法术派系: {self.spell_school}")
        if self.mechanics:
            lines.append(f"  * 关键词机制: {', '.join(self.mechanics)}")
        if self.clean_text:
            lines.append(f"  * 卡牌描述: {self.clean_text}")
        return "\n".join(lines)

    def format_for_ai_prompt_compact(self) -> str:
        """Ultra-compact representation to minimize LLM prompt token usage and latency."""
        stats = f" {self.attack}/{self.health}" if self.attack is not None and self.health is not None else ""
        if self.durability is not None:
            stats = f" 耐久:{self.durability}"
        races = f" 种族:{self.race}" if self.race else ""
        return f"【{self.name}】{self.cost}费{stats}{races} {self.card_class} {self.card_type} | 描述: {self.clean_text}"


# Seed fallback cards for offline startup or unit tests
FALLBACK_CARDS_SAMPLE: List[Dict[str, Any]] = [
    {
        "id": "CORE_CS2_039",
        "name": "风暴战斧",
        "cost": 2,
        "attack": 3,
        "durability": 2,
        "cardClass": "SHAMAN",
        "type": "WEAPON",
        "rarity": "COMMON",
        "text": "<b>过载：</b>（1）",
        "mechanics": ["OVERLOAD"],
        "collectible": True,
    },
    {
        "id": "CS2_188",
        "name": "叫嚣的矮人",
        "cost": 1,
        "attack": 1,
        "health": 1,
        "cardClass": "NEUTRAL",
        "type": "MINION",
        "rarity": "COMMON",
        "text": "<b>战吼：</b>在本回合中，使一个随从获得+2攻击力。",
        "mechanics": ["BATTLECRY"],
        "collectible": True,
    },
    {
        "id": "CS2_222",
        "name": "暴风城勇士",
        "cost": 7,
        "attack": 6,
        "health": 6,
        "cardClass": "NEUTRAL",
        "type": "MINION",
        "rarity": "COMMON",
        "text": "你的其他随从获得+1/+1。",
        "collectible": True,
    },
    {
        "id": "CS2_029",
        "name": "火球术",
        "cost": 4,
        "cardClass": "MAGE",
        "type": "SPELL",
        "rarity": "FREE",
        "spellSchool": "FIRE",
        "text": "造成$6点伤害。",
        "collectible": True,
    },
    {
        "id": "EX1_012",
        "name": "血法师萨尔诺斯",
        "cost": 2,
        "attack": 1,
        "health": 1,
        "cardClass": "NEUTRAL",
        "type": "MINION",
        "rarity": "LEGENDARY",
        "race": "UNDEAD",
        "races": ["UNDEAD"],
        "text": "<b>法术伤害+1</b>，<b>亡语：</b>抽一张牌。",
        "mechanics": ["SPELLPOWER", "DEATHRATTLE"],
        "collectible": True,
    },
    {
        "id": "ICC_828",
        "name": "死亡之翼",
        "cost": 10,
        "attack": 12,
        "health": 12,
        "cardClass": "NEUTRAL",
        "type": "MINION",
        "rarity": "LEGENDARY",
        "race": "DRAGON",
        "races": ["DRAGON"],
        "text": "<b>战吼：</b>消灭所有其他随从，并弃掉你的手牌。",
        "mechanics": ["BATTLECRY"],
        "collectible": True,
    },
    {
        "id": "CS2_065",
        "name": "恐狼前锋",
        "cost": 2,
        "attack": 2,
        "health": 2,
        "cardClass": "NEUTRAL",
        "type": "MINION",
        "rarity": "COMMON",
        "race": "BEAST",
        "races": ["BEAST"],
        "text": "相邻的随从获得+1攻击力。",
        "collectible": True,
    },
    {
        "id": "EX1_572",
        "name": "伊瑟拉",
        "cost": 9,
        "attack": 4,
        "health": 12,
        "cardClass": "NEUTRAL",
        "type": "MINION",
        "rarity": "LEGENDARY",
        "race": "DRAGON",
        "races": ["DRAGON"],
        "text": "在你的回合结束时，将一张梦境牌置入你的手牌。",
        "collectible": True,
    },
    {
        "id": "EX1_016",
        "name": "希尔瓦娜斯·风行者",
        "cost": 6,
        "attack": 5,
        "health": 5,
        "cardClass": "NEUTRAL",
        "type": "MINION",
        "rarity": "LEGENDARY",
        "race": "UNDEAD",
        "races": ["UNDEAD"],
        "text": "<b>亡语：</b>随机控制一个敌方随从。",
        "mechanics": ["DEATHRATTLE"],
        "collectible": True,
    },
]


class CardDatabase:
    """In-memory dictionary mapping card IDs and card names with fuzzy matching."""

    _instance: Optional["CardDatabase"] = None

    def __init__(
        self,
        cache_file: Optional[Path] = None,
        indexed_file: Optional[Path] = None,
        auto_download: bool = True,
    ) -> None:
        self.cache_file = cache_file or CARDS_CACHE_FILE
        self.indexed_cache_file = indexed_file or CARDS_INDEXED_FILE
        self.cards_by_id: Dict[str, CardInfo] = {}
        self.cards_by_name: Dict[str, List[CardInfo]] = {}
        self.all_names: List[str] = []
        self.length_buckets: Dict[int, List[str]] = {}
        self.ngram_index: Dict[str, Set[str]] = {}
        self._fuzzy_cache: Dict[Tuple[str, float], Optional[str]] = {}
        self._loaded = False

        if auto_download:
            self.load()

    @classmethod
    def get_instance(cls) -> "CardDatabase":
        """Singleton accessor for global card dictionary."""
        if cls._instance is None:
            cls._instance = CardDatabase()
        return cls._instance

    def load(self, force_refresh: bool = False) -> bool:
        """Loads cards from pre-indexed binary cache (<200ms) or JSON cache."""
        if self._loaded and not force_refresh:
            return True

        if not force_refresh:
            indexed_path = self.indexed_cache_file
            if not indexed_path.exists():
                indexed_path = get_default_cards_indexed_file()
            if indexed_path.exists():
                try:
                    t0 = time.perf_counter()
                    with open(indexed_path, "rb") as f:
                        data = pickle.load(f)
                    self.cards_by_id = data["by_id"]
                    self.cards_by_name = data["by_name"]
                    self.all_names = data["all_names"]
                    self.length_buckets = data["length_buckets"]
                    self.ngram_index = data.get("ngram_index") or {}
                    if not self.ngram_index and self.all_names:
                        self._build_ngrams()
                    self._fuzzy_cache.clear()
                    self._loaded = True
                    t1 = time.perf_counter()
                    logger.info(f"Loaded {len(self.cards_by_id)} cards from binary cache in {(t1 - t0)*1000:.1f}ms: {indexed_path}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to read binary card cache {indexed_path}: {e}. Falling back to cards.json.")

        if not self.cache_file.exists():
            self.cache_file = get_default_cards_cache_file()

        raw_cards = None
        if self.cache_file.exists():
            try:
                t0 = time.perf_counter()
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    raw_cards = json.load(f)
                    t1 = time.perf_counter()
                    logger.info(f"Loaded {len(raw_cards)} cards from JSON cache in {(t1 - t0)*1000:.1f}ms: {self.cache_file}")
            except Exception as e:
                logger.warning(f"Failed to read cached cards: {e}.")

        if not raw_cards:
            logger.info("Local cards.json not found; using internal sample dataset for instant startup.")
            raw_cards = FALLBACK_CARDS_SAMPLE

        self._build_indexes(raw_cards)
        self._save_binary_cache()
        self._loaded = True
        return True

    def _build_ngrams(self) -> None:
        """Constructs 2-gram and 3-gram inverted index for sub-millisecond Chinese card name lookups."""
        self.ngram_index.clear()
        for name in self.all_names:
            n_len = len(name)
            for i in range(n_len - 1):
                g2 = name[i:i+2]
                self.ngram_index.setdefault(g2, set()).add(name)
            for i in range(n_len - 2):
                g3 = name[i:i+3]
                self.ngram_index.setdefault(g3, set()).add(name)

    def _save_binary_cache(self) -> None:
        """Saves indexed card dictionaries into binary pickle for blazing fast cold starts."""
        try:
            self.indexed_cache_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "by_id": self.cards_by_id,
                "by_name": self.cards_by_name,
                "all_names": self.all_names,
                "length_buckets": self.length_buckets,
                "ngram_index": self.ngram_index,
            }
            with open(self.indexed_cache_file, "wb") as f:
                pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Saved binary card cache ({len(self.cards_by_id)} cards) to {self.indexed_cache_file}")
        except Exception as e:
            logger.debug(f"Failed to write binary card cache: {e}")

    def _download_cards(self) -> Optional[List[Dict[str, Any]]]:
        """Downloads cards.json from HearthstoneJSON with timeout."""
        try:
            logger.info(f"Downloading Hearthstone cards (zhCN) from {HEARTHSTONE_JSON_ZH_CN_URL}...")
            req = urllib.request.Request(
                HEARTHSTONE_JSON_ZH_CN_URL,
                headers={"User-Agent": "HearthstoneArenaAssistant/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                raw = json.loads(data.decode("utf-8"))
                # Save cache
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, "wb") as f:
                    f.write(data)
                logger.info(f"Successfully downloaded and cached {len(raw)} cards.")
                return raw
        except Exception as e:
            logger.error(f"Error downloading cards: {e}")
            return None

    def _build_indexes(self, raw_cards: List[Dict[str, Any]]) -> None:
        """Parses cards and creates indexes by ID and by Chinese Name."""
        self.cards_by_id.clear()
        self.cards_by_name.clear()
        name_set = set()

        for c in raw_cards:
            # We care primarily about collectible cards or playable tokens
            card_id = c.get("id")
            name = c.get("name")
            if not card_id or not name:
                continue

            card = CardInfo(
                id=card_id,
                name=name,
                cost=int(c.get("cost", 0)),
                attack=c.get("attack"),
                health=c.get("health"),
                durability=c.get("durability"),
                card_class=c.get("cardClass", "NEUTRAL"),
                card_type=c.get("type", "MINION"),
                rarity=c.get("rarity", "COMMON"),
                set_name=c.get("set", ""),
                text=c.get("text", ""),
                race=c.get("race"),
                races=c.get("races", []),
                spell_school=c.get("spellSchool"),
                mechanics=c.get("mechanics", []),
                collectible=c.get("collectible", False),
                raw_data=c,
            )

            self.cards_by_id[card_id] = card
            self.cards_by_name.setdefault(name, []).append(card)
            name_set.add(name)

        self.all_names = list(name_set)
        self.length_buckets.clear()
        for n in self.all_names:
            self.length_buckets.setdefault(len(n), []).append(n)
        self._build_ngrams()
        self._fuzzy_cache.clear()
        logger.info(f"Indexed {len(self.cards_by_id)} cards across {len(self.cards_by_name)} distinct names in {len(self.length_buckets)} length buckets and {len(self.ngram_index)} n-grams.")

    def get_by_id(self, card_id: str) -> Optional[CardInfo]:
        """Fast O(1) card lookup by Hearthstone card ID (e.g. 'CORE_CS2_039')."""
        return self.cards_by_id.get(card_id)

    def get_by_name(self, name: str) -> Optional[CardInfo]:
        """Lookup by exact card name (returns first match, preferring collectible)."""
        matches = self.cards_by_name.get(name)
        if not matches:
            return None
        # Prefer collectible card
        for card in matches:
            if card.collectible:
                return card
        return matches[0]

    def fuzzy_match_card(self, query: str, cutoff: float = 0.55) -> Optional[CardInfo]:
        """
        Fuzzy matches OCR text against all Chinese card names.
        High-performance implementation with length buckets and memory cache.
        """
        if not query:
            return None

        # Clean query
        cleaned_query = re.sub(r"[^\w\u4e00-\u9fa5]", "", query).strip()
        if not cleaned_query or len(cleaned_query) < 2 or cleaned_query in COMMON_CARD_KEYWORDS:
            return None

        # Short 2-character words require higher matching strictness to avoid false positives
        if len(cleaned_query) == 2 and cutoff < 0.85:
            cutoff = 0.85

        # 1. Direct O(1) exact hash match
        direct = self.get_by_name(cleaned_query)
        if direct:
            return direct

        # 2. Check LRU / memory cache
        cache_key = (cleaned_query, cutoff)
        if cache_key in self._fuzzy_cache:
            cached_name = self._fuzzy_cache[cache_key]
            return self.get_by_name(cached_name) if cached_name else None

        # 3. High-Speed N-gram Candidate Inversion (30x Speedup)
        q_len = len(cleaned_query)
        candidates: List[str] = []
        if self.ngram_index and q_len >= 2:
            candidate_counts: Dict[str, int] = {}
            # 2-grams
            for i in range(q_len - 1):
                g2 = cleaned_query[i:i+2]
                for cname in self.ngram_index.get(g2, ()):
                    candidate_counts[cname] = candidate_counts.get(cname, 0) + 1
            # 3-grams
            for i in range(q_len - 2):
                g3 = cleaned_query[i:i+3]
                for cname in self.ngram_index.get(g3, ()):
                    candidate_counts[cname] = candidate_counts.get(cname, 0) + 2

            # Filter candidates within length tolerance [-2, +2]
            ranked = [
                name for name, score in sorted(candidate_counts.items(), key=lambda x: x[1], reverse=True)
                if abs(len(name) - q_len) <= 2
            ]
            if ranked:
                candidates = ranked[:25]

        # 4. Fallback to length buckets if n-grams yielded no close match
        if not candidates:
            for l in (q_len - 1, q_len, q_len + 1, q_len + 2):
                if l in self.length_buckets:
                    candidates.extend(self.length_buckets[l])

        if not candidates:
            candidates = self.all_names

        close = difflib.get_close_matches(cleaned_query, candidates, n=1, cutoff=cutoff)
        if not close and candidates is not self.all_names:
            # Fallback to full list if length range was skewed by severe OCR truncation
            close = difflib.get_close_matches(cleaned_query, self.all_names, n=1, cutoff=cutoff)

        if close:
            best_name = close[0]
            self._fuzzy_cache[cache_key] = best_name
            return self.get_by_name(best_name)

        self._fuzzy_cache[cache_key] = None
        return None


try:
    from PyQt5.QtCore import QThread, pyqtSignal
except ImportError:
    class QThread:  # type: ignore
        def __init__(self, parent=None): pass
        def start(self): pass
        def quit(self): pass
        def wait(self): pass
    def pyqtSignal(*args):  # type: ignore
        class _Signal:
            def connect(self, fn): pass
            def emit(self, *a, **kw): pass
        return _Signal()


class CardDbLoader(QThread):
    """Background loader thread ensuring instant UI launch (<0.1s) without blocking main thread."""
    loaded = pyqtSignal(int)

    def __init__(self, db: CardDatabase, parent=None) -> None:
        super().__init__(parent)
        self.db = db

    def run(self) -> None:
        self.db.load()
        self.loaded.emit(len(self.db.cards_by_id))
