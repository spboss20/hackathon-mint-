
from typing import Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    customer_name: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=5000)

    source: Literal[
        "chat",
        "browser_voice",
        "phone"
    ] = "chat"


class AIAnalysis(BaseModel):
    category: Literal[
        "Payment",
        "Refund",
        "Delivery",
        "Technical",
        "Account Security",
        "General"
    ]

    priority: Literal[
        "Low",
        "Medium",
        "High",
        "Critical"
    ]

    sentiment: Literal[
        "Positive",
        "Neutral",
        "Negative"
    ]

    escalate: bool

    reply: str


class TicketStatusUpdate(BaseModel):
    status: Literal[
        "Open",
        "In Progress",
        "Resolved",
        "Escalated"
    ]


class ChatResponse(BaseModel):
    ticket_id: int
    category: str
    priority: str
    sentiment: str
    escalate: bool
    reply: str
    status: str
