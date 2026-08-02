"""Automated tests for the Sprint7 Todo API using FastAPI TestClient."""
import os
import sys
import tempfile

# Point the app at a throwaway test DB so tests never touch dev data.
TEST_DB = os.path.join(tempfile.gettempdir(), "sprint7_test_todo.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main  # noqa: E402

# Override DB_PATH to the temp file BEFORE init_db runs.
main.DB_PATH = TEST_DB
main.init_db()

from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(main.app)


def _make_todo(title="Write report", description="Q3 summary"):
    """Helper: create a todo and return its id."""
    r = client.post("/api/todos", json={"title": title, "description": description})
    assert r.status_code == 201
    return r.json()["id"]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_todo():
    r = client.post("/api/todos", json={"title": "Write report", "description": "Q3 summary"})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Write report"
    assert data["description"] == "Q3 summary"
    assert data["completed"] == 0
    assert data["id"] > 0


def test_list_todos():
    r = client.get("/api/todos")
    assert r.status_code == 200
    todos = r.json()
    assert isinstance(todos, list)
    assert len(todos) >= 1


def test_get_todo():
    tid = _make_todo()
    r = client.get(f"/api/todos/{tid}")
    assert r.status_code == 200
    assert r.json()["id"] == tid


def test_get_todo_not_found():
    r = client.get("/api/todos/999999")
    assert r.status_code == 404


def test_update_todo_completed():
    tid = _make_todo()
    r = client.put(f"/api/todos/{tid}", json={"completed": True})
    assert r.status_code == 200
    assert r.json()["completed"] == 1


def test_update_todo_title():
    tid = _make_todo()
    r = client.put(f"/api/todos/{tid}", json={"title": "Renamed"})
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"


def test_update_todo_not_found():
    r = client.put("/api/todos/999999", json={"completed": True})
    assert r.status_code == 404


def test_filter_by_completed():
    # Create one completed and one pending todo
    done_id = _make_todo(title="Done task")
    client.put(f"/api/todos/{done_id}", json={"completed": True})
    _make_todo(title="Pending task")

    r = client.get("/api/todos", params={"completed": True})
    assert r.status_code == 200
    for t in r.json():
        assert t["completed"] == 1

    r = client.get("/api/todos", params={"completed": False})
    assert r.status_code == 200
    for t in r.json():
        assert t["completed"] == 0


def test_delete_todo():
    tid = _make_todo()
    r = client.delete(f"/api/todos/{tid}")
    assert r.status_code == 204
    # Confirm it's gone
    r = client.get(f"/api/todos/{tid}")
    assert r.status_code == 404


def test_delete_todo_not_found():
    r = client.delete("/api/todos/999999")
    assert r.status_code == 404


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
