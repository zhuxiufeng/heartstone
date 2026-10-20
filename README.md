# 炉石传说竞技场全场景 AI 助手 (Python 商业级重构版)

基于 Python 3.10+ 开发的轻量级、无内存注入的《炉石传说》竞技场战术辅助工具。

## 核心特性

- **100% 暴雪合规**：零内存注入、零封包拦截，纯基于本地文件日志读取与屏幕截图 OCR。
- **底层数据总线 (Phase 1)**：
  - `config_manager.py`：管理本地配置 (`config.json`)，支持一键配置游戏 `log.config`。
  - `card_db.py`：自动下载并本地缓存 HearthstoneJSON 官方中文卡牌数据（36,000+ 卡牌），构建内存快速索引，支持 OCR 模糊纠错。
  - `log_listener.py`：`QThread` 线程实时监听 `Power.log` 和 `Arena.log`，精准拦截选牌 `MakePick` 与对局状态。
- **动态视觉感知与防抖机制 (Phase 2)**：
  - `window_finder.py`：动态获取游戏真实窗口坐标，按比例计算截图区域，自适应 1080p, 2K, 4K 及窗口模式。
  - `ocr_engine.py`：`mss` 极速截图 + `cv2` 二值化与降噪 + `Tesseract` 识别，并配套 ~2.5s 状态锁（防抖机制），避免卡牌翻转动画导致误识别。
- **AI 大脑与双模状态机 (Phase 3)**：
  - `ai_engine.py`：注入完整卡牌元数据消除幻觉。支持**选牌模式 (Draft Mode)**与**实战模式 (Play Mode)**。
  - **本地缓存 (Evaluation Cache)**：基于“职业 + 法力曲线 + 候选牌”生成确定性 Hash，相同情境零延迟、零 Token 消耗返回。
  - **离线启发式引擎**：无网络或无 API Key 时自动无缝降级为内置规则评估，保证 100% 可用。
- **商业级 PyQt5 UI (Phase 4)**：
  - `overlay.py`：无边框半透明悬浮窗，永远置顶，支持鼠标拖拽与穿透模式。
  - `mana_curve.py`：可视化 0~7+ 费用法力曲线柱状图，实时更新套牌曲线。
  - `settings_dialog.py`：系统托盘右键菜单随时呼出参数配置（Gemini API Key、模型选择、透明度调整等）。
  - **优雅退出 (Graceful Shutdown)**：重写 `closeEvent`，退出时向子线程发送终止信号，安全释放文件句柄与线程。

---

## 目录结构

```text
├── config.json                 # 本地运行时配置文件
├── main.py                     # 程序主入口，生命周期管理
├── requirements.txt            # Python 依赖清单
├── core/                       # 核心业务逻辑
│   ├── config_manager.py       # 配置管理
│   ├── card_db.py              # 卡牌数据库与模糊匹配
│   ├── window_finder.py        # 窗口寻址与分辨率自适应
│   ├── log_listener.py         # 日志监听 QThread
│   ├── ocr_engine.py           # 屏幕识别与防抖锁 QThread
│   └── ai_engine.py            # AI 大脑、Prompt 注入与双模引擎
├── ui/                         # 界面组件
│   ├── overlay.py              # 透明悬浮窗主窗口
│   ├── mana_curve.py           # 可视化法力曲线
│   ├── recommendation_card.py  # 三选一卡牌推荐卡片
│   └── settings_dialog.py      # 参数设置对话框
├── tests/                      # 单元与集成测试
│   ├── test_config.py
│   ├── test_card_db.py
│   ├── test_window_finder.py
│   ├── test_log_listener.py
│   ├── test_ocr_engine.py
│   └── test_ai_engine.py
└── data/                       # 缓存与数据目录
    └── cards.json
```

---

## 快速上手

### Windows 环境（推荐）

1. **一键安装**：直接双击运行 [`install_windows.bat`](file:///home/zxf/workspace/code/agy/game/heartstone/install_windows.bat)（会自动创建 `.venv` 并安装包括 `pywin32` 在内的全部依赖）。
2. **一键启动**：直接双击运行 [`start_windows.bat`](file:///home/zxf/workspace/code/agy/game/heartstone/start_windows.bat)。
3. **打包 EXE（可选）**：双击运行 [`build_exe.bat`](file:///home/zxf/workspace/code/agy/game/heartstone/build_exe.bat)，即可在 `dist\炉石竞技场AI助手\` 获得免 Python 环境的绿色版程序。

### Linux / 跨平台手动启动

```bash
# 1. 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 启动助手
python main.py

# 启动并自动进行一次模拟三选一测试
python main.py --simulate-draft
```

### 3. 配置游戏日志输出

如果炉石传说尚未开启日志记录，请启动助手后在设置菜单中点击 **“⚡ 一键配置 Hearthstone log.config 文件”**，或者手动在 `%LOCALAPPDATA%\Blizzard\Hearthstone\log.config` 添加：

```ini
[Power]
LogLevel=1
FilePrinting=True
ConsolePrinting=False
ScreenPrinting=False

[Arena]
LogLevel=1
FilePrinting=True
ConsolePrinting=False
ScreenPrinting=False
```

### 4. 运行自动化测试

```bash
pytest tests/ -v
```
