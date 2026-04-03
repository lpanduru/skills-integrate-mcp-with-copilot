"""Storage layer for persistent application data.

This module replaces in-memory dictionaries with SQLite persistence while
keeping the API contract unchanged for existing endpoints.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Tuple


DB_PATH = Path(__file__).parent / "data.db"


# Seed data retained from the original in-memory implementation.
INITIAL_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migration_1(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            schedule_text TEXT NOT NULL,
            max_participants INTEGER NOT NULL CHECK(max_participants > 0)
        );

        CREATE TABLE IF NOT EXISTS activity_participants (
            activity_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            PRIMARY KEY(activity_id, email),
            FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE
        );
        """
    )


def _migration_2(conn: sqlite3.Connection) -> None:
    # Base schema for upcoming issue work. These tables are intentionally small
    # and can be expanded through future migrations.
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            password_hash TEXT,
            role_id INTEGER,
            FOREIGN KEY(role_id) REFERENCES roles(id)
        );

        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            principal_user_id INTEGER,
            is_banned INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(principal_user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS club_memberships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(club_id, user_id),
            FOREIGN KEY(club_id) REFERENCES clubs(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS activity_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            state TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            FOREIGN KEY(club_id) REFERENCES clubs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER,
            author_user_id INTEGER,
            recipient_user_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(club_id) REFERENCES clubs(id) ON DELETE CASCADE,
            FOREIGN KEY(author_user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY(recipient_user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS finance_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            txn_type TEXT NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(club_id) REFERENCES clubs(id) ON DELETE CASCADE
        );
        """
    )

    conn.execute("INSERT OR IGNORE INTO roles(name) VALUES ('student')")
    conn.execute("INSERT OR IGNORE INTO roles(name) VALUES ('club_admin')")
    conn.execute("INSERT OR IGNORE INTO roles(name) VALUES ('federation_admin')")


def initialize_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _get_connection() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]

        if version < 1:
            _migration_1(conn)
            conn.execute("PRAGMA user_version = 1")

        if version < 2:
            _migration_2(conn)
            conn.execute("PRAGMA user_version = 2")

        _seed_if_empty(conn)


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) AS cnt FROM activities").fetchone()["cnt"]
    if existing > 0:
        return

    for name, details in INITIAL_ACTIVITIES.items():
        cursor = conn.execute(
            """
            INSERT INTO activities(name, description, schedule_text, max_participants)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                details["description"],
                details["schedule"],
                details["max_participants"],
            ),
        )
        activity_id = cursor.lastrowid
        for email in details["participants"]:
            conn.execute(
                "INSERT INTO activity_participants(activity_id, email) VALUES (?, ?)",
                (activity_id, email),
            )


def get_activities() -> Dict[str, dict]:
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, description, schedule_text, max_participants
            FROM activities
            ORDER BY name ASC
            """
        ).fetchall()

        activity_map: Dict[str, dict] = {}
        for row in rows:
            participants = conn.execute(
                """
                SELECT email FROM activity_participants
                WHERE activity_id = ?
                ORDER BY email ASC
                """,
                (row["id"],),
            ).fetchall()

            activity_map[row["name"]] = {
                "description": row["description"],
                "schedule": row["schedule_text"],
                "max_participants": row["max_participants"],
                "participants": [p["email"] for p in participants],
            }

        return activity_map


def signup_for_activity(activity_name: str, email: str) -> Tuple[bool, str, int]:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT id, max_participants FROM activities WHERE name = ?", (activity_name,)
        ).fetchone()
        if row is None:
            return False, "Activity not found", 404

        exists = conn.execute(
            """
            SELECT 1 FROM activity_participants
            WHERE activity_id = ? AND email = ?
            """,
            (row["id"], email),
        ).fetchone()
        if exists:
            return False, "Student is already signed up", 400

        current_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM activity_participants WHERE activity_id = ?",
            (row["id"],),
        ).fetchone()["cnt"]
        if current_count >= row["max_participants"]:
            return False, "Activity is full", 400

        conn.execute(
            "INSERT INTO activity_participants(activity_id, email) VALUES (?, ?)",
            (row["id"], email),
        )

    return True, f"Signed up {email} for {activity_name}", 200


def unregister_from_activity(activity_name: str, email: str) -> Tuple[bool, str, int]:
    with _get_connection() as conn:
        row = conn.execute("SELECT id FROM activities WHERE name = ?", (activity_name,)).fetchone()
        if row is None:
            return False, "Activity not found", 404

        exists = conn.execute(
            """
            SELECT 1 FROM activity_participants
            WHERE activity_id = ? AND email = ?
            """,
            (row["id"], email),
        ).fetchone()
        if not exists:
            return False, "Student is not signed up for this activity", 400

        conn.execute(
            "DELETE FROM activity_participants WHERE activity_id = ? AND email = ?",
            (row["id"], email),
        )

    return True, f"Unregistered {email} from {activity_name}", 200