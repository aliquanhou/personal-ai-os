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


if __name__ == "__main__":
    app()
