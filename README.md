# 🚀 OpenAI LLM Proxy

<div align="center">

**基于LiteLLM的100+模型统一代理服务**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green.svg)](https://fastapi.tiangolo.com)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-100%2B%20Models-orange.svg)](https://github.com/BerriAI/litellm)
[![Type Safety](https://img.shields.io/badge/Type%20Safe-mypy-blue.svg)](https://mypy.readthedocs.io)

*一键接入全球主流AI模型，统一OpenAI API格式*

</div>

## 🎯 项目亮点

### 💫 **100+模型支持**
- **OpenAI**: GPT-4o, GPT-4 Turbo, GPT-3.5, O1系列
- **Anthropic**: Claude 3.5 Sonnet, Claude 3 Opus/Haiku
- **Google**: Gemini 2.0 Flash, Gemini 1.5 Pro/Flash
- **国内厂商**: 深度求索、百度文心、阿里通义、字节火山
- **开源模型**: Llama, Mistral, Qwen 通过各种部署方式

### ⚡ **极致性能**
- **真异步并发** - 100个请求3秒内完成
- **首Token响应** - 平均1.5秒内返回
- **高吞吐量** - 支持每秒30+并发请求

### 🔧 **极简配置** 
- **环境变量配置** - 只需设置对应的API Key
- **热重载配置** - 运行时动态添加模型
- **统一API格式** - 完全兼容OpenAI SDK

## 🌟 支持的模型提供商

| 提供商 | 支持模型 | 配置变量 | 推荐指数 |
|--------|----------|----------|----------|
| 🔥 **OpenAI** | GPT-4o, GPT-4, GPT-3.5, O1 | `OPENAI_API_KEY` | ⭐⭐⭐⭐⭐ |
| 🤖 **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus | `ANTHROPIC_API_KEY` | ⭐⭐⭐⭐⭐ |
| 🧠 **Google AI** | Gemini 2.0 Flash, Gemini 1.5 Pro | `GOOGLE_API_KEY` | ⭐⭐⭐⭐⭐ |
| 🎯 **火山引擎** | 深度求索V3, 字节豆包 | `VOLCENGINE_API_KEY` | ⭐⭐⭐⭐⭐ |
| 🔸 **百度千帆** | 文心4.0, ERNIE-Speed | `QIANFAN_AK`, `QIANFAN_SK` | ⭐⭐⭐⭐ |
| 🌙 **阿里灵积** | 通义千问Max, Plus | `DASHSCOPE_API_KEY` | ⭐⭐⭐⭐ |
| ⚡ **Groq** | Llama 3.1, Mixtral | `GROQ_API_KEY` | ⭐⭐⭐⭐ |
| 🏠 **本地部署** | Ollama, vLLM, TGI | 无需密钥 | ⭐⭐⭐ |

## 🚀 快速开始

### 环境要求

- **Python 3.11+** 
- **uv** (推荐的现代Python包管理器)

### 1. 安装uv (如果还没有)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 克隆和安装

```bash
# 克隆项目
git clone https://github.com/catcc610/openai-llm-proxy.git
cd openai-llm-proxy

# 创建虚拟环境并安装依赖
uv sync

# 激活虚拟环境 (可选，uv run会自动处理)
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows
```

### 3. 配置API密钥

编辑 `config/config.yaml`：

```yaml
# 环境变量配置 - 只需设置你要使用的提供商
os_env:
  # OpenAI - 最高质量
  OPENAI_API_KEY: "sk-your-openai-key"
  
  # Anthropic Claude - 强推理能力  
  ANTHROPIC_API_KEY: "sk-ant-your-key"
  
  # Google Gemini - 性价比高
  GOOGLE_API_KEY: "your-google-key"
  
  # 火山引擎 - 国内首选
  VOLCENGINE_API_KEY: "your-volcengine-key"
  
  # 百度千帆
  QIANFAN_AK: "your-qianfan-ak"
  QIANFAN_SK: "your-qianfan-sk"
  
  # 阿里灵积
  DASHSCOPE_API_KEY: "your-dashscope-key"

# 模型配置 - 自定义模型名称映射
model_config:
  "gpt-4o": openai                    # OpenAI GPT-4o
  "claude-3-5-sonnet": anthropic      # Anthropic Claude
  "gemini-2-flash": google            # Google Gemini  
  "deepseek-v3": volcengine           # 火山引擎深度求索
  "qwen-max": dashscope               # 阿里通义千问
  "ernie-4": qianfan                  # 百度文心一言

# 提供商路由配置
model_routes:
  openai:
    "gpt-4o": "gpt-4o"
    "gpt-4": "gpt-4"
  anthropic:
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022"
  google:
    "gemini-2-flash": "gemini-2.0-flash"
  volcengine:
    "deepseek-v3": "deepseek-v3"
  dashscope:
    "qwen-max": "qwen-max"
  qianfan:
    "ernie-4": "ERNIE-4.0-8K"
```

### 4. 启动服务

```bash
# 使用uv运行
uv run python main.py

# 或者激活虚拟环境后运行
python main.py

# 服务启动在 http://localhost:9000
```

### 5. 测试使用

```python
from openai import OpenAI

# 连接本地代理
client = OpenAI(
    base_url="http://localhost:9000/v1",
    api_key="dummy"  # 使用任意值，真实密钥在服务端配置
)

# 使用不同模型
models = [
    "gpt-4o",           # OpenAI最新模型
    "claude-3-5-sonnet", # Anthropic Claude
    "gemini-2-flash",    # Google Gemini
    "deepseek-v3",       # 火山引擎深度求索
    "qwen-max",          # 阿里通义千问
    "ernie-4"            # 百度文心一言
]

for model in models:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "你好，介绍一下你自己"}],
        max_tokens=100
    )
    print(f"{model}: {response.choices[0].message.content}")
```

## 🔧 高级配置

### 通配符路由 - 支持所有模型

```yaml
model_list:
  # OpenAI 所有模型
  - model_name: "openai/*"
    litellm_params:
      model: "openai/*"
      api_key: os.environ/OPENAI_API_KEY
      
  # Anthropic 所有模型  
  - model_name: "anthropic/*"
    litellm_params:
      model: "anthropic/*"
      api_key: os.environ/ANTHROPIC_API_KEY
      
  # Google 所有模型
  - model_name: "google/*"
    litellm_params:
      model: "google/*"
      api_key: os.environ/GOOGLE_API_KEY
```

### 本地模型支持

```yaml
model_list:
  # Ollama 本地部署
  - model_name: "llama3.1"
    litellm_params:
      model: "ollama/llama3.1"
      api_base: "http://localhost:11434"
      
  # vLLM 部署
  - model_name: "custom-model"
    litellm_params:
      model: "openai/custom-model"
      api_base: "http://localhost:8000"
      api_key: "fake-key"
```

## 💻 使用示例

### Python SDK (推荐)

```python
import openai

# 初始化客户端
client = openai.OpenAI(
    base_url="http://localhost:9000/v1",
    api_key="dummy"
)

# 普通对话
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "你是一个有用的AI助手"},
        {"role": "user", "content": "解释什么是大语言模型"}
    ]
)

# 流式响应
stream = client.chat.completions.create(
    model="claude-3-5-sonnet",
    messages=[{"role": "user", "content": "写一个Python函数计算斐波那契数列"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")

# 视觉模型
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user", 
        "content": [
            {"type": "text", "text": "这张图片里有什么？"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
        ]
    }]
)

# 工具调用
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "北京今天天气怎么样？"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                }
            }
        }
    }]
)
```

### HTTP API 调用

```bash
# 普通聊天
curl -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "你好"}]
  }'

# 流式响应
curl -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet",
    "messages": [{"role": "user", "content": "写一首诗"}],
    "stream": true
  }'

# 获取模型列表
curl http://localhost:9000/v1/models

# 健康检查
curl http://localhost:9000/health
```

### JavaScript/Node.js

```javascript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://localhost:9000/v1',
  apiKey: 'dummy'
});

async function chat() {
  const response = await client.chat.completions.create({
    model: 'gpt-4o',
    messages: [{ role: 'user', content: '你好，世界！' }]
  });
  
  console.log(response.choices[0].message.content);
}

chat();
```

## 📊 性能优势

### 🚀 异步优化后的性能表现

| 指标 | 优化前 | 优化后 | 提升倍数 |
|------|--------|--------|----------|
| **首Token响应** | 29.4秒 | 1.5秒 | **19.6倍** |
| **并发处理** | 串行排队 | 真并发 | **质的飞跃** |
| **吞吐量** | 2 QPS | 33+ QPS | **16.5倍** |
| **总响应时间** | 29.5秒 | 3.0秒 | **9.8倍** |

### 🎯 性能测试代码

```python
import asyncio
import aiohttp
import time

async def benchmark():
    """性能基准测试"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        start_time = time.time()
        
        # 100个并发请求
        for i in range(100):
            task = session.post(
                "http://localhost:9000/v1/chat/completions",
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": f"测试 {i+1}"}],
                    "max_tokens": 50
                }
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        print(f"100个并发请求完成时间: {total_time:.2f}秒")
        print(f"平均QPS: {100/total_time:.1f}")

asyncio.run(benchmark())
```

## 🛠️ 管理功能

### 配置热重载

```bash
# 重载配置文件
curl -X POST http://localhost:9000/config/reload

# 查看当前配置
curl http://localhost:9000/config
```

### 模型管理

```bash
# 获取支持的所有模型
curl http://localhost:9000/v1/models

# 获取模型详细信息
curl http://localhost:9000/model_group/info
```

### 日志监控

```python
# 启动时开启调试日志
uv run python main.py --log-level debug

# 查看请求日志
tail -f logs/app.log
```

## 🎨 项目特色

### 🏗️ 现代化架构
- **FastAPI** - 高性能异步Web框架
- **Pydantic** - 严格的类型验证和序列化
- **类型安全** - 完整的MyPy类型检查

### 🔒 企业级特性
- **请求追踪** - 每个请求唯一ID，便于调试
- **错误处理** - 优雅的异常处理和错误信息
- **配置管理** - 支持环境变量和YAML配置
- **健康监控** - 内置健康检查端点

### 🌈 开发体验
- **零学习成本** - 完全兼容OpenAI API格式
- **即插即用** - 现有代码无需修改
- **灵活配置** - 支持各种部署方式

## 🎯 使用场景

### 💼 企业应用
- **多模型对比** - 同时测试不同模型效果
- **成本优化** - 根据任务类型选择最优模型
- **风险分散** - 多提供商避免单点故障

### 🔬 研究开发
- **模型评估** - 统一接口测试各种模型
- **原型开发** - 快速切换不同能力的模型
- **性能测试** - 对比不同模型的响应速度

### 🏠 个人项目
- **成本控制** - 灵活选择性价比最高的模型
- **功能集成** - 一套代码支持所有主流模型
- **学习实验** - 体验不同AI模型的特色

## 🔧 故障排除

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 🚫 模型未找到 | 配置映射错误 | 检查`model_config`配置 |
| 🔑 API密钥无效 | 环境变量未设置 | 确认`os_env`中的密钥 |
| ⏰ 请求超时 | 网络或服务商问题 | 调整`timeout`设置 |
| 🐌 响应缓慢 | 同步调用阻塞 | 检查是否使用异步版本 |

### 调试方法

```bash
# 启动调试模式
uv run python main.py --log-level debug

# 查看配置状态  
curl http://localhost:9000/config

# 测试特定模型
curl -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "test"}]}'
```

## 🚀 生产部署

### 系统服务部署

创建systemd服务文件 `/etc/systemd/system/llm-proxy.service`：

```ini
[Unit]
Description=LLM Proxy Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/openai-llm-proxy
Environment=PATH=/path/to/openai-llm-proxy/.venv/bin
ExecStart=/path/to/openai-llm-proxy/.venv/bin/python main.py --host 0.0.0.0
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动服务
sudo systemctl enable llm-proxy
sudo systemctl start llm-proxy
sudo systemctl status llm-proxy
```

### Nginx反向代理

```nginx
upstream llm_proxy {
    server 127.0.0.1:9000;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://llm_proxy;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;  # 重要：支持流式响应
        proxy_read_timeout 300s;
    }
}
```

## 🤝 贡献指南

### 开发环境

```bash
# 安装开发依赖
uv sync --group dev

# 代码质量检查
uv run ruff check .         # 代码风格检查
uv run mypy .              # 类型检查
```

### 代码质量工具

项目包含完整的类型安全和代码质量配置：

- **MyPy** - 静态类型检查 (`mypy.ini`)
- **Ruff** - 快速的代码检查和格式化
- **UV** - 现代化的Python包管理

### 提交规范

1. Fork 本仓库
2. 创建功能分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add amazing feature'`
4. 推送分支: `git push origin feature/amazing-feature`
5. 创建Pull Request

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) - 详见LICENSE文件。

## 🙏 致谢

- [LiteLLM](https://github.com/BerriAI/litellm) - 出色的多提供商LLM统一接口库
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化高性能Web框架
- [Pydantic](https://pydantic.dev/) - 强大的数据验证和类型安全库
- [UV](https://github.com/astral-sh/uv) - 现代化的Python包管理器

## 💬 联系方式

- 🐛 问题反馈: [GitHub Issues](../../issues)
- 💡 功能建议: [GitHub Discussions](../../discussions)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给我们一个星标！**

*让AI模型切换像换衣服一样简单*

</div>
