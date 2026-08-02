"""Sprint7 Todo API — a simple FastAPI to-do REST API with SQLite persistence."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "todo.db")

app = FastAPI(title="Sprint7 Todo API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ──
class TodoCreate(BaseModel):
    """Payload for creating a new todo item."""
    title: str
    description: str = ""


class TodoUpdate(BaseModel):
    """Payload for updating an existing todo item (all fields optional)."""
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None


# ── Database helpers ──
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the database file and todos table if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )"""
    )
    conn.commit()
    conn.close()


init_db()


# ── Routes ──
@app.get("/health")
def health():
    return {"status": "ok", "app": "Sprint7 Todo API"}


@app.get("/api/todos", response_model=List[dict])
def list_todos(completed: Optional[bool] = None):
    """List all todos, optionally filtered by completion status."""
    conn = get_db()
    if completed is None:
        rows = conn.execute("SELECT * FROM todos ORDER BY id").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM todos WHERE completed=? ORDER BY id", (int(completed),)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/todos/{todo_id}", response_model=dict)
def get_todo(todo_id: int):
    """Get a single todo by id."""
    conn = get_db()
    row = conn.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Todo not found")
    return dict(row)


@app.post("/api/todos", response_model=dict, status_code=201)
def create_todo(todo: TodoCreate):
    """Create a new todo item."""
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO todos(title, description) VALUES(?, ?)",
        (todo.title, todo.description),
    )
    conn.commit()
    tid = cur.lastrowid
    row = conn.execute("SELECT * FROM todos WHERE id=?", (tid,)).fetchone()
    conn.close()
    return dict(row)


@app.put("/api/todos/{todo_id}", response_model=dict)
def update_todo(todo_id: int, update: TodoUpdate):
    """Update an existing todo (title, description, and/or completed)."""
    conn = get_db()
    row = conn.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo not found")

    # Build dynamic UPDATE based on which fields were provided
    fields, params = [], []
    if update.title is not None:
        fields.append("title=?")
        params.append(update.title)
    if update.description is not None:
        fields.append("description=?")
        params.append(update.description)
    if update.completed is not None:
        fields.append("completed=?")
        params.append(int(update.completed))

    if fields:
        fields_sql = ", ".join(fields)
        params.append(todo_id)
        conn.execute(f"UPDATE todos SET {fields_sql} WHERE id=?", params)
        conn.commit()

    updated = conn.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
    conn.close()
    return dict(updated)


@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    """Delete a todo item by id."""
    conn = get_db()
    row = conn.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo not found")
    conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
    conn.commit()
    conn.close()
    return None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
