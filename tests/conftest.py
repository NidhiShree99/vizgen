import os
import sys

import pytest

# Make the app modules importable from tests/.
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# db.py reads this at import time; a dummy value keeps imports working
# offline. Nothing in the offline suite opens a real connection.
os.environ.setdefault("DATABASE_URL", "postgresql://test/test")


class FakeCursor:
    """Records SQL instead of running it, and replays canned rows."""

    def __init__(self, recorder, results):
        self._recorder = recorder
        self._results = results

    def execute(self, sql, params=None):
        self._recorder.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self._results.pop(0) if self._results else None

    def fetchall(self):
        return self._results.pop(0) if self._results else []


class FakeConnection:
    def __init__(self, recorder, results):
        self._recorder = recorder
        self._results = results
        self.committed = False
        self.closed = False

    def cursor(self):
        return FakeCursor(self._recorder, self._results)

    def execute(self, sql, params=None):
        self._recorder.append((" ".join(sql.split()), params))

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        self.closed = True


@pytest.fixture
def fake_db(monkeypatch):
    """
    Patch db.get_connection so DB functions can be exercised without
    a live Postgres. Returns a handle exposing every statement that
    was issued, so tests can assert on scoping clauses and params.
    """
    import db

    state = {"recorder": [], "results": []}

    def get_connection():
        return FakeConnection(state["recorder"], state["results"])

    monkeypatch.setattr(db, "get_connection", get_connection)

    class Handle:
        def queue(self, *rows):
            """Canned rows returned by fetchone/fetchall, in order."""
            state["results"].extend(rows)

        @property
        def statements(self):
            return [sql for sql, _ in state["recorder"]]

        @property
        def calls(self):
            return list(state["recorder"])

        def sql_containing(self, needle):
            return [sql for sql in self.statements if needle in sql]

    return Handle()
