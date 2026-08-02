"""TaskFlow — Simple Project Management API"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal
import sqlite3
import os
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "database", "taskflow.db")

app = FastAPI(title="TaskFlow", version="0.1.0")

# ── CORS ──
# 安全修复：明确指定前端来源，禁止 "*" + allow_credentials=True 的非法组合。
# 前端为 React (Vite)，默认开发端口 5173。
# 如需新增来源（如生产域名），在此列表追加即可。
CORS_ALLOW_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def hash_password(password: str) -> str:
    """Return the SHA256 hex digest of the given password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ── Models ──
class UserLogin(BaseModel):
    username: str
    password: str


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    project_id: int = 1


# Valid task statuses
TaskStatus = Literal["todo", "in_progress", "done"]


class TaskUpdate(BaseModel):
    """Status update model for PATCH /api/tasks/{id}."""
    status: TaskStatus


# ── Init DB ──
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'user')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY, name TEXT, owner_id INTEGER)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY, title TEXT, description TEXT, project_id INTEGER,
        status TEXT DEFAULT 'todo', assignee_id INTEGER)""")
    # Store SHA256-hashed passwords (never plaintext)
    conn.execute("INSERT OR IGNORE INTO users(id,username,password,role) VALUES(1,'admin',?,'admin')",
                 (hash_password("admin123"),))
    conn.execute("INSERT OR IGNORE INTO users(id,username,password,role) VALUES(2,'dev',?,'developer')",
                 (hash_password("dev123"),))
    conn.execute("INSERT OR IGNORE INTO projects(id,name,owner_id) VALUES(1,'TaskFlow Dev',1)")
    conn.commit()
    conn.close()


init_db()


# ── Login (hashed comparison) ──
@app.post("/api/login")
def login(user: UserLogin):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Compare against the stored hash — never compare plaintext
    row = conn.execute("SELECT * FROM users WHERE username=?", (user.username,)).fetchone()
    conn.close()
    if not row or row["password"] != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": f"fake-jwt-{row['username']}", "user": dict(row)}


@app.get("/api/projects")
def list_projects():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/tasks")
def create_task(task: TaskCreate):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("INSERT INTO tasks(title,description,project_id) VALUES(?,?,?)",
                 (task.title, task.description, task.project_id))
    conn.commit()
    tid = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
    conn.close()
    return {"id": tid, "status": "created"}


@app.get("/api/tasks")
def list_tasks(project_id: int = 1, assignee_id: Optional[int] = None):
    """List tasks, optionally filtered by project_id and/or assignee_id."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM tasks WHERE project_id=?"
    params: list = [project_id]
    if assignee_id is not None:
        query += " AND assignee_id=?"
        params.append(assignee_id)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.patch("/api/tasks/{task_id}")
def update_task_status(task_id: int, update: TaskUpdate):
    """Update a task's status. Allowed values: todo / in_progress / done."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Check the task exists
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    # Update status
    conn.execute("UPDATE tasks SET status=? WHERE id=?", (update.status, task_id))
    conn.commit()
    updated = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    return dict(updated)


@app.get("/health")
def health():
    return {"status": "ok", "app": "TaskFlow"}
