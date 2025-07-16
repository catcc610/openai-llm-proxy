# Python 项目管理 Makefile

# 初始化项目依赖
init:
	uv sync

# 启动开发服务器
run:
	uv run python main.py --reload

# 生产环境启动
start:
	uv run python main.py --host 0.0.0.0 --port 8000

# 代码检查
lint:
	ruff check . --exclude test

# 自动修复代码问题
lint-fix:
	ruff check --fix . --exclude test

# 代码格式化检查
format:
	ruff format --check . --exclude test

# 自动格式化代码
format-fix:
	ruff format . --exclude test

# 类型检查
type-check:
	mypy . --exclude test

# 完整检查（不修复）- 显示所有问题但不停止
check:
	@echo "🔍 开始代码检查..."
	@echo "📝 检查代码格式..."
	@ruff format --check . --exclude test || echo "❌ 格式检查失败，运行 'make format-fix' 修复"
	@echo "🔍 检查代码规范..."
	@ruff check . --exclude test || echo "❌ 代码规范检查失败，运行 'make lint-fix' 修复"
	@echo "🔎 检查类型注解..."
	@mypy . --exclude test || echo "❌ 类型检查失败，需要手动修复"
	@echo "✅ 检查完成"

# 快速检查（遇到错误就停止）
check-strict:
	make format
	make lint  
	make type-check

# 自动修复所有问题
fix:
	@echo "🔧 开始自动修复..."
	make lint-fix
	make format-fix
	@echo "✅ 自动修复完成，建议再次运行 'make check' 验证"

# 清理缓存
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

# 安装开发依赖
dev:
	uv add --dev pytest pytest-asyncio httpx

# 运行测试
test:
	uv run pytest

# 显示帮助信息
help:
	@echo "可用命令："
	@echo "  init       - 初始化项目依赖"
	@echo "  run        - 启动开发服务器（热重载）"
	@echo "  start      - 启动生产服务器"
	@echo "  lint       - 检查代码风格"
	@echo "  lint-fix   - 自动修复代码风格问题"
	@echo "  format     - 检查代码格式"
	@echo "  format-fix - 自动格式化代码"
	@echo "  type-check - 类型检查"
	@echo "  check      - 完整检查（不修复）"
	@echo "  fix        - 自动修复所有问题"
	@echo "  clean      - 清理缓存文件"
	@echo "  test       - 运行测试"
	@echo "  help       - 显示此帮助信息"

# 设置默认目标
.DEFAULT_GOAL := help

# 声明伪目标
.PHONY: init run start lint lint-fix format format-fix type-check check fix clean dev test help

supervisor-init:
	supervisorctl reread && supervisorctl update