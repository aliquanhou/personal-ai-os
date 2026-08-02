# Personal AI OS v1.0

> **Your autonomous AI workstation.**
>
> Not a chatbot. Not an agent framework. An AI operating system runtime — like running a micro AI company on your machine.

---

## What You Get

| Capability | Status |
|-----------|:--:|
| 🤖 **AI Coding Agent** — develop apps, fix bugs, review code, run tests | ✅ |
| 🔍 **AI Research Agent** — market analysis, competitor research, reports | ✅ |
| ✍️ **AI Writing Agent** — blogs, docs, product copy, technical writing | ✅ |
| 📦 **Plugin Marketplace** — install/uninstall capability packs, one click | ✅ |
| 🧠 **Local Memory** — remembers your projects, decisions, experiences | ✅ |
| 🔗 **Multi-Agent Workflow** — CEO → PM → Coder → Writer → Review, automated | ✅ |
| ⚡ **AI Native Setup** — `python main.py start`, auto-detect + fix environment | ✅ |
| ⏱️ **Task Timeline** — visual pipeline: Request → Plan → Skill → Execute → Result | ✅ |

---

## Quick Start (5 minutes)

```bash
# 1. Clone
git clone <repo-url> personal-ai-os
cd personal-ai-os

# 2. Configure API key
cp .env.example .env
# Edit .env, add your LLM API key
# Recommended: DEEPSEEK_API_KEY=sk-...

# 3. One-command launch
python main.py start
# Auto-checks: OS → Python → dependencies → Node → Git → .env → port
# Installs missing packages automatically

# 4. Open Studio
cd studio && npm install && npm run dev
# http://localhost:3000
```

**First task:**
```bash
python main.py chat "Create a FastAPI todo API with CRUD and tests"
```

---

## Architecture

```
User → Studio UI → API Server → Kernel → Agent Runtime → Memory
                                    │
                          ┌─────────┼─────────┐
                          │         │         │
                     Agent Registry  Router  Task Graph
                          │         │         │
                     Skill System  Comm Bus  Governance
                          │
                    Plugin Marketplace
```

**Core modules**: Config · Events · LLM Router · Workspace · Agent Registry · Router · Task Graph · Comm Bus · Reputation · Budget · Audit · Evolution · Plugin Runtime · Skill System

---

## Included Official Plugins

| Plugin | Default | Does |
|--------|:--:|------|
| **Coding Agent** | ✅ ON | Python dev, web backend, bug fix, code review, test generation |
| **Research Agent** | ✅ ON | Market analysis, competitor research, strategic reports |
| **Writing Agent** | ✅ ON | Blog posts, technical docs, product copy, email |
| **Knowledge & File** | OFF | Connect local files, Markdown, knowledge base Q&A |
| **Web Assistant** | OFF | Web scraping, content extraction, online research |

Toggle in Studio → Plugins. One click.

---

## CLI Reference

```bash
python main.py start                  # First-run: auto-detect + fix + launch
python main.py serve                  # Direct start (skip checks)
python main.py restart --port 8001    # Precision restart (port-based, not kill-all)
python main.py chat "your goal"       # Send a task to the CEO Agent
python main.py agents                 # List all available agents
python main.py profile                # Show your AI-known profile
python main.py benchmark              # Run 32-case Skill Benchmark suite
```

---

## Configuration

`.env` file:

```bash
# DeepSeek (recommended: low cost, strong Chinese)
DEEPSEEK_API_KEY=sk-...
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_MODEL=deepseek-chat

# Or OpenAI
# OPENAI_API_KEY=sk-...
# DEFAULT_LLM_PROVIDER=openai
# DEFAULT_MODEL=gpt-4o

# Or local Ollama
# DEFAULT_LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434/v1
```

---

## Create a Plugin

`plugins/my-plugin/plugin.json`:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "display_name": "My Plugin",
  "description": "Custom capability pack",
  "official": false,
  "skills": ["python_backend"],
  "target_agents": ["coding_agent"],
  "enabled": true
}
```

Restart. Auto-discovered.

---

## Documentation

Full architecture docs in [docs/architecture/](docs/architecture/):

[overview](docs/architecture/overview.md) · [kernel](docs/architecture/kernel.md) · [agent-runtime](docs/architecture/agent-runtime.md) · [memory](docs/architecture/memory-architecture.md) · [routing](docs/architecture/routing-and-orchestration.md) · [communication](docs/architecture/communication-layer.md) · [governance](docs/architecture/governance-layer.md) · [security](docs/architecture/security-model.md)

---

## Technical Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| Frontend | React 19, TypeScript, Vite, Tailwind, Zustand |
| LLM | DeepSeek / OpenAI / Anthropic / Ollama |
| Testing | pytest, Scenario Framework, 32-case Benchmark Suite (97%) |

---

## Release History

```
v1.0.0  First Public Beta — Plugin Marketplace + Complete UI
v0.8.0  Plugin Marketplace + Studio UI
v0.7.0  AI Native User Experience
v0.6.0  Production Readiness + Skill Architecture
v0.5.0  Governance Layer
v0.4.0  Agent Communication Layer
v0.3.0  Agent Organization Layer
v0.2.0  Reliability Layer
```

18 commits. 13 tags. 195 files.

---

## Vision

**One person + one AI team = micro enterprise.**

---

🤖 Built with AI | Personal AI OS v1.0.0
