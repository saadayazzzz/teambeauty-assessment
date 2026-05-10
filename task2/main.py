"""
Task 2: Bilingual AI Customer Intake Agent (English + Urdu)
FastAPI application that qualifies inbound leads via conversational AI.

Design decisions:
- Uses OpenAI's GPT model for language detection, conversation, and field extraction.
  This avoids a separate language detection library and keeps the pipeline simple.
- Conversation state is stored in-memory (dict keyed by session_id).
  For production, this would be Redis or a database.
- The system prompt is bilingual, with hardcoded Urdu instructions so the model
  knows how to respond in Urdu naturally.
- Integrates with Task 1B's ChromaDB vector knowledge base to answer packaging/MOQ questions.
"""

import os
import sys
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI

# --- Add task1 to path so we can import vector_kb ---
TASK1_DIR = os.path.join(os.path.dirname(__file__), "..", "task1")
sys.path.insert(0, TASK1_DIR)

# We import the query function but handle the case where chroma_db doesn't exist yet
try:
    original_cwd = os.getcwd()
    os.chdir(TASK1_DIR)
    from vector_kb import query_database, populate_database, collection
    # Auto-load data if collection is empty
    if collection.count() == 0:
        print("Vector DB empty — auto-loading data.csv...")
        populate_database()
    os.chdir(original_cwd)
    VECTOR_KB_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not load vector KB from task1: {e}")
    VECTOR_KB_AVAILABLE = False

from dotenv import load_dotenv

# Load environment variables from .env file in the root directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# --- Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not set. The agent will not function without it.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(
    title="Team Beauty — Bilingual AI Intake Agent",
    description="Qualifies inbound private-label leads in English and Urdu",
    version="1.0.0"
)

# --- In-memory session store ---
# Key: session_id, Value: dict with conversation history & collected fields
sessions: dict = {}

# --- Required lead fields ---
REQUIRED_FIELDS = [
    "company_name",
    "contact_name",
    "product_category",
    "target_quantity",
    "timeline",
    "brand_goals"
]

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    session_id: str
    channel: str  # e.g. "whatsapp", "instagram", "email", "phone"
    message: str

class ChatResponse(BaseModel):
    reply: str
    language_detected: str
    fields_collected: dict
    complete: bool

class LeadSummary(BaseModel):
    session_id: str
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    product_category: Optional[str] = None
    target_quantity: Optional[str] = None
    timeline: Optional[str] = None
    brand_goals: Optional[str] = None
    channel: Optional[str] = None
    complete: bool = False
    conversation_summary: Optional[str] = None

# --- System Prompt ---
# Design decision: We embed Urdu instructions directly in the system prompt
# so the model knows how to handle both languages natively.
SYSTEM_PROMPT = """You are Agent 01, a bilingual (English and Urdu) customer intake assistant for Team Beauty & Cosmix — a private-labelling and contract manufacturing company in the beauty and cosmetics industry.

Your job is to:
1. DETECT the language of the incoming message (English or Urdu) and ALWAYS respond in the SAME language.
2. Be warm, professional, and helpful.
3. Through natural conversation, collect ALL of the following information:
   - company_name: The name of the prospect's company
   - contact_name: The name of the contact person
   - product_category: What type of product they are interested in (e.g., skincare, haircare, makeup, bodycare, fragrance)
   - target_quantity: Their target order quantity / MOQ expectations
   - timeline: When they need the products delivered or launched
   - brand_goals: What they want to achieve with their brand (e.g., launch a new brand, expand product line, etc.)

4. If they ask about packaging options, MOQs, lead times, or formulation capabilities, answer using the CONTEXT provided below.
5. Do NOT ask for all fields at once. Gather them naturally over the conversation, 1-2 at a time.
6. After EACH message, output a JSON block (fenced with ```json ... ```) containing ONLY the fields you have confidently extracted so far. Use null for fields not yet collected. Format:
```json
{"company_name": "...", "contact_name": "...", "product_category": "...", "target_quantity": "...", "timeline": "...", "brand_goals": "...", "language": "english_or_urdu"}
```

اردو میں جواب دینے کے لیے ہدایات:
- اگر صارف اردو میں پیغام بھیجے تو آپ کو لازمی طور پر اردو میں جواب دینا ہے۔
- اردو میں بات کرتے وقت پیشہ ورانہ اور دوستانہ لہجہ استعمال کریں۔
- تکنیکی اصطلاحات (جیسے MOQ, packaging) انگریزی میں رکھ سکتے ہیں کیونکہ یہ صنعت کی معیاری اصطلاحات ہیں۔

IMPORTANT RULES:
- Always respond in the SAME language the user wrote in.
- Be conversational, not robotic. 
- Always include the JSON extraction block at the end of your response.
"""


def get_kb_context(question: str) -> str:
    """Query the vector knowledge base for relevant packaging info."""
    if not VECTOR_KB_AVAILABLE:
        return ""
    try:
        original_cwd = os.getcwd()
        os.chdir(TASK1_DIR)
        results = query_database(question, n_results=3)
        os.chdir(original_cwd)
        if results and results['documents'] and results['documents'][0]:
            context_parts = []
            for doc in results['documents'][0]:
                context_parts.append(doc)
            return "\n\nRELEVANT PACKAGING KNOWLEDGE:\n" + "\n---\n".join(context_parts)
    except Exception as e:
        print(f"KB query error: {e}")
    return ""


def extract_fields_from_response(response_text: str) -> dict:
    """Extract the JSON field block from the AI response."""
    import json
    import re
    
    # Look for ```json ... ``` block
    pattern = r'```json\s*(\{.*?\})\s*```'
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Fallback: try to find any JSON object in the response
    pattern2 = r'\{[^{}]*"company_name"[^{}]*\}'
    match2 = re.search(pattern2, response_text, re.DOTALL)
    if match2:
        try:
            return json.loads(match2.group(0))
        except json.JSONDecodeError:
            pass
    
    return {}


def clean_reply(response_text: str) -> str:
    """Remove the JSON block from the reply shown to the user."""
    import re
    cleaned = re.sub(r'```json\s*\{.*?\}\s*```', '', response_text, flags=re.DOTALL)
    return cleaned.strip()


def get_session(session_id: str, channel: str = "unknown") -> dict:
    """Get or create a session."""
    if session_id not in sessions:
        sessions[session_id] = {
            "messages": [],
            "fields": {f: None for f in REQUIRED_FIELDS},
            "language": None,
            "channel": channel,
            "complete": False
        }
    return sessions[session_id]


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint. Accepts a message and returns an AI response."""
    session = get_session(request.session_id, request.channel)
    
    if session["complete"]:
        return ChatResponse(
            reply="This lead has already been fully qualified. Use GET /lead/{session_id} to view the summary.",
            language_detected=session.get("language", "english"),
            fields_collected=session["fields"],
            complete=True
        )
    
    # Get relevant context from vector KB
    kb_context = get_kb_context(request.message)
    
    # Build the messages list for the API call
    system_msg = SYSTEM_PROMPT
    if kb_context:
        system_msg += kb_context
    
    api_messages = [{"role": "system", "content": system_msg}]
    
    # Add conversation history
    for msg in session["messages"]:
        api_messages.append(msg)
    
    # Add the new user message
    api_messages.append({"role": "user", "content": request.message})
    
    # Call OpenAI
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=api_messages,
            temperature=0.7,
            max_tokens=1000
        )
        assistant_reply = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")
    
    # Extract fields from the response
    extracted = extract_fields_from_response(assistant_reply)
    
    # Detect language from extraction
    language = extracted.get("language", session.get("language", "english"))
    if language:
        session["language"] = language
    
    # Update session fields (only overwrite with non-null values)
    for field in REQUIRED_FIELDS:
        if field in extracted and extracted[field] is not None:
            session["fields"][field] = extracted[field]
    
    # Check completeness
    all_collected = all(session["fields"].get(f) is not None for f in REQUIRED_FIELDS)
    if all_collected:
        session["complete"] = True
    
    # Save messages to session history
    session["messages"].append({"role": "user", "content": request.message})
    session["messages"].append({"role": "assistant", "content": assistant_reply})
    
    # Clean the reply (remove JSON block) for user-facing response
    user_reply = clean_reply(assistant_reply)
    
    return ChatResponse(
        reply=user_reply,
        language_detected=language or "english",
        fields_collected=session["fields"],
        complete=session["complete"]
    )


@app.get("/lead/{session_id}", response_model=LeadSummary)
async def get_lead(session_id: str):
    """Returns the structured lead summary once complete."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session["complete"]:
        raise HTTPException(
            status_code=400,
            detail="Lead qualification is not yet complete. Continue the conversation via POST /chat."
        )
    
    fields = session["fields"]
    return LeadSummary(
        session_id=session_id,
        company_name=fields.get("company_name"),
        contact_name=fields.get("contact_name"),
        product_category=fields.get("product_category"),
        target_quantity=fields.get("target_quantity"),
        timeline=fields.get("timeline"),
        brand_goals=fields.get("brand_goals"),
        channel=session.get("channel"),
        complete=True,
        conversation_summary=f"Lead qualified over {len(session['messages'])//2} messages via {session.get('channel', 'unknown')} channel."
    )


@app.get("/")
async def root():
    return {
        "service": "Team Beauty — Bilingual AI Intake Agent",
        "endpoints": {
            "POST /chat": "Send a message to the agent",
            "GET /lead/{session_id}": "Get the lead summary"
        }
    }
