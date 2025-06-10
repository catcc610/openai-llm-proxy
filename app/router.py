"""
模型路由逻辑
处理模型ID的解析和映射，严格依赖配置文件
"""

from app.config import get_model_route


class ModelRouter:
    """模型路由器，负责解析和路由模型请求"""

    def resolve_model(self, model_id: str) -> str:
        """
        解析模型ID，返回LiteLLM格式的模型名称

        Args:
            model_id: 请求的模型ID

        Returns:
            LiteLLM格式的模型名称

        Raises:
            ValueError: 如果模型ID无法解析或未在配置文件中定义
        """
        if not model_id or not model_id.strip():
            raise ValueError("模型ID不能为空")

        model_id = model_id.strip()

        # 从配置文件获取模型路由
        configured_route = get_model_route(model_id)
        if configured_route != model_id:  # 如果有配置的路由
            print(f"🎯 配置路由: {model_id} -> {configured_route}")
            return configured_route

        # 如果配置文件中没有找到路由，直接报错
        raise ValueError(
            f"模型 '{model_id}' 未在配置文件中定义，请在 config.yaml 中添加相应的模型配置"
        )

    def get_provider_from_model(self, model_id: str) -> str:
        """
        从模型ID获取提供商名称

        Args:
            model_id: 模型ID

        Returns:
            提供商名称

        Raises:
            ValueError: 如果模型ID无法解析
        """
        resolved = self.resolve_model(model_id)
        if "/" in resolved:
            return resolved.split("/")[0]
        raise ValueError(f"无法从模型 '{model_id}' 中解析提供商")


# 全局路由器实例
_router = ModelRouter()


def resolve_model(model_id: str) -> str:
    """
    解析模型ID的便捷函数

    Args:
        model_id: 请求的模型ID

    Returns:
        LiteLLM格式的模型名称

    Raises:
        ValueError: 如果模型ID无法解析或未在配置文件中定义
    """
    return _router.resolve_model(model_id)


def get_provider_from_model(model_id: str) -> str:
    """
    获取提供商名称的便捷函数

    Args:
        model_id: 模型ID

    Returns:
        提供商名称

    Raises:
        ValueError: 如果模型ID无法解析
    """
    return _router.get_provider_from_model(model_id)
