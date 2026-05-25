# 📊 Git-Pulse — Local Repository Analytics Dashboard

Git-Pulse is a high-performance, resource-optimized local Git repository analytics dashboard. Tailored specifically for low-spec hardware, it bypasses heavy JavaScript runtimes, Node.js bundlers, and bloated charting libraries in favor of a lean Python backend, direct SQLite transactions, native Python-rendered SVGs, and dynamic frontend refreshes driven by HTMX.

---

## ⚡ Core Features

- **🚀 Smart Git Crawler:** Powered by `GitPython` to read repository logs. Features **incremental scanning** which records the latest scanned commit SHA to process future updates instantly. Natively ignores untracked/ignored folders like `node_modules` or `venv` by scanning committed files.
- **🎨 Python-Native SVG Visual Charts:** Avoids heavy client-side graphing frameworks. All vectors are computed dynamically in Python and returned as lightweight SVG XML strings:
  - **Code Change Velocity Chart:** Line/area graph tracking additions vs. deletions over the last 14 active days.
  - **Active Coding Hours Heatmap:** A 24x7 grid showcasing commit activity density by hour of day and day of week.
  - **File Type Distribution Chart:** A donut diagram showing volumetric breakdown by file extensions.
- **🔄 HTMX-Powered Single Page App (SPA):** Single-page visual interface styled in Tailwind CSS (CDN). Employs an auto-polling cycle (`hx-trigger="every 30s"`) that triggers an incremental Git scan at the exact moment of the poll and updates dashboard metrics seamlessly without full page reloads.
- **📂 Multi-Repository Support:** Track, manage, and toggle between multiple local repositories.
- **⚙️ Low-Spec Hardware Profile:** Built with zero ORM overhead using raw `sqlite3` queries, zero Node.js dependencies, and high-speed Python backend computation.

---

## 🏗️ Folder Structure

```text
git-pulse/
├── api/
│   ├── main.py          # FastAPI application routes & HTMX partial handlers
│   ├── database.py      # SQLite connection helpers, schema creation & raw queries
│   ├── scanner.py       # Incremental Git crawler core using GitPython
│   └── charts.py        # Vector graphics compiler (Velocity, Heatmap, Donut SVGs)
├── templates/
│   ├── index.html       # SPA layout containing forms & sidebar
│   └── dashboard.html   # Dynamic dashboard partial injected by HTMX
├── .gitignore           # Highly optimized Git ignore rules for SQLite & caches
├── requirements.txt     # Python dependencies list
├── vercel.json          # Deployment routing config
└── verify.py            # Local automated verification test suite
```

---

## 🚀 Getting Started

### 1. Clone & Setup
Ensure you have Python 3.10+ installed. Open your terminal and run:

```powershell
# Navigate to project directory
cd C:\Users\ACer\.gemini\antigravity\scratch\git-pulse

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch Local Server
Start the Uvicorn web server:

```powershell
python api/main.py
```

### 3. Open in Browser
Open your browser and navigate to:
👉 **[http://127.0.0.1:8080](http://127.0.0.1:8080)**

Provide the absolute path to any local Git repository (for example, the Git-Pulse folder itself: `C:\Users\ACer\.gemini\antigravity\scratch\git-pulse`) and click **+ Register Repo** to map your repository analytics instantly!

---

## 🧪 Automated Verification
To ensure full system integrity, Git-Pulse includes an automated end-to-end testing script. This script boots a dummy repository, executes commits, runs incremental scanning logic, validates file extension statistics, and tests SVG renders:

```powershell
python verify.py
```

---

## 🌐 Cloud Deployment Notes
Because Git-Pulse utilizes `GitPython` to execute local shell-level git system calls on your directories, it is optimized to run locally. 

If you want a public cloud demo, you should deploy to persistent container environments like **Railway.app** or **Render.com** (where the system `git` command-line tool is fully pre-installed and SQLite write paths are allowed), rather than Serverless functions like Vercel.
