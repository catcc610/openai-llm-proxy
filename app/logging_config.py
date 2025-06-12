"""
彩色日志配置模块
支持不同日志等级的颜色显示和从配置文件读取日志等级
"""

import logging
import sys
from typing import Dict, Optional
from enum import Enum


class LogColor:
    """ANSI颜色代码"""

    # 颜色代码
    RED = "\033[91m"  # 红色 - ERROR
    YELLOW = "\033[93m"  # 黄色 - WARNING
    GREEN = "\033[92m"  # 绿色 - INFO
    PURPLE = "\033[95m"  # 紫色 - DEBUG
    CYAN = "\033[96m"  # 青色 - 其他
    WHITE = "\033[97m"  # 白色 - 默认

    # 样式
    BOLD = "\033[1m"  # 粗体
    UNDERLINE = "\033[4m"  # 下划线

    # 重置
    RESET = "\033[0m"  # 重置所有格式


class LogLevel(str, Enum):
    """日志等级枚举"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # 日志等级到颜色的映射
    LEVEL_COLORS: Dict[str, str] = {
        "DEBUG": LogColor.PURPLE,
        "INFO": LogColor.GREEN,
        "WARNING": LogColor.YELLOW,
        "ERROR": LogColor.RED,
        "CRITICAL": LogColor.RED + LogColor.BOLD,
    }

    def __init__(
        self, fmt: Optional[str] = None, datefmt: Optional[str] = None
    ) -> None:
        """初始化彩色格式化器"""
        if fmt is None:
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        if datefmt is None:
            datefmt = "%Y-%m-%d %H:%M:%S"

        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录，添加颜色"""
        # 获取原始格式化结果
        log_message = super().format(record)

        # 获取日志等级对应的颜色
        level_color = self.LEVEL_COLORS.get(record.levelname, LogColor.WHITE)

        # 只对终端输出添加颜色（检查是否为TTY）
        if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
            # 为整行添加颜色
            colored_message = f"{level_color}{log_message}{LogColor.RESET}"
            return colored_message
        else:
            # 非终端环境（如文件输出）不添加颜色
            return log_message


class LoggingConfig:
    """日志配置管理器"""

    def __init__(self) -> None:
        self._configured = False

    def setup_logging(self, level: str = "info") -> None:
        """
        配置应用日志系统

        Args:
            level: 日志等级 (debug, info, warning, error)
        """
        # 避免重复配置
        if self._configured:
            return

        # 日志等级映射
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }

        # 获取日志等级
        log_level = level_map.get(level.lower(), logging.INFO)

        # 创建根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # 清除现有的处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)

        # 使用彩色格式化器
        formatter = ColoredFormatter()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # 设置第三方库的日志等级
        self._configure_third_party_loggers(log_level)

        self._configured = True

        # 输出配置信息
        logger = logging.getLogger(__name__)
        logger.info(f"🎨 日志系统已配置 - 等级: {level.upper()}, 彩色输出: 开启")

    def _configure_third_party_loggers(self, level: int) -> None:
        """配置第三方库的日志等级"""
        # 设置常见第三方库的日志等级，避免过多输出
        third_party_loggers = [
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
            "fastapi",
            "httpx",
            "httpcore",
        ]

        for logger_name in third_party_loggers:
            logger = logging.getLogger(logger_name)
            # 第三方库使用稍高的日志等级
            if level == logging.DEBUG:
                logger.setLevel(logging.INFO)
            else:
                logger.setLevel(max(level, logging.WARNING))

    def reset_configuration(self) -> None:
        """重置日志配置状态"""
        self._configured = False


# 全局日志配置实例 - 使用None初始化
_logging_config: Optional[LoggingConfig] = None


def get_logging_config() -> LoggingConfig:
    """获取日志配置实例"""
    global _logging_config
    if _logging_config is None:
        _logging_config = LoggingConfig()
    return _logging_config


def setup_colored_logging(level: str = "info") -> None:
    """
    设置彩色日志 - 便捷函数

    Args:
        level: 日志等级
    """
    config = get_logging_config()
    config.setup_logging(level)


def reset_logging() -> None:
    """重置日志配置"""
    config = get_logging_config()
    config.reset_configuration()


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器 - 便捷函数"""
    return logging.getLogger(name)


# 测试函数
def test_colored_logging() -> None:
    """测试彩色日志输出"""
    setup_colored_logging("debug")

    logger = get_logger("test")

    logger.debug("🔍 这是一条DEBUG消息 - 紫色")
    logger.info("ℹ️  这是一条INFO消息 - 绿色")
    logger.warning("⚠️  这是一条WARNING消息 - 黄色")
    logger.error("❌ 这是一条ERROR消息 - 红色")

    try:
        raise ValueError("测试异常")
    except Exception:
        logger.exception("💥 这是一条异常消息")


if __name__ == "__main__":
    test_colored_logging()
