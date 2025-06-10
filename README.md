# 🚀 OpenAI LLM Proxy

<div align="center">

**基于LiteLLM的高性能多厂商LLM代理服务**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green.svg)](https://fastapi.tiangolo.com)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-latest-orange.svg)](https://github.com/BerriAI/litellm)
[![Type Safety](https://img.shields.io/badge/Type%20Safe-mypy-blue.svg)](https://mypy.readthedocs.io)

</div>

## 📖 项目简介

OpenAI LLM Proxy 是一个高性能的LLM API代理服务，提供完全兼容OpenAI API的统一接口，支持多个主流LLM提供商。通过统一的API格式，你可以轻松切换不同的AI模型，而无需修改客户端代码。

### 🎯 核心价值

- **API统一化** - 一套API接口，接入所有主流LLM服务
- **成本优化** - 灵活切换提供商，选择最优性价比方案  
- **高可用性** - 多厂商备份，避免单点故障
- **开发效率** - 标准OpenAI格式，无缝迁移现有代码

## ✨ 核心特性

### 🔥 性能特性
- **真异步并发** - 100个并发请求，3秒内完成响应
- **首Token快响应** - 平均1.5秒内返回首个字符
- **流式处理** - 实时数据流，优化用户体验
- **高吞吐量** - 支持每秒数十个并发请求

### 🛡️ 企业级特性
- **完全类型安全** - Pydantic + MyPy严格类型检查
- **生产就绪** - 完善的错误处理、监控和日志系统
- **热配置重载** - 运行时动态调整配置，无需重启
- **请求链路追踪** - 每个请求唯一ID，便于调试和监控

### 🌐 兼容性特性
- **OpenAI API兼容** - 100%兼容ChatGPT API格式
- **多厂商支持** - 火山引擎、百度文心、阿里通义等
- **SDK支持** - 支持官方OpenAI SDK和其他第三方客户端

## 🚀 快速开始

### 环境要求

```bash
Python 3.11+
uv (推荐) 或 pip
```

### 一键安装

```bash
# 1. 克隆项目
git clone <repository-url>
cd openai-llm-proxy

# 2. 自动化安装
make init

# 3. 配置API密钥
cp config/.axample config/config.yaml
vim config/config.yaml  # 添加你的API密钥

# 4. 启动服务
make run
```

### 验证安装

```bash
# 健康检查
curl http://localhost:9000/health

# 测试聊天接口
curl -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v3-0324",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'
```

## ⚙️ 配置指南

### 基础配置文件

编辑 `config/config.yaml`：

```yaml
# API密钥配置
os_env:
  # 火山引擎（推荐 - 性价比高）
  VOLCENGINE_API_KEY: "your-volcengine-key"
  
  # OpenAI（质量最高）
  OPENAI_API_KEY: "your-openai-key"
  
  # Anthropic Claude（推理能力强）
  ANTHROPIC_API_KEY: "your-anthropic-key"

# 模型映射配置
model_config:
  # 推荐配置 - 高性价比
  "deepseek-v3-0324": volcengine      # 代码和推理
  "gpt-4o-mini": openai               # 轻量任务
  "claude-3-sonnet": anthropic        # 复杂推理
  
  # 兼容配置 - OpenAI标准名称
  "gpt-3.5-turbo": volcengine         # 重定向到DeepSeek
  "gpt-4": openai                     # 保持OpenAI

# 提供商模型映射
model_routes:
  volcengine:
    "deepseek-v3-0324": "deepseek-v3-250324"
    "gpt-3.5-turbo": "deepseek-v3-250324"
  openai:
    "gpt-4o-mini": "gpt-4o-mini"
    "gpt-4": "gpt-4"
  anthropic:
    "claude-3-sonnet": "claude-3-sonnet-20240229"

# 服务配置
server:
  host: "0.0.0.0"
  port: 9000
  log_level: "info"

# 性能调优
proxy:
  timeout: 30          # 请求超时时间
  max_retries: 3       # 最大重试次数
  default_model: "deepseek-v3-0324"
```

### 支持的提供商

| 提供商 | 优势 | 适用场景 | 成本 |
|--------|------|----------|------|
| 🔥 **火山引擎** | 性价比最高，速度快 | 日常开发、批量处理 | ⭐⭐⭐⭐⭐ |
| 🤖 **OpenAI** | 质量最佳，生态最完善 | 生产应用、高质量需求 | ⭐⭐ |
| 🧠 **Anthropic** | 推理能力强，安全性高 | 复杂逻辑、敏感内容 | ⭐⭐⭐ |
| 📚 **百度文心** | 中文优化，本土化 | 中文内容、合规要求 | ⭐⭐⭐⭐ |

## 💻 使用方法

### Python SDK (推荐)

```python
from openai import OpenAI

# 连接本地代理
client = OpenAI(
    base_url="http://localhost:9000/v1",
    api_key="dummy"  # 代理不需要真实密钥
)

# 聊天对话
response = client.chat.completions.create(
    model="deepseek-v3-0324",
    messages=[
        {"role": "system", "content": "你是一个有用的AI助手"},
        {"role": "user", "content": "解释什么是异步编程"}
    ],
    temperature=0.7,
    max_tokens=2000
)

print(response.choices[0].message.content)
```

### 流式响应

```python
# 实时流式输出
stream = client.chat.completions.create(
    model="deepseek-v3-0324",
    messages=[{"role": "user", "content": "写一个Python异步编程教程"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### HTTP API 调用

```bash
# 非流式请求
curl -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v3-0324",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下Python的asyncio库"}
    ],
    "temperature": 0.7,
    "max_tokens": 1500
  }'

# 流式请求
curl -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v3-0324", 
    "messages": [{"role": "user", "content": "解释异步编程的优势"}],
    "stream": true
  }'
```

### 性能测试

```python
# 并发性能测试示例
import asyncio
import aiohttp
import time

async def concurrent_test():
    """测试并发性能"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        start_time = time.time()
        
        # 创建100个并发请求
        for i in range(100):
            task = session.post(
                "http://localhost:9000/v1/chat/completions",
                json={
                    "model": "deepseek-v3-0324",
                    "messages": [{"role": "user", "content": f"请求 {i+1}"}],
                    "max_tokens": 50
                }
            )
            tasks.append(task)
        
        # 等待所有请求完成
        responses = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        print(f"100个并发请求完成时间: {total_time:.2f}秒")
        print(f"平均QPS: {100/total_time:.1f}")

# 运行测试
asyncio.run(concurrent_test())
```

## 📊 性能指标

基于异步优化后的实际测试数据：

| 指标 | 数值 | 说明 |
|------|------|------|
| **并发处理能力** | 100 req/3s | 100个并发请求3秒内完成 |
| **首Token响应** | 1.5s (平均) | 从请求到首个字符返回 |
| **最快响应** | 0.4s | 最优网络条件下 |
| **吞吐量** | 33+ QPS | 每秒查询数 |
| **成功率** | 100% | 在正常网络环境下 |

## 🔗 API文档

启动服务后访问：
- **交互式文档**: http://localhost:9000/docs
- **API规范**: http://localhost:9000/redoc

### 主要端点

| 端点 | 方法 | 功能 | 兼容性 |
|------|------|------|--------|
| `/v1/chat/completions` | POST | 聊天完成 | ✅ OpenAI完全兼容 |
| `/health` | GET | 健康检查 | - |
| `/config` | GET | 配置信息 | - |
| `/config/reload` | POST | 热重载配置 | - |

## 🛠️ 开发指南

### 开发环境设置

```bash
# 安装开发依赖
make dev-install

# 代码质量检查
make check        # 完整检查
make lint         # 代码风格
make type-check   # 类型检查
make test         # 运行测试

# 自动修复问题
make fix          # 自动修复所有可修复的问题
```

### 代码规范

本项目严格遵循以下规范：

- **类型安全**: 所有函数都有完整的类型注解
- **错误处理**: 使用具体异常类型，避免裸露的try/except
- **代码风格**: 使用ruff进行代码格式化和检查
- **函数设计**: 职责单一，参数≤5个，扁平化逻辑
- **文档完善**: 所有公共API都有详细docstring

### 项目架构

```
app/
├── app.py          # FastAPI应用主体，处理HTTP请求
├── config.py       # 配置管理，支持热重载和缓存
├── router.py       # 模型路由逻辑，提供商映射
├── models.py       # Pydantic数据模型，类型安全
├── middleware.py   # 中间件（日志、请求ID等）
└── errors.py       # 统一错误处理和响应格式
```

### 添加新的LLM提供商

1. **配置模型映射**:
```yaml
# config/config.yaml
model_config:
  "new-model": new_provider

model_routes:
  new_provider:
    "new-model": "provider-specific-model-id"
```

2. **设置API密钥**:
```yaml
os_env:
  NEW_PROVIDER_API_KEY: "your-api-key"
```

3. **测试配置**:
```bash
# 重载配置
curl -X POST http://localhost:9000/config/reload

# 测试新模型
curl -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "new-model", "messages": [{"role": "user", "content": "test"}]}'
```

## 🔧 故障排除

### 常见问题速查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 🚫 `模型未找到` | 配置映射错误 | 检查`model_config`和`model_routes` |
| 🔑 `API密钥无效` | 环境变量未设置 | 确认`os_env`中的密钥配置 |
| ⏰ `请求超时` | 网络或服务商问题 | 调整`proxy.timeout`设置 |
| 🐌 `响应慢` | 同步调用问题 | 确认使用异步版本的代码 |

### 性能优化建议

```yaml
# 高并发配置
server:
  workers: 4        # 多进程（生产环境）

proxy:  
  timeout: 30       # 合理超时时间
  max_retries: 2    # 减少重试次数

# 客户端连接池配置
connector:
  limit: 100        # 最大连接数
  limit_per_host: 30 # 单个主机连接数
```

### 监控和日志

```bash
# 查看详细日志
python main.py --log-level debug

# 追踪特定请求
grep "request_id_xxx" logs/app.log

# 监控性能指标
curl http://localhost:9000/health
```

## 📈 生产部署

### Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install uv && \
    uv pip install -r pyproject.toml

EXPOSE 9000
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "9000"]
```

### 系统服务

```bash
# 创建systemd服务
sudo tee /etc/systemd/system/llm-proxy.service > /dev/null <<EOF
[Unit]
Description=LLM Proxy Service
After=network.target

[Service]
Type=simple
User=llm-proxy
WorkingDirectory=/opt/llm-proxy
ExecStart=/opt/llm-proxy/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl enable llm-proxy
sudo systemctl start llm-proxy
```

### 反向代理

```nginx
# Nginx配置
upstream llm_proxy {
    server 127.0.0.1:9000;
    server 127.0.0.1:9001;  # 多实例负载均衡
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://llm_proxy;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;  # 关键：支持流式响应
    }
}
```

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 提交代码

1. Fork项目并创建分支
2. 遵循代码规范，通过所有检查
3. 添加测试用例
4. 提交PR并详细描述更改

### 报告问题

请使用以下模板报告问题：

```markdown
**环境信息**
- Python版本：
- 依赖版本：
- 操作系统：

**问题描述**
[详细描述问题]

**重现步骤**
1. ...
2. ...

**预期行为**
[描述预期的正确行为]

**实际行为**  
[描述实际发生的问题]
```

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [LiteLLM](https://github.com/BerriAI/litellm) - 优秀的多厂商LLM统一接口
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化高性能Web框架  
- [Pydantic](https://pydantic.dev/) - 强大的数据验证库

## 💬 社区与支持

- 📖 [完整文档](http://localhost:9000/docs)
- 🐛 [问题反馈](../../issues)
- 💡 [功能建议](../../issues/new?template=feature_request.md)
- 📧 技术交流: [your-email@domain.com]

---

<div align="center">

**如果这个项目对你有帮助，请给我们一个 ⭐**

Made with ❤️ by developers, for developers

</div>
