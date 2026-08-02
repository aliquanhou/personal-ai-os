# -*- coding: utf-8 -*-
"""Personal AI OS Kernel — Configuration Management"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class MemoryConfig:
    db_url: str = "sqlite+aiosqlite:///data/personal_ai_os.db"
    file_dir: str = "./memory_data"


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8000


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-change-me"

    @classmethod
    def from_env(cls) -> "Config":
        provider = os.getenv("DEFAULT_LLM_PROVIDER", "deepseek")
        model = os.getenv("DEFAULT_MODEL", "")
        api_key = ""

        # Provider-specific base URLs
        provider_base_urls = {
            "deepseek": "https://api.deepseek.com/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "ollama": "http://localhost:11434/v1",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }

        if provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            model = model or "deepseek-chat"
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            model = model or "claude-sonnet-5-20251001"
            base_url = "https://api.anthropic.com"
        elif provider == "ollama":
            api_key = "ollama"
            model = model or "llama3"
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        elif provider == "qwen":
            api_key = os.getenv("QWEN_API_KEY", os.getenv("DASHSCOPE_API_KEY", ""))
            model = model or "qwen-plus"
            base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        else:  # openai or any OpenAI-compatible
            api_key = os.getenv("OPENAI_API_KEY", "")
            model = model or "gpt-4o"
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

        return cls(
            llm=LLMConfig(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
            ),
            memory=MemoryConfig(
                db_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/personal_ai_os.db"),
                file_dir=os.getenv("MEMORY_DIR", "./memory_data"),
            ),
            server=ServerConfig(
                host=os.getenv("HOST", "127.0.0.1"),
                port=int(os.getenv("PORT", "8000")),
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
        )


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    global _config
    _config = config
