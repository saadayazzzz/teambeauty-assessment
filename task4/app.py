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

# --- Configuration ---
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "teambeauty"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

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
def get_db():
    """Get a database connection. Returns None if unavailable."""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"DB unavailable: {e}")
        return None


def db_save_review(review: ReviewSubmission) -> dict:
    """Save a review to the database."""
    conn = get_db()
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
    conn = get_db()
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
    conn = get_db()
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


# --- Shopify Admin Embed (simplified) ---
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    """
    Shopify admin embedded panel.
    In a real Shopify app, this would be served within the Shopify admin iframe
    using the App Bridge library. This is a simplified standalone version
    that demonstrates the review management UI.
    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Team Beauty Reviews — Admin</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f6f6f7; color: #202223; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { font-size: 20px; margin-bottom: 20px; }
            .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
            .card h2 { font-size: 16px; margin-bottom: 12px; }
            input, textarea, select { width: 100%; padding: 8px 12px; border: 1px solid #c9cccf; border-radius: 6px; margin-bottom: 10px; font-size: 14px; }
            button { background: #008060; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; }
            button:hover { background: #006e52; }
            .review { border-bottom: 1px solid #e1e3e5; padding: 12px 0; }
            .review:last-child { border-bottom: none; }
            .stars { color: #f5a623; font-size: 16px; }
            .summary-box { background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
            .summary-box h3 { color: #166534; margin-bottom: 8px; }
            #loading { display: none; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧴 Product Reviews — Admin Dashboard</h1>

            <div class="card">
                <h2>Look Up Reviews</h2>
                <input type="text" id="skuInput" placeholder="Enter Product SKU (e.g., TB-SERUM-001)" />
                <button onclick="loadReviews()">Load Reviews</button>
                <span id="loading"> Loading...</span>
            </div>

            <div id="summarySection" style="display:none;">
                <div class="summary-box">
                    <h3>🤖 AI Summary</h3>
                    <p id="aiSummary"></p>
                    <p style="margin-top:8px; font-size:13px; color:#666;">
                        <span id="totalReviews"></span> reviews · Average: <span id="avgRating"></span>/5
                    </p>
                </div>
            </div>

            <div id="reviewsList"></div>

            <div class="card" style="margin-top: 24px;">
                <h2>Submit a Test Review</h2>
                <input type="text" id="testSku" placeholder="Product SKU" />
                <input type="text" id="testName" placeholder="Customer Name" />
                <select id="testRating">
                    <option value="5">⭐⭐⭐⭐⭐ (5)</option>
                    <option value="4">⭐⭐⭐⭐ (4)</option>
                    <option value="3">⭐⭐⭐ (3)</option>
                    <option value="2">⭐⭐ (2)</option>
                    <option value="1">⭐ (1)</option>
                </select>
                <textarea id="testReview" placeholder="Write your review..." rows="3"></textarea>
                <button onclick="submitReview()">Submit Review</button>
            </div>
        </div>

        <script>
            const API = window.location.origin;

            async function loadReviews() {
                const sku = document.getElementById('skuInput').value.trim();
                if (!sku) return alert('Enter a product SKU');
                document.getElementById('loading').style.display = 'inline';

                try {
                    const res = await fetch(`${API}/api/reviews/${sku}`);
                    const data = await res.json();

                    document.getElementById('summarySection').style.display = 'block';
                    document.getElementById('aiSummary').textContent = data.ai_summary;
                    document.getElementById('totalReviews').textContent = data.total_reviews;
                    document.getElementById('avgRating').textContent = data.average_rating;

                    const list = document.getElementById('reviewsList');
                    if (data.reviews.length === 0) {
                        list.innerHTML = '<div class="card"><p>No reviews found for this SKU.</p></div>';
                    } else {
                        list.innerHTML = data.reviews.map(r => `
                            <div class="card review">
                                <div class="stars">${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</div>
                                <strong>${r.customer_name}</strong>
                                <p>${r.review_text}</p>
                                <small style="color:#666;">${r.created_at}</small>
                            </div>
                        `).join('');
                    }
                } catch (e) {
                    alert('Error loading reviews: ' + e.message);
                }
                document.getElementById('loading').style.display = 'none';
            }

            async function submitReview() {
                const body = {
                    product_sku: document.getElementById('testSku').value.trim(),
                    customer_name: document.getElementById('testName').value.trim(),
                    rating: parseInt(document.getElementById('testRating').value),
                    review_text: document.getElementById('testReview').value.trim(),
                };
                if (!body.product_sku || !body.customer_name || !body.review_text) {
                    return alert('Fill in all fields');
                }
                try {
                    const res = await fetch(`${API}/api/reviews`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(body),
                    });
                    if (res.ok) {
                        alert('Review submitted!');
                        document.getElementById('testReview').value = '';
                    } else {
                        const err = await res.json();
                        alert('Error: ' + JSON.stringify(err));
                    }
                } catch (e) {
                    alert('Error: ' + e.message);
                }
            }
        </script>
    </body>
    </html>
    """


# --- Shopify Storefront App Block (Theme Extension) ---
@app.get("/storefront/reviews/{product_sku}", response_class=HTMLResponse)
async def storefront_reviews_block(product_sku: str):
    """
    Storefront App Block — renders reviews on the product page.
    In a real Shopify app, this would be a Liquid theme extension (App Block).
    This endpoint simulates the rendered output that would appear on the product page.
    The Shopify App Proxy would route requests to this endpoint.
    """
    reviews = db_get_reviews(product_sku)
    ai_summary = generate_ai_summary(reviews) if reviews else ""
    avg_rating = sum(r["rating"] for r in reviews) / len(reviews) if reviews else 0

    reviews_html = ""
    for r in reviews:
        stars = "★" * r["rating"] + "☆" * (5 - r["rating"])
        reviews_html += f"""
        <div class="tb-review">
            <div class="tb-stars">{stars}</div>
            <strong>{r['customer_name']}</strong>
            <p>{r['review_text']}</p>
        </div>
        """

    return f"""
    <div class="tb-reviews-widget" style="font-family: sans-serif; max-width: 600px; margin: 20px auto; padding: 20px;">
        <h3>Customer Reviews</h3>
        {f'<div style="background:#f0fdf4;padding:12px;border-radius:8px;margin-bottom:16px;"><strong>Summary:</strong> {ai_summary}</div>' if ai_summary else ''}
        {f'<p>Average Rating: {"★" * round(avg_rating)}{"☆" * (5 - round(avg_rating))} ({avg_rating:.1f}/5 from {len(reviews)} reviews)</p>' if reviews else ''}
        
        {reviews_html if reviews else '<p>No reviews yet. Be the first to review this product!</p>'}
        
        <hr style="margin:20px 0;">
        <h4>Write a Review</h4>
        <form id="tb-review-form" onsubmit="return submitStorefrontReview(event)">
            <input type="hidden" name="product_sku" value="{product_sku}" />
            <div style="margin-bottom:10px;">
                <input type="text" name="customer_name" placeholder="Your Name" required style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;" />
            </div>
            <div style="margin-bottom:10px;">
                <select name="rating" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;">
                    <option value="5">⭐⭐⭐⭐⭐ (5)</option>
                    <option value="4">⭐⭐⭐⭐ (4)</option>
                    <option value="3">⭐⭐⭐ (3)</option>
                    <option value="2">⭐⭐ (2)</option>
                    <option value="1">⭐ (1)</option>
                </select>
            </div>
            <div style="margin-bottom:10px;">
                <textarea name="review_text" placeholder="Write your review..." rows="3" required style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;"></textarea>
            </div>
            <button type="submit" style="background:#008060;color:white;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;">Submit Review</button>
        </form>
    </div>
    <script>
    async function submitStorefrontReview(e) {{
        e.preventDefault();
        const form = e.target;
        const body = {{
            product_sku: form.product_sku.value,
            customer_name: form.customer_name.value,
            rating: parseInt(form.rating.value),
            review_text: form.review_text.value,
        }};
        const res = await fetch('/api/reviews', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(body),
        }});
        if (res.ok) {{
            alert('Thank you for your review!');
            location.reload();
        }}
    }}
    </script>
    """


@app.get("/")
async def root():
    return {
        "service": "Team Beauty — Product Review App",
        "admin_panel": "/admin",
        "endpoints": {
            "POST /api/reviews": "Submit a review",
            "GET /api/reviews/{product_sku}": "Get reviews + AI summary",
            "GET /storefront/reviews/{product_sku}": "Storefront widget",
        },
    }
