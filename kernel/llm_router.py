"""Personal AI OS Agent Runtime — LLM Router

Routes LLM calls to the right provider (DeepSeek, OpenAI, Anthropic, Ollama).
Single interface, multiple backends.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from kernel.config import LLMConfig, get_config

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict:
        """Send a chat completion request. Returns the response message dict."""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream a chat completion. Yields content chunks."""
        ...


class OpenAICompatibleProvider(LLMProvider):
    """Provider for OpenAI-compatible APIs (DeepSeek, OpenAI, Ollama, etc.)."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key

    async def _request(self, messages, tools=None, temperature=0.7, max_tokens=4096, stream=False):
        import httpx

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        body = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            if response.status_code != 200:
                error_text = response.text[:500]
                logger.error("LLM API error: %s — %s", response.status_code, error_text)
                raise RuntimeError(f"LLM API error ({response.status_code}): {error_text}")
            return response

    async def chat(self, messages, tools=None, temperature=0.7, max_tokens=4096):
        response = await self._request(messages, tools, temperature, max_tokens, stream=False)
        data = response.json()
        choice = data["choices"][0]
        msg = choice["message"]
        result = {"role": msg.get("role", "assistant"), "content": msg.get("content", "")}
        if msg.get("tool_calls"):
            result["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]},
                }
                for tc in msg["tool_calls"]
            ]
        return result

    async def chat_stream(self, messages, tools=None, temperature=0.7, max_tokens=4096):
        response = await self._request(messages, tools, temperature, max_tokens, stream=True)
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    if delta.get("content"):
                        yield delta["content"]
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude API."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key

    async def chat(self, messages, tools=None, temperature=0.7, max_tokens=4096):
        import httpx

        # Convert OpenAI format messages to Anthropic format
        system_msg = ""
        anthropic_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                anthropic_msgs.append({"role": m["role"], "content": m["content"]})

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        body = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "messages": anthropic_msgs,
        }
        if system_msg:
            body["system"] = system_msg
        if tools:
            body["tools"] = self._convert_tools(tools)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body,
            )
            if response.status_code != 200:
                error_text = response.text[:500]
                raise RuntimeError(f"Anthropic API error ({response.status_code}): {error_text}")

            data = response.json()
            content_blocks = data.get("content", [])
            text = ""
            tool_calls = []
            for block in content_blocks:
                if block["type"] == "text":
                    text += block["text"]
                elif block["type"] == "tool_use":
                    tool_calls.append({
                        "id": block["id"],
                        "type": "function",
                        "function": {
                            "name": block["name"],
                            "arguments": json.dumps(block["input"]),
                        },
                    })

            result = {"role": "assistant", "content": text}
            if tool_calls:
                result["tool_calls"] = tool_calls
            return result

    async def chat_stream(self, messages, tools=None, temperature=0.7, max_tokens=4096):
        # Simplification: non-streaming fallback for Anthropic
        result = await self.chat(messages, tools, temperature, max_tokens)
        yield result.get("content", "")

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert OpenAI tool format to Anthropic format."""
        converted = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                converted.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
                })
        return converted


class LLMRouter:
    """Routes LLM calls to the configured provider."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or get_config().llm
        self._provider: LLMProvider | None = None

    @property
    def provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider

    def _create_provider(self) -> LLMProvider:
        if self.config.provider == "anthropic":
            return AnthropicProvider(self.config)
        else:
            # All OpenAI-compatible: deepseek, openai, ollama, qwen, etc.
            return OpenAICompatibleProvider(self.config)

    async def chat(self, messages, tools=None, temperature=None, max_tokens=None):
        return await self.provider.chat(
            messages,
            tools=tools,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
        )

    async def chat_stream(self, messages, tools=None, temperature=None, max_tokens=None):
        async for chunk in self.provider.chat_stream(
            messages,
            tools=tools,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
        ):
            yield chunk


# Global singleton
_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
