"""
OcrEngine: High-speed screenshot capture and text recognition for Hearthstone Arena.
Implements:
1. Dynamic resolution adaptation with WindowFinder
2. OpenCV binarization & image preprocessing
3. Tesseract OCR with fuzzy dictionary matching
4. State Lock debouncing (~2.5s) to avoid capturing card flip animations
5. PyQt5 QThread integration
"""

from __future__ import annotations

import logging
import os
import platform
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

_cv2_cached = None
_mss_cached = None
_pytesseract_cached = None


def _get_cv2():
    global _cv2_cached
    if _cv2_cached is None:
        try:
            import cv2
            _cv2_cached = cv2
        except Exception:
            _cv2_cached = False
    return _cv2_cached if _cv2_cached is not False else None


def _get_mss():
    global _mss_cached
    if _mss_cached is None:
        try:
            import mss
            _mss_cached = mss
        except Exception:
            _mss_cached = False
    return _mss_cached if _mss_cached is not False else None


def _get_pytesseract():
    global _pytesseract_cached
    if _pytesseract_cached is None:
        try:
            import pytesseract
            _pytesseract_cached = pytesseract
        except Exception:
            _pytesseract_cached = False
    return _pytesseract_cached if _pytesseract_cached is not False else None


_rapidocr_cached = None


def _get_rapidocr():
    global _rapidocr_cached
    if _rapidocr_cached is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _rapidocr_cached = RapidOCR(use_angle_cls=False)
        except Exception as e:
            logging.getLogger("OcrEngine").warning(f"RapidOCR initialization failed: {e}")
            _rapidocr_cached = False
    return _rapidocr_cached if _rapidocr_cached is not False else None

try:
    from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
except ImportError:
    # Minimal fallback for headless/test environments
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
    def pyqtSlot(*args):  # type: ignore
        return lambda fn: fn

from .card_db import CardDatabase, CardInfo
from .window_finder import WindowFinder, WindowRect

logger = logging.getLogger("OcrEngine")

HERO_KEYWORDS = {
    "死亡骑士": "DEATHKNIGHT", "死骑": "DEATHKNIGHT", "巫妖王": "DEATHKNIGHT", "阿尔萨斯": "DEATHKNIGHT",
    "恶魔猎手": "DEMONHUNTER", "蛋总": "DEMONHUNTER", "伊利丹": "DEMONHUNTER",
    "德鲁伊": "DRUID", "玛法里奥": "DRUID",
    "猎人": "HUNTER", "雷克萨": "HUNTER",
    "法师": "MAGE", "吉安娜": "MAGE",
    "圣骑士": "PALADIN", "乌瑟尔": "PALADIN", "骑士": "PALADIN",
    "牧师": "PRIEST", "安度因": "PRIEST",
    "潜行者": "ROGUE", "瓦莉拉": "ROGUE", "盗贼": "ROGUE",
    "萨满祭司": "SHAMAN", "萨满": "SHAMAN", "萨尔": "SHAMAN",
    "术士": "WARLOCK", "古尔丹": "WARLOCK",
    "战士": "WARRIOR", "加尔鲁什": "WARRIOR",
}


def classify_hero_banner(banner) -> str:
    """Classifies Hearthstone hero class from its arena draft ribbon banner color."""
    if banner is None or banner.size == 0:
        return ""
    import cv2
    import numpy as np

    hsv = cv2.cvtColor(banner, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([0, 40, 30]), np.array([180, 255, 245]))
    if np.sum(mask) < 40:
        return ""

    mean_h = float(np.mean(hsv[:, :, 0][mask > 0]))
    mean_s = float(np.mean(hsv[:, :, 1][mask > 0]))
    mean_v = float(np.mean(hsv[:, :, 2][mask > 0]))
    b = float(np.mean(banner[:, :, 0][mask > 0]))
    g = float(np.mean(banner[:, :, 1][mask > 0]))
    r = float(np.mean(banner[:, :, 2][mask > 0]))

    if mean_s < 45 and mean_v > 130:
        return "牧师"
    if mean_v < 45 or (mean_s < 50 and mean_v < 75):
        return "潜行者"
    if (60 <= mean_h <= 78 and b > 75 and g > 75) or (b > 85 and g > 85 and r < 65):
        return "死亡骑士"
    if (78 < mean_h <= 126 or (b > g * 1.1 and b > r * 1.05)) and b > 55:
        return "萨满祭司"
    if 86 <= mean_h <= 104 and b > 85 and r >= 40:
        return "法师"
    if 38 <= mean_h <= 58 and g > r * 1.15 and g > b * 1.3:
        return "猎人"
    if 25 <= mean_h <= 38 and g > 100 and mean_s > 150:
        return "恶魔猎手"
    if 18 <= mean_h <= 36 and r > 105 and g > 85 and b < 65:
        return "圣骑士"
    if 10 <= mean_h < 22 and r > g and g > b:
        return "德鲁伊"
    if 126 <= mean_h <= 162 and (b > g * 1.1 or r > g * 1.1):
        return "术士"
    if (mean_h < 12 or mean_h > 162) and r > g * 1.2:
        return "战士"
    return ""


def compute_dhash(img_bgr: np.ndarray) -> int:
    """Computes 64-bit difference hash (dHash) for sub-millisecond visual screen deduplication."""
    cv2 = _get_cv2()
    if cv2 is None or img_bgr is None or img_bgr.size == 0:
        return 0
    try:
        if len(img_bgr.shape) == 3:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_bgr
        small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
        diff = small[:, 1:] > small[:, :-1]
        h = 0
        for bit in diff.flatten():
            h = (h << 1) | int(bit)
        return h
    except Exception:
        return 0


class OcrWorker(QThread):
    """Background QThread performing non-blocking OCR screen polling and debounce locking."""

    cards_detected = pyqtSignal(list)       # List[CardInfo]
    heroes_detected = pyqtSignal(list)      # List[str] (Hero class names)
    deck_detected = pyqtSignal(dict)        # {"cards": List[CardInfo], "total_picked": int}
    ocr_status = pyqtSignal(str)           # Status message string
    state_lock_changed = pyqtSignal(bool)  # True = animation locked, False = unlocked

    def __init__(
        self,
        card_db: Optional[CardDatabase] = None,
        poll_interval_ms: int = 1000,
        animation_lock_duration: float = 2.5,
        tesseract_cmd: str = "",
        ocr_lang: str = "chi_sim+eng",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.card_db = card_db or CardDatabase.get_instance()
        self.poll_interval_sec = max(0.2, poll_interval_ms / 1000.0)
        self.animation_lock_duration = animation_lock_duration
        self.ocr_lang = ocr_lang

        self.tesseract_cmd = tesseract_cmd

        self.window_finder = WindowFinder()
        self._running = False
        self._paused = False
        self._is_animation_locked = False
        self._lock_until_timestamp: float = 0.0
        self._last_detected_card_ids: List[str] = []
        self._slot_memory: List[Optional[CardInfo]] = [None, None, None]
        self._last_detected_heroes: List[str] = []
        self._last_banner_thumbnails: List[np.ndarray] = []
        self._last_dhash: int = 0
        self._last_deck_signature: str = ""
        self.frame_diff_threshold: float = 4.0  # Pixel intensity difference threshold (0-255)
        self.is_hero_mode: bool = True

    def set_hero_mode(self, enabled: bool) -> None:
        self.is_hero_mode = enabled
        logger.info(f"OcrWorker: is_hero_mode set to {enabled}")

    def set_poll_interval(self, ms: int) -> None:
        self.poll_interval_sec = max(0.2, ms / 1000.0)

    def pause(self) -> None:
        """Suspends screen OCR polling (e.g. during active play where logs provide 100% of state)."""
        self._paused = True
        logger.info("OcrWorker: Polling suspended for zero-CPU play mode.")
        self.ocr_status.emit("OCR 挂起 (对战模式日志驱动)")

    def resume(self) -> None:
        """Resumes screen OCR polling for draft selection."""
        self._paused = False
        logger.info("OcrWorker: Polling resumed.")
        self.ocr_status.emit("OCR 运行中 (选牌模式)")

    def is_paused(self) -> bool:
        return self._paused

    def trigger_animation_lock(self, duration: Optional[float] = None) -> None:
        """
        Locks OCR scanning for specified duration (default ~2.5s)
        when a card pick action is triggered, avoiding flip/shuffle animation errors.
        """
        dur = duration if duration is not None else self.animation_lock_duration
        self._lock_until_timestamp = time.time() + dur
        self._last_detected_card_ids = []
        self._slot_memory = [None, None, None]
        self._last_banner_thumbnails = []
        if not self._is_animation_locked:
            self._is_animation_locked = True
            logger.info(f"OcrWorker: Animation lock engaged for {dur:.1f}s")
            self.state_lock_changed.emit(True)

    def is_animation_locked(self) -> bool:
        if self._is_animation_locked:
            if time.time() >= self._lock_until_timestamp:
                self._is_animation_locked = False
                logger.info("OcrWorker: Animation lock released.")
                self.state_lock_changed.emit(False)
                return False
            return True
        return False

    def stop(self) -> None:
        """Signal worker thread to stop cleanly."""
        self._running = False

    def _setup_tesseract(self) -> None:
        pytesseract = _get_pytesseract()
        if pytesseract:
            cmd = self.tesseract_cmd
            if not cmd and platform.system() == "Windows":
                candidates = [
                    Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Tesseract-OCR" / "tesseract.exe",
                    Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Tesseract-OCR" / "tesseract.exe",
                    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
                ]
                for c in candidates:
                    if c.exists():
                        cmd = str(c)
                        logger.info(f"Auto-detected Windows Tesseract at: {cmd}")
                        break
            if cmd:
                pytesseract.pytesseract.tesseract_cmd = cmd

    def run(self) -> None:
        """Main background loop."""
        self._running = True
        self._setup_tesseract()
        logger.info("OcrWorker thread started.")
        self.ocr_status.emit("OCR 线程启动")

        while self._running:
            try:
                # Mode-aware suspension: sleep when paused
                if self._paused:
                    time.sleep(1.0)
                    continue

                # Check animation lock
                if self.is_animation_locked():
                    time.sleep(0.2)
                    continue

                # Locate Hearthstone window
                win_rect = self.window_finder.find_window()
                if not win_rect:
                    time.sleep(self.poll_interval_sec)
                    continue

                # 1. High-Speed Visual Perception for Arena 3-Hero Draft (<10ms, only if hero not yet selected)
                if getattr(self, "is_hero_mode", True):
                    frame = self.window_finder.grab_window_image(win_rect)
                    if frame is not None and frame.size > 0:
                        fh, fw = frame.shape[:2]
                        hero_boxes = [
                            (int(fw * 0.18), int(fh * 0.405), int(fw * 0.10), int(fh * 0.05)),
                            (int(fw * 0.355), int(fh * 0.405), int(fw * 0.10), int(fh * 0.05)),
                            (int(fw * 0.53), int(fh * 0.405), int(fw * 0.10), int(fh * 0.05)),
                        ]
                        detected_heroes = [classify_hero_banner(frame[y:y+rh, x:x+rw]) for x, y, rw, rh in hero_boxes]
                        valid_heroes = [h for h in detected_heroes if h]
                        if len(valid_heroes) >= 2 and len(set(valid_heroes)) >= 2 and valid_heroes != self._last_detected_heroes:
                            self._last_detected_heroes = valid_heroes
                            logger.info(f"Visual perception auto-recognized hero choices: {valid_heroes}")
                            self.heroes_detected.emit(valid_heroes)
                            self.ocr_status.emit(f"⚡ 自动识别到英雄: {' / '.join(valid_heroes)}")
                            time.sleep(self.poll_interval_sec)
                            continue

                # 2. Regular 3-card draft choices via RapidOCR / Tesseract
                candidates, raw_texts = self.recognize_draft_choices(win_rect)
                if candidates and len(candidates) == 3 and any(c is not None for c in candidates):
                    # Detect if a new round started (any slot changed to a different card ID)
                    is_new_round = any(
                        candidates[i] is not None
                        and self._slot_memory[i] is not None
                        and candidates[i].id != self._slot_memory[i].id
                        for i in range(3)
                    )
                    if is_new_round:
                        self._slot_memory = list(candidates)
                    else:
                        for i in range(3):
                            if candidates[i] is not None:
                                self._slot_memory[i] = candidates[i]

                    slot_ids = [c.id if c is not None else "" for c in self._slot_memory]
                    if slot_ids != self._last_detected_card_ids:
                        self._last_detected_card_ids = slot_ids
                        # Sync already-drafted deck list from the right-hand sidebar before evaluating choices
                        drafted_cards, total_picked = self.recognize_drafted_deck(win_rect)
                        deck_sig = f"{total_picked}:" + ",".join(c.id for c in drafted_cards)
                        if (drafted_cards or total_picked > 0) and deck_sig != self._last_deck_signature:
                            self._last_deck_signature = deck_sig
                            logger.info(
                                f"Visual perception recognized drafted deck ({total_picked}/30): "
                                f"{[c.name for c in drafted_cards]}"
                            )
                            self.deck_detected.emit({"cards": drafted_cards, "total_picked": total_picked})

                        names_str = " / ".join(c.name if c is not None else "待识别" for c in self._slot_memory)
                        logger.info(f"Visual perception recognized cards: {[c.name if c else None for c in self._slot_memory]}")
                        self.cards_detected.emit(list(self._slot_memory))
                        self.ocr_status.emit(f"自动识别选牌 ({total_picked}/30): {names_str}")

            except Exception as e:
                logger.error(f"Error in OCR worker loop: {e}", exc_info=True)
                self.ocr_status.emit(f"OCR 异常: {e}")

            time.sleep(self.poll_interval_sec)

        logger.info("OcrWorker thread terminated gracefully.")

    def recognize_drafted_deck(self, win_rect: WindowRect) -> Tuple[List[CardInfo], int]:
        """Captures and recognizes the already-drafted deck list on the right sidebar ('你的套牌')."""
        import re
        cv2 = _get_cv2()
        rapidocr = _get_rapidocr()
        if not cv2 or not rapidocr:
            return [], 0

        try:
            frame = self.window_finder.grab_window_image(win_rect)
            if frame is None or frame.size == 0:
                return [], 0
            fh, fw = frame.shape[:2]
            # Right-hand Arena deck list sidebar ('你的套牌' & 'X/30' counter)
            deck_crop = frame[int(fh * 0.07):int(fh * 0.96), int(fw * 0.72):int(fw * 0.88), :3]
            small = cv2.resize(deck_crop, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
            res, _ = rapidocr(small)

            drafted_cards: List[CardInfo] = []
            total_picked = 0
            ignore_keywords = ("你的套牌", "套牌", "完成", "返回")

            for line in res or []:
                _, text, _ = line
                t = text.strip()
                if not t:
                    continue
                # Check for X/30 counter (e.g., '5/30' or '12 / 30')
                m_cnt = re.search(r"(\d{1,2})\s*/\s*30", t)
                if m_cnt:
                    total_picked = int(m_cnt.group(1))
                    continue
                if any(kw in t for kw in ignore_keywords) or t.isdigit():
                    continue
                # Check for duplicate count suffix like 'x2' or trailing digit
                copies = 1
                m_dup = re.search(r"[x×*]\s*([2-9])$", t)
                if m_dup:
                    copies = int(m_dup.group(1))
                    t = t[:m_dup.start()].strip()
                card = self.card_db.fuzzy_match_card(t)
                if card:
                    for _ in range(copies):
                        drafted_cards.append(card)

            if total_picked == 0 and drafted_cards:
                total_picked = len(drafted_cards)
            return drafted_cards, total_picked
        except Exception as e:
            logger.debug(f"recognize_drafted_deck error: {e}")
            return [], 0

    def recognize_draft_choices(self, win_rect: WindowRect) -> Tuple[List[Optional[CardInfo]], List[str]]:
        """Captures and recognizes the 3 draft choice cards from the game screen."""
        mss = _get_mss()
        cv2 = _get_cv2()
        rapidocr = _get_rapidocr()
        pytesseract = _get_pytesseract()
        if not mss or not cv2 or (not rapidocr and not pytesseract):
            return [], []

        try:
            with mss.mss() as sct:
                # 1. Prefer high-speed local RapidOCR (100% offline, zero config)
                if rapidocr:
                    frame = self.window_finder.grab_window_image(win_rect)
                    if frame is None or frame.size == 0:
                        shot = sct.grab(win_rect.to_mss_dict())
                        frame = np.array(shot)
                    fh, fw = frame.shape[:2]

                    # Extract the 3 card title banners on the Arena Draft board (left/center 66% of window)
                    y0, y1 = int(fh * 0.33), int(fh * 0.41)
                    w_box = int(fw * 0.17)
                    b0 = frame[y0:y1, int(fw * 0.155):int(fw * 0.155) + w_box, :3]
                    b1 = frame[y0:y1, int(fw * 0.315):int(fw * 0.315) + w_box, :3]
                    b2 = frame[y0:y1, int(fw * 0.475):int(fw * 0.475) + w_box, :3]
                    stacked = np.vstack([b0, b1, b2])

                    # Ultra-fast 64-bit dHash perceptual filter (<0.05ms) to skip redundant neural inferences
                    curr_dhash = compute_dhash(stacked)
                    if self._last_dhash != 0 and all(self._last_detected_card_ids) and len(self._last_detected_card_ids) == 3:
                        hamming = bin(curr_dhash ^ self._last_dhash).count("1")
                        if hamming <= 1:
                            return [], []
                    self._last_dhash = curr_dhash

                    # Frame diff check against previous capture (only skip if all 3 slots are already populated)
                    gray = cv2.cvtColor(stacked, cv2.COLOR_BGR2GRAY)
                    thumb = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
                    if (
                        self._last_banner_thumbnails
                        and self._last_banner_thumbnails[0] is not None
                        and self._last_banner_thumbnails[0].shape == thumb.shape
                    ):
                        diff = cv2.absdiff(thumb, self._last_banner_thumbnails[0])
                        if float(np.mean(diff)) <= self.frame_diff_threshold and all(self._last_detected_card_ids) and len(self._last_detected_card_ids) == 3:
                            return [], []
                    self._last_banner_thumbnails = [thumb]

                    small = cv2.resize(stacked, (0, 0), fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA)
                    res, _ = rapidocr(small)
                    sh = small.shape[0] / 3.0
                    cards: List[Optional[CardInfo]] = [None, None, None]
                    raw_texts = ["", "", ""]
                    for line in res or []:
                        box, text, score = line
                        cy = sum(pt[1] for pt in box) / 4.0
                        slot = min(2, max(0, int(cy // sh)))
                        card = self.card_db.fuzzy_match_card(text)
                        if card:
                            cards[slot] = card
                            raw_texts[slot] = text

                    if any(c is not None for c in cards):
                        return cards, raw_texts

                # 2. Fallback to Tesseract if RapidOCR unavailable
                if pytesseract:
                    banner_rects = WindowFinder.get_draft_card_name_regions(win_rect)
                    results: List[Optional[CardInfo]] = []
                    raw_texts = []
                    for r in banner_rects:
                        mon = r.to_mss_dict()
                        shot = sct.grab(mon)
                        raw_arr = np.array(shot)
                        processed = self.preprocess_banner_image(raw_arr)
                        tess_config = f"--psm 7 -l {self.ocr_lang}"
                        raw_text = pytesseract.image_to_string(processed, config=tess_config).strip()
                        raw_texts.append(raw_text)
                        card = self.card_db.fuzzy_match_card(raw_text)
                        results.append(card)
                    return results, raw_texts

            return [], []
        except Exception as e:
            logger.debug(f"recognize_draft_choices error: {e}")
            return [], []

    @staticmethod
    def preprocess_banner_image(img_bgra: np.ndarray) -> np.ndarray:
        """
        Applies grayscale, contrast stretching, bilateral filtering and adaptive binarization
        to optimize Hearthstone card banner text for Tesseract.
        """
        cv2 = _get_cv2()
        if cv2 is None:
            return img_bgra

        # 1. Convert to BGR then Grayscale
        if img_bgra.shape[2] == 4:
            bgr = cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2BGR)
        else:
            bgr = img_bgra

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # 2. Resize x2 with cubic interpolation for cleaner edges
        h, w = gray.shape[:2]
        scaled = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

        # 3. Bilateral filter removes noise while keeping font edges sharp
        filtered = cv2.bilateralFilter(scaled, 9, 75, 75)

        # 4. Otsu's thresholding
        _, binary = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Invert if majority of pixels are dark (we want dark text on light background or vice-versa)
        white_pixels = cv2.countNonZero(binary)
        total_pixels = binary.size
        if white_pixels < total_pixels * 0.4:
            binary = cv2.bitwise_not(binary)

        return binary
