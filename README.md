# Virtual Class Voice AI System

雙路徑語音 AI 系統：使用者透過語音與虛擬學生互動，系統同時執行快速語音回應和完整對話記錄。

## 🏗️ 系統架構

### 核心特色：雙路徑設計

1. **快速路徑（Fast Path）**
   - 使用 OpenAI Realtime API 進行 Speech-to-Speech
   - 延遲目標：200-500ms
   - 目的：提供最快的語音回應體驗

2. **慢速路徑（Slow Path）**
   - Whisper STT 進行高品質轉錄
   - 將使用者和 AI 的語音都轉換為文字
   - 完整對話記錄存入資料庫
   - 可匯出文字檔（Markdown/TXT）

### 技術棧

- **後端**: FastAPI + PostgreSQL
- **前端**: Next.js + React
- **即時通訊**: LiveKit (WebRTC)
- **語音處理**: OpenAI Realtime API (Speech-to-Speech)
- **AI 協調**: LangGraph
- **LLM**: OpenAI GPT-4

## 📁 專案結構

```
virtual_class/
├── main.py                      # FastAPI 應用入口
├── models.py                    # SQLAlchemy 資料模型
├── database.py                  # 資料庫配置
├── requirements.txt             # Python 依賴
├── .env                         # 環境變數（需自行設定）
├── usage_guide_cn.md            # 中文使用手冊
│
├── api/                         # API 層
│   ├── session.py               # Session 管理（無需登入）
│   ├── report.py                # 報告匯出
│   └── livekit_token.py         # LiveKit Token 生成
│
├── services/                    # 服務層
│   ├── db_manager.py            # 資料庫 CRUD 操作封裝
│   └── gcc_module.py            # GCC 上下文管理與事件記錄
│
├── core/                        # 核心模組
│   ├── auth_module.py           # LiveKit Token 認證
│   ├── session_manager.py       # Session 狀態管理
│   └── langgraph_coordinator.py # LangGraph 協調器
│
├── agents/                      # Agent 層
│   ├── prompts.py               # Agent Persona
│   ├── student_agent.py         # 虛擬學生 Agent
│   ├── expert_agent.py          # 專家評估 Agent
│   └── voice_pipeline.py        # 🔥 雙路徑語音 Pipeline
│
├── utils/                       # 工具層
│   └── logger.py                # 對話記錄器
│
└── web_client/                  # 前端 (Next.js)
    ├── app/                     # Next.js App Router
    ├── components/              # React 元件
    └── public/                  # 靜態資源
```

## 🚀 快速開始

### 1. 環境準備

```powershell
# 建立虛擬環境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安裝 Python 依賴
pip install -r requirements.txt

# 安裝前端依賴
cd web_client
npm install
cd ..
```

### 2. 配置環境變數

在專案根目錄建立 `.env` 檔案，填入以下資訊：

```ini
# LiveKit Cloud Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIqwerty12345
LIVEKIT_API_SECRET=Secretqwerty12345

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx

# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/virtual_class_db
```

### 3. 啟動 PostgreSQL 資料庫

```powershell
# 確保 PostgreSQL 已安裝並在背景執行（預設 Port 5432）
```

### 4. 啟動伺服器（需同時開啟三個終端）

```powershell
# 終端 1：啟動後端 API Server
uvicorn main:app --port 8000

# 終端 2：啟動前端網頁
cd web_client
npm run dev

# 終端 3：啟動 Voice AI Agent
python -m agents.voice_pipeline dev
```

## 📝 API 使用流程

> 本系統無需登入驗證，所有 API 端點均可直接呼叫。

### 1. 快速取得 Token（推薦測試用）

```bash
curl -X POST "http://localhost:8000/livekit/quick_token"
```

會自動建立 guest 使用者和 Session，返回 LiveKit Token。

### 2. 創建 Session

```bash
curl -X POST "http://localhost:8000/session/create" \
  -H "Content-Type: application/json" \
  -d '{"title": "My First Teaching Session"}'
```

### 3. 獲取 LiveKit Token

```bash
curl -X POST "http://localhost:8000/livekit/token" \
  -H "Content-Type: application/json" \
  -d '{"session_uuid": "YOUR_SESSION_UUID"}'
```

### 4. 連線到 LiveKit（前端）

使用返回的 `token` 和 `url` 連線到 LiveKit 房間，開始語音互動。
或直接開啟 `http://localhost:3000` 使用前端介面。

### 5. 下載對話記錄

```bash
# Markdown 格式
curl -X GET "http://localhost:8000/report/YOUR_SESSION_UUID/transcript?format=markdown" \
  --output transcript.md

# TXT 格式
curl -X GET "http://localhost:8000/report/YOUR_SESSION_UUID/transcript?format=txt" \
  --output transcript.txt
```

### 6. 獲取 Session 摘要

```bash
curl -X GET "http://localhost:8000/report/YOUR_SESSION_UUID/summary"
```

## 🔧 開發指南

### 資料庫遷移（使用 Alembic）

```powershell
# 初始化 Alembic
alembic init alembic

# 創建遷移
alembic revision --autogenerate -m "Initial migration"

# 執行遷移
alembic upgrade head
```

### 測試語音 Pipeline

```powershell
# 啟動 Worker 並查看日誌
python -m agents.voice_pipeline dev
```

## 🎯 系統運作流程

```mermaid
sequenceDiagram
    participant User as 使用者
    participant LiveKit
    participant FastPath as 快速路徑
    participant SlowPath as 慢速路徑
    participant DB as 資料庫

    User->>LiveKit: 語音輸入
    LiveKit->>FastPath: Audio Stream
    
    par 並行處理
        FastPath->>User: 語音回應 (200-500ms)
    and
        FastPath->>SlowPath: 觸發轉錄
        SlowPath->>DB: 保存使用者轉錄
        SlowPath->>DB: 保存 AI 轉錄
    end
    
    Note over SlowPath,DB: 對話結束後可匯出文字檔
```

## 📚 關鍵檔案說明

### `agents/voice_pipeline.py` - 雙路徑 Pipeline 核心

這是整個系統最關鍵的檔案，實作了：
- **OpenAI Realtime 連線**: `OpenAIRealtimeClient` 透過 WebSocket 直連 OpenAI Realtime API
- **雙路徑處理**: `DualPathVoicePipeline` 同時處理語音回應與文字轉錄
- **音訊串流**: 將 OpenAI 回應的音訊即時推送到 LiveKit 房間

### `services/db_manager.py` - 資料庫操作封裝

封裝所有 CRUD 操作：User、Session、Conversation、Transcript。

### `services/gcc_module.py` - GCC 上下文模組

為 Agent 提供上下文管理（context/context_full）與事件記錄（log_ota）。

### `core/langgraph_coordinator.py` - 場景協調

使用 LangGraph 管理 Student Agent 和 Expert Agent 的狀態機，決定何時調用哪個 Agent。

## 🐛 常見問題

### Q: LiveKit 連線失敗？
A: 確認 LiveKit Server 已啟動，並檢查 `.env` 中的 `LIVEKIT_URL` 配置。

### Q: 語音回應延遲太高？
A: 檢查：
1. OpenAI Realtime API 是否可用
2. 網路連線品質
3. LiveKit Server 是否與應用在同一區域

### Q: 轉錄文字不完整？
A: 慢速路徑是異步的，確保在結束 session 前等待所有轉錄完成。

### Q: Port 被佔用？
A: 參考 `usage_guide_cn.md` 中的常見問題段落進行排除。

## 📄 授權

MIT License

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

---

**開發團隊**: Virtual Class AI Team  
**聯絡方式**: support@virtualclass.ai
