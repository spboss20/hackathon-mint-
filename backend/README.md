# SupportIQ – AI-Powered Customer Support System

## Overview
SupportIQ is an AI-powered customer support and intelligent ticket triage system. It uses Gemini AI, RAG and ChromaDB to classify customer queries, generate responses and manage support tickets.

## Technology Stack
- Python
- FastAPI
- Google Gemini API
- SQLite
- ChromaDB
- RAG
- Twilio Voice
- Pydantic

## Project Structure
- main.py – FastAPI application and API routes
- database.py – SQLite database connection
- models.py – Pydantic request and response models
- classifier.py – AI-based ticket classification
- ai_agent.py – AI customer support agent
- rag.py – Knowledge retrieval system
- tickets.py – Ticket management
- analytics.py – Dashboard analytics and weekly insights
- voice.py – Twilio voice integration
- support_faq.txt – Customer support FAQ

## Installation

1. Clone or download the repository.
2. Open the backend folder.
3. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
