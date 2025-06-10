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

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_config


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="LLM Proxy Service")
    parser.add_argument("--host", type=str, help="服务器host地址 (默认从配置文件读取)")
    parser.add_argument("--port", type=int, help="服务器端口号 (默认从配置文件读取)")
    parser.add_argument("--reload", action="store_true", help="启用热重载 (开发模式)")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数 (默认: 1)")
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["debug", "info", "warning", "error"],
        help="日志级别 (默认从配置文件读取)",
    )

    return parser.parse_args()


def main() -> None:
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_args()

        # 获取配置
        config = get_config()
        server_config = config.server

        # 使用命令行参数覆盖配置文件设置
        host = args.host or server_config.host
        port = args.port or server_config.port
        reload = args.reload or server_config.reload
        log_level = args.log_level or server_config.log_level

        print("🚀 启动 LLM Proxy Service")
        print(f"📍 地址: http://{host}:{port}")
        print(f"📖 API文档: http://{host}:{port}/docs")
        print(f"🔄 热重载: {'开启' if reload else '关闭'}")
        print(f"📊 日志级别: {log_level}")
        print("-" * 50)

        # 启动服务器
        uvicorn.run(
            "app.app:app",
            host=host,
            port=port,
            reload=reload,
            workers=args.workers if not reload else 1,  # 热重载模式下只能用1个worker
            log_level=log_level,
            access_log=True,
        )

    except Exception as e:
        print(f"❌ 应用启动失败: {e}")
        print("使用默认配置重试...")

        # 使用默认配置启动
        uvicorn.run(
            "app.app:app", host="0.0.0.0", port=9991, reload=True, log_level="info"
        )


if __name__ == "__main__":
    main()
