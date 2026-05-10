# Task 1: Database Design & AI Knowledge Base

## Overview
This task establishes the core data infrastructure for the Team Beauty & Cosmix ecosystem. It consists of two main components:
1.  **PostgreSQL Schema**: A unified data model for customers, brands, products, formulations, price comparisons, and reviews.
2.  **AI Knowledge Base (Vector DB)**: A local RAG system that stores and retrieves technical product specifications (MOQs, lead times, materials).

## Files
- `schema.sql`: The complete PostgreSQL schema.
- `vector_kb.py`: Python script to manage the ChromaDB vector store.
- `data.csv`: Raw packaging data used to train the Knowledge Base.

## Setup Instructions
1.  **PostgreSQL**:
    - Run the commands in `schema.sql` to initialize your database.
2.  **Vector KB**:
    - Install dependencies: `pip install chromadb sentence-transformers pandas`
    - Run the script to populate/query:
      ```bash
      python vector_kb.py --query "What is the MOQ for glass dropper bottles?"
      ```

## Design Notes
- **Normalization**: The schema is normalized to ensure a single customer identity across multiple brands.
- **Local Embeddings**: We use `all-MiniLM-L6-v2` for embeddings, allowing the vector store to run entirely offline without requiring OpenAI credits for the indexing phase.
- **SKU-Centric Design**: The `sku` field is the primary link between the product catalog, scraper results (Task 3), and reviews (Task 4).
