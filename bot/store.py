"""Per-guild model and alert switches stored in SQLite."""
import sqlite3
from pathlib import Path

EVENTS = ("test_success", "test_failure", "request_failure", "recovered")

class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS models (guild INTEGER, provider TEXT, enabled INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(guild, provider))")
        self.db.execute("CREATE TABLE IF NOT EXISTS alerts (guild INTEGER, provider TEXT, event TEXT, enabled INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(guild, provider, event))")
        self.db.execute("CREATE TABLE IF NOT EXISTS health (guild INTEGER, provider TEXT, last_ok INTEGER, PRIMARY KEY(guild, provider))")
        self.db.commit()

    def enabled(self, guild, provider):
        row = self.db.execute("SELECT enabled FROM models WHERE guild=? AND provider=?", (guild, provider)).fetchone()
        return bool(row and row[0])

    def turn(self, guild, provider, enabled):
        with self.db:
            self.db.execute("INSERT INTO models VALUES (?, ?, ?) ON CONFLICT(guild, provider) DO UPDATE SET enabled=excluded.enabled", (guild, provider, int(enabled)))

    def alert(self, guild, provider, event, enabled=None):
        if enabled is None:
            row = self.db.execute("SELECT enabled FROM alerts WHERE guild=? AND provider=? AND event=?", (guild, provider, event)).fetchone()
            return bool(row and row[0])
        with self.db:
            self.db.execute("INSERT INTO alerts VALUES (?, ?, ?, ?) ON CONFLICT(guild, provider, event) DO UPDATE SET enabled=excluded.enabled", (guild, provider, event, int(enabled)))

    def outcome(self, guild, provider, ok):
        row = self.db.execute("SELECT last_ok FROM health WHERE guild=? AND provider=?", (guild, provider)).fetchone()
        recovered = bool(ok and row and row[0] == 0)
        with self.db:
            self.db.execute("INSERT INTO health VALUES (?, ?, ?) ON CONFLICT(guild, provider) DO UPDATE SET last_ok=excluded.last_ok", (guild, provider, int(ok)))
        return recovered

    def health_status(self, guild, provider):
        row = self.db.execute("SELECT last_ok FROM health WHERE guild=? AND provider=?", (guild, provider)).fetchone()
        return "untested" if row is None else ("reachable on last test" if row[0] else "failed on last request")
