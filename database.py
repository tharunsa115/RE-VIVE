
import sqlite3

DATABASE = "app.db"


def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS green_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence_path TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                points INTEGER NOT NULL DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_interaction(prompt: str, response: str):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            "INSERT INTO interactions (prompt, response) VALUES (?, ?)",
            (prompt, response)
        )


def save_green_action(
    action_type: str,
    description: str,
    evidence_path: str,
    latitude=None,
    longitude=None,
    points: int = 10
):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO green_actions
            (action_type, description, evidence_path,
             latitude, longitude, points)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            action_type,
            description,
            evidence_path,
            latitude,
            longitude,
            points
        ))


def get_green_stats():
    with sqlite3.connect(DATABASE) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM green_actions"
        ).fetchone()[0]

        points = conn.execute(
            "SELECT COALESCE(SUM(points), 0) FROM green_actions"
        ).fetchone()[0]

        dates = conn.execute("""
            SELECT DISTINCT date(created_at)
            FROM green_actions
            ORDER BY date(created_at) DESC
        """).fetchall()

    streak = 0
    if dates:
        from datetime import date, timedelta

        recorded_dates = {date.fromisoformat(row[0]) for row in dates}
        today = date.today()

        current = today if today in recorded_dates else today - timedelta(days=1)

        while current in recorded_dates:
            streak += 1
            current -= timedelta(days=1)

    return {
        "earth_points": points,
        "green_actions": total,
        "current_streak": streak
    }


def get_green_history():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, action_type, description, evidence_path,
                   latitude, longitude, points, created_at
            FROM green_actions
            ORDER BY id DESC
        """).fetchall()

    return [dict(row) for row in rows]