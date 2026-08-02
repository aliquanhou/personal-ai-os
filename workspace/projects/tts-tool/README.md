# TTS 语音生成工具

基于 [edge-tts](https://github.com/rany2/edge-tts) 的轻量级文字转语音（TTS）工具。无需 API key，免费使用微软 Edge 的 TTS 服务。

## 功能

- 📝 文字转语音，输出 MP3 音频文件
- 🎙️ 支持多种语音角色（中文、英文等）
- ⚡ 无需 API key，开箱即用

## 安装

```bash
pip install edge-tts
```

## 使用

### 基本用法

```bash
python main.py "你好，欢迎使用 TTS 语音生成工具"
```

### 指定输出文件

```bash
python main.py "你好，世界" -o hello.mp3
```

### 指定语音角色

```bash
python main.py "你好，世界" -v zh-CN-YunxiNeural -o hello.mp3
```

### 查看所有可用语音

```bash
python main.py --list-voices
```

## 常用中文语音角色

| 角色 | 说明 |
|------|------|
| `zh-CN-XiaoxiaoNeural` | 女声，温柔（默认） |
| `zh-CN-YunxiNeural` | 男声，阳光 |
| `zh-CN-YunjianNeural` | 男声，浑厚 |
| `zh-CN-XiaoyiNeural` | 女声，活泼 |

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `text` | 要转换的文字（位置参数） | 必填 |
| `-o, --output` | 输出文件路径 | `output.mp3` |
| `-v, --voice` | 语音角色 | `zh-CN-XiaoxiaoNeural` |
| `--list-voices` | 列出所有语音角色 | - |

## 项目结构

```
tts-tool/
├── main.py      # 主程序
└── README.md    # 项目说明
```

## 说明

- 音频默认输出为 MP3 格式
- 需要联网（edge-tts 调用微软在线服务）
- 适合批量生成、原型验证等场景
