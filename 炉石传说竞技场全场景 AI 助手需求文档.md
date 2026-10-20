# 炉石传说竞技场全场景 AI 助手 (Python 商业级重构版) - 需求文档 (PRD)

## 1. 项目概述 (Project Overview)
本项目旨在开发一款基于 Python 的轻量级、无内存注入的《炉石传说》辅助工具。工具通过 **本地日志解析** 跟踪对局状态，通过 **动态屏幕截图与 OCR** 获取视觉信息，并调用 **大模型 API (Gemini)** 提供实时战术分析。最后通过 **PyQt5 透明悬浮窗** 将法力曲线和建议展示给玩家。

**核心红线**：严禁任何内存读取和封包拦截，确保 100% 遵守暴雪 ToS，零封号风险。

## 2. 技术栈 (Tech Stack)
*   **主语言**: Python 3.10+
*   **GUI & 并发**: `PyQt5` (实现透明置顶悬浮窗、系统托盘、QThread 多线程调度)
*   **视觉感知**: `mss` (极速截图), `opencv-python` (二值化预处理), `pytesseract` (文本提取), `pywin32` (动态窗口寻址)
*   **大模型通信**: `google-generativeai` (Gemini API)
*   **底层数据源**: `HearthstoneJSON` API, `watchdog` / 文件流读取 (日志实时监听)

## 3. 核心功能与架构模块 (Architecture & Features)

### Phase 1: 底层数据总线与日志监听 (Data & Logging)
*   **`config_manager.py` (新增)**:
    *   管理本地 `config.json`，保存 Gemini API Key、模型选择 (Flash/Pro) 等用户配置。
*   **`card_db.py` (卡牌词典)**:
    *   首次启动时自动下载 `cards.json` (zhCN 语言包)。
    *   构建内存字典，将日志中的 `cardId` 极速映射为包含完整元数据（中文名、费用、攻击、血量、种族、法术派系、文本）的字典。
*   **`log_listener.py` (日志钩子)**:
    *   作为后台 `QThread` 运行，死循环监听 `Power.log` 和 `Arena.log`。
    *   选牌态：拦截 `MakePick` 等关键字提取 `cardId`，翻译后触发抓牌信号。

### Phase 2: 动态视觉感知与防抖机制 (Perception & Debouncing)
*   **`ocr_engine.py` (智能识别)**:
    *   **动态分辨率适配**：使用 `win32gui` 获取炉石传说真实窗口坐标与大小，按比例计算截图区域，完美适配 1080p, 2K, 4K 及窗口模式。
    *   使用 `mss` 抓取三选一卡牌名称，`cv2` 二值化处理后交由 Tesseract 识别。
*   **状态锁 (State Lock)**：识别到抓牌动作后，主进程锁定 `is_drafting_animation = True` (~2.5秒)，期间停止截图，防止捕获卡牌翻转动画导致的错乱。

### Phase 3: AI 大脑与双模状态机 (AI & State Machine)
*   **`ai_engine.py` (核心大脑)**:
    *   **元数据注入**：从 OCR 拿到卡名后，先从 `card_db` 提取其费用、身材、种族等属性，拼接成详细 Prompt 发给大模型，彻底消除新卡幻觉。
    *   **选牌模式 (Draft Mode)**：结合当前职业、已抓法力曲线，给出三选一的最优抓取建议。
    *   **实战模式 (Play Mode)**：结合费用截图与日志提供的场面信息，提供随从交换与打法建议。
    *   **本地缓存 (Evaluation Cache)**：建立 `职业+已选曲线+候选牌` Hash 字典，相同情境直接返回缓存，零延迟、零 Token 消耗。

### Phase 4: 商业级 PyQt5 UI 与工程健壮性 (UI & UX)
*   **`overlay.py` (悬浮窗与托盘)**:
    *   **透明悬浮窗**：无边框、鼠标穿透、背景半透明、永远置顶，支持鼠标拖拽。
    *   **可视化法力曲线**：底部绘制 0~7+ 费用的柱状图 (`QProgressBar`)，抓牌后动态更新高度。
    *   **系统托盘与可视化配置**：不在任务栏显示，常驻右下角托盘。右键可呼出独立设置窗口，供用户填写 API Key 和选择偏好。
*   **并发与优雅退出 (Graceful Shutdown)**:
    *   UI 渲染在主线程，OCR 轮询与 Log 监听分别跑在两个 `QThread`，互不阻塞。
    *   重写 `closeEvent`，退出时向所有子线程发送终止信号，确保无僵尸进程残留、释放文件锁。