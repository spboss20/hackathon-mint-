
from datetime import datetime, timezone
from database import get_connection


def create_ticket(customer_name, message, analysis, source="chat"):
    """Create and save a customer support ticket."""

    conn = get_connection()

    cursor = conn.execute(
        """
        INSERT INTO tickets (
            customer_name,
            message,
            category,
            priority,
            sentiment,
            ai_reply,
            status,
            source,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            customer_name,
            message,
            analysis["category"],
            analysis["priority"],
            analysis["sentiment"],
            analysis["reply"],
            "Escalated" if analysis["escalate"] else "Open",
            source,
            datetime.now(timezone.utc).isoformat()
        )
    )

    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return ticket_id


def get_all_tickets():
    """Fetch all support tickets."""

    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tickets ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return [dict(row) for row in rows]


def update_ticket_status(ticket_id, status):
    """Update the status of an existing ticket."""

    allowed_statuses = ["Open", "In Progress", "Resolved", "Escalated"]

    if status not in allowed_statuses:
        raise ValueError("Invalid ticket status")

    conn = get_connection()

    cursor = conn.execute(
        "UPDATE tickets SET status = ? WHERE id = ?",
        (status, ticket_id)
    )

    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()

    return updated
