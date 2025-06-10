"""
配置管理系统
负责加载YAML配置文件、设置环境变量，并支持多厂商模型路由
优化版本：内存缓存、文件变更检测、智能重载
"""

import os
import yaml
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from threading import Lock
from functools import lru_cache


class ServerConfig(BaseModel):
    """服务器配置模型"""

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"


class ProxyConfig(BaseModel):
    """代理配置模型"""

    timeout: int = 30
    max_retries: int = 3
    default_model: str = "gpt-3.5-turbo"


class SecurityConfig(BaseModel):
    """安全配置模型"""

    api_keys: List[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    """应用总配置模型"""

    model_config = ConfigDict(protected_namespaces=())  # 解决model_前缀警告

    os_env: Dict[str, str] = Field(default_factory=dict)
    model_config_mapping: Dict[str, str] = Field(
        default_factory=dict, alias="model_config"
    )
    model_routes: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    server: ServerConfig = Field(default_factory=ServerConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


class ConfigCache:
    """配置缓存管理器"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Any:
        """获取缓存值"""
        with self._lock:
            return self._cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            self._cache[key] = value
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def has(self, key: str) -> bool:
        """检查缓存中是否存在key"""
        with self._lock:
            return key in self._cache


class ConfigManager:
    """配置管理器 - 优化版本"""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config: Optional[AppConfig] = None
        self._file_mtime: Optional[float] = None
        self._cache = ConfigCache()
        self._lock = Lock()
        self._load_config()

    def _get_file_mtime(self) -> Optional[float]:
        """获取配置文件的修改时间"""
        try:
            return self.config_path.stat().st_mtime
        except FileNotFoundError:
            return None

    def _should_reload(self) -> bool:
        """检查是否需要重新加载配置"""
        if not self.config or not self._file_mtime:
            return True
        
        current_mtime = self._get_file_mtime()
        if current_mtime is None:
            return False
        
        return current_mtime > self._file_mtime

    def _load_config(self) -> None:
        """加载配置文件"""
        with self._lock:
            try:
                # 检查文件是否存在
                if not self.config_path.exists():
                    raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

                # 记录文件修改时间
                self._file_mtime = self._get_file_mtime()

                # 加载主配置文件
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)

                # 验证并创建配置对象
                self.config = AppConfig(**config_data)

                # 清空缓存
                self._cache.clear()

                # 设置环境变量
                self._set_environment_variables()

                print(f"✅ 配置加载成功: {self.config_path} (修改时间: {time.ctime(self._file_mtime)})")

            except Exception as e:
                print(f"❌ 配置加载失败: {e}")
                raise

    def _set_environment_variables(self) -> None:
        """设置环境变量供LiteLLM使用"""
        if not self.config:
            return

        # 设置配置文件中的环境变量
        for key, value in self.config.os_env.items():
            if value and value.strip():  # 只设置非空值
                os.environ[key] = value
                print(f"✅ {key} 已设置到环境变量")

        # 特殊处理Google Cloud凭证文件路径
        if "GOOGLE_APPLICATION_CREDENTIALS" in self.config.os_env:
            cred_path = Path(self.config.os_env["GOOGLE_APPLICATION_CREDENTIALS"])
            if not cred_path.is_absolute():
                cred_path = Path.cwd() / cred_path

            if cred_path.exists():
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)
                print(f"✅ GOOGLE_APPLICATION_CREDENTIALS 已设置: {cred_path}")
            else:
                print(f"⚠️  Google凭证文件不存在: {cred_path}")

    def _ensure_config_loaded(self) -> None:
        """确保配置已加载，如果文件有变更则自动重新加载"""
        if self._should_reload():
            print("🔄 检测到配置文件变更，重新加载配置...")
            self._load_config()

    def get_config(self) -> AppConfig:
        """获取配置对象"""
        self._ensure_config_loaded()
        if not self.config:
            raise RuntimeError("配置未加载")
        return self.config

    @lru_cache(maxsize=256)
    def _get_model_route_cached(self, model_name: str, config_hash: str) -> str:
        """获取模型路由的缓存版本"""
        if not self.config:
            raise RuntimeError("配置未加载")

        # 1. 查看model_config，确定使用哪个厂商
        provider = self.config.model_config_mapping.get(model_name)
        if not provider:
            # 如果没有配置厂商，返回原始模型名
            return model_name

        # 2. 从对应厂商的model_routes中获取具体的模型ID
        provider_routes = self.config.model_routes.get(provider, {})
        model_id = provider_routes.get(model_name)

        if model_id:
            # 构建LiteLLM格式的模型名称
            litellm_model = f"{provider}/{model_id}"
            print(f"🎯 模型路由: {model_name} -> {litellm_model} (via {provider})")
            return litellm_model
        else:
            # 如果找不到具体映射，使用默认格式
            default_model = f"{provider}/{model_name}"
            print(f"🎯 默认路由: {model_name} -> {default_model}")
            return default_model

    def get_model_route(self, model_name: str) -> str:
        """
        获取模型路由
        根据model_config选择厂商，然后从model_routes获取具体的模型ID

        Args:
            model_name: 模型名称

        Returns:
            LiteLLM格式的模型名称
        """
        self._ensure_config_loaded()
        
        # 使用配置的哈希值作为缓存键的一部分，确保配置变更时缓存失效
        config_hash = str(hash(str(self.config.model_config_mapping) + str(self.config.model_routes)))
        
        return self._get_model_route_cached(model_name, config_hash)

    def get_available_models(self) -> Dict[str, str]:
        """获取所有可配置的模型及其当前厂商"""
        self._ensure_config_loaded()
        
        # 使用缓存
        cache_key = "available_models"
        cached_result = self._cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        if not self.config:
            return {}
        
        result = dict(self.config.model_config_mapping)
        self._cache.set(cache_key, result)
        return result

    def get_provider_models(self, provider: str) -> Dict[str, str]:
        """获取指定厂商的所有模型映射"""
        self._ensure_config_loaded()
        
        # 使用缓存
        cache_key = f"provider_models_{provider}"
        cached_result = self._cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        if not self.config:
            return {}
        
        result = self.config.model_routes.get(provider, {})
        self._cache.set(cache_key, result)
        return result

    def reload_config(self) -> None:
        """强制重新加载配置"""
        print("🔄 手动重新加载配置...")
        # 清空LRU缓存
        self._get_model_route_cached.cache_clear()
        self._load_config()

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        cache_info = self._get_model_route_cached.cache_info()
        return {
            "model_route_cache": {
                "hits": cache_info.hits,
                "misses": cache_info.misses,
                "current_size": cache_info.currsize,
                "max_size": cache_info.maxsize,
                "hit_rate": cache_info.hits / (cache_info.hits + cache_info.misses) if (cache_info.hits + cache_info.misses) > 0 else 0
            },
            "config_file_mtime": self._file_mtime,
            "config_loaded": self.config is not None
        }

    def clear_cache(self) -> None:
        """清空所有缓存"""
        self._get_model_route_cached.cache_clear()
        self._cache.clear()
        print("🧹 缓存已清空")


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """获取应用配置"""
    return config_manager.get_config()


def get_model_route(model_name: str) -> str:
    """获取模型路由"""
    return config_manager.get_model_route(model_name)


def get_available_models() -> Dict[str, str]:
    """获取所有可用的模型配置"""
    return config_manager.get_available_models()


def get_provider_models(provider: str) -> Dict[str, str]:
    """获取指定厂商的模型映射"""
    return config_manager.get_provider_models(provider)


def reload_config() -> None:
    """重新加载配置"""
    config_manager.reload_config()


def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息"""
    return config_manager.get_cache_stats()


def clear_cache() -> None:
    """清空缓存"""
    config_manager.clear_cache()
