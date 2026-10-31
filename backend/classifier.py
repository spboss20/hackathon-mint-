
import os
import json

from google import genai
from dotenv import load_dotenv

from models import AIAnalysis

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key) if api_key else None


def classify_query(message: str) -> AIAnalysis:

    if not client:
        raise RuntimeError("GEMINI_API_KEY is missing in .env")

    prompt = f"""
    You are an intelligent customer support classifier.

    Analyze the customer message.

    Customer message:
    {message}

    Return JSON with these fields:

    category: Payment, Refund, Delivery, Technical,
              Account Security, General

    priority: Low, Medium, High, Critical

    sentiment: Positive, Neutral, Negative

    escalate: true or false

    reply: A helpful customer response.

    Rules:
    1. Account hacking and unauthorized access must be Critical.
    2. Suspected fraud and unauthorized financial transactions
       must be escalated.
    3. Refund requests should not be marked resolved automatically.
    4. Never invent payment, order or refund information.
    5. Escalate sensitive complaints to a human.
    6. If information is insufficient, ask the customer
       for clarification.
    """

    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": AIAnalysis
        }
    )

    data = json.loads(response.text)

    return AIAnalysis.model_validate(data)
