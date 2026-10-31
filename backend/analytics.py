
from database import get_connection


def get_analytics():
    conn = get_connection()

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
        "SELECT category, COUNT(*) FROM tickets GROUP BY category"
    ).fetchall()

    priorities = conn.execute(
        "SELECT priority, COUNT(*) FROM tickets GROUP BY priority"
    ).fetchall()

    conn.close()

    return {
        "total_tickets": total,
        "open_tickets": open_count,
        "resolved_tickets": resolved,
        "escalated_tickets": escalated,
        "negative_sentiment": negative,
        "category_distribution": {
            row[0]: row[1] for row in categories
        },
        "priority_distribution": {
            row[0]: row[1] for row in priorities
        }
    }


def get_weekly_insights():
    conn = get_connection()

    rows = conn.execute("""
        SELECT category, priority, sentiment, status, message
        FROM tickets
        WHERE datetime(created_at) >= datetime('now', '-7 days')
    """).fetchall()

    conn.close()

    total = len(rows)

    if total == 0:
        return {
            "period": "Last 7 days",
            "total_tickets": 0,
            "message": "No tickets received in the last 7 days.",
            "recommendations": []
        }

    categories = {}
    high_critical = 0
    negative = 0
    resolved = 0
    complaints = {}

    for row in rows:
        category, priority, sentiment, status, message = row

        categories[category] = categories.get(category, 0) + 1

        if priority in ("High", "Critical"):
            high_critical += 1

        if sentiment == "Negative":
            negative += 1

        if status == "Resolved":
            resolved += 1

        complaints[message] = complaints.get(message, 0) + 1

    common_category = max(categories, key=categories.get)

    recommendations = []

    if negative:
        recommendations.append(
            "Review negative-sentiment tickets and improve customer responses."
        )

    if high_critical:
        recommendations.append(
            "Prioritize high and critical priority tickets."
        )

    if resolved < total:
        recommendations.append(
            "Follow up on unresolved customer tickets."
        )

    if not recommendations:
        recommendations.append(
            "Maintain current support performance and monitor new tickets."
        )

    return {
        "period": "Last 7 days",
        "total_tickets": total,
        "most_common_category": common_category,
        "category_distribution": categories,
        "high_critical_tickets": high_critical,
        "negative_sentiment_tickets": negative,
        "resolved_tickets": resolved,
        "unresolved_tickets": total - resolved,
        "common_complaints": sorted(
            complaints.items(),
            key=lambda item: item[1],
            reverse=True
        )[:5],
        "recommendations": recommendations
    }
