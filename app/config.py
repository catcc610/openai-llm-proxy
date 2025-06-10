"""
配置管理系统
负责加载YAML配置文件、设置环境变量，并支持多厂商模型路由
"""

import os
import yaml
from typing import Dict, List, Optional
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict


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


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config: Optional[AppConfig] = None
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            # 加载主配置文件
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # 验证并创建配置对象
            self.config = AppConfig(**config_data)

            # 设置环境变量
            self._set_environment_variables()

            print(f"✅ 配置加载成功: {self.config_path}")

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

    def get_config(self) -> AppConfig:
        """获取配置对象"""
        if not self.config:
            raise RuntimeError("配置未加载")
        return self.config

    def get_model_route(self, model_name: str) -> str:
        """
        获取模型路由
        根据model_config选择厂商，然后从model_routes获取具体的模型ID

        Args:
            model_name: 模型名称

        Returns:
            LiteLLM格式的模型名称
        """
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

    def get_available_models(self) -> Dict[str, str]:
        """获取所有可配置的模型及其当前厂商"""
        if not self.config:
            return {}
        return dict(self.config.model_config_mapping)

    def get_provider_models(self, provider: str) -> Dict[str, str]:
        """获取指定厂商的所有模型映射"""
        if not self.config:
            return {}
        return self.config.model_routes.get(provider, {})

    def reload_config(self) -> None:
        """重新加载配置"""
        self._load_config()


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
