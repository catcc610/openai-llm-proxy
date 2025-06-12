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

- **⚡ 统一API**：完全兼容 OpenAI SDK 和 API 格式，无缝切换模型。
- **🔌 多模型支持**：通过 LiteLLM 集成超过100种模型，包括 OpenAI, Anthropic, Google Gemini, 以及国内主流模型。
- **⚙️ 集中化配置**：通过单个 `config.yaml` 文件统一管理所有模型的API密钥和路由规则。
- **🚀 高性能**：基于 FastAPI 的全异步架构，为高并发场景提供高吞吐量和低延迟。
- **🛡️ 类型安全**：使用 Pydantic 和 mypy 强制执行严格的类型检查，保证代码的健壮性和可维护性。

## 🌟 支持的部分模型提供商

| 提供商 | 支持模型 | 配置变量 |
|--------|----------|----------|
| 🔥 **OpenAI** | GPT-4o, GPT-4, GPT-3.5 | `OPENAI_API_KEY` |
| 🤖 **Anthropic** | Claude 3.5 Sonnet, Opus | `ANTHROPIC_API_KEY` |
| 🧠 **Google AI** | Gemini 1.5 Pro, Flash | `GOOGLE_API_KEY` |
| 🎯 **火山引擎** | 深度求索, 豆包 | `VOLCENGINE_API_KEY` |
| 🏠 **本地部署** | Ollama, vLLM, TGI | (查看高级配置) |

> **重要提示**: 提供商名称和所需的环境变量由 LiteLLM 定义。为了确保配置正确，请在添加新模型前查阅 [**LiteLLM 官方支持的模型提供商文档**](https://docs.litellm.ai/docs/providers)。

## 🚀 快速开始

### 环境要求

- **Python 3.11+**
- **uv** (推荐的现代Python包管理器)

### 1. 安装 uv

如果你的系统中还没有 `uv`，请先执行安装：

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 克隆与安装依赖

```bash
# 克隆项目
git clone https://github.com/catcc610/openai-llm-proxy.git
cd openai-llm-proxy

# 使用 uv 创建虚拟环境并安装依赖
uv sync

# (可选) 激活虚拟环境
# source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate      # Windows
```

### 3. 配置模型

编辑 `config/config.yaml` 文件。这是你管理所有模型密钥和路由的核心位置。

下面是一个基础配置示例，演示如何添加 GPT-4o 和 Claude 3.5 Sonnet：

```yaml
# 1. 在 os_env 部分，为你需要使用的模型提供商设置 API 密钥。
#    这些值将被加载为环境变量。
os_env:
  OPENAI_API_KEY: "sk-your-openai-key"
  ANTHROPIC_API_KEY: "sk-ant-your-key"

# 2. 在 model_config 部分，将你希望在API中使用的自定义模型名称映射到提供商。
#    这是告诉代理"当我请求'gpt-4o'时，你应该使用'openai'这个提供商的配置"。
model_config:
  "gpt-4o": openai
  "claude-3.5-sonnet": anthropic

# 3. 在 model_routes 部分，为每个提供商定义具体的模型ID。
#    这会将你的自定义名称映射到LiteLLM所需的实际模型名称。
model_routes:
  openai:
    "gpt-4o": "gpt-4o-2024-08-06"  # LiteLLM 需要的实际模型ID
  anthropic:
    "claude-3.5-sonnet": "claude-3-5-sonnet-20240620"
```

> **为什么需要这样配置？**
>
> 这种三段式配置提供了一种灵活的路由机制：
> - `os_env` 集中管理密钥。
> - `model_config` 允许你使用简洁的自定义名称（如 `gpt-4o`）作为API入口。
> - `model_routes` 则将这些名称精确映射到不同提供商不断更新的官方模型ID上，而无需修改你的客户端代码。

### 4. 启动服务

```bash
# 使用 uv 直接运行
uv run python main.py

# 服务将启动在 http://localhost:9000
```

### 5. 测试调用

使用你喜欢的HTTP客户端或OpenAI官方SDK进行测试。

```python
from openai import OpenAI

# 连接到本地代理服务
client = OpenAI(
    base_url="http://localhost:9000/v1",
    api_key="any-key"  # 代理服务端的密钥才是关键，这里可填任意值
)

# 使用你在 config.yaml 中定义的模型名称
models_to_test = ["gpt-4o", "claude-3-5-sonnet"]

for model_name in models_to_test:
    try:
        print(f"--- 正在测试模型: {model_name} ---")
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "你好，请介绍一下你自己。"}],
            max_tokens=100
        )
        print(f"响应: {response.choices[0].message.content}\n")
    except Exception as e:
        print(f"调用模型 {model_name} 时出错: {e}\n")
```

## 🔧 高级配置

### 本地模型 (Ollama)

你可以配置代理以连接到本地运行的模型，例如通过Ollama部署的Llama 3.1。

```yaml
# config/config.yaml

# 1. os_env 中无需添加密钥 (对于本地Ollama)

# 2. model_config 中映射模型名称到自定义的提供商名称 "ollama_local"
model_config:
  "llama3.1": ollama_local

# 3. model_routes 中定义 "ollama_local" 提供商的具体配置
model_routes:
  ollama_local:
    # 这里的 "llama3.1" 必须与 model_config 中的名称匹配
    "llama3.1": "ollama/llama3.1" # LiteLLM格式: "ollama/<model_tag>"
```
> **注意**: 上述配置中的 `ollama_local` 是一个自定义的提供商标识符，你可以使用任何你喜欢的名称，只要在 `model_config` 和 `model_routes` 中保持一致即可。LiteLLM将根据 `ollama/` 前缀识别并连接到默认的Ollama服务地址 (`http://localhost:11434`)。

## 💻 API 使用示例

代理服务完全兼容OpenAI的API规范。你可以使用任何支持OpenAI API的工具。

### Python SDK

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:9000/v1",
    api_key="dummy-key"
)

# --- 基础对话 ---
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "你是一个乐于助人的AI助手。"},
        {"role": "user", "content": "解释一下什么是"量子纠缠"。"}
    ]
)
print(response.choices[0].message.content)

# --- 流式响应 ---
stream = client.chat.completions.create(
    model="claude-3-5-sonnet",
    messages=[{"role": "user", "content": "用Python写一个斐波那契数列函数，并解释其工作原理。"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)

# --- 视觉模型（多模态） ---
response = client.chat.completions.create(
    model="gpt-4o", # 确保此模型支持视觉
    messages=[{
        "role": "user", 
        "content": [
            {"type": "text", "text": "这张图片里有什么内容？"},
            {
                "type": "image_url", 
                "image_url": {
                    # 支持URL或Base64编码的图片
                    "url": "data:image/jpeg;base64,/9j/4AAQSk...your_base64_string...",
                }
            }
        ]
    }]
)
print(response.choices[0].message.content)
```

### cURL

```bash
# 基础对话
curl http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "你好！"}]
  }'

# 流式响应
curl http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet",
    "messages": [{"role": "user", "content": "写一首关于宇宙的短诗。"}],
    "stream": true
  }'

# 获取可用模型列表 (基于你的配置)
curl http://localhost:9000/v1/models

# 健康检查
curl http://localhost:9000/health
```

## 🧪 性能测试

本项目基于异步框架构建，能够处理高并发请求。你可以使用以下脚本进行简单的基准测试。

```python
import asyncio
import aiohttp
import time

# 测试参数
CONCURRENT_REQUESTS = 100
MODEL_TO_TEST = "gpt-4o" # 替换为你想测试的、已配置的模型
PROMPT = "你好"

async def benchmark():
    """对代理服务进行并发请求基准测试"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        start_time = time.time()
        
        # 创建并发任务
        for i in range(CONCURRENT_REQUESTS):
            task = session.post(
                "http://localhost:9000/v1/chat/completions",
                json={
                    "model": MODEL_TO_TEST,
                    "messages": [{"role": "user", "content": f"{PROMPT} {i+1}"}],
                    "max_tokens": 50
                },
                headers={"Authorization": "Bearer dummy-key"}
            )
            tasks.append(task)
        
        # 等待所有请求完成
        responses = await asyncio.gather(*[asyncio.ensure_future(t) for t in tasks])
        
        successful_requests = [r for r in responses if r.status == 200]
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"--- 性能基准测试结果 ---")
        print(f"测试模型: {MODEL_TO_TEST}")
        print(f"总请求数: {CONCURRENT_REQUESTS}")
        print(f"成功请求数: {len(successful_requests)}")
        print(f"总耗时: {total_time:.2f} 秒")
        
        if total_time > 0:
            qps = len(successful_requests) / total_time
            print(f"平均QPS (每秒请求数): {qps:.2f}")

if __name__ == "__main__":
    asyncio.run(benchmark())
```