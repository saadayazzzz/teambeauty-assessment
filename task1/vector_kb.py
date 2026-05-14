import argparse
import os
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
import warnings

# Suppress some noisy warnings from sentence-transformers if they occur
warnings.filterwarnings("ignore")

# Base directory of the script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize ChromaDB client (local persistent storage)
# We store it in a local directory 'chroma_db' relative to the script
client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))

# Use the default Sentence Transformer embedding function (all-MiniLM-L6-v2)
# This is an open-source alternative that runs locally and doesn't require an API key
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Get or create a collection
collection = client.get_or_create_collection(
    name="packaging_knowledge",
    embedding_function=sentence_transformer_ef
)

def populate_database(csv_path=None):
    """Reads the CSV, chunks the data, and stores it in ChromaDB."""
    if csv_path is None:
        csv_path = os.path.join(BASE_DIR, "data.csv")
    
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: Could not find {csv_path}. Please ensure it exists.")
        return

    documents = []
    metadatas = []
    ids = []

    # --- CHUNKING STRATEGY ---
    # We use a row-based semantic chunking strategy.
    # Instead of blindly splitting text by characters, we format each row 
    # of the highly structured CSV into a natural language paragraph.
    # This ensures that "MOQ of 500" remains semantically linked to 
    # "Glass Dropper Bottle 30ml" and "Skincare" in the embedding space.
    for index, row in df.iterrows():
        chunk_text = (
            f"Category: {row['Category']}. "
            f"Packaging Type: {row['Packaging Type']}. "
            f"Minimum Order Quantity (MOQ): {row['MOQ']} units. "
            f"Lead Time: {row['Lead Time (Days)']} days. "
            f"Formulation Capabilities: {row['Formulation Capability']}. "
            f"Additional Notes: {row['Notes']}"
        )
        documents.append(chunk_text)
        
        # Store structured data as metadata for potential filtering later
        metadatas.append({
            "category": str(row['Category']),
            "packaging_type": str(row['Packaging Type']),
            "moq": int(row['MOQ']),
            "lead_time": int(row['Lead Time (Days)']),
            "capabilities": str(row['Formulation Capability'])
        })
        ids.append(f"doc_{index}")

    # Upsert data into ChromaDB
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"Successfully loaded {len(documents)} records into the vector database.")

def query_database(query_text, n_results=3):
    """Queries the database and returns top N relevant chunks."""
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    
    print("\n--- Top Results ---")
    if not results['documents'][0]:
        print("No results found. Please ensure the database is loaded.")
        return results
        
    for i, doc in enumerate(results['documents'][0]):
        distance = results['distances'][0][i] if 'distances' in results and results['distances'] else "N/A"
        dist_str = f"{distance:.4f}" if isinstance(distance, float) else str(distance)
        print(f"\nResult {i+1} (Distance: {dist_str}):")
        print(doc)
    print("-------------------\n")
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vector Knowledge Base for Packaging Data")
    parser.add_argument('--load', action='store_true', help="Load data from data.csv into the database")
    parser.add_argument('--query', type=str, help="Ask a question to the knowledge base")
    
    args = parser.parse_args()

    if args.load:
        populate_database()
    elif args.query:
        query_database(args.query)
    else:
        # Default interactive CLI behavior
        print("Welcome to the Packaging Knowledge Base CLI.")
        print("Type 'load' to populate the database, or just type your question. Type 'exit' to quit.")
        while True:
            try:
                user_input = input("\n> ")
                if user_input.lower() in ['exit', 'quit']:
                    break
                elif user_input.lower() == 'load':
                    populate_database()
                elif user_input.strip() == "":
                    continue
                else:
                    query_database(user_input)
            except KeyboardInterrupt:
                break
