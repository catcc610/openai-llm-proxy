# OpenAI LLM Proxy

🚀 基于LiteLLM的多厂商LLM代理服务，提供OpenAI兼容的API接口

## ✨ 特性

- 🔗 **OpenAI兼容API** - 完全兼容OpenAI ChatGPT API格式
- 🌐 **多厂商支持** - 支持火山引擎、百度文心、阿里通义等多个LLM提供商
- ⚡ **高性能** - 基于FastAPI构建，支持异步处理和流式响应
- 🛡️ **类型安全** - 使用Pydantic和强类型系统，通过MyPy检查
- 📊 **完善监控** - 请求ID追踪、详细日志记录、错误处理
- 🔧 **灵活配置** - YAML配置文件，支持热重载
- 🏗️ **生产就绪** - 完善的错误处理、中间件支持、标准化响应

## 📦 安装

### 环境要求

- Python 3.11+
- uv (推荐的包管理器)

### 快速开始

```bash
# 克隆项目
git clone <repository-url>
cd openai-llm-proxy

# 安装依赖
make init

# 复制配置文件
cp config/.axample config/config.yaml

# 编辑配置文件，添加你的API密钥
vim config/config.yaml

# 启动开发服务器
make run
```

## ⚙️ 配置

### 基础配置

编辑 `config/config.yaml` 文件：

```yaml
# 环境变量设置
os_env:
  VOLCENGINE_API_KEY: "your-volcengine-api-key"
  OPENAI_API_KEY: "your-openai-api-key"
  ANTHROPIC_API_KEY: "your-anthropic-api-key"

# 模型配置映射 - 指定每个模型使用的提供商
model_config:
  "gpt-3.5-turbo": openai
  "gpt-4": openai
  "claude-3-sonnet": anthropic
  "deepseek-v3": volcengine

# 模型路由配置 - 每个提供商的具体模型映射
model_routes:
  openai:
    "gpt-3.5-turbo": "gpt-3.5-turbo"
    "gpt-4": "gpt-4"
  anthropic:
    "claude-3-sonnet": "claude-3-sonnet-20240229"
  volcengine:
    "deepseek-v3": "deepseek-v3-250324"

# 服务器配置
server:
  host: "0.0.0.0"
  port: 8000
  reload: false
  log_level: "info"

# 代理配置
proxy:
  timeout: 30
  max_retries: 3
  default_model: "gpt-3.5-turbo"

# 安全配置
security:
  api_keys: []  # 可选：API密钥列表
```

### 支持的提供商

| 提供商 | 标识符 | 支持的模型 |
|--------|--------|-----------|
| OpenAI | `openai` | GPT-3.5, GPT-4, GPT-4o |
| Anthropic | `anthropic` | Claude-3 系列 |
| 火山引擎 | `volcengine` | DeepSeek, Doubao |
| 百度文心 | `baidu` | ERNIE 系列 |
| 阿里通义 | `alibaba` | Qwen 系列 |

## 🚀 使用方法

### 启动服务

```bash
# 开发模式（热重载）
make run

# 生产模式
make start

# 自定义参数
python main.py --host 0.0.0.0 --port 8080 --reload
```

### API调用示例

#### 非流式请求

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={"Content-Type": "application/json"},
    json={
        "model": "deepseek-v3",
        "messages": [
            {"role": "user", "content": "你好，请介绍一下你自己"}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
)

print(response.json())
```

#### 流式请求

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={"Content-Type": "application/json"},
    json={
        "model": "deepseek-v3",
        "messages": [
            {"role": "user", "content": "请写一个简短的故事"}
        ],
        "stream": True
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

#### 使用OpenAI SDK

```python
from openai import OpenAI

# 配置客户端指向本地代理
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"  # 如果没有配置API密钥验证
)

response = client.chat.completions.create(
    model="deepseek-v3",
    messages=[
        {"role": "user", "content": "Hello, world!"}
    ]
)

print(response.choices[0].message.content)
```

## 🔗 API文档

启动服务后，访问以下地址查看API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 健康检查 |
| `/health` | GET | 详细健康检查 |
| `/config` | GET | 获取配置信息 |
| `/config/reload` | POST | 重新加载配置 |
| `/v1/chat/completions` | POST | 聊天完成（OpenAI兼容） |

## 🛠️ 开发

### 环境设置

```bash
# 安装开发依赖
uv add --dev pytest pytest-asyncio httpx

# 安装开发工具（如果没有全局安装）
uv tool install mypy ruff
```

### 代码质量检查

```bash
# 代码风格检查
make lint

# 代码格式化
make format-fix

# 类型检查
make type-check

# 完整检查
make check

# 自动修复所有问题
make fix
```

### 运行测试

```bash
# 运行测试
make test

# 运行测试并生成覆盖率报告
uv run pytest --cov=app --cov-report=html
```

## 📋 项目结构

```
openai-llm-proxy/
├── app/                    # 核心应用模块
│   ├── __init__.py
│   ├── app.py             # FastAPI应用主体
│   ├── config.py          # 配置管理
│   ├── router.py          # 模型路由逻辑
│   ├── models.py          # Pydantic数据模型
│   ├── middleware.py      # 中间件（请求ID、日志等）
│   └── errors.py          # 错误处理
├── config/                # 配置文件目录
│   ├── config.yaml        # 主配置文件
│   └── .axample          # 配置示例
├── main.py               # 应用入口
├── pyproject.toml        # 项目依赖配置
├── mypy.ini             # MyPy类型检查配置
├── Makefile             # 开发工具命令
└── README.md            # 项目文档
```

## 🔧 故障排除

### 常见问题

**Q: 启动时报错 "Invalid args for response field"**

A: 这是FastAPI的返回类型注解问题，已通过添加 `response_model=None` 解决。

**Q: 模型未找到错误**

A: 检查 `config/config.yaml` 中是否正确配置了模型映射：
```yaml
model_config:
  "your-model-name": provider_name
model_routes:
  provider_name:
    "your-model-name": "actual-model-id"
```

**Q: API密钥认证失败**

A: 确保在 `config/config.yaml` 的 `os_env` 部分设置了正确的API密钥。

**Q: 连接超时**

A: 检查网络连接和提供商服务状态，可在配置中调整超时设置。

### 日志查看

```bash
# 启动时查看详细日志
python main.py --log-level debug

# 查看请求ID追踪
grep "request_id" logs/app.log
```

## 🤝 贡献

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [LiteLLM](https://github.com/BerriAI/litellm) - 多厂商LLM统一接口
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证和设置管理

## 📞 支持

如果您遇到问题或有建议，请：

1. 查看本文档的故障排除部分
2. 在GitHub上创建Issue
3. 查看API文档: http://localhost:8000/docs
