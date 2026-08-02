# Personal AI OS v1.0.0 — First Public Beta

> **Release Date**: 2026-08-02
> **Branch**: `release/v1.0.0`
> **Tag**: `v1.0.0`
> **Type**: Public Beta

---

## What is Personal AI OS?

**An autonomous AI workstation.** Not a chatbot. Not a code generation tool. An AI operating system runtime — like running a micro AI company on your machine.

You give it goals. It plans, delegates to specialist agents, executes with tools, reflects, and learns.

```
CEO understands your goal
  ↓
Router assigns tasks to specialists
  ↓
Coding Agent · Research Agent · Writing Agent
  ↓
Reflection Agent captures lessons
  ↓
Evolution Advisor proposes improvements
```

---

## Highlights

| Feature | Description |
|---------|------------|
| 🤖 **AI Coding Agent** | Develop apps, fix bugs, code review, test generation — 92% code_gen success rate |
| 🔍 **AI Research Agent** | Market analysis, competitor research, strategic reports |
| ✍️ **AI Writing Agent** | Blogs, technical docs, product copy, marketing content |
| 📦 **Plugin Marketplace** | One-click install/uninstall. 5 official plugins included |
| 🧠 **Local Memory** | Remembers your projects, decisions, experiences, goals |
| 🔗 **Multi-Agent Workflow** | CEO → PM → Coder → Writer → Review — automated pipeline |
| ⚡ **One-Command Start** | `python main.py start` — auto-detect OS, fix dependencies, launch |
| ⏱️ **Timeline UI** | Visual pipeline: Request → Plan → Skill → Execute → Result |

---

## Quick Start

```bash
git clone https://github.com/<user>/personal-ai-os
cd personal-ai-os
cp .env.example .env
# Edit .env: DEEPSEEK_API_KEY=sk-...
python main.py start
```

Open another terminal:
```bash
cd studio && npm install && npm run dev
# http://localhost:3000
```

### Your First Task

```bash
python main.py chat "Create a FastAPI todo API with CRUD and tests"
```

Or open Studio → Chat tab → type your goal.

---

## Included Official Plugins

| Plugin | Default | Capabilities |
|--------|:--:|------|
| **Coding Agent** | ✅ ON | Python dev, web backend, bug fix, code review, test generation |
| **Research Agent** | ✅ ON | Market analysis, competitor research, strategic reports |
| **Writing Agent** | ✅ ON | Blog posts, technical docs, product copy, email |
| **Knowledge & File** | OFF | Connect local files, Markdown, knowledge base Q&A |
| **Web Assistant** | OFF | Web scraping, content extraction, online research |

Toggle in Studio → Plugins. One click.

---

## Architecture

```
Studio UI (React 19) → API Server (FastAPI, 60+ endpoints)
    → Kernel (14 modules)
        → Agent Runtime (7 agents)
            → Memory (SQLite, 9 tables)
                → Plugin Marketplace (5 official plugins)
```

**14 kernel modules**: Config · Events · LLM Router · Workspace · Registry · Router · Task Graph · Comm Bus · Reputation · Budget · Audit · Evolution · Skill System · Plugin Runtime

**7 Agents**: CEO · Project Manager · Coding · Research · Writing · Reflection · Environment

**Technical Stack**: Python 3.12 · FastAPI · SQLAlchemy · SQLite · React 19 · TypeScript · Vite · Tailwind · DeepSeek / OpenAI / Anthropic / Ollama

---

## Verified

| Metric | Result |
|--------|:--:|
| Skill Benchmark (32 cases) | 97% accuracy |
| Real Task Validation (12 tasks) | 91% tool pass rate |
| Fresh Install Test (3 demos) | System launch + API + Studio all healthy |
| Plugin discovery + lifecycle | install → uninstall → reinstall verified |

---

## Known Limitations

- **Shell approval layer** blocks `pytest`/`npm test` in default workspace. Toggle via `tools/registry.py` risk rules or use `python main.py restart` for safety.
- **Vector search** not yet integrated. Memory uses SQL `LIKE` queries. Planned for v1.1.
- **Multi-user** not supported. Single profile, single process.
- **Windows** requires Git Bash. Linux/macOS run natively.
- **No Docker UI entry**. Docker is dev-only, not user-facing. Use `python main.py start`.

---

## Roadmap

```
v1.0.0  First Public Beta ← you are here
v1.1.0  Community plugins + rating leaderboard
v1.2.0  Vector memory search
v1.5.0  Multi-user + Docker sandbox
v2.0.0  Plugin marketplace economy
```

---

## Feedback

[FEEDBACK.md](FEEDBACK.md) — tell us what you think.

---

## License

MIT — see [LICENSE](LICENSE)

---

🤖 Built with AI | Personal AI OS v1.0.0
