# Team Beauty & Cosmix — Technical Assessment

This repository contains the full implementation of the four-task technical assessment for the **Team Beauty & Cosmix** Technical Architect / Software Engineer role.

---

## 🚀 Quick Start (All Tasks)

### 1. Prerequisites
- **Python 3.10+**
- **PostgreSQL** (Optional — all tasks have in-memory/JSON fallbacks)
- **Playwright** (Required for Task 3)
- **API Keys**: 
  - `OPENAI_API_KEY`: Required for Task 2 (Bilingual Agent).
  - `ANTHROPIC_API_KEY`: Required for Task 4 (AI Review Summaries).

### 2. Environment Setup
Create a `.env` file in the root directory (already partially set up for you):
```bash
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Installation
```bash
# Install dependencies for all tasks
pip install -r task2/requirements.txt
pip install -r task3/requirements.txt
pip install -r task4/requirements.txt
playwright install chromium
```

---

## 📂 Repository Structure & Task Overview

### **Task 1: Database Design & AI Knowledge Base**
- **1A (PostgreSQL Schema)**: `task1/schema.sql`. A normalized schema designed for multi-brand customer identity, shared products, and formulation tracking.
- **1B (Vector KB)**: `task1/vector_kb.py`. A local RAG system using **ChromaDB** and **Sentence Transformers** (`all-MiniLM-L6-v2`).
- **Data**: `task1/data.csv` contains packaging details (MOQ, lead times) used to train the KB.

### **Task 2: Bilingual AI Customer Intake Agent**
- **Core**: `task2/main.py` (FastAPI).
- **Features**: 
  - Naturally detects and responds in **English and Urdu**.
  - Qualifies leads by extracting company name, contact info, and product needs.
  - **RAG Integration**: Queries Task 1's Vector KB to answer MOQ/packaging questions in real-time.
- **Run**: `cd task2 && uvicorn main:app --port 8000`

### **Task 3: Price Comparison Scraper**
- **Core**: `task3/scraper.py` (Playwright).
- **Target**: `scrapeme.live/shop`. (Targeted for 100% reliability during evaluation; demonstrates the same logic required for Amazon/eBay).
- **Features**: 
  - Stores data in `price_comparisons` table.
  - **Price Change Detection**: Compares current prices against previous scrapes and flags changes.
  - **Scheduling**: Includes APScheduler for 6-hour interval scraping.
- **Run**: `cd task3 && python scraper.py`

### **Task 4: Shopify Product Review App**
- **Backend**: `task4/app.py` (FastAPI).
- **Shopify Config**: `task4/shopify.app.toml`.
- **Theme Extension**: `task4/extensions/product-reviews/` (Liquid App Block).
- **Features**: 
  - Accepts product reviews via API.
  - **AI Summaries**: Uses **Claude API** to generate one-sentence sentiment summaries for products.
- **Run**: `cd task4 && uvicorn app:app --port 8001`

---

## 🔗 Cross-Task Consistency
This project was designed as a single integrated ecosystem:
- **Unified Database**: All tasks share the schema defined in `task1/schema.sql`.
- **Knowledge Flow**: Task 2's AI agent directly imports and queries the Task 1 Vector KB.
- **Shared Identifiers**: Product SKUs link Task 1 (products), Task 3 (pricing), and Task 4 (reviews).

---

## ⚖️ Tradeoffs & Design Decisions
1. **Playwright over Scrapy**: Chosen because Amazon/cosmetics sites are heavily JS-rendered. Playwright handles this natively as a headless browser.
2. **Local Embeddings**: Used `Sentence Transformers` for the Vector KB. This ensures Task 1 works out-of-the-box without an OpenAI key, while Task 2 uses OpenAI for conversation logic.
3. **In-memory Fallbacks**: Every task (Scraper, Review App, Agent) includes an in-memory or JSON fallback. This ensures the apps remain functional during your evaluation even if a PostgreSQL instance is not active.
4. **FastAPI for Shopify**: While Shopify typically uses Node/Remix, I chose FastAPI for consistency across all tasks, allowing for a unified Python-based tech stack.

---

## 🛠 Manual Testing (CLI / Curl)

**Task 1 (Vector Query):**
```bash
cd task1 && python vector_kb.py --query "What is the MOQ for glass dropper bottles?"
```

**Task 2 (Chat API):**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test_01", "channel": "web", "message": "mujhe serum ke liye bottles chahiye"}'
```

**Task 4 (Review API):**
```bash
curl -X POST http://localhost:8001/api/reviews \
  -H "Content-Type: application/json" \
  -d '{"product_sku": "SKU-GD30", "customer_name": "Ali", "rating": 5, "review_text": "Great quality!"}'
```
