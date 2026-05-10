# Task 2: Bilingual AI Customer Intake Agent

## Overview
A FastAPI-based conversational AI agent designed to qualify inbound leads for private-label services. It handles both English and Urdu naturally and extracts structured lead data.

## Features
- **Bilingual Support**: Detects and responds in English/Urdu based on user input.
- **Lead Qualification**: Automatically extracts `company_name`, `contact_name`, `product_category`, etc.
- **RAG Integration**: Directly queries the Task 1 Vector KB to answer technical questions about packaging and MOQs.

## Setup Instructions
1.  **Dependencies**:
    - `pip install fastapi uvicorn openai python-dotenv`
2.  **Environment**:
    - Ensure `OPENAI_API_KEY` is set in the root `.env` file.
3.  **Run**:
    ```bash
    uvicorn main:app --port 8000
    ```

## Design Notes
- **State Management**: Uses in-memory session storage for simplicity during the demonstration.
- **Hybrid RAG**: The system prompt is dynamically updated with context retrieved from Task 1's ChromaDB, ensuring the agent provides accurate technical specs.
- **Urdu Logic**: The agent uses hardcoded Urdu instructions in the system prompt to maintain a professional "Team Beauty" tone in both languages.
