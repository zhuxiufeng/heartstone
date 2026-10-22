"""
SettingsDialog: Modal configuration window for Hearthstone Arena AI Assistant.
Allows user to configure Gemini API Key, Model, Hearthstone log path, OCR options,
and overlay transparency.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

try:
    from core.ai_engine import AiEngine
    from core.config_manager import ConfigManager, get_default_hearthstone_log_dir
except (ImportError, ValueError):
    from ..core.ai_engine import AiEngine
    from ..core.config_manager import ConfigManager, get_default_hearthstone_log_dir


class SettingsDialog(QDialog):
    """Configuration settings window."""

    settings_saved = pyqtSignal(dict)

    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("⚙️ 炉石竞技场 AI 助手 - 参数设置")
        self.resize(600, 700)
        self.setMinimumSize(540, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        self._load_values()

    def _init_ui(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #f8fafc;
                font-family: "Segoe UI", "Microsoft YaHei", "Segoe UI Emoji", "PingFang SC", sans-serif;
            }
            QScrollArea, QScrollArea > QWidget > QWidget {
                background-color: #0b0f19;
                border: none;
            }
            QWidget#contentWidget {
                background-color: #0b0f19;
            }
            QGroupBox {
                background-color: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(56, 189, 248, 0.22);
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 20px;
                padding-bottom: 12px;
                padding-left: 12px;
                padding-right: 12px;
                font-weight: 800;
                color: #38bdf8;
                font-size: 12.5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 14px;
                padding: 2px 8px;
                background-color: #0f172a;
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.45);
                border-radius: 4px;
            }
            QLabel {
                background-color: transparent;
                color: #cbd5e1;
                font-size: 12px;
            }
            QCheckBox {
                background-color: transparent;
                color: #cbd5e1;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 4px;
                background-color: #0f172a;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #38bdf8;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
            }
            QLineEdit, QComboBox {
                background-color: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #f8fafc;
                padding: 4px 10px;
                min-height: 28px;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1.5px solid #38bdf8;
                background-color: rgba(15, 23, 42, 0.98);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #0369a1);
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 5px 12px;
                min-height: 28px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #0284c7);
                border-color: #7dd3fc;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
            QPushButton#secondaryBtn {
                background-color: rgba(255, 255, 255, 0.06);
                color: #94a3b8;
                font-weight: 600;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
            }
            QPushButton#secondaryBtn:hover {
                background-color: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
                border: 1px solid #38bdf8;
            }
            QPushButton#secondaryBtn:pressed {
                background-color: rgba(14, 165, 233, 0.25);
            }
            QPushButton#actionBtn {
                background-color: rgba(14, 165, 233, 0.16);
                color: #38bdf8;
                font-weight: bold;
                border: 1px solid rgba(56, 189, 248, 0.45);
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton#actionBtn:hover {
                background-color: rgba(14, 165, 233, 0.30);
                color: #ffffff;
                border: 1px solid #38bdf8;
            }
            QPushButton#actionBtn:pressed {
                background-color: rgba(2, 132, 199, 0.45);
            }
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: rgba(255, 255, 255, 0.12);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #0284c7;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #38bdf8;
                border: 1px solid #ffffff;
                width: 14px;
                height: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #7dd3fc;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(15, 23, 42, 0.6);
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(56, 189, 248, 0.35);
                min-height: 25px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(56, 189, 248, 0.75);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                height: 0px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Scroll Area for comfortable layout on all screen sizes & DPI scaling
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(2, 2, 6, 2)
        content_layout.setSpacing(12)

        # 1. AI Engine Config
        ai_group = QGroupBox("🤖 大模型通信 (Gemini API)")
        ai_layout = QFormLayout(ai_group)
        ai_layout.setSpacing(8)

        # API Key with eye toggle
        key_box = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("填入 Google Gemini API Key (可空，自动启用内置启发策略)")
        self.toggle_eye_btn = QPushButton("👁️")
        self.toggle_eye_btn.setObjectName("secondaryBtn")
        self.toggle_eye_btn.setFixedSize(36, 28)
        self.toggle_eye_btn.clicked.connect(self._toggle_api_key_visibility)
        key_box.addWidget(self.api_key_input)
        key_box.addWidget(self.toggle_eye_btn)
        ai_layout.addRow("API Key:", key_box)

        # Model choice
        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)  # User can type ANY latest/custom model!
        self.model_combo.addItems([
            "gemini-4",
            "gemini-4-flash",
            "gemini-4-pro",
            "gemini-3.8",
            "gemini-3.8-flash",
            "gemini-3.8-pro",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-exp",
            "gemini-2.0-pro-exp-02-05",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro-latest",
        ])
        self.fetch_models_btn = QPushButton("🔄 获取模型")
        self.fetch_models_btn.setToolTip("通过已填入的 API Key 联网向 Google 官方实时获取全部最新可用模型列表")
        self.fetch_models_btn.setObjectName("secondaryBtn")
        self.fetch_models_btn.setFixedHeight(28)
        self.fetch_models_btn.clicked.connect(self._fetch_latest_models)

        model_row.addWidget(self.model_combo, stretch=1)
        model_row.addWidget(self.fetch_models_btn)
        ai_layout.addRow("模型选择:", model_row)

        # Cache enabled
        self.cache_chk = QCheckBox("启用评估缓存 (Evaluation Cache，相同情境零延迟零消耗)")
        self.cache_chk.setChecked(True)
        ai_layout.addRow("", self.cache_chk)
        content_layout.addWidget(ai_group)

        # 2. Hearthstone Logs Config
        log_group = QGroupBox("📁 炉石日志数据源 (Logs Directory)")
        log_layout = QVBoxLayout(log_group)
        log_path_row = QHBoxLayout()

        self.log_dir_input = QLineEdit()
        self.log_dir_input.setPlaceholderText("例如: C:/Users/.../AppData/Local/Blizzard/Hearthstone/Logs")
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setObjectName("secondaryBtn")
        self.browse_btn.setFixedSize(70, 28)
        self.browse_btn.clicked.connect(self._browse_log_dir)
        self.autodetect_btn = QPushButton("自动探测")
        self.autodetect_btn.setObjectName("secondaryBtn")
        self.autodetect_btn.setFixedSize(85, 28)
        self.autodetect_btn.clicked.connect(self._auto_detect_logs)

        log_path_row.addWidget(self.log_dir_input)
        log_path_row.addWidget(self.browse_btn)
        log_path_row.addWidget(self.autodetect_btn)
        log_layout.addLayout(log_path_row)

        self.setup_log_config_btn = QPushButton("⚡ 一键配置 Hearthstone log.config 文件")
        self.setup_log_config_btn.setObjectName("actionBtn")
        self.setup_log_config_btn.setMinimumHeight(32)
        self.setup_log_config_btn.clicked.connect(self._setup_log_config)
        log_layout.addWidget(self.setup_log_config_btn)

        content_layout.addWidget(log_group)

        # 3. OCR & Window Config
        ocr_group = QGroupBox("👁️ 视觉与防抖 (Perception)")
        ocr_layout = QFormLayout(ocr_group)
        ocr_layout.setSpacing(8)

        self.tesseract_input = QLineEdit()
        self.tesseract_input.setPlaceholderText("留空则使用系统 PATH 中的 tesseract")
        ocr_layout.addRow("Tesseract 路径:", self.tesseract_input)

        self.lock_duration_input = QLineEdit("2.5")
        ocr_layout.addRow("防抖动画锁 (秒):", self.lock_duration_input)

        content_layout.addWidget(ocr_group)

        # 4. UI Appearance
        ui_group = QGroupBox("🎨 悬浮窗外观")
        ui_layout = QFormLayout(ui_group)
        ui_layout.setSpacing(8)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(40, 100)
        self.opacity_slider.setValue(92)
        self.opacity_lbl = QLabel("92%")
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_lbl.setText(f"{v}%"))

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self.opacity_slider)
        opacity_row.addWidget(self.opacity_lbl)
        ui_layout.addRow("透明度:", opacity_row)

        self.click_through_chk = QCheckBox("启用鼠标穿透 (锁定位置，不可点击交互)")
        ui_layout.addRow("", self.click_through_chk)

        content_layout.addWidget(ui_group)

        # 5. Sound & Voice Alerts
        sound_group = QGroupBox("🔊 音效与语音播报")
        sound_layout = QFormLayout(sound_group)
        sound_layout.setSpacing(8)

        self.sound_enabled_chk = QCheckBox("启用核心战局音效 (斩杀提示音、高危清场预警、跳币)")
        sound_layout.addRow("", self.sound_enabled_chk)

        self.tts_enabled_chk = QCheckBox("启用 TTS 实时战术语音播报 (战局关键点语音提醒)")
        sound_layout.addRow("", self.tts_enabled_chk)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_lbl = QLabel("80%")
        self.volume_slider.valueChanged.connect(lambda v: self.volume_lbl.setText(f"{v}%"))

        vol_row = QHBoxLayout()
        vol_row.addWidget(self.volume_slider)
        vol_row.addWidget(self.volume_lbl)
        sound_layout.addRow("音效音量:", vol_row)

        content_layout.addWidget(sound_group)

        # Put content inside scroll area
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Bottom buttons: Cancel, Save
        btn_box = QHBoxLayout()
        btn_box.setContentsMargins(4, 4, 4, 0)
        btn_box.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setFixedSize(85, 32)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("保存配置")
        save_btn.setFixedSize(95, 32)
        save_btn.clicked.connect(self._save_values)

        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)
        main_layout.addLayout(btn_box)

    def _toggle_api_key_visibility(self) -> None:
        if self.api_key_input.echoMode() == QLineEdit.Password:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
            self.toggle_eye_btn.setText("🔒")
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.toggle_eye_btn.setText("👁️")

    def _browse_log_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择炉石传说日志目录 (Logs)")
        if folder:
            self.log_dir_input.setText(folder)

    def _auto_detect_logs(self) -> None:
        path = get_default_hearthstone_log_dir()
        self.log_dir_input.setText(path)
        QMessageBox.information(self, "自动探测", f"已探测并填入日志路径:\n{path}")

    def _setup_log_config(self) -> None:
        success = self.config_manager.ensure_log_config()
        if success:
            QMessageBox.information(self, "成功", "已成功配置 Hearthstone log.config 确保输出 Power.log 与 Arena.log！")
        else:
            QMessageBox.warning(self, "提示", "未能自动定位到用户目录下的 log.config 路径，请手动确认。")

    def _fetch_latest_models(self) -> None:
        """Fetches all supported models for the provided API key."""
        key = self.api_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "请先在上方输入有效的 Google Gemini API Key。")
            return

        self.fetch_models_btn.setEnabled(False)
        self.fetch_models_btn.setText("获取中...")
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            models = AiEngine.fetch_available_models(key)
            if models:
                current_text = self.model_combo.currentText()
                self.model_combo.clear()
                self.model_combo.addItems(models)
                # Keep previously selected model if found
                idx = self.model_combo.findText(current_text)
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)
                else:
                    self.model_combo.setCurrentIndex(0)
                QMessageBox.information(
                    self,
                    "获取成功",
                    f"已成功从 Google 官方检索到 {len(models)} 个可用模型！\n首选: {self.model_combo.currentText()}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "未获取到模型",
                    "未能检索到模型列表。请检查：\n1. API Key 是否正确有效\n2. 网络是否能访问 Google API（如需系统代理请先配置）\n3. Google Cloud 项目是否启用了 Generative Language API。"
                )
        except Exception as e:
            QMessageBox.critical(self, "请求异常", f"获取失败: {e}")
        finally:
            self.fetch_models_btn.setEnabled(True)
            self.fetch_models_btn.setText("🔄 获取模型")

    def _load_values(self) -> None:
        cfg = self.config_manager.as_dict()
        self.api_key_input.setText(cfg.get("gemini_api_key", ""))

        model = cfg.get("gemini_model", "gemini-2.0-flash")
        idx = self.model_combo.findText(model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setEditText(model)

        self.cache_chk.setChecked(cfg.get("evaluation_cache_enabled", True))
        self.log_dir_input.setText(cfg.get("hearthstone_log_dir", ""))
        self.tesseract_input.setText(cfg.get("tesseract_cmd", ""))
        self.lock_duration_input.setText(str(cfg.get("animation_lock_duration_sec", 2.5)))

        opacity = int(cfg.get("overlay_opacity", 0.92) * 100)
        self.opacity_slider.setValue(opacity)
        self.opacity_lbl.setText(f"{opacity}%")
        self.click_through_chk.setChecked(cfg.get("click_through", False))

        self.sound_enabled_chk.setChecked(cfg.get("sound_enabled", True))
        self.tts_enabled_chk.setChecked(cfg.get("tts_enabled", False))
        vol = cfg.get("sound_volume", 80)
        self.volume_slider.setValue(vol)
        self.volume_lbl.setText(f"{vol}%")

    def _save_values(self) -> None:
        try:
            lock_dur = float(self.lock_duration_input.text().strip())
        except ValueError:
            lock_dur = 2.5

        new_config = {
            "gemini_api_key": self.api_key_input.text().strip(),
            "gemini_model": self.model_combo.currentText().strip() or "gemini-2.0-flash",
            "evaluation_cache_enabled": self.cache_chk.isChecked(),
            "hearthstone_log_dir": self.log_dir_input.text().strip(),
            "tesseract_cmd": self.tesseract_input.text().strip(),
            "animation_lock_duration_sec": lock_dur,
            "overlay_opacity": self.opacity_slider.value() / 100.0,
            "click_through": self.click_through_chk.isChecked(),
            "sound_enabled": self.sound_enabled_chk.isChecked(),
            "tts_enabled": self.tts_enabled_chk.isChecked(),
            "sound_volume": self.volume_slider.value(),
        }

        self.config_manager.update(new_config)
        self.settings_saved.emit(new_config)
        self.accept()
