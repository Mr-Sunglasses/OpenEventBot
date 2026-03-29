import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import DATABASE_PATH


def _get_connection() -> sqlite3.Connection:
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                photo_file_id TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events(id),
                UNIQUE(event_id, user_id)
            )
        """)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(events)").fetchall()}
    if "photo_file_id" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN photo_file_id TEXT")


def create_event(chat_id: int, message_id: int, description: str, photo_file_id: str | None = None) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO events (chat_id, message_id, description, photo_file_id) VALUES (?, ?, ?, ?)",
            (chat_id, message_id, description, photo_file_id),
        )
        return cursor.lastrowid


def get_event_by_message(chat_id: int, message_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM events WHERE chat_id = ? AND message_id = ?",
            (chat_id, message_id),
        ).fetchone()
        return dict(row) if row else None


def get_event_by_id(event_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        return dict(row) if row else None


def add_attendee(event_id: int, user_id: int, name: str) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO attendees (event_id, user_id, name) VALUES (?, ?, ?) "
            "ON CONFLICT(event_id, user_id) DO UPDATE SET name = excluded.name",
            (event_id, user_id, name),
        )


def remove_attendee(event_id: int, user_id: int) -> None:
    with get_db() as conn:
        conn.execute(
            "DELETE FROM attendees WHERE event_id = ? AND user_id = ?",
            (event_id, user_id),
        )


def get_attendees(event_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM attendees WHERE event_id = ? ORDER BY id",
            (event_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def update_event_message_id(event_id: int, new_message_id: int) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE events SET message_id = ? WHERE id = ?",
            (new_message_id, event_id),
        )


def delete_event(event_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM attendees WHERE event_id = ?", (event_id,))
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
