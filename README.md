# 🚀 LLM Proxy: 统一大模型 API 网关

<div align="center">

**一行代码，统一调用全球100+大模型**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green.svg)](https://fastapi.tiangolo.com)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-100%2B%20Models-orange.svg)](https://github.com/BerriAI/litellm)
[![Type Safety](https://img.shields.io/badge/Type%20Safe-mypy-blue.svg)](https://mypy.readthedocs.io)

*基于 LiteLLM 和 FastAPI 构建，提供与 OpenAI API 完全兼容的统一接口*

</div>

## 🎯 项目特点

- **⚡ 统一API**：完全兼容 OpenAI SDK 和 API 格式，无缝切换模型
- **🔄 智能轮询**：支持多API Key自动轮询，提高并发能力和稳定性
- **🔐 环境变量支持**：安全的API Key管理，支持动态配置
- **🌍 多厂商支持**：集成 OpenRouter、火山引擎、Google Gemini 等主流平台
- **🚀 高性能**：基于 FastAPI 的全异步架构，支持高并发调用
- **🛡️ 类型安全**：使用 Pydantic 和 mypy 强制执行严格的类型检查

## 🌟 支持的模型

| 厂商 | 支持模型 | 环境变量 |
|------|----------|----------|
| 🔥 **OpenRouter** | GPT-4o-mini, GPT-4-turbo, Claude, Grok, Mistral, 通义千问等 | `OPENROUTER_API_KEY_N` |
| 🌋 **火山引擎** | DeepSeek-R1, DeepSeek-V3 | `VOLCENGINE_API_KEY_N` |
| 🧠 **Google AI** | Gemini 2.0/2.5 Flash, Pro | `GEMINI_API_KEY_N` |

> **轮询支持**：每个厂商支持配置多个API Key (N=1,2,3...)，系统自动轮询使用以提高并发处理能力

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/catcc610/openai-llm-proxy.git
cd openai-llm-proxy

# 安装依赖 (推荐使用 uv)
uv sync
# 或使用 pip: pip install -r requirements.txt
```

### 2. 配置API密钥

创建 `.env` 文件并配置你的API密钥：

```bash
# 复制示例文件
cp env.example .env
```

编辑 `.env` 文件：

```bash
# OpenRouter API Keys (支持多个key轮询)
OPENROUTER_API_KEY_1=sk-or-v1-your-first-key
OPENROUTER_API_KEY_2=sk-or-v1-your-second-key

# 火山引擎 API Keys
VOLCENGINE_API_KEY_1=your-volcengine-key

# Google Gemini API Keys  
GEMINI_API_KEY_1=your-gemini-key-1
GEMINI_API_KEY_2=your-gemini-key-2
```

### 3. 启动服务

```bash
# 启动服务
uv run python main.py
# 服务将在 http://localhost:9000 启动
```

### 4. 测试调用

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:9000/v1",
    api_key="any-key"  # 可以是任意值
)

# 测试不同厂商的模型
models = [
    "gpt-4o-mini",        # OpenRouter
    "grok-3-beta",        # OpenRouter  
    "deepseek-v3-0324",   # 火山引擎
    "gemini-2.0-flash"    # Google AI
]

for model in models:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "你好"}]
    )
    print(f"{model}: {response.choices[0].message.content}")
```

## 📋 支持的完整模型列表

### OpenRouter 模型
- `gpt-4o-mini` - OpenAI GPT-4o Mini
- `gpt-4-turbo` - OpenAI GPT-4 Turbo  
- `claude-3.5-sonnet` - Anthropic Claude
- `grok-3-beta` - xAI Grok 3
- `minimax-01` - MiniMax 模型
- `mistral-nemo` - Mistral Nemo
- `qwen3-235b-a22b` - 阿里通义千问

### 火山引擎模型
- `deepseek-r1-0528` - DeepSeek R1 推理模型
- `deepseek-v3-0324` - DeepSeek V3 对话模型

### Google Gemini 模型
- `gemini-2.0-flash` - Gemini 2.0 Flash (支持多模态)
- `gemini-2.5-flash` - Gemini 2.5 Flash (支持多模态)
- `gemini-2.5-pro` - Gemini 2.5 Pro

## 💻 完全兼容 OpenAI API

本项目提供与 OpenAI API **100%兼容**的接口，你可以直接替换 `base_url` 使用任何支持 OpenAI 的工具和 SDK。

### Python SDK 示例

```python
from openai import OpenAI

# 完全兼容 OpenAI SDK - 只需修改 base_url
client = OpenAI(
    base_url="http://localhost:9000/v1",  # 指向本地代理
    api_key="any-key"  # 可以是任意值
)

# --- 基础对话 ---
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "你是一个乐于助人的AI助手。"},
        {"role": "user", "content": "解释一下什么是量子纠缠？"}
    ],
    temperature=0.7,
    max_tokens=1000
)
print(response.choices[0].message.content)

# --- 流式响应 ---
stream = client.chat.completions.create(
    model="claude-3.5-sonnet",
    messages=[{"role": "user", "content": "用Python写一个斐波那契函数"}],
    stream=True,
    temperature=0.5
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)

# --- 多模态支持 (Gemini) ---
response = client.chat.completions.create(
    model="gemini-2.0-flash",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "这张图片里有什么内容？"},
            {
                "type": "image_url",
                "image_url": {
                    "url": "https://example.com/image.jpg"
                    # 也支持 base64: "data:image/jpeg;base64,/9j/4AAQ..."
                }
            }
        ]
    }]
)
print(response.choices[0].message.content)
```

### cURL 示例

```bash
# 基础聊天请求
curl http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer any-key" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "system", "content": "你是一个专业的翻译助手"},
      {"role": "user", "content": "将这段话翻译成英文：人工智能正在改变世界"}
    ],
    "temperature": 0.3,
    "max_tokens": 500
  }'

# 流式响应
curl http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer any-key" \
  -d '{
    "model": "grok-3-beta",
    "messages": [{"role": "user", "content": "写一首关于春天的诗"}],
    "stream": true,
    "temperature": 0.8
  }'

# 获取支持的模型列表
curl http://localhost:9000/v1/models

# 健康检查
curl http://localhost:9000/health
```

### 无缝替换现有代码

如果你已经在使用 OpenAI API，只需要修改一行代码：

```python
# 原有代码
client = OpenAI(api_key="sk-...")

# 替换为代理服务 - 仅修改 base_url
client = OpenAI(
    base_url="http://localhost:9000/v1",
    api_key="any-key"
)

# 其他代码完全不变！
response = client.chat.completions.create(...)
```

### 适配 Claude Code 编程助手

本服务完全兼容 Anthropic 的 **Claude Code** 终端编程助手。Claude Code 是官方推出的终端AI编程工具，支持代码生成、调试和重构。

#### 安装 Claude Code

```bash
# 使用 npm 安装 Claude Code
npm install -g @anthropic-ai/claude-code
```

更多安装方式请参考：[Claude Code 官方仓库](https://github.com/anthropics/claude-code)

#### 配置代理服务

设置环境变量让 Claude Code 使用本地代理：

```bash
# 设置 Claude Code 使用本地代理服务
export ANTHROPIC_BASE_URL=http://localhost:9000

```

#### 支持的模型

Claude Code 通过代理服务可以使用以下模型(config/external_llm/external_llm.yaml 自行配置（provider_config）)：


```bash
# 指定特定模型
claude --model deepseek-r1-0528 
```

#### 自定义模型配置

可以通过修改 `config/external_llm/external_llm.yaml` 来自定义模型映射：

```yaml
# 添加新的模型映射
provider_config:
  your-custom-model: volcengine  # 指定使用的厂商

model_routes:
  volcengine:
    "your-custom-model": "actual-backend-model"  # 后端实际模型名
```

## 🔧 高级功能

### API Key 轮询机制

系统支持为每个厂商配置多个API Key，自动轮询使用：

```bash
# 配置多个 OpenRouter keys
OPENROUTER_API_KEY_1=first-key
OPENROUTER_API_KEY_2=second-key  
OPENROUTER_API_KEY_3=third-key
```

系统会按 `key1 → key2 → key3 → key1...` 的顺序轮询，实现：
- ✅ 提高并发处理能力
- ✅ 避免单key限流
- ✅ 增强服务稳定性

## 📊 性能测试

运行内置的性能测试：

```bash
cd test
python test_models.py
```

测试结果示例：
```
--- STANDARD TEXT ---
总测试数: 13, 成功: 8, 失败: 5
性能最佳 (Top 3):
1. gpt-4o-mini          | 响应时间: 2.82s
2. gpt-4-turbo          | 响应时间: 3.00s  
3. mistral-nemo         | 响应时间: 3.34s
```

## 🔗 API 接口

- **聊天补全**: `POST /v1/chat/completions`
- **模型列表**: `GET /v1/models`  
- **健康检查**: `GET /health`
- **API文档**: `GET /docs` (Swagger UI)

完全兼容 OpenAI API 规范，支持所有标准参数。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License