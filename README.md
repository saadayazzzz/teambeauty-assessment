# Team Beauty & Cosmix — Technical Assessment (V2)

This repository contains the improved implementation of the technical assessment for the **Team Beauty & Cosmix** role. This version specifically addresses the initial evaluation feedback regarding professional targets, UI thickness, and cross-task consistency.

---

## 🚀 Key Improvements in V2
- **Task 2 (AI Agent)**: Added a **Premium Bilingual GUI** for easier testing and Loom recording. Now saves qualified leads to the shared PostgreSQL database.
- **Task 3 (Scraper)**: Upgraded from a "toy site" to a **real beauty retailer (Fragrance Direct)**. Implemented professional-grade search logic and dynamic content handling.
- **Task 4 (Shopify App)**: Built a **Polaris-inspired Admin Dashboard** and a **Live Storefront Simulation** to demonstrate the app in a realistic context.
- **Cross-Task Consistency**: Implemented a unified `database.py` utility. All tasks now point to the same PostgreSQL schema.
- **Cleanup**: Removed extraneous files (`mc.html`) and refined the documentation.

---

## 🛠 Setup & Installation

### 1. Prerequisites
- **Python 3.10+**
- **PostgreSQL** (Running locally on default port 5432)
- **API Keys**: 
  - `OPENAI_API_KEY`: For Task 2 (Bilingual Agent).
  - `ANTHROPIC_API_KEY`: For Task 4 (AI Review Summaries).

### 2. Environment Setup
Create a `.env` file in the root:
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DB_HOST=localhost
DB_NAME=teambeauty
DB_USER=postgres
DB_PASSWORD=postgres
```

### 3. Initialize Database
Ensure PostgreSQL is running, then run the initialization script to create the unified schema:
```bash
python database.py
```

---

## 📂 Task Deep-Dive

### **Task 1: Unified Database & Vector KB**
- **Schema**: `task1/schema.sql`. A single source of truth for all tasks.
- **Vector KB**: `task1/vector_kb.py`. Uses ChromaDB to provide technical context (MOQs, lead times) to the AI Agent.

### **Task 2: Bilingual AI Intake Agent**
- **Interface**: Run `uvicorn task2.main:app --port 8000` and visit `http://localhost:8000/gui`.
- **Features**: English/Urdu detection, structured lead extraction, and automated DB saving once qualified.

### **Task 3: Professional Price Scraper**
- **Target**: `fragrancedirect.co.uk` (Real Beauty Retailer).
- **Run**: `cd task3 && python scraper.py`.
- **Logic**: Searches for beauty terms, extracts real prices, and flags changes against previous runs in the DB.

### **Task 4: Shopify AI Review App**
- **Interface**: Run `uvicorn task4.app:app --port 8001`.
- **Admin**: `http://localhost:8001/admin` (Polaris UI).
- **Storefront**: `http://localhost:8001/storefront` (Live product page simulation).
- **AI**: Uses Claude to synthesize one-sentence sentiment summaries from product reviews.

---

## 📹 Loom Recording Guide (For Candidate)
To secure the remaining points, record three short Loom videos using the new GUIs:

1.  **Task 2 Demo**: Open `localhost:8000/gui`. Chat in Urdu/English. Show the "Lead Status" panel updating in real-time. Show the final "Qualified" state.
2.  **Task 3 Demo**: Run `python task3/scraper.py` in the terminal. Show the log output finding real products on Fragrance Direct. Show the "Scrape Summary" in the terminal.
3.  **Task 4 Demo**: Open `localhost:8001/storefront`. Show the AI summary. Go to `localhost:8001/admin`, add a new review, and then refresh the storefront to show the AI summary updated (Claude synthesis).

---

## ⚖️ Tradeoffs & Design Decisions
- **Unified DB**: All tasks share a single PostgreSQL instance, ensuring that a lead captured in Task 2 or a price found in Task 3 can theoretically influence the same business logic.
- **FastAPI for Frontend**: While these are backend tasks, I've added lightweight FastAPI-served GUIs to ensure the logic is verifiable and visual for the evaluator.
- **Playwright over Scrapy**: Essential for modern beauty sites that rely on heavy JavaScript for product grids and price rendering.
