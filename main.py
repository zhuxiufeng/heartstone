#!/usr/bin/env python3
"""
Hearthstone Arena AI Assistant (炉石传说竞技场全场景 AI 助手)
Commercial-grade refactored entry point.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# Fix working directory immediately before any module-level path evaluation
if getattr(sys, "frozen", False):
    os.chdir(Path(sys.executable).resolve().parent)

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication

from core.ai_engine import AiEngine
from core.card_db import CardDatabase, CardDbLoader
from core.config_manager import ConfigManager
from core.log_listener import LogListener
from core.ocr_engine import OcrWorker
from ui.overlay import OverlayWindow, create_app_icon


def setup_logging(debug: bool = False) -> None:
    """Configures application-wide logging format and global exception hook."""
    level = logging.DEBUG if debug else logging.INFO
    log_format = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
    handlers: list[logging.Handler] = []
    if sys.stdout is not None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(log_format, datefmt="%H:%M:%S"))
        handlers.append(handler)
    try:
        fh = logging.FileHandler("assistant_runtime.log", mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter(log_format, datefmt="%H:%M:%S"))
        handlers.append(fh)
    except Exception:
        pass
    logging.basicConfig(level=level, handlers=handlers, force=True)

    def _global_excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.getLogger("Main").error("Unhandled exception caught by excepthook:", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _global_excepthook


def main() -> int:
    parser = argparse.ArgumentParser(description="Hearthstone Arena AI Assistant")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--simulate-draft", action="store_true", help="Automatically trigger draft test on launch")
    parser.add_argument("--simulate-play", action="store_true", help="Automatically trigger play recommendation test on launch")
    parser.add_argument("--simulate-mulligan", action="store_true", help="Automatically trigger mulligan guidance test on launch")
    parser.add_argument("--test-run", action="store_true", help="Start app and exit after 2s (for smoke testing)")
    args = parser.parse_args()

    # 1. Config & Logging
    config = ConfigManager(args.config)
    setup_logging(debug=args.debug or config.get("debug_mode", False))
    logger = logging.getLogger("Main")
    logger.info("Starting Hearthstone Arena AI Assistant...")

    # 2. High-DPI Scaling for PyQt5
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray when overlay is hidden
    app.setWindowIcon(create_app_icon())

    from PyQt5.QtGui import QFont
    default_font = QFont("Microsoft YaHei", 9)
    default_font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(default_font)

    # 3. Initialize Card DB
    card_db = CardDatabase(auto_download=False)
    card_db.load()

    # 4. Initialize AI Brain
    ai_engine = AiEngine(
        api_key=config.get("gemini_api_key", ""),
        model_name=config.get("gemini_model", "gemini-1.5-flash"),
        card_db=card_db,
        cache_enabled=config.get("evaluation_cache_enabled", True),
    )

    # 5. Initialize Worker Threads
    log_dir = config.get("hearthstone_log_dir", "")
    log_listener = LogListener(log_dir=log_dir, card_db=card_db)

    ocr_worker = OcrWorker(
        card_db=card_db,
        poll_interval_ms=config.get("ocr_poll_interval_ms", 1000),
        animation_lock_duration=config.get("animation_lock_duration_sec", 2.5),
        tesseract_cmd=config.get("tesseract_cmd", ""),
        ocr_lang=config.get("ocr_lang", "chi_sim+eng"),
    )

    # 6. Initialize UI Overlay
    overlay = OverlayWindow(
        config_manager=config,
        card_db=card_db,
        ai_engine=ai_engine,
        log_listener=log_listener,
        ocr_worker=ocr_worker,
    )

    # 7. Start Background Worker Threads
    log_listener.start()
    ocr_worker.start()

    # 8. Show Overlay IMMEDIATELY (Instant <0.1s render)
    overlay.show()
    overlay._on_status_updated("⚡ 正在极速就绪...")
    logger.info("Application initialized and overlay displayed instantly.")

    # 9. Asynchronously load card database in background
    db_loader = CardDbLoader(card_db, overlay)
    db_loader.loaded.connect(lambda count: overlay._on_status_updated(f"就绪 ({count} 张卡牌)"))
    db_loader.start()
    overlay._db_loader = db_loader

    if args.simulate_draft:
        QTimer.singleShot(500, overlay.simulate_sample_draft)

    if args.simulate_play:
        QTimer.singleShot(500, overlay.simulate_sample_play)

    if args.simulate_mulligan:
        QTimer.singleShot(500, overlay.simulate_sample_mulligan)

    if args.test_run:
        # Auto-shutdown after 2 seconds for CI/smoke testing
        QTimer.singleShot(2000, overlay.shutdown)

    # Allow SIGINT (Ctrl+C) to terminate cleanly in terminal
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)
    signal.signal(signal.SIGINT, lambda sig, frame: overlay.shutdown())

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
