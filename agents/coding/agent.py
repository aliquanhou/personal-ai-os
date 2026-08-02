# -*- coding: utf-8 -*-
"""Personal AI OS Agents — Coding Agent

Handles code generation, review, and debugging tasks.
"""

from agents.runtime import AgentContext, BaseAgent


class CodingAgent(BaseAgent):
    """Coding Agent — writes, reviews, and debugs code."""

    def __init__(self):
        super().__init__(
            name="coding_agent",
            description="代码编写、审查和调试专家",
        )

    def system_prompt(self, ctx: AgentContext) -> str:
        return f"""你是一个 AI 编程助手。你可以：
- 编写高质量代码
- 审查代码质量
- 调试和修复问题
- 创建项目结构

## 用户信息
技能水平: {ctx.user_profile.get('skill_level', 'intermediate')}
技术栈: {', '.join(ctx.user_profile.get('tech_stack', []))}

## 工具使用
- 用 read_file 读取现有代码
- 用 write_file 创建或修改文件
- 用 shell 运行测试和命令
- 用 save_to_memory 记录重要的技术决策

请用中文回复。写代码时注意遵循用户现有代码风格。"""


class ResearchAgent(BaseAgent):
    """Research Agent — searches, analyzes, and synthesizes information."""

    def __init__(self):
        super().__init__(
            name="research_agent",
            description="信息搜索、分析和综合专家",
        )

    def system_prompt(self, ctx: AgentContext) -> str:
        return f"""你是一个 AI 研究助手。你可以：
- 搜索和分析信息
- 总结关键发现
- 提供深度分析

## 工具使用
- 用 search_memory 查找已有的知识
- 用 read_file 读取文件
- 用 save_to_memory 保存研究发现

请用中文回复。提供的信息要有根据、有条理。"""


class WritingAgent(BaseAgent):
    """Writing Agent — creates, edits, and improves written content."""

    def __init__(self):
        super().__init__(
            name="writing_agent",
            description="写作、编辑和内容创作专家",
        )

    def system_prompt(self, ctx: AgentContext) -> str:
        return f"""你是一个 AI 写作助手。你可以：
- 撰写文章、报告、文档
- 编辑和改进文本
- 翻译内容

请用中文回复（除非用户指定其他语言）。写作风格根据场景调整。"""
