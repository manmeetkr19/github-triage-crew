"""
Audit Log - a custom MCP server, built from scratch (unlike GitHub's, which
we reuse). SQLite-backed, two tools: record_decision and get_history.
This is the crew's own record of *why* it did what it did, independent of
whatever GitHub itself shows.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DB_PATH = Path(__file__).parent / "audit_log.db"
PORT = 8010

mcp = FastMCP("Audit Log", port=PORT)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo TEXT NOT NULL,
            issue_number INTEGER NOT NULL,
            labels TEXT NOT NULL,
            notes TEXT NOT NULL,
            raw_verdicts TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


@mcp.tool()
def record_decision(repo: str, issue_number: int, labels: list[str], notes: list[str], raw_verdicts: dict) -> dict:
    """Record one triage decision: the final labels/notes and each specialist's raw verdict."""
    conn = _get_connection()
    created_at = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO decisions (repo, issue_number, labels, notes, raw_verdicts, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (repo, issue_number, json.dumps(labels), json.dumps(notes), json.dumps(raw_verdicts), created_at),
    )
    conn.commit()
    decision_id = cursor.lastrowid
    conn.close()
    return {"id": decision_id, "created_at": created_at}


@mcp.tool()
def get_history(repo: str, since: str | None = None) -> list[dict]:
    """Return past triage decisions for a repo, optionally only those at/after an ISO timestamp."""
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    if since:
        rows = conn.execute(
            "SELECT * FROM decisions WHERE repo = ? AND created_at >= ? ORDER BY created_at", (repo, since)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM decisions WHERE repo = ? ORDER BY created_at", (repo,)).fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "issue_number": row["issue_number"],
            "labels": json.loads(row["labels"]),
            "notes": json.loads(row["notes"]),
            "raw_verdicts": json.loads(row["raw_verdicts"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
