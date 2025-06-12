#!/usr/bin/env python3
"""
LLM Proxy Service - 启动脚本
使用方法:
    python main.py                    # 使用默认配置启动
    python main.py --host 0.0.0.0    # 指定host
    python main.py --port 8080       # 指定端口
    python main.py --reload          # 开启热重载
"""

import argparse
import uvicorn
import sys
import os
import logging

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_config
from app.logging_config import setup_colored_logging

# 获取日志记录器
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="LLM Proxy Service")
    parser.add_argument("--host", type=str, help="服务器host地址 (默认从配置文件读取)")
    parser.add_argument("--port", type=int, help="服务器端口号 (默认从配置文件读取)")
    parser.add_argument("--reload", action="store_true", help="启用热重载 (开发模式)")
    parser.add_argument("--workers", type=int, help="工作进程数 (默认从配置文件读取)")
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["debug", "info", "warning", "error"],
        help="日志级别 (默认从配置文件读取)",
    )

    return parser.parse_args()


def setup_logging_from_config(args: argparse.Namespace) -> str:
    """根据配置文件和命令行参数设置日志"""
    try:
        # 获取配置
        config = get_config()
        logging_config = config.logging

        # 命令行参数优先级高于配置文件
        log_level = args.log_level or logging_config.level

        # 设置彩色日志
        setup_colored_logging(level=log_level)

        return log_level

    except Exception as e:
        # 配置加载失败时使用默认设置
        # 这里还需要用print，因为logger还没有配置
        print(f"⚠️  日志配置加载失败: {e}")
        print("📝 使用默认日志配置")

        log_level = args.log_level or "info"
        setup_colored_logging(level=log_level)

        return log_level


def main() -> None:
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_args()

        # 设置日志配置（从配置文件和命令行参数）
        log_level = setup_logging_from_config(args)

        # 获取配置
        config = get_config()
        server_config = config.server

        # 使用命令行参数覆盖配置文件设置
        host = args.host or server_config.host
        port = args.port or server_config.port
        workers = args.workers or server_config.workers
        reload = args.reload  # 热重载只能通过命令行参数启用

        logger.info("🚀 启动 LLM Proxy Service")
        logger.info(f"📍 地址: http://{host}:{port}")
        logger.info(f"📖 API文档: http://{host}:{port}/docs")
        logger.info(f"🔄 热重载: {'开启' if reload else '关闭'}")
        logger.info(f"👥 工作进程: {workers if not reload else 1}")
        logger.info(f"📊 日志级别: {log_level}")
        logger.info("🎨 彩色输出: 开启")
        logger.info("-" * 50)

        # 启动服务器
        uvicorn.run(
            "app.app:app",
            host=host,
            port=port,
            reload=reload,
            workers=workers if not reload else 1,  # 热重载模式下只能用1个worker
            log_level=log_level,
            access_log=True,
        )

    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        logger.info("使用默认配置重试...")

        # 使用默认配置启动
        setup_colored_logging("info")
        uvicorn.run(
            "app.app:app", host="0.0.0.0", port=9000, reload=True, log_level="info"
        )


if __name__ == "__main__":
    main()
