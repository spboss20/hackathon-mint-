
import os
import chromadb
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Gemini connection
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# Persistent ChromaDB storage
chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = chroma_client.get_or_create_collection(
    name="supportiq_knowledge",
    metadata={"hnsw:space": "cosine"}
)


def split_text(text, chunk_size=800):
    """Split documents into smaller chunks."""
    return [
        text[i:i + chunk_size]
        for i in range(0, len(text), chunk_size)
        if text[i:i + chunk_size].strip()
    ]


def get_embedding(text):
    """Generate embeddings using Gemini."""
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return response.embeddings[0].values


def add_knowledge(text, source="manual"):
    """Store knowledge in ChromaDB."""

    chunks = split_text(text)

    if not chunks:
        raise ValueError("Document is empty")

    embeddings = [get_embedding(chunk) for chunk in chunks]

    import uuid
    ids = [str(uuid.uuid4()) for _ in chunks]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{"source": source} for _ in chunks]
    )

    return len(chunks)


def search_knowledge(question, limit=3):
    """Retrieve relevant knowledge from ChromaDB."""

    if collection.count() == 0:
        return []

    embedding = get_embedding(question)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(limit, collection.count())
    )

    return results["documents"][0]


def get_knowledge_answer(question):
    """Generate an answer using retrieved knowledge."""

    documents = search_knowledge(question)

    if not documents:
        return {
            "answer": "I could not find this information in our knowledge base. I will escalate your query to a support agent.",
            "found": False
        }

    context = "\n\n".join(documents)

    prompt = f"""
    You are SupportIQ, a customer support assistant.

    Answer the customer's question using ONLY the
    information provided in the knowledge base.

    If the answer is missing, say that you do not
    have enough information and recommend human support.

    Knowledge Base:
    {context}

    Customer Question:
    {question}
    """

    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        contents=prompt
    )

    return {
        "answer": response.text,
        "found": True
    }
