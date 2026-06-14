import sqlite3

# Path to the SQLite database file (relative to the project root).
DATABASE_URL = "backend/penguwave.db"


def get_db():
    """Open a SQLite connection for the lifetime of a single request.

    Yields a connection whose rows behave like dicts (access columns by
    name), then guarantees the connection is closed afterwards. Intended
    for use as a FastAPI dependency.
    """
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create the database tables if they don't already exist."""
    conn = sqlite3.connect(DATABASE_URL)
    try:
        cursor = conn.cursor()

        # users: the people who can log in to PenguWave. Stores credentials
        # (hashed, never plaintext), an access role for authorization, and a
        # status so accounts can be disabled without deleting their history.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'analyst',   -- only 'admin' or 'analyst' allowed
                status TEXT NOT NULL DEFAULT 'active',  -- only 'active' or 'inactive' allowed
                created_at TEXT NOT NULL
            )
            """
        )

        # events: the security events analysts review and triage. Each event
        # captures what happened (severity, title, description), which asset
        # and network endpoints were involved, free-form tags, and which user
        # it is assigned to. tags is stored as a JSON string and parsed on read.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                assetHostname TEXT,
                assetIp TEXT,
                sourceIp TEXT,
                tags TEXT,        -- stored as JSON string, parsed on read
                userId TEXT
            )
            """
        )

        conn.commit()
    finally:
        conn.close()
