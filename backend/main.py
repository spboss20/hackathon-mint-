
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
from rag import add_knowledge
from analytics import get_weekly_insights
from fastapi import Request, Form, Response
from voice import create_incoming_voice_response, create_voice_reply

from database import init_db, get_connection
from models import ChatRequest, ChatResponse, TicketStatusUpdate
from ai_agent import process_customer_query
from tickets import create_ticket, get_all_tickets, update_ticket_status



app = FastAPI(
    title="SupportIQ API",
    description="AI-Powered Customer Support and Intelligent Ticket Triage",
    version="1.0.0"
)


# Frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def home():
    return {
        "message": "Welcome to SupportIQ API",
        "status": "running"
    }


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


# 1. Customer Chat API
@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    try:
        # Analyse customer message using Gemini AI
        analysis = process_customer_query(request.message)

        # Save ticket in SQLite database
        ticket_id = create_ticket(
            customer_name=request.customer_name,
            message=request.message,
            analysis=analysis,
            source=request.source
        )

        status = "Escalated" if analysis["escalate"] else "Open"

        return {
            "ticket_id": ticket_id,
            "category": analysis["category"],
            "priority": analysis["priority"],
            "sentiment": analysis["sentiment"],
            "escalate": analysis["escalate"],
            "reply": analysis["reply"],
            "status": status
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 2. Get All Tickets API
@app.get("/api/tickets")
def get_tickets():

    try:
        return get_all_tickets()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 3. Update Ticket Status API
@app.patch("/api/tickets/{ticket_id}")
def update_status(ticket_id: int, request: TicketStatusUpdate):

    try:
        updated = update_ticket_status(ticket_id, request.status)

        if not updated:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found"
            )

        return {
            "message": "Ticket status updated successfully",
            "ticket_id": ticket_id,
            "status": request.status
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 4. Dashboard Analytics API
@app.get("/api/analytics")
def get_analytics():

    conn = get_connection()

    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM tickets"
        ).fetchone()[0]

        open_count = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'Open'"
        ).fetchone()[0]

        resolved = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'Resolved'"
        ).fetchone()[0]

        escalated = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'Escalated'"
        ).fetchone()[0]

        negative = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE sentiment = 'Negative'"
        ).fetchone()[0]

        categories = conn.execute(
            "SELECT category, COUNT(*) AS count FROM tickets GROUP BY category"
        ).fetchall()

        priorities = conn.execute(
            "SELECT priority, COUNT(*) AS count FROM tickets GROUP BY priority"
        ).fetchall()

        return {
            "total_tickets": total,
            "open_tickets": open_count,
            "resolved_tickets": resolved,
            "escalated_tickets": escalated,
            "negative_sentiment": negative,
            "category_distribution": {
                row["category"]: row["count"] for row in categories
            },
            "priority_distribution": {
                row["priority"]: row["count"] for row in priorities
            }
        }

    finally:
        conn.close()

from pathlib import Path

@app.post("/api/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):

    allowed_extensions = [".txt", ".md"]

    extension = Path(file.filename).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only TXT and MD files are supported"
        )

    content = await file.read()

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be UTF-8 encoded"
        )

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )

    try:
        chunks = add_knowledge(
            text=text,
            source=file.filename
        )

        return {
            "message": "Knowledge uploaded successfully",
            "filename": file.filename,
            "chunks_added": chunks
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Weekly AI Insights API
@app.get("/api/insights/weekly")
def weekly_insights():
    try:
        return get_weekly_insights()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate weekly insights"
        )
    # Twilio: Incoming phone call
@app.post("/api/voice/incoming")
async def incoming_voice(request: Request):

    action_url = str(request.url_for("process_voice"))

    twiml = create_incoming_voice_response(action_url)

    return Response(content=twiml, media_type="application/xml")


# Twilio: Process customer's spoken query
@app.post("/api/voice/process", name="process_voice")
async def process_voice(
    SpeechResult: str = Form(default=""),
    From: str = Form(default="Unknown")
):

    message = SpeechResult.strip()

    if not message:
        return Response(
            content=create_voice_reply(
                "Sorry, I could not understand you. Please call again."
            ),
            media_type="application/xml"
        )

    try:
        analysis = process_customer_query(message)

    except Exception as e:
        print("Voice AI error:", str(e))

        analysis = {
            "category": "General",
            "priority": "Medium",
            "sentiment": "Neutral",
            "escalate": False,
            "reply": "Sorry, our AI support is temporarily unavailable. Please try again later."
        }

    try:
        ticket_id = create_ticket(
            customer_name=From,
            message=message,
            analysis=analysis,
            source="phone"
        )

        reply = f"Your support ticket number is {ticket_id}. {analysis['reply']}"

    except Exception as e:
        print("Ticket creation error:", str(e))
        reply = "Sorry, we could not save your support ticket."

    return Response(
        content=create_voice_reply(reply),
        media_type="application/xml"
    )