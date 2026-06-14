import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from auth import hash_password


def seed_db():
    """Populate the database with initial users and events.

    Seeding is idempotent: before inserting anything we check whether the row
    already exists (by email for users, by id for events). This means startup
    can call seed_db() every time without creating duplicates or overwriting
    data that may have changed since the first run.
    """

    # --- Step 1: default users ---
    # We store only bcrypt hashes, never the plaintext password — so we hash
    # here at seed time. The plaintext below is purely for first-login
    # convenience in development and never reaches the database.
    default_users = [
        {"email": "admin@penguwave.com", "password": "admin123", "role": "admin"},
        {"email": "analyst@penguwave.com", "password": "analyst123", "role": "analyst"},
    ]

    for user in default_users:
        db = sqlite3.connect("penguwave.db")
        db.row_factory = sqlite3.Row
        try:
            cursor = db.cursor()
            # Parameterized query — the email is bound as a value, never
            # interpolated into the SQL string.
            cursor.execute("SELECT * FROM users WHERE email = ?", (user["email"],))
            existing = cursor.fetchone()

            if existing is None:
                cursor.execute(
                    """
                    INSERT INTO users (id, email, hashed_password, role, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        user["email"],
                        hash_password(user["password"]),
                        user["role"],
                        "active",
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                db.commit()
                print(f"Seeded user: {user['email']}")
            else:
                print(f"User already exists: {user['email']}")
        finally:
            db.close()

    # --- Step 2: events from mock_events.json ---
    events_path = os.path.join(os.path.dirname(__file__), "..", "data", "mock_events.json")
    with open(events_path) as f:
        events = json.load(f)

    new_count = 0
    for event in events:
        db = sqlite3.connect("penguwave.db")
        db.row_factory = sqlite3.Row
        try:
            cursor = db.cursor()
            # Skip events already present so re-running seed_db() adds only new ones.
            cursor.execute("SELECT id FROM events WHERE id = ?", (event.get("id"),))
            existing = cursor.fetchone()

            if existing is None:
                cursor.execute(
                    """
                    INSERT INTO events (
                        id, timestamp, severity, title, description,
                        assetHostname, assetIp, sourceIp, tags, userId
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.get("id"),
                        event.get("timestamp"),
                        event.get("severity"),
                        event.get("title"),
                        event.get("description"),
                        event.get("assetHostname"),
                        event.get("assetIp"),
                        event.get("sourceIp"),
                        # tags are stored as a JSON string and parsed on read.
                        json.dumps(event.get("tags", [])),
                        event.get("userId"),
                    ),
                )
                db.commit()
                new_count += 1
        finally:
            db.close()

    print(f"Seeded {new_count} new events")
