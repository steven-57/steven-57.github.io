# steven-57.github.io 維護指南

本專案是一個個人部落格 / 遊記網站，託管於 GitHub Pages。網頁內容是由 `sources/` 資料夾底下的 Word 文件 (`.docx`)、設定檔 (`.json`) 等資源，透過 Python 腳本自動生成 HTML 頁面。

為了避免 GitHub 單一檔案大小上限（100MB）的問題，`.docx` 原始檔並不會直接上傳至 Git，而是透過腳本分割成碎片後儲存，並在本地端合併還原進行編輯。

---

## 🛠️ 環境準備

### 1. 安裝 Python 依賴套件
在開始維護前，請確保安裝了必要的 Python 套件：
```bash
pip install -r requirments.txt
```

---

## 🔄 工作流程

### 📥 首次下載 / 更新程式碼後的合併步驟 (Merge)
因為 `.docx` 檔案被設定在 `.gitignore` 中，拉取專案後本地端不會有 `.docx` 原始檔。請先將碎片檔案合併：

1. 執行以下指令：
   ```bash
   python fragments.py
   ```
2. 當系統提示 `what operation do you want to perform? (1: split, 2: merge):` 時，輸入 **`2`** 進行合併。
3. 合併完成後，你將會在 `sources/` 資料夾下看到還原的 `.docx` 檔案。

---

### 📝 新增或修改遊記

若要新增一篇名為 `MyTravel` 的遊記，請在 `sources/` 資料夾下準備以下 4 個檔案：

1. **Word 內容檔** (`sources/MyTravel.docx`)
   * 撰寫遊記的 Word 檔案，請將照片直接插入在 Word 檔的對應位置中。

2. **封面圖片檔** (`sources/MyTravel.png` 或 `.jpg`, `.jpeg`)
   * 用於首頁卡片顯示的代表圖片。

3. **簡介描述檔** (`sources/MyTravel.txt`)
   * 純文字檔案，內含簡短的一兩句話，用來顯示在首頁卡片的介紹中。

4. **設定檔** (`sources/MyTravel.json`)
   * 範例格式如下：
     ```json
     {
       "cmds": [
         {
           "type": "changetag",
           "place": "text_para",
           "target": "Day",
           "tag": "h1"
         },
         {
           "type": "addele",
           "place": "text_para",
           "pos": "before",
           "target": "Day",
           "html": "<hr>"
         }
       ],
       "order": -20260609
     }
     ```
     * **`order`**：排序用的權重數字（整數）。首頁會以 **升冪 (Ascending)** 進行排序。一般習慣使用**負數的日期時間**（例如 `-20260609`），如此一來最新的遊記（數值越小）就會排在首頁最前面。
     * **`cmds`**：針對 Word 內容轉換 HTML 的微調指令：
       * `changetag`: 將包含特定字串的段落（如 `"Day"`) 改為指定的 HTML 標籤（如 `<h1>`）。
       * `addele`: 在包含特定字串的段落前方 (`before`) 或後方 (`after`) 插入自訂 HTML（如分隔線 `<hr>`）。
       * `eximg`: 針對特定圖片進行特別的樣式微調（如排版、CSS 垂直對齊等）。

---

### 🚀 產生網頁 (Build)
當你在 `sources/` 完成編輯或新增後，可以透過以下步驟重新編譯網頁：

1. 執行編譯腳本：
   ```bash
   python builder.py
   ```
2. 該腳本將會自動執行以下操作：
   * 從 Word 中提取圖片至 `images/MyTravel/` 並進行 MD5 去重與排序。
   * 解析 Word XML 排版，並套用自訂樣式。
   * 套用 `templates/page.html` 產生 `MyTravel.html`。
   * 讀取所有遊記資訊，套用 `templates/index.html` 重新生成首頁 `index.html`。
   * 自動更新 `sitemap.xml` 提供搜尋引擎索引（SEO）。

---

### 📤 上傳至 GitHub 前的分割步驟 (Split)
在將變更提交（Commit & Push）回 GitHub 之前，**務必**將 `.docx` 檔案重新分割成碎片檔案，以便版本控制與避開 GitHub 的大檔案上傳限制：

1. 執行以下指令：
   ```bash
   python fragments.py
   ```
2. 當系統提示 `what operation do you want to perform? (1: split, 2: merge):` 時，輸入 **`1`** 進行分割。
3. 腳本會將大檔案分割存入 `sources/fragments/MyTravel/` 下。
4. 使用 Git 提交變更（`.docx` 本身會被自動忽略，只需提交變更的 `fragments/` 及產出的 HTML）：
   ```bash
   git add .
   git commit -m "Update travel diary: MyTravel"
   git push origin main
   ```

---

## 📂 專案結構說明
* `sources/`：存放遊記的原始檔案（`.docx` 暫存檔、設定檔 `.json`、碎影片段 `.part`、封面、介紹 `.txt`）。
* `templates/`：Jinja2 模板檔案，決定首頁 (`index.html`) 與內頁 (`page.html`) 的排版。
* `images/`：從 Word 自動提取並優化後的圖片輸出資料夾。
* `style/` / `script/`：網站所需的 CSS 樣式及 JavaScript 腳本。
* `builder.py`：網頁生成器核心腳本。
* `fragments.py`：處理大檔案分割與合併的工具腳本。
* `index.html`、`*.html`：網站發佈的網頁主體。
