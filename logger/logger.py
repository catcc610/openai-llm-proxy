"""
通用日志记录模块，基于 loguru 库

该模块提供:
- 一个可配置的全局日志记录器，默认使用彩色，带有适用于开发和生产环境的设置
- 简便的日志轮转配置
- 控制台和文件输出
- 可选的 JSON 格式化
- 生产环境中记录堆栈跟踪的能力
"""

import sys
import json
from pathlib import Path
from loguru import logger
from typing import Union, Optional, Any

class LogConfig:
    """日志记录器配置类"""
    
    _DEFAULT_LOG_PATH = "logs/app.log"
    _DEFAULT_LOG_LEVEL = "INFO"
    _DEFAULT_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)
    _DEFAULT_ROTATION = "10 MB"
    _DEFAULT_RETENTION = "1 week"
    _DEFAULT_COMPRESSION = "zip"

    def __init__(
        self,
        level: str = _DEFAULT_LOG_LEVEL,
        format_string: str = _DEFAULT_LOG_FORMAT,
        json_logs: bool = False,
        log_to_console: bool = True,
        log_to_file: bool = False,
        log_path: Optional[Union[str, Path]] = _DEFAULT_LOG_PATH,
        rotation: str = _DEFAULT_ROTATION,
        retention: str = _DEFAULT_RETENTION,
        compression: str = _DEFAULT_COMPRESSION,
    ):
        """
        初始化日志记录配置

        Args:
            level: 日志级别, 默认为 "INFO"
            format_string: 日志格式字符串
            json_logs: 是否以 JSON 格式输出日志
            log_to_console: 是否输出到控制台
            log_to_file: 是否输出到文件
            log_path: 日志文件路径，如果为 None 则使用默认路径
            rotation: 日志轮转大小，例如 "10 MB" 或 "1 day"
            retention: 日志保留时间，例如 "1 week" 或 "10 days"
            compression: 压缩方式，例如 "zip" 或 "gz"
        """
        self.level = level
        self.format_string = format_string
        self.json_logs = json_logs
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.log_path = Path(log_path)
        if self.log_to_file:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.rotation = rotation  
        self.retention = retention
        self.compression = compression

def setup_logging(config: Optional[LogConfig] = None) -> None:
    """
    配置全局 Loguru Logger

    Args:
        config: 日志配置，如果未提供则使用默认配置
    """
    if config is None:
        config = LogConfig()

    # 移除所有默认处理器
    logger.remove()
    # 获取格式
    log_format = format_json if config.json_logs else config.format_string
    
    # 添加控制台处理器
    if config.log_to_console:
        logger.add(
            sys.stderr,
            format=log_format,
            level=config.level,
            colorize=not config.json_logs,
        )
    
    # 添加文件处理器
    if config.log_to_file:
        logger.add(
            str(config.log_path),
            format=log_format,
            level=config.level,
            rotation=config.rotation,
            retention=config.retention,
            compression=config.compression,
            enqueue=True,
        )

def format_json(record):
    return json.dumps(
        {
            "timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S.%f"),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "process_id": record["process"].id,
            "thread_id": record["thread"].id,
            "extra": record["extra"],
        }
    ) + "\n"

def get_logger(name: str = None) -> Any:
    """
    获取已配置的 logger 实例
    
    Args:
        name: 日志记录器名称，通常为模块名
    
    Returns:
        已配置的 logger 实例
    """
    return logger.bind(name=name)

setup_logging()
