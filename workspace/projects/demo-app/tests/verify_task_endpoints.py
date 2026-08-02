"""Verify the new task endpoints in main.py.

Run: python tests/verify_task_endpoints.py
Expected output: all assertions pass, exit code 0.

This script uses FastAPI's TestClient (requires `pip install httpx`).
If httpx is unavailable, it falls back to pure SQLite checks.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "app"))

try:
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient
    HAS_TESTCLIENT = True
except ImportError:
    HAS_TESTCLIENT = False

if HAS_TESTCLIENT:
    import main
    client = TestClient(main.app)

    # ── 1. PATCH /api/tasks/{id} — valid status transitions ──
    # Create a task first
    resp = client.post("/api/tasks", json={"title": "Test Task", "description": "x", "project_id": 1})
    assert resp.status_code == 200, f"create failed: {resp.status_code} {resp.text}"
    tid = resp.json()["id"]

    # Default status should be 'todo'
    resp = client.get("/api/tasks", params={"project_id": 1})
    task = next(t for t in resp.json() if t["id"] == tid)
    assert task["status"] == "todo", f"default status should be todo, got {task['status']}"

    # Patch to in_progress
    resp = client.patch(f"/api/tasks/{tid}", json={"status": "in_progress"})
    assert resp.status_code == 200, f"patch failed: {resp.status_code} {resp.text}"
    assert resp.json()["status"] == "in_progress", resp.json()
    print(f"OK: PATCH to in_progress -> {resp.json()['status']}")

    # Patch to done
    resp = client.patch(f"/api/tasks/{tid}", json={"status": "done"})
    assert resp.status_code == 200, f"patch failed: {resp.status_code} {resp.text}"
    assert resp.json()["status"] == "done", resp.json()
    print(f"OK: PATCH to done -> {resp.json()['status']}")

    # Patch back to todo
    resp = client.patch(f"/api/tasks/{tid}", json={"status": "todo"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "todo"
    print("OK: PATCH back to todo")

    # ── 2. PATCH — invalid status should be rejected (422) ──
    resp = client.patch(f"/api/tasks/{tid}", json={"status": "invalid_status"})
    assert resp.status_code == 422, f"invalid status should be 422, got {resp.status_code}"
    print("OK: invalid status rejected with 422")

    # ── 3. PATCH — nonexistent task should be 404 ──
    resp = client.patch("/api/tasks/999999", json={"status": "done"})
    assert resp.status_code == 404, f"nonexistent task should be 404, got {resp.status_code}"
    print("OK: nonexistent task returns 404")

    # ── 4. GET /api/tasks?assignee_id=N ──
    # Set an assignee on our task (via direct DB, since no assignee API yet)
    import sqlite3
    conn = sqlite3.connect(main.DB_PATH)
    conn.execute("UPDATE tasks SET assignee_id=? WHERE id=?", (2, tid))
    conn.commit()
    conn.close()

    resp = client.get("/api/tasks", params={"project_id": 1, "assignee_id": 2})
    assert resp.status_code == 200, f"assignee query failed: {resp.status_code}"
    tasks = resp.json()
    assert any(t["id"] == tid for t in tasks), "task with assignee_id=2 should appear"
    assert all(t["assignee_id"] == 2 for t in tasks), "all returned tasks should have assignee_id=2"
    print(f"OK: assignee_id=2 filter returns {len(tasks)} task(s)")

    # assignee_id filter with no matches returns empty list
    resp = client.get("/api/tasks", params={"project_id": 1, "assignee_id": 5})
    assert resp.status_code == 200
    assert resp.json() == [], f"expected empty list, got {resp.json()}"
    print("OK: assignee_id=5 (no match) returns empty list")

    print("\nAll endpoint checks passed.")

else:
    # Fallback: pure SQLite verification of schema + logic
    print("TestClient unavailable (httpx not installed). Running SQLite-only checks...")
    import sqlite3
    import tempfile
    from main import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Verify tasks table has status and assignee_id columns
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    assert "status" in cols, "tasks table missing status column"
    assert "assignee_id" in cols, "tasks table missing assignee_id column"
    print(f"OK: tasks columns present: {cols}")
    conn.close()
    print("SQLite-only schema check passed.")
