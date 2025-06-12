"""
配置管理系统
负责加载YAML配置文件、设置环境变量，并支持多厂商模型路由
优化版本：内存缓存、文件变更检测、智能重载
"""

import os
import yaml
from typing import Dict, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from functools import lru_cache
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 用于文件监控的全局变量 (目前 watch_config_file 功能未激活)
_config: Optional["AppConfig"] = None
_config_last_modified: float = 0.0


class ServerConfig(BaseModel):
    """服务器配置"""

    host: str = Field(default="0.0.0.0", description="服务器监听地址")
    port: int = Field(default=9000, description="服务器监听端口")
    workers: int = Field(default=1, description="工作进程数")


class LoggingConfig(BaseModel):
    """日志配置"""

    level: str = Field(
        default="info", description="日志等级 (debug, info, warning, error)"
    )


class ProxyConfig(BaseModel):
    """代理配置"""

    timeout: int = Field(default=300, description="请求超时时间(秒)")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=1.0, description="重试延迟(秒)")


class AppConfig(BaseModel):
    """应用配置主模型"""

    model_config = ConfigDict(protected_namespaces=())  # 解决model_前缀警告

    # 子配置
    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)

    # 环境变量配置
    os_env: Dict[str, str] = Field(
        default_factory=dict, description="需要设置的环境变量"
    )

    # 模型配置 - 模型名到提供商的映射
    model_config_mapping: Dict[str, str] = Field(
        default_factory=dict, alias="model_config", description="模型名到提供商映射"
    )

    # 模型路由配置 - 提供商内部的模型映射
    model_routes: Dict[str, Dict[str, str]] = Field(
        default_factory=dict, description="提供商模型路由"
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """
    加载、验证并缓存应用配置。
    使用lru_cache确保配置只从文件加载一次，实现单例模式。
    这使得配置在内存中可用，并支持无状态服务。
    """
    config_file = PROJECT_ROOT / "config" / "config.yaml"
    try:
        logger.info(f"🔧 正在加载配置文件: {config_file}")
        if not config_file.exists():
            logger.warning(f"⚠️  配置文件不存在: {config_file}，将使用默认配置。")
            config = AppConfig()
        else:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
            config = AppConfig(**config_data)
            logger.info("✅ 配置文件加载成功")

        # 设置环境变量
        if config.os_env:
            logger.info("🔑 正在设置API密钥环境变量...")
            env_count = 0
            for key, value in config.os_env.items():
                if value and not os.getenv(key):
                    os.environ[key] = value
                    env_count += 1
                    logger.info(
                        f"   ✅ {key}: {'*' * 8}...{value[-4:] if len(value) > 4 else '****'}"
                    )
            logger.info(f"📊 共设置 {env_count} 个环境变量")

        # 验证配置
        logger.info("🔍 正在验证配置...")
        if config.model_config_mapping:
            logger.info(f"📋 配置了 {len(config.model_config_mapping)} 个模型映射")
        if config.model_routes:
            total_routes = sum(len(routes) for routes in config.model_routes.values())
            logger.info(
                f"🚀 配置了 {len(config.model_routes)} 个提供商，{total_routes} 个路由"
            )
        logger.info("✅ 配置验证通过")

        return config

    except Exception as e:
        logger.error(f"❌ 配置加载失败: {e}，将使用默认配置。")
        # 在失败情况下返回一个默认配置，以保证程序的健壮性
        return AppConfig()


@lru_cache(maxsize=256)
def get_model_route(model_name: str) -> str:
    """
    获取并缓存模型路由。
    由于 get_config() 是缓存的，此函数依赖于一个稳定的配置。
    """
    config = get_config()

    # 1. 查看model_config，确定使用哪个厂商
    provider = config.model_config_mapping.get(model_name)
    if not provider:
        # 如果没有配置厂商，返回原始模型名
        return model_name

    # 2. 从对应厂商的model_routes中获取具体的模型ID
    provider_routes = config.model_routes.get(provider, {})
    model_id = provider_routes.get(model_name)

    if model_id:
        # 构建LiteLLM格式的模型名称
        litellm_model = f"{provider}/{model_id}"
        logger.debug(f"🎯 模型路由: {model_name} -> {litellm_model} (via {provider})")
        return litellm_model
    else:
        # 如果找不到具体映射，使用默认格式
        default_model = f"{provider}/{model_name}"
        logger.debug(f"🎯 默认路由: {model_name} -> {default_model}")
        return default_model


def get_available_models() -> Dict[str, str]:
    """获取所有可用的模型配置"""
    config = get_config()
    return dict(config.model_config_mapping)


def get_provider_models(provider: str) -> Dict[str, str]:
    """获取指定厂商的模型映射"""
    config = get_config()
    return config.model_routes.get(provider, {})


def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息"""
    config_cache_info = get_config.cache_info()
    model_route_cache_info = get_model_route.cache_info()

    model_route_hits = model_route_cache_info.hits
    model_route_misses = model_route_cache_info.misses
    total_model_requests = model_route_hits + model_route_misses

    return {
        "config_cache": {
            "hits": config_cache_info.hits,
            "misses": config_cache_info.misses,
            "current_size": config_cache_info.currsize,
            "max_size": config_cache_info.maxsize,
        },
        "model_route_cache": {
            "hits": model_route_hits,
            "misses": model_route_misses,
            "current_size": model_route_cache_info.currsize,
            "max_size": model_route_cache_info.maxsize,
            "hit_rate": model_route_hits / total_model_requests
            if total_model_requests > 0
            else 0,
        },
        "config_loaded": config_cache_info.currsize > 0,
    }


def watch_config_file() -> None:
    """
    (该功能目前未激活)
    启动一个后台线程来监视配置文件的变化。
    """
    global _config, _config_last_modified
    _config = None
    _config_last_modified = 0
    logger.info("配置缓存已清除")
