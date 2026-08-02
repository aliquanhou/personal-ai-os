"""
中文 TTS 工具 - 供应商抽象基类
所有 TTS 供应商实现统一接口，支持可插拔切换。
"""
from abc import ABC, abstractmethod
from typing import Optional


class TTSProvider(ABC):
    """TTS 供应商抽象基类"""

    name: str = "base"
    description: str = ""

    @abstractmethod
    def synthesize(self, text: str, voice: str = "", **kwargs) -> bytes:
        """
        将文本合成为音频字节流。

        Args:
            text: 要合成的文本
            voice: 音色标识（可选）
            **kwargs: 供应商特定参数（语速/音量/情感等）

        Returns:
            bytes: 音频数据（通常为 MP3/WAV）
        """
        raise NotImplementedError

    @abstractmethod
    def list_voices(self) -> list:
        """返回可用音色列表"""
        raise NotImplementedError


class TTSProviderRegistry:
    """供应商注册表，支持按名称获取"""

    def __init__(self):
        self._providers: dict[str, TTSProvider] = {}

    def register(self, provider: TTSProvider):
        self._providers[provider.name] = provider

    def get(self, name: str) -> Optional[TTSProvider]:
        return self._providers.get(name)

    def available(self) -> list[str]:
        return list(self._providers.keys())

    def default(self) -> TTSProvider:
        """返回默认（最廉价）供应商"""
        if "volcengine" in self._providers:
            return self._providers["volcengine"]
        if self._providers:
            return list(self._providers.values())[0]
        raise RuntimeError("没有可用的 TTS 供应商，请先注册")


# 全局注册表
registry = TTSProviderRegistry()
