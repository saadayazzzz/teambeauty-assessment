# Task 2: Bilingual AI Customer Intake Agent

A FastAPI application that simulates **Agent 01** — the first AI agent in Team Beauty & Cosmix's lead qualification pipeline. It handles inbound enquiries in **English and Urdu** via a REST API.

## Features
- **Bilingual**: Automatically detects English/Urdu and responds in the same language
- **Conversational Lead Qualification**: Naturally collects company name, contact name, product category, target quantity, timeline, and brand goals
- **Vector KB Integration**: Answers packaging/MOQ questions using the ChromaDB knowledge base from Task 1B
- **Session Management**: Maintains conversation state across multiple messages
- **Structured Output**: Returns a complete lead summary when all fields are collected

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your OpenAI API key
```bash
# Linux/Mac
export OPENAI_API_KEY="sk-your-key-here"

# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-key-here"
```

### 3. Load the vector knowledge base (from Task 1)
```bash
cd ../task1
python vector_kb.py --load
cd ../task2
```

### 4. Run the server
```bash
uvicorn main:app --reload --port 8000
```

## API Specification

### `POST /chat`
Send a message to the agent.

**Request:**
```json
{
  "session_id": "session_001",
  "channel": "whatsapp",
  "message": "Hi, I'm looking for private label skincare products"
}
```

**Response:**
```json
{
  "reply": "Welcome to Team Beauty & Cosmix! ...",
  "language_detected": "english",
  "fields_collected": {
    "company_name": null,
    "contact_name": null,
    "product_category": "skincare",
    "target_quantity": null,
    "timeline": null,
    "brand_goals": null
  },
  "complete": false
}
```

### `GET /lead/{session_id}`
Returns the structured lead summary once all fields are collected.

**Response:**
```json
{
  "session_id": "session_001",
  "company_name": "Glow Cosmetics",
  "contact_name": "Sara Ahmed",
  "product_category": "skincare",
  "target_quantity": "1000 units",
  "timeline": "3 months",
  "brand_goals": "Launch a premium skincare line",
  "channel": "whatsapp",
  "complete": true,
  "conversation_summary": "Lead qualified over 5 messages via whatsapp channel."
}
```

## Example Conversations

### English (curl)
```bash
# Message 1
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "eng_01", "channel": "whatsapp", "message": "Hi, I am looking for a private label partner for skincare products"}'

# Message 2
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "eng_01", "channel": "whatsapp", "message": "My name is Sara from Glow Cosmetics. We want to launch a serum line with about 1000 units in the next 3 months."}'

# Message 3
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "eng_01", "channel": "whatsapp", "message": "Our goal is to create a premium skincare brand targeting millennials."}'

# Get lead summary
curl http://localhost:8000/lead/eng_01
```

### Urdu (curl)
```bash
# Message 1
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "urdu_01", "channel": "instagram", "message": "السلام علیکم، میں سکن کیئر پروڈکٹس کے لیے پرائیویٹ لیبل پارٹنر تلاش کر رہا ہوں"}'

# Message 2
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "urdu_01", "channel": "instagram", "message": "میرا نام احمد ہے اور میری کمپنی کا نام روشنی کاسمیٹکس ہے۔ ہمیں 2000 یونٹس چاہئیں اگلے 2 مہینوں میں۔ ہمارا مقصد ایک نئی بیوٹی برانڈ لانچ کرنا ہے۔"}'

# Get lead summary
curl http://localhost:8000/lead/urdu_01
```

## Design Notes

### Language Detection Approach
Rather than using a separate language detection library (like `langdetect`), we leverage the LLM itself to detect the language. This is more robust for mixed-script messages and avoids adding another dependency. The system prompt contains instructions in both English and Urdu, so the model naturally responds in the appropriate language.

### System Prompt Design
The system prompt includes hardcoded Urdu instructions (اردو میں ہدایات) so the model understands it should:
1. Detect the language from the user's message
2. Respond entirely in the detected language
3. Keep technical terms (MOQ, packaging) in English as they are industry standard

### Vector KB Integration
When a user asks about packaging, MOQs, or lead times, the agent queries the ChromaDB knowledge base from Task 1B and includes the relevant context in the system prompt. This gives the agent accurate, up-to-date information to share.
