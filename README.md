# Team Beauty & Cosmix — Technical Assessment

## 👋 Approach

I approached this assessment by **reading all four tasks end-to-end first**, then designing a shared foundation (database schema) that supports all tasks before writing any feature code. This is why:

- The `price_comparisons` and `product_reviews` tables appear in the Task 1 schema — they were designed to support Tasks 3 and 4 from the start.
- The vector knowledge base from Task 1B is directly imported by the Task 2 agent, so packaging/MOQ data flows naturally into the conversation.
- All tasks share the same PostgreSQL database and consistent data models.

## 📁 Repository Structure

```
teambeauty-assessment/
├── README.md                          ← You are here
├── task1/
│   ├── README.md                      ← Setup & design notes
│   ├── schema.sql                     ← PostgreSQL schema (shared across tasks)
│   ├── data.csv                       ← Sample packaging data (14 rows)
│   └── vector_kb.py                   ← Vector knowledge base (ChromaDB + CLI)
├── task2/
│   ├── README.md                      ← API docs & curl examples
│   ├── main.py                        ← FastAPI bilingual AI agent
│   └── requirements.txt
├── task3/
│   ├── README.md                      ← Setup & design notes
│   ├── scraper.py                     ← Playwright price scraper
│   └── requirements.txt
└── task4/
    ├── README.md                      ← Setup & Shopify integration guide
    ├── app.py                         ← FastAPI review app backend
    ├── requirements.txt
    ├── shopify.app.toml               ← Shopify app config
    └── extensions/
        └── product-reviews/
            └── blocks/
                └── reviews.liquid     ← Storefront App Block
```

## 🤖 AI Tools Used

| Tool | Where Used | How |
|------|-----------|-----|
| **OpenAI GPT-4o-mini** | Task 2 | Powers the bilingual conversation agent. Handles language detection, lead qualification, and natural dialogue. |
| **Claude API (Haiku)** | Task 4 | Generates one-sentence AI summaries of product reviews. |
| **Sentence Transformers** | Task 1B | `all-MiniLM-L6-v2` model generates embeddings locally for the vector knowledge base. No API key required. |
| **ChromaDB** | Task 1B & 2 | Local vector store. Used in Task 1B for storage and queried in Task 2 for RAG. |

## ⚖️ Tradeoffs Under Time Pressure

1. **In-memory session storage (Task 2)**: Sessions are stored in a Python dict. For production, I'd use Redis or PostgreSQL-backed sessions. The tradeoff is simplicity vs. durability — sessions are lost on restart.

2. **FastAPI for Shopify app (Task 4)**: Shopify CLI scaffolds a Remix/Node app. I chose FastAPI for consistency with Tasks 2 and 3. The core review flow (submission, AI summary, display) works identically — only the Shopify App Bridge integration layer differs.

3. **Amazon UK as scraper target (Task 3)**: Selected for reliable pricing data on cosmetic packaging. Playwright handles the JS-heavy rendering. The scraper includes graceful fallback to JSON storage if PostgreSQL is unavailable.

4. **Sentence Transformers over OpenAI embeddings (Task 1B)**: Runs locally without an API key, making it easier to evaluate. Trades some embedding quality for zero-config setup.

5. **Row-based chunking (Task 1B)**: Each CSV row becomes one semantic chunk. Given the highly structured nature of the data (each row = one packaging option), this preserves context better than character-based splitting.

## 🚀 Quick Start (All Tasks)

### Prerequisites
- Python 3.10+
- PostgreSQL (optional — all tasks have fallbacks)
- API keys: `OPENAI_API_KEY` (Task 2), `ANTHROPIC_API_KEY` (Task 4)

### 1. Set up the database (optional)
```bash
createdb teambeauty
psql -U postgres -d teambeauty -f task1/schema.sql
```

### 2. Install all dependencies
```bash
pip install -r task2/requirements.txt
pip install -r task3/requirements.txt
pip install -r task4/requirements.txt
playwright install chromium
```

### 3. Run each task
```bash
# Task 1B: Load vector knowledge base
cd task1 && python vector_kb.py --load
python vector_kb.py --query "What is the MOQ for glass dropper bottles?"

# Task 2: Start the AI agent
cd task2 && uvicorn main:app --reload --port 8000

# Task 3: Run the price scraper
cd task3 && python scraper.py

# Task 4: Start the review app
cd task4 && uvicorn app:app --reload --port 8001
```

## 🔗 Cross-Task Consistency

| Shared Element | Tasks |
|---------------|-------|
| PostgreSQL schema (`schema.sql`) | All tasks |
| `price_comparisons` table | Task 1 schema → Task 3 storage |
| `product_reviews` table | Task 1 schema → Task 4 storage |
| Vector KB (ChromaDB) | Task 1B creation → Task 2 queries |
| Product SKU as identifier | Task 1 products → Task 4 reviews |
| Consistent Python/FastAPI stack | Tasks 2, 3, 4 |
