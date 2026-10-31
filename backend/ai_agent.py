
from classifier import classify_query
from rag import get_knowledge_answer


def process_customer_query(message: str):
    """Classify customer query and generate a knowledge-based reply."""

    # Step 1: AI classification
    result = classify_query(message)

    # Step 2: Default Gemini reply
    final_reply = result.reply

    # Step 3: Retrieve answer from knowledge base
    try:
        knowledge_result = get_knowledge_answer(message)

        if knowledge_result.get("found"):
            final_reply = knowledge_result["answer"]

    except Exception as e:
        print("RAG error:", str(e))

    # Step 4: Return final analysis
    return {
        "category": result.category,
        "priority": result.priority,
        "sentiment": result.sentiment,
        "escalate": result.escalate,
        "reply": final_reply
    }
