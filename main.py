# -*- coding: utf-8 -*-
"""Personal AI OS — Main Entry Point

Start the full Personal AI OS server:
    python main.py

Or use the CLI for individual operations:
    python main.py chat "帮我开发一个电商网站"
    python main.py memory-search "用户偏好"
    python main.py agents
"""

import asyncio
import sys

import typer

app = typer.Typer(help="Personal AI OS CLI")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = True):
    """Start the Personal AI OS server."""
    import uvicorn
    uvicorn.run("api.app:app", host=host, port=port, reload=reload)


@app.command()
def chat(message: str, agent: str = "ceo"):
    """Send a chat message to an agent (CLI mode)."""

    async def _chat():
        from agents.runtime import get_agent_runtime
        from agents.ceo import CEOAgent
        from agents.project_manager import ProjectManagerAgent
        from agents.coding import CodingAgent, ResearchAgent, WritingAgent
        from agents.reflection import ReflectionAgent
        from memory.manager import get_memory

        runtime = get_agent_runtime()
        runtime.register(CEOAgent())
        runtime.register(ProjectManagerAgent())
        runtime.register(CodingAgent())
        runtime.register(ResearchAgent())
        runtime.register(WritingAgent())
        runtime.register(ReflectionAgent())

        print(f"\n🤖 正在调用 {agent}...\n")
        result = await runtime.execute(agent, message)
        print(result.output)
        if result.tool_calls:
            print(f"\n📎 工具调用: {len(result.tool_calls)} 次")
            for tc in result.tool_calls:
                status = "✅" if tc["success"] else "❌"
                print(f"  {status} {tc['tool']}: {str(tc['args'])[:80]}")
        print(f"\n⏱️  耗时: {result.duration_ms:.0f}ms | 迭代: {result.iterations} | 记忆更新: {result.memory_updates}")

    asyncio.run(_chat())


@app.command()
def memory_search(query: str):
    """Search the personal memory."""

    async def _search():
        from memory.manager import get_memory
        memory = get_memory()
        results = memory.search_knowledge(query)
        print(f"\n🔍 搜索记忆: {query}\n")
        for r in results:
            print(f"[{r['category']}] {r['title']}")
            print(f"  {r['content'][:200]}")
            print()

    asyncio.run(_search())


@app.command()
def agents():
    """List available agents."""

    async def _list():
        from agents.runtime import get_agent_runtime
        from agents.ceo import CEOAgent
        from agents.project_manager import ProjectManagerAgent
        from agents.coding import CodingAgent, ResearchAgent, WritingAgent
        from agents.reflection import ReflectionAgent

        runtime = get_agent_runtime()
        runtime.register(CEOAgent())
        runtime.register(ProjectManagerAgent())
        runtime.register(CodingAgent())
        runtime.register(ResearchAgent())
        runtime.register(WritingAgent())
        runtime.register(ReflectionAgent())

        print("\n🤖 可用 Agents:\n")
        for a in runtime.list_agents():
            print(f"  {a['name']}: {a['description']}")

    asyncio.run(_list())


@app.command()
def profile():
    """Show user profile."""

    async def _profile():
        from memory.manager import get_memory
        import json
        p = get_memory().get_profile()
        print("\n👤 用户档案:\n")
        for k, v in p.items():
            print(f"  {k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v}")

    asyncio.run(_profile())


@app.command()
def restart(port: int = 8001, host: str = "127.0.0.1"):
    """Restart the server gracefully — kill only the process on PORT, then relaunch.

    Unlike 'taskkill -f -im python.exe' (which kills ALL Python),
    this uses netstat/lsof to find only the server process on the given port.
    """

    async def _restart():
        from tools.registry import ServerRestartTool
        tool = ServerRestartTool()
        result = await tool.execute(port=port, host=host)
        if result.success:
            print(f"[OK] {result.output}")
        else:
            print(f"[FAIL] {result.error}", file=sys.stderr)
            sys.exit(1)

    asyncio.run(_restart())


@app.command()
def start(fix: bool = True, port: int = 8001, host: str = "127.0.0.1"):
    """First-run experience — check environment, fix issues, start server.

    Detects OS, Python, Node, Git, dependencies, config, ports.
    Auto-fixes solvable problems. Starts the server when ready.

    Usage:
      python main.py start           # Full check + start
      python main.py start --no-fix  # Check only, don't fix
    """

    def _run():
        import subprocess, os, sys, time
        from pathlib import Path

        project_root = Path(__file__).parent

        print("\n" + "=" * 60)
        print("  Personal AI OS — First Run")
        print("  AI Chief of Staff | v0.7.0-alpha")
        print("=" * 60)

        checks_passed = 0
        checks_total = 0
        issues = []

        # ── 1. OS ──
        checks_total += 1
        print(f"\n[1/7] OS Check...", end=" ")
        try:
            import platform
            system = platform.system()
            version = platform.version()
            print(f"OK  ({system} {version[:40]})")
            checks_passed += 1
        except Exception as e:
            print(f"FAIL — {e}")
            issues.append(("OS detection", str(e), None))

        # ── 2. Python ──
        checks_total += 1
        print(f"[2/7] Python...", end=" ")
        py_ver = sys.version_info
        if py_ver >= (3, 10):
            print(f"OK  ({sys.version.split()[0]})")
            checks_passed += 1
        else:
            print(f"WARN — Python {sys.version.split()[0]} (need 3.10+)")
            issues.append(("Python version", f"3.10+ required, have {sys.version.split()[0]}",
                          "Install Python 3.12 from https://python.org"))

        # ── 3. Dependencies ──
        checks_total += 1
        print(f"[3/7] Dependencies...", end=" ")
        required = ["fastapi", "uvicorn", "sqlalchemy", "httpx", "pydantic", "typer"]
        missing = []
        for pkg in required:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
        if not missing:
            print(f"OK  ({len(required)} packages)")
            checks_passed += 1
        else:
            print(f"WARN — missing: {', '.join(missing)}")
            cmd = f"pip install {' '.join(missing)}"
            issues.append((f"Missing deps: {', '.join(missing)}", "", cmd))
            if fix:
                print(f"       Auto-installing...")
                subprocess.run([sys.executable, "-m", "pip", "install"] + missing,
                             capture_output=True)
                # Re-check
                still_missing = []
                for pkg in missing:
                    try:
                        __import__(pkg)
                    except ImportError:
                        still_missing.append(pkg)
                if not still_missing:
                    checks_passed += 1
                    print(f"       FIXED — all dependencies installed")

        # ── 4. Node.js ──
        checks_total += 1
        print(f"[4/7] Node.js...", end=" ")
        try:
            r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                print(f"OK  ({r.stdout.strip()})")
                checks_passed += 1
            else:
                print("WARN — Node not found (Studio frontend needs it)")
                issues.append(("Node.js", "Not installed or not in PATH",
                              "Install Node.js 20+ from https://nodejs.org"))
        except FileNotFoundError:
            print("WARN — Node not found (Studio frontend needs it)")
            issues.append(("Node.js", "Not found", "Install Node.js 20+ from https://nodejs.org"))

        # ── 5. Git ──
        checks_total += 1
        print(f"[5/7] Git...", end=" ")
        try:
            r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                print(f"OK  ({r.stdout.strip()[:30]})")
                checks_passed += 1
            else:
                print("WARN")
                issues.append(("Git", "Not found", "Install Git from https://git-scm.com"))
        except FileNotFoundError:
            print("WARN")
            issues.append(("Git", "Not found", "Install Git from https://git-scm.com"))

        # ── 6. .env Config ──
        checks_total += 1
        print(f"[6/7] Configuration (.env)...", end=" ")
        env_path = project_root / ".env"
        if env_path.exists():
            content = env_path.read_text()
            if "DEEPSEEK_API_KEY=sk-" in content and "sk-..." not in content:
                print("OK  (API key configured)")
                checks_passed += 1
            elif "OPENAI_API_KEY=sk-" in content and "sk-..." not in content:
                print("OK  (OpenAI key configured)")
                checks_passed += 1
            elif "ANTHROPIC_API_KEY=sk-ant-" in content and "sk-ant-..." not in content:
                print("OK  (Anthropic key configured)")
                checks_passed += 1
            else:
                print("WARN — API key not configured")
                issues.append((".env API key", "No valid LLM API key found",
                              "Edit .env and set DEEPSEEK_API_KEY=sk-..."))
        else:
            print("WARN — .env not found, creating from .env.example")
            example = project_root / ".env.example"
            if example.exists():
                env_path.write_text(example.read_text())
                print("       Created .env. Edit it to add your API key.")
            issues.append((".env file", "Created from template, needs API key",
                          "Edit .env and set DEEPSEEK_API_KEY=sk-..."))

        # ── 7. Port ──
        checks_total += 1
        print(f"[7/7] Port {port}...", end=" ")
        try:
            if sys.platform == "win32":
                r = subprocess.run(
                    ["bash", "-c", f"netstat -ano | grep ':{port} ' | grep LISTENING | head -3"],
                    capture_output=True, text=True, timeout=5
                )
                if r.stdout.strip():
                    print(f"WARN — port {port} is in use")
                    issues.append((f"Port {port}", "Already in use",
                                  f"Run: python main.py restart --port {port}"))
                else:
                    print(f"OK  (free)")
                    checks_passed += 1
            else:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                result = s.connect_ex((host, port))
                s.close()
                if result == 0:
                    print(f"WARN — port {port} is in use")
                    issues.append((f"Port {port}", "In use", f"Run: lsof -ti:{port} | xargs kill"))
                else:
                    print(f"OK  (free)")
                    checks_passed += 1
        except Exception:
            print("OK  (could not verify, will try to bind)")

        # ── Summary ──
        print(f"\n{'='*60}")
        print(f"  RESULT: {checks_passed}/{checks_total} checks passed")
        print(f"{'='*60}")

        if issues and fix:
            print(f"\n  {len(issues)} issue(s) found:")
            for i, (name, detail, suggestion) in enumerate(issues, 1):
                print(f"\n  [{i}] {name}")
                if detail:
                    print(f"      {detail}")
                if suggestion:
                    print(f"      Fix: {suggestion}")

        # ── Start server ──
        if checks_passed >= checks_total - 1 or fix:
            print(f"\n{'='*60}")
            print(f"  Starting Personal AI OS on {host}:{port}...")
            print(f"{'='*60}")
            print(f"\n  Studio:  http://localhost:3000  (cd studio && npm run dev)")
            print(f"  API:     http://{host}:{port}/health")
            print(f"  Agents:  python main.py agents")
            print(f"  Chat:    python main.py chat \"your goal\"")
            print(f"\n  Starting server...\n")

            import uvicorn
            uvicorn.run("api.app:app", host=host, port=port, reload=False)
        else:
            print(f"\n  Too many issues. Fix them and run again: python main.py start")
            print(f"  Or skip checks: python main.py serve")

    _run()


@app.command()
def benchmark(json_output: bool = False, simulate_ratings: bool = False):
    """Run the Skill Benchmark suite against the current system state."""

    def _run():
        from tests.benchmark.runner import SkillBenchmark

        bench = SkillBenchmark()
        bench.load_cases()

        print("\n" + "=" * 60)
        print("  Personal AI OS — Skill Benchmark v0.1")
        print("=" * 60)

        report = bench.run_all()

        # ── Summary ──
        print(f"\n{'='*60}")
        print(f"  RESULTS: {report.passed}/{report.total_cases} passed")
        print(f"{'='*60}")
        print(f"  Router Accuracy:    {report.router_accuracy:.0%}")
        print(f"  Skill Precision:    {report.skill_precision_avg:.0%}")
        print(f"  Avg Confidence:     {report.confidence_avg:.3f}")
        print(f"  Gap Detection:      {report.gap_detection_accuracy:.0%}")
        print(f"\n  {report.summary}")
        print(f"  {report.recommendation}")

        # ── By Category ──
        print(f"\n{'─'*60}")
        print(f"  BY CATEGORY")
        print(f"{'─'*60}")
        for cat, stats in sorted(report.by_category.items()):
            bar = "█" * int(stats["passed"] / max(stats["total"], 1) * 20)
            print(f"  {cat:15s} {stats['passed']:2d}/{stats['total']:2d}  {bar}")

        # ── Per-case detail ──
        print(f"\n{'─'*60}")
        print(f"  PER-CASE DETAIL")
        print(f"{'─'*60}")
        for r in report.results:
            icon = "✅" if r["passed"] else "❌"
            ag = "✓" if r["agent_match"] else "✗"
            print(f"  {icon} {r['id']:4s} [{r['category']:12s}] agent={ag} "
                  f"skills={r['skills_hit']}/{r['skills_hit']+r['skills_miss']} "
                  f"conf={r['confidence']:.2f} "
                  f"| {r['note'][:60]}")
            if r["error"]:
                print(f"       ERROR: {r['error']}")

        # ── Skill Ratings ──
        print(f"\n{'─'*60}")
        print(f"  SKILL RATINGS")
        print(f"{'─'*60}")
        for sr in report.skill_ratings:
            r = sr["rating"]
            bar = "█" * int(r["success_rate"] * 10) + "░" * (10 - int(r["success_rate"] * 10))
            print(f"  [{r['tier']}] {sr['name']:25s} {bar} SR={r['success_rate']:.2f} "
                  f"uses={r['total_uses']}")

        # ── Rating Evolution Simulation ──
        if simulate_ratings:
            print(f"\n{'─'*60}")
            print(f"  RATING EVOLUTION (100 iterations simulated)")
            print(f"{'─'*60}")
            evolution = bench.simulate_rating_evolution(iterations=100)
            for skill_name, snapshots in evolution.items():
                if len(snapshots) >= 3:
                    first = snapshots[0]
                    last = snapshots[-1]
                    delta = last["reputation_score"] - first["reputation_score"]
                    trend = "↑" if delta > 0.05 else ("↓" if delta < -0.05 else "→")
                    print(f"  {trend} {skill_name:25s} "
                          f"{first['tier']}({first['reputation_score']:.2f}) → "
                          f"{last['tier']}({last['reputation_score']:.2f}) "
                          f"Δ={delta:+.2f}")

        # ── JSON output ──
        if json_output:
            import json as _json
            output = {
                "summary": report.summary,
                "recommendation": report.recommendation,
                "metrics": {
                    "router_accuracy": report.router_accuracy,
                    "skill_precision": report.skill_precision_avg,
                    "confidence": report.confidence_avg,
                    "gap_detection": report.gap_detection_accuracy,
                },
                "by_category": report.by_category,
                "results": report.results,
                "skill_ratings": report.skill_ratings,
            }
            print(f"\n{'='*60}")
            print(_json.dumps(output, ensure_ascii=False, indent=2))

        print(f"\n{'='*60}\n")

    _run()


if __name__ == "__main__":
    app()
