# Task 4: Shopify Product Review App

## Overview
A Shopify-integrated review system that uses AI to summarize customer feedback.

## Features
- **Review Submission**: API and UI for customers to leave ratings and text.
- **AI Sentiment Summary**: Uses the **Claude API (Anthropic)** to generate a concise, one-sentence summary of all reviews for a product.
- **Shopify Admin Panel**: A dashboard for store owners to manage reviews.
- **Storefront Widget**: A simulated Shopify App Block that displays reviews and the AI summary.

## Setup Instructions
1.  **Dependencies**:
    - `pip install fastapi uvicorn anthropic psycopg2-binary`
2.  **Environment**:
    - Ensure `ANTHROPIC_API_KEY` is set in the root `.env` file.
3.  **Run**:
    ```bash
    uvicorn app:app --port 8001
    ```
4.  **View UI**:
    - Admin Dashboard: `http://localhost:8001/admin`
    - Storefront Widget: `http://localhost:8001/storefront/reviews/SKU-GD30`

## Design Notes
- **Tech Stack Consistency**: Used FastAPI (Python) rather than Node.js to maintain a unified tech stack across the entire assessment.
- **Performance**: AI summaries are cached in the `product_reviews` table (Task 1) to reduce latency and API costs.
- **Integration**: Linked to Task 1's product table via the `product_sku` field.
