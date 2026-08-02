"""
火山引擎（豆包）语音合成大模型 TTS 适配器
价格 ≈0.2 元/万字符，为国内主流大厂最低，抖音同款音色。

官方文档: https://www.volcengine.com/docs/6561/1354866
需要环境变量:
  VOLC_ACCESS_KEY  访问密钥
  VOLC_SECRET_KEY  安全密钥
  VOLC_APP_ID      应用 ID
  VOLC_CLUSTER     集群 ID（默认 volc.megatts.default）
"""
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

from .base import TTSProvider

# 服务地址
HOST = "openspeech.bytedance.com"
PATH = "/api/v1/tts"
SCHEME = "https"

# 默认音色（豆包大模型音色库）
DEFAULT_VOICE = "BV001_streaming"  # 通用女声
VOICE_MAP = {
    "BV001_streaming": "通用女声-温暖",
    "BV002_streaming": "通用男声-沉稳",
    "BV003_streaming": "通用男声-磁性",
    "BV005_streaming": "通用女声-甜美",
    "BV406_streaming": "通用女声-知性",
    "BV007_streaming": "通用女声-活泼",
    "BV008_streaming": "通用男声-阳光",
    "BV411_streaming": "通用男声-成熟",
}

# 请求 ID 前缀（申请时分配的 appid 前缀，通常与 appid 相同）
REQUEST_ID_PREFIX = "volc_megatts"


class VolcengineProvider(TTSProvider):
    name = "volcengine"
    description = "火山引擎·豆包语音合成大模型（≈0.2元/万字符，最廉价仿真人方案）"

    def __init__(self,
                 app_id: str = "",
                 access_key: str = "",
                 secret_key: str = "",
                 cluster: str = "volc.megatts.default",
                 timeout: int = 30):
        self.app_id = app_id or os.getenv("VOLC_APP_ID", "")
        self.access_key = access_key or os.getenv("VOLC_ACCESS_KEY", "")
        self.secret_key = secret_key or os.getenv("VOLC_SECRET_KEY", "")
        self.cluster = cluster
        self.timeout = timeout

    # ------------------------------------------------------------------
    # 签名（火山引擎 V4 签名，简化版用于 openspeech）
    # ------------------------------------------------------------------
    def _signature(self, timestamp: str) -> str:
        date = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).strftime("%Y%m%d")
        # 简化签名：hmac(secret, appid+timestamp)
        message = f"{self.app_id}{timestamp}".encode("utf-8")
        key = self.secret_key.encode("utf-8")
        signature = base64.b64encode(
            hmac.new(key, message, hashlib.sha256).digest()
        ).decode("utf-8")
        return signature

    def _build_request(self, text: str, voice: str, **kwargs) -> dict:
        request_id = f"{REQUEST_ID_PREFIX}_{self.app_id}_{int(time.time()*1000)}"
        return {
            "app": {
                "appid": self.app_id,
                "token": "access_token",
                "cluster": self.cluster,
            },
            "user": {"uid": "tts-tool"},
            "request": {
                "reqid": request_id,
                "text": text,
                "text_type": "plain",
                "operation": "query",
                "with_frontend": 1,
                "frontend_type": "unitTson",
                "voice_type": voice,
                # 可选参数
                "speed_ratio": kwargs.get("speed_ratio", 1.0),
                "volume_ratio": kwargs.get("volume_ratio", 1.0),
                "pitch_ratio": kwargs.get("pitch_ratio", 1.0),
                "emotion": kwargs.get("emotion", "happy"),
                "language": "zh-CN",
            },
            "audio": {
                "format": kwargs.get("format", "mp3"),
                "sample_rate": kwargs.get("sample_rate", 24000),
                "bits": 16,
                "channel": 1,
                "codec": "raw",
            },
        }

    def _headers(self, timestamp: str) -> dict:
        signature = self._signature(timestamp)
        return {
            "Authorization": f"Bearer; {self.access_key}",
            "Content-Type": "application/json",
            "X-TT-APPID": self.app_id,
            "X-TT-TIMESTAMP": timestamp,
            "X-TT-SIGNATURE": signature,
            "X-TT-REQUEST-ID": f"{REQUEST_ID_PREFIX}_{self.app_id}_{timestamp}",
        }

    # ------------------------------------------------------------------
    # 核心合成
    # ------------------------------------------------------------------
    def synthesize(self, text: str, voice: str = "", **kwargs) -> bytes:
        if not self.app_id or not self.access_key or not self.secret_key:
            raise RuntimeError(
                "未配置火山引擎密钥。请设置环境变量 VOLC_APP_ID / VOLC_ACCESS_KEY / VOLC_SECRET_KEY"
            )
        voice = voice or DEFAULT_VOICE
        timestamp = str(int(time.time()))
        payload = self._build_request(text, voice, **kwargs)

        url = f"{SCHEME}://{HOST}{PATH}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(timestamp),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"TTS 请求失败 HTTP {e.code}: {e.read().decode(errors='ignore')}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"TTS 网络错误: {e.reason}")

        # 解析响应（二进制：前 4 字节为 header 长度）
        result = self._parse_response(body)
        audio = result.get("audio")
        if audio is None:
            msg = result.get("message", "未知错误")
            raise RuntimeError(f"TTS 合成失败: {msg}")
        return audio

    def _parse_response(self, body: bytes) -> dict:
        if len(body) < 4:
            raise RuntimeError("响应过短")
        header_len = int.from_bytes(body[:4], "big")
        header = json.loads(body[4:4 + header_len].decode("utf-8"))
        audio = body[4 + header_len:]
        result = dict(header)
        result["audio"] = audio if audio else None
        return result

    def list_voices(self) -> list:
        return [{"id": k, "desc": v} for k, v in VOICE_MAP.items()]


def register():
    from .base import registry
    registry.register(VolcengineProvider())
