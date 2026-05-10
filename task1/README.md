# Task 1: Database Design & AI Knowledge Base

This folder contains the solutions for Task 1A and 1B.

## Task 1A: Schema Design
The schema is defined in `schema.sql`. 

### Design Decisions:
1. **Shared Customer Identity**: Customers are decoupled from brands. A single `customers` table exists. The relationship between a brand and a customer is tracked implicitly via the `orders` table. This allows a unified view of the customer across brands without needing complex mapping tables.
2. **Formulations**: The `product_formulations` table acts as a many-to-many junction between `products` and `raw_materials`, including the `quantity_required` for the recipe.
3. **Cross-Task Consistency**: 
   - A `price_comparisons` table is included for **Task 3**, storing scraped data and tracking price changes.
   - A `product_reviews` table is included for **Task 4**, linked to the product SKU and including a column for the AI-generated summary.

## Task 1B: Vector Knowledge Base Setup
The Python script `vector_kb.py` creates a local Chroma vector database and populates it with embeddings from `data.csv`.

### Setup Instructions
1. Install requirements:
   ```bash
   pip install pandas chromadb sentence-transformers
   ```
2. Run the script (CLI included):
   ```bash
   python vector_kb.py
   ```

### Chunking Strategy
The script uses row-based chunking. Since the data is highly structured (packaging options, MOQs, lead times), each row is concatenated into a natural language sentence or paragraph. This ensures that the context of "MOQ" and "Lead Time" remains directly attached to the specific "Product" and "Packaging" being discussed, preventing context loss that might occur with naive character-based splitting.
