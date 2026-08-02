"""TTS 语音生成工具 - 基于 edge-tts 实现文字转语音

用法:
    python main.py "要转换的文字" -o output.mp3
    python main.py "要转换的文字" -v zh-CN-XiaoxiaoNeural -o output.mp3

依赖:
    pip install edge-tts asyncio

edge-tts 免费使用微软 Edge 的 TTS 服务，无需 API key。
"""

import argparse
import asyncio
import sys

import edge_tts


async def text_to_speech(text: str, output_file: str, voice: str) -> None:
    """将文字转换为语音并保存为音频文件。

    Args:
        text: 要转换的文字
        output_file: 输出音频文件路径（支持 mp3 等格式）
        voice: 语音角色名称
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)
    print(f"✅ 已生成音频: {output_file}")
    print(f"   语音角色: {voice}")


async def list_voices() -> None:
    """列出可用的语音角色。"""
    voices = await edge_tts.list_voices()
    print(f"共 {len(voices)} 个语音角色:")
    for v in voices:
        print(f"  {v['ShortName']} - {v['Locale']} - {v['Gender']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TTS 语音生成工具 - 基于 edge-tts",
    )
    parser.add_argument("text", nargs="?", help="要转换的文字")
    parser.add_argument(
        "-o", "--output",
        default="output.mp3",
        help="输出音频文件路径 (默认: output.mp3)",
    )
    parser.add_argument(
        "-v", "--voice",
        default="zh-CN-XiaoxiaoNeural",
        help="语音角色 (默认: zh-CN-XiaoxiaoNeural)，用 --list-voices 查看",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="列出所有可用的语音角色",
    )

    args = parser.parse_args()

    if args.list_voices:
        asyncio.run(list_voices())
        return

    if not args.text:
        parser.print_help()
        sys.exit(1)

    asyncio.run(text_to_speech(args.text, args.output, args.voice))


if __name__ == "__main__":
    main()
