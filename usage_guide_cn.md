# Virtual Class Voice AI System - 使用手冊 (User Manual)

本手冊將引導您完成環境建置、套件安裝及伺服器啟動，確保您能在前端網頁與 AI 虛擬學生進行即時語音/文字對話。

---

## 1. 系統簡介 (Introduction)

本系統整合了以下技術：
*   **Backend**: Python FastAPI (處理資料庫與 API 請求)。
*   **Frontend**: Next.js + React (提供使用者介面與 WebSocket 連線)。
*   **AI Agent**: LiveKit Agent + OpenAI Realtime API (負責即時語音理解與生成)。
*   **Protocol**: WebSocket (用於低延遲通訊)。

---

## 2. 事前準備 (Prerequisites)

在開始之前，請確保您的電腦已安裝以下軟體：

1.  **Python 3.10 或以上版本**: [下載連結](https://www.python.org/downloads/)
    *   請確保安裝時勾選 "Add Python to PATH"。
2.  **Node.js 18 或以上版本**: [下載連結](https://nodejs.org/)
    *   包含 `npm` 套件管理工具。
3.  **PostgreSQL 資料庫**: [下載連結](https://www.postgresql.org/download/)
    *   請確保資料庫服務已在背景執行 (預設 Port 5432)。
4.  **LiveKit Server URL & API Key**:
    *   您可以註冊 [LiveKit Cloud](https://cloud.livekit.io/) 取得免費專案的 URL 與 Key。
5.  **OpenAI API Key**:
    *   必須具備存取 `gpt-4o-realtime-preview` 模型的權限。

---

## 3. 環境設定 (Environment Setup)

### 步驟 3.1: 建立並啟動虛擬環境 (推薦)
使用虛擬環境可以避免套件衝突，建議在專案中使用。

**建立虛擬環境 (首次設定)**
```bash
# 進入專案根目錄
cd virtual_class

# 建立虛擬環境
python -m venv .venv
```

**啟動虛擬環境 (每次使用前)**
```powershell
# PowerShell
.\.venv\Scripts\Activate.ps1

# 或 CMD
.\.venv\Scripts\activate.bat
```
> 啟動成功後，終端提示符會顯示 `(.venv)` 前綴。

### 步驟 3.2: Python 套件安裝
在虛擬環境中安裝依賴套件：

```bash
pip install -r requirements.txt
```

### 步驟 3.3: Node.js 套件安裝
進入前端目錄並安裝依賴套件：

```bash
cd web_client
npm install
cd ..  # 安裝完後回到根目錄
```

### 步驟 3.4: 設定環境變數 (.env)
請在專案根目錄確認有沒有 `.env` 檔案，若無請建立，並填入以下資訊：

```ini
# LiveKit Cloud Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIqwerty12345
LIVEKIT_API_SECRET=Secretqwerty12345

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx

# Database Configuration (依據您的 PostgreSQL 設定調整)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/virtual_class_db
```

---

## 4. 啟動伺服器 (Startup Guide)

為了讓系統正常運作，我們需要**同時啟動三個服務**。請開啟三個不同的終端機視窗 (或分頁) 分別執行。

> ⚠️ **重要**：啟動前請確保已啟動虛擬環境 (`.\.venv\Scripts\Activate.ps1`)

### 📌 視窗 1: 啟動後端 API Server (FastAPI)
此服務負責處理 Token 發放與資料庫存取。

```bash
# 確保在專案根目錄 (virtual_class) 且虛擬環境已啟動
uvicorn main:app --port 8000
```
> 當看到 `Application startup complete` 代表啟動成功。

### 📌 視窗 2: 啟動前端網頁 (Next.js)
此服務提供使用者操作介面。

```bash
# 進入前端目錄
cd web_client
npm run dev
```
> 當看到 `Ready in xxxms` 代表啟動成功，網頁位於 `http://localhost:3000`。

### 📌 視窗 3: 啟動 Voice AI Agent
此服務負責連線 OpenAI 並進行語音對話。

```bash
# 確保在專案根目錄 (virtual_class)
python -m agents.voice_pipeline dev
```
> 當看到 `registered worker` 代表 Agent 已連線到 LiveKit Cloud 等待呼叫。

---

## 5. 開始使用 (How to Use)

1.  開啟瀏覽器 (推薦 Chrome/Edge)，前往 **`http://localhost:3000`**。
2.  您會看到聊天室介面與 "Connect" 按鈕 (或自動連線)。
3.  **文字對話**：
    *   在下方輸入框打字 (例如："你好") 並按 Enter。
    *   Agent 會透過文字回覆您，同時也會播放語音。
4.  **語音對話**：
    *   點擊麥克風圖示 (若有) 或直接對著麥克風說話 (視目前 VAD 設定而定)。
    *   Agent 會即時用語音回應。

---

## 6. 常見問題 (Troubleshooting)

*   **Q: Port 8000 已被佔用 (Errno 10048)?**
    
    當啟動 `uvicorn` 時出現 `[Errno 10048] error while attempting to bind on address` 錯誤，表示該 Port 已被其他程式佔用。
    
    **解決方法：找出並終止佔用該 Port 的進程**
    ```powershell
    # 1. 查詢佔用 Port 8000 的進程 PID
    netstat -ano | findstr :8000
    
    # 輸出範例: TCP 127.0.0.1:8000 0.0.0.0:0 LISTENING 12345
    # 最後一欄 (12345) 就是 PID
    
    # 2. 終止該進程 (將 12345 替換為實際 PID)
    taskkill /F /PID 12345
    ```
    
    **快速清除所有 Python 進程 (謹慎使用)**
    ```powershell
    taskkill /F /IM python.exe
    ```

*   **Q: `npm run dev` 顯示 Port 3000 被佔用或 lock 錯誤?**
    
    當出現 `Port 3000 is in use` 或 `Unable to acquire lock` 錯誤時：
    
    **解決方法 1：終止佔用 Port 3000 的進程**
    ```powershell
    # 查詢並終止佔用 Port 3000 的進程
    netstat -ano | findstr :3000
    taskkill /F /PID <顯示的PID>
    ```
    
    **解決方法 2：刪除 lock 檔案並重啟**
    ```powershell
    # 進入前端目錄
    cd web_client
    
    # 刪除 .next 快取資料夾
    Remove-Item -Recurse -Force .next
    
    # 重新啟動
    npm run dev
    ```

*   **Q: 網頁顯示連線失敗？**
    *   檢查 `.env` 中的 `LIVEKIT_URL` 是否正確。
    *   確認 `uvicorn main:app` 有在 Port 8000 執行。
*   **Q: Agent 有回應聲音但沒文字？**
    *   請確認 Agent 終端視窗有無錯誤訊息。
    *   刷新網頁重試。
*   **Q: OpenAI 回應 404？**
    *   請確認您的 `OPENAI_API_KEY` 是否有權限使用 Realtime Model (`gpt-4o-realtime-preview`)。
