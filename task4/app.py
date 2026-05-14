"""
Task 4: Shopify Product Review App — Backend Server

A lightweight Express-like server (using FastAPI) that:
1. Serves as the Shopify app backend (embeds in admin)
2. Accepts review submissions via API
3. Stores reviews in PostgreSQL (product_reviews table from Task 1)
4. Uses Claude API to generate AI summaries of reviews
5. Serves review data to the storefront theme extension (App Block)

Design decision: Using FastAPI (Python) rather than Node/Remix for consistency
with the rest of the assessment. The Shopify App Proxy pattern is used for
storefront integration.
"""

import os
import json
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
from anthropic import Anthropic

# Add root to path to import shared database utility
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import get_db_connection

CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# In-memory fallback if DB is unavailable
in_memory_reviews: dict = {}  # keyed by product_sku

app = FastAPI(
    title="Team Beauty — Product Review App",
    description="Shopify embedded app for product reviews with AI summaries",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your Shopify store domain
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---
class ReviewSubmission(BaseModel):
    product_sku: str
    customer_name: str = Field(..., min_length=1, max_length=255)
    rating: int = Field(..., ge=1, le=5)
    review_text: str = Field(..., min_length=1)


class ReviewResponse(BaseModel):
    id: int
    product_sku: str
    customer_name: str
    rating: int
    review_text: str
    created_at: str


class ReviewSummaryResponse(BaseModel):
    product_sku: str
    total_reviews: int
    average_rating: float
    ai_summary: str
    reviews: List[ReviewResponse]


# --- Database helpers ---
def db_save_review(review: ReviewSubmission) -> dict:
    """Save a review to the database."""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                INSERT INTO product_reviews (product_sku, customer_name, rating, review_text, created_at)
                VALUES (%s, %s, %s, %s, %s) RETURNING id, product_sku, customer_name, rating, review_text, created_at
                """,
                (review.product_sku, review.customer_name, review.rating, review.review_text, datetime.now()),
            )
            result = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return dict(result)
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"DB insert error: {e}")

    # Fallback to in-memory
    review_id = len(in_memory_reviews.get(review.product_sku, [])) + 1
    review_data = {
        "id": review_id,
        "product_sku": review.product_sku,
        "customer_name": review.customer_name,
        "rating": review.rating,
        "review_text": review.review_text,
        "created_at": datetime.now().isoformat(),
    }
    if review.product_sku not in in_memory_reviews:
        in_memory_reviews[review.product_sku] = []
    in_memory_reviews[review.product_sku].append(review_data)
    return review_data


def db_get_reviews(product_sku: str) -> list:
    """Get all reviews for a product."""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT id, product_sku, customer_name, rating, review_text, created_at FROM product_reviews WHERE product_sku = %s ORDER BY created_at DESC",
                (product_sku,),
            )
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            conn.close()
            print(f"DB query error: {e}")

    # Fallback
    return in_memory_reviews.get(product_sku, [])


def db_save_ai_summary(product_sku: str, summary: str):
    """Update the AI summary for reviews of a product."""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE product_reviews SET ai_summary = %s WHERE product_sku = %s",
                (summary, product_sku),
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            conn.close()
            print(f"DB update error: {e}")


# --- AI Summary ---
def generate_ai_summary(reviews: list) -> str:
    """Use Claude API to generate a one-sentence summary of all reviews."""
    if not reviews:
        return "No reviews yet."

    if not CLAUDE_API_KEY:
        # Fallback if no API key — generate a basic summary
        avg_rating = sum(r["rating"] for r in reviews) / len(reviews)
        return f"Based on {len(reviews)} reviews with an average rating of {avg_rating:.1f}/5."

    client = Anthropic(api_key=CLAUDE_API_KEY)

    review_texts = "\n".join(
        [f"- Rating: {r['rating']}/5 — \"{r['review_text']}\"" for r in reviews]
    )

    try:
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=150,
            messages=[
                {
                    "role": "user",
                    "content": f"""You are summarizing product reviews for a cosmetics brand. 
Generate a single, concise sentence that captures the overall sentiment and key themes from these reviews.
Example output: "Customers love the texture but note the scent is strong"

Reviews:
{review_texts}

One-sentence summary:""",
                }
            ],
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"Claude API error: {e}")
        avg_rating = sum(r["rating"] for r in reviews) / len(reviews)
        return f"Based on {len(reviews)} reviews with an average rating of {avg_rating:.1f}/5."


# --- API Endpoints ---

@app.post("/api/reviews", response_model=ReviewResponse)
async def submit_review(review: ReviewSubmission):
    """Submit a new product review."""
    saved = db_save_review(review)
    return ReviewResponse(
        id=saved["id"],
        product_sku=saved["product_sku"],
        customer_name=saved["customer_name"],
        rating=saved["rating"],
        review_text=saved["review_text"],
        created_at=str(saved["created_at"]),
    )


@app.get("/api/reviews/{product_sku}", response_model=ReviewSummaryResponse)
async def get_reviews(product_sku: str):
    """Get all reviews and AI summary for a product."""
    reviews = db_get_reviews(product_sku)
    
    avg_rating = 0.0
    if reviews:
        avg_rating = sum(r["rating"] for r in reviews) / len(reviews)

    # Generate AI summary
    ai_summary = generate_ai_summary(reviews)

    # Save AI summary back to DB
    if reviews:
        db_save_ai_summary(product_sku, ai_summary)

    review_responses = [
        ReviewResponse(
            id=r["id"],
            product_sku=r["product_sku"],
            customer_name=r["customer_name"],
            rating=r["rating"],
            review_text=r["review_text"],
            created_at=str(r["created_at"]),
        )
        for r in reviews
    ]

    return ReviewSummaryResponse(
        product_sku=product_sku,
        total_reviews=len(reviews),
        average_rating=round(avg_rating, 1),
        ai_summary=ai_summary,
        reviews=review_responses,
    )


# --- Shopify Admin Embed (Polaris Inspired) ---
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Team Beauty | Review Management</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; background-color: #f1f2f4; color: #202223; }
            .polaris-card { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e1e3e5; }
            .polaris-btn { background: #008060; color: white; padding: 8px 16px; border-radius: 6px; font-weight: 500; transition: all 0.2s; }
            .polaris-btn:hover { background: #006e52; }
        </style>
    </head>
    <body class="p-8">
        <div class="max-w-5xl mx-auto">
            <header class="flex justify-between items-center mb-8">
                <div>
                    <h1 class="text-2xl font-semibold text-gray-900">Product Reviews</h1>
                    <p class="text-gray-500">Manage customer feedback and AI-generated insights.</p>
                </div>
                <a href="/storefront" target="_blank" class="text-indigo-600 font-medium hover:underline">View Live Store →</a>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="polaris-card p-6">
                    <h3 class="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">Total Reviews</h3>
                    <p class="text-3xl font-bold text-gray-900" id="statTotal">-</p>
                </div>
                <div class="polaris-card p-6">
                    <h3 class="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">Avg. Sentiment</h3>
                    <p class="text-3xl font-bold text-green-600" id="statSentiment">Positive</p>
                </div>
                <div class="polaris-card p-6">
                    <h3 class="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">AI Summaries</h3>
                    <p class="text-3xl font-bold text-gray-900">Active</p>
                </div>
            </div>

            <div class="polaris-card mb-8">
                <div class="p-6 border-b border-gray-200">
                    <h2 class="text-lg font-semibold">Review Lookup</h2>
                </div>
                <div class="p-6 flex gap-4">
                    <input type="text" id="skuInput" placeholder="Enter Product SKU (e.g., SKU-GD30)" class="flex-1 border border-gray-300 rounded-md px-4 py-2 focus:ring-2 focus:ring-green-500 outline-none">
                    <button onclick="loadReviews()" class="polaris-btn">Analyze Reviews</button>
                </div>
            </div>

            <div id="aiSummarySection" class="hidden mb-8">
                <div class="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-100 rounded-xl p-6 shadow-sm">
                    <div class="flex items-center gap-2 mb-3">
                        <span class="text-xl">🤖</span>
                        <h3 class="font-bold text-emerald-900 uppercase text-sm tracking-widest">AI Synthesis Summary</h3>
                    </div>
                    <p id="aiSummary" class="text-lg text-emerald-800 leading-relaxed italic"></p>
                </div>
            </div>

            <div id="reviewsList" class="space-y-4"></div>
            
            <div class="polaris-card mt-12 p-6">
                <h2 class="text-lg font-semibold mb-4">Submit a Test Review</h2>
                <div class="grid grid-cols-2 gap-4 mb-4">
                    <input type="text" id="testSku" placeholder="Product SKU" class="border border-gray-300 rounded-md px-4 py-2">
                    <input type="text" id="testName" placeholder="Customer Name" class="border border-gray-300 rounded-md px-4 py-2">
                </div>
                <select id="testRating" class="w-full border border-gray-300 rounded-md px-4 py-2 mb-4">
                    <option value="5">⭐⭐⭐⭐⭐ (5)</option>
                    <option value="4">⭐⭐⭐⭐ (4)</option>
                    <option value="3">⭐⭐⭐ (3)</option>
                    <option value="2">⭐⭐ (2)</option>
                    <option value="1">⭐ (1)</option>
                </select>
                <textarea id="testReview" placeholder="Write your review..." rows="3" class="w-full border border-gray-300 rounded-md px-4 py-2 mb-4"></textarea>
                <button onclick="submitReview()" class="polaris-btn w-full">Submit Review</button>
            </div>
        </div>

        <script>
            async function loadReviews() {
                const sku = document.getElementById('skuInput').value.trim();
                if (!sku) return;
                
                const res = await fetch(`/api/reviews/${sku}`);
                const data = await res.json();

                document.getElementById('statTotal').textContent = data.total_reviews;
                
                if (data.total_reviews > 0) {
                    document.getElementById('aiSummarySection').classList.remove('hidden');
                    document.getElementById('aiSummary').textContent = `"${data.ai_summary}"`;
                }

                const list = document.getElementById('reviewsList');
                list.innerHTML = data.reviews.map(r => `
                    <div class="polaris-card p-6">
                        <div class="flex justify-between items-start mb-4">
                            <div>
                                <span class="text-yellow-400 text-lg">${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</span>
                                <h4 class="font-bold text-gray-900">${r.customer_name}</h4>
                            </div>
                            <span class="text-xs text-gray-400">${new Date(r.created_at).toLocaleDateString()}</span>
                        </div>
                        <p class="text-gray-700 leading-relaxed">${r.review_text}</p>
                    </div>
                `).join('') || '<div class="text-center py-12 text-gray-400">No reviews found for this product.</div>';
            }

            async function submitReview() {
                const body = {
                    product_sku: document.getElementById('testSku').value.trim(),
                    customer_name: document.getElementById('testName').value.trim(),
                    rating: parseInt(document.getElementById('testRating').value),
                    review_text: document.getElementById('testReview').value.trim(),
                };
                const res = await fetch('/api/reviews', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body),
                });
                if (res.ok) {
                    alert('Review submitted!');
                    loadReviews();
                }
            }
        </script>
    </body>
    </html>
    """

# --- Live Storefront Simulator ---
@app.get("/storefront", response_class=HTMLResponse)
async def storefront_sim():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Team Beauty | Hydrating Glow Serum</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { font-family: 'Helvetica Neue', Arial, sans-serif; }
            .btn-buy { background: #000; color: #fff; width: 100%; padding: 16px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
        </style>
    </head>
    <body class="bg-white">
        <nav class="border-b p-4 flex justify-between items-center px-12">
            <div class="font-black text-2xl tracking-tighter">TEAM BEAUTY.</div>
            <div class="space-x-8 text-sm font-medium">
                <a href="#">SKINCARE</a>
                <a href="#">MAKEUP</a>
                <a href="#">NEW ARRIVALS</a>
            </div>
            <div class="text-xl">🛒</div>
        </nav>

        <main class="max-w-7xl mx-auto px-12 py-16 grid grid-cols-1 md:grid-cols-2 gap-16">
            <div class="bg-gray-100 rounded-2xl flex items-center justify-center p-12 min-h-[500px]">
                <div class="text-center">
                    <div class="text-8xl mb-4">🧴</div>
                    <div class="text-gray-400 font-medium">30ml / 1.0 fl.oz</div>
                </div>
            </div>

            <div class="py-4">
                <div class="flex items-center gap-2 mb-4">
                    <span class="text-yellow-400">★★★★★</span>
                    <span class="text-sm text-gray-500 underline">4.8 (124 reviews)</span>
                </div>
                <h1 class="text-5xl font-bold mb-4 tracking-tight">Glow Serum 30ml</h1>
                <p class="text-2xl font-light mb-8">£25.00</p>
                <div class="prose text-gray-600 mb-12">
                    A potent blend of Vitamin C and Hyaluronic acid designed to brighten and hydrate your skin instantly.
                </div>
                <button class="btn-buy hover:bg-gray-800 transition">Add to Bag</button>

                <div id="review-extension" class="border-t mt-12 pt-12">
                    <h3 class="text-xl font-bold mb-6">Customer Insights</h3>
                    <div id="extension-content">
                        <div class="animate-pulse bg-gray-100 h-24 rounded-lg"></div>
                    </div>
                </div>
            </div>
        </main>

        <script>
            async function loadExtension() {
                const res = await fetch('/api/reviews/SKU-GD30');
                const data = await res.json();
                const container = document.getElementById('extension-content');
                container.innerHTML = `
                    <div class="bg-indigo-50 border border-indigo-100 p-6 rounded-xl mb-8">
                        <div class="flex items-center gap-2 mb-2">
                            <span class="text-sm font-bold text-indigo-900 uppercase">AI Summary</span>
                        </div>
                        <p class="text-indigo-800 italic text-lg leading-relaxed">"${data.ai_summary}"</p>
                    </div>
                    <div class="space-y-6">
                        ${data.reviews.slice(0, 2).map(r => `
                            <div class="border-b pb-4">
                                <div class="text-yellow-400 text-xs mb-1">${'★'.repeat(r.rating)}</div>
                                <div class="font-bold text-sm uppercase">${r.customer_name}</div>
                                <p class="text-gray-600 text-sm mt-1">${r.review_text}</p>
                            </div>
                        `).join('')}
                    </div>
                `;
            }
            loadExtension();
        </script>
    </body>
    </html>
    """

@app.get("/")
async def root():
    return {
        "service": "Team Beauty — Product Review App",
        "admin_panel": "/admin",
        "storefront": "/storefront",
        "endpoints": {
            "POST /api/reviews": "Submit a review",
            "GET /api/reviews/{product_sku}": "Get reviews + AI summary",
        },
    }
