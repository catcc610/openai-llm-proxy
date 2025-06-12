"""
错误处理模块 - 处理LiteLLM和代理服务的各种异常
"""

# 标准库导入
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

# 第三方库导入
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models import ErrorDetail, ErrorResponse

# 只在类型检查时导入，运行时动态导入
if TYPE_CHECKING:
    from litellm import (
        BadRequestError,
        AuthenticationError,
        NotFoundError,
        RateLimitError,
        APIError,
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
        ServiceUnavailableError,
        ContextWindowExceededError,
    )
else:
    # 运行时动态导入
    try:
        from litellm import (
            BadRequestError,
            AuthenticationError,
            NotFoundError,
            RateLimitError,
            APIError,
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
            ServiceUnavailableError,
            ContextWindowExceededError,
        )
    except ImportError:
        # 如果导入失败，创建占位符类
        BadRequestError = type("BadRequestError", (Exception,), {})
        AuthenticationError = type("AuthenticationError", (Exception,), {})
        NotFoundError = type("NotFoundError", (Exception,), {})
        RateLimitError = type("RateLimitError", (Exception,), {})
        APIError = type("APIError", (Exception,), {})
        APIConnectionError = type("APIConnectionError", (Exception,), {})
        APITimeoutError = type("APITimeoutError", (Exception,), {})
        InternalServerError = type("InternalServerError", (Exception,), {})
        ServiceUnavailableError = type("ServiceUnavailableError", (Exception,), {})
        ContextWindowExceededError = type(
            "ContextWindowExceededError", (Exception,), {}
        )


# 配置日志
logger = logging.getLogger(__name__)


class ProxyError(Exception):
    """代理服务中所有自定义错误的基类"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_type: str = "internal_error",
        param: str | None = None,
        code: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.type = error_type
        self.param = param
        self.code = code

    def to_error_response(self) -> ErrorResponse:
        """将异常转换为OpenAI格式的错误响应模型"""
        return ErrorResponse(
            error=ErrorDetail(
                message=self.message,
                type=self.type,
                param=self.param,
                code=self.code,
            )
        )


class ModelNotFoundError(ProxyError):
    """模型未找到错误"""

    def __init__(self, model: str):
        super().__init__(
            message=f"模型 '{model}' 不受支持或未配置",
            status_code=400,
            error_type="model_not_found",
            param=model,
            code="MODEL_NOT_FOUND",
        )


class ConfigurationError(ProxyError):
    """配置错误"""

    def __init__(self, message: str):
        super().__init__(
            message=f"配置错误: {message}",
            status_code=500,
            error_type="configuration_error",
            param=message,
            code="CONFIGURATION_ERROR",
        )


def map_litellm_error_to_http(error: Exception) -> tuple[int, str, str]:
    """
    将LiteLLM错误映射到HTTP状态码和错误信息

    Returns:
        tuple[status_code, error_code, message]
    """
    error_type = type(error).__name__
    error_message = str(error)

    # 模型路由相关错误 - 优先处理
    if isinstance(error, ValueError):
        if "未在配置文件中定义" in error_message:
            return 400, "MODEL_NOT_CONFIGURED", error_message
        elif "模型ID不能为空" in error_message:
            return 400, "INVALID_MODEL_ID", error_message
        elif "无法从模型" in error_message and "中解析提供商" in error_message:
            return 400, "PROVIDER_PARSE_ERROR", error_message

    # LiteLLM错误映射 - 使用类名进行匹配以处理动态创建的类
    if isinstance(error, BadRequestError) or error_type == "BadRequestError":
        return 400, "BAD_REQUEST", f"请求参数无效: {error_message}"

    elif isinstance(error, AuthenticationError) or error_type == "AuthenticationError":
        return 401, "AUTHENTICATION_ERROR", f"API密钥认证失败: {error_message}"

    elif isinstance(error, NotFoundError) or error_type == "NotFoundError":
        return 404, "NOT_FOUND", f"资源未找到: {error_message}"

    elif isinstance(error, RateLimitError) or error_type == "RateLimitError":
        return 429, "RATE_LIMIT_EXCEEDED", f"请求频率限制: {error_message}"

    elif (
        isinstance(error, ContextWindowExceededError)
        or error_type == "ContextWindowExceededError"
    ):
        return 400, "CONTEXT_LENGTH_EXCEEDED", f"上下文长度超出限制: {error_message}"

    elif isinstance(error, APIConnectionError) or error_type == "APIConnectionError":
        return 502, "UPSTREAM_CONNECTION_ERROR", f"上游服务连接失败: {error_message}"

    elif isinstance(error, APITimeoutError) or error_type == "APITimeoutError":
        return 504, "UPSTREAM_TIMEOUT", f"上游服务响应超时: {error_message}"

    elif (
        isinstance(error, ServiceUnavailableError)
        or error_type == "ServiceUnavailableError"
    ):
        return 503, "SERVICE_UNAVAILABLE", f"服务暂时不可用: {error_message}"

    elif isinstance(error, InternalServerError) or error_type == "InternalServerError":
        return 500, "UPSTREAM_INTERNAL_ERROR", f"上游服务内部错误: {error_message}"

    elif isinstance(error, APIError) or error_type == "APIError":
        return 500, "API_ERROR", f"API调用失败: {error_message}"

    # 自定义代理错误
    elif isinstance(error, ProxyError):
        return error.status_code, error.code or "PROXY_ERROR", error.message

    # HTTP异常
    elif isinstance(error, HTTPException):
        return error.status_code, "HTTP_EXCEPTION", error.detail

    # 请求验证错误（Pydantic）
    elif isinstance(error, RequestValidationError):
        error_details = []
        for err in error.errors():
            field = " -> ".join(str(x) for x in err["loc"])
            error_details.append(f"{field}: {err['msg']}")
        return 422, "VALIDATION_ERROR", f"请求参数验证失败: {'; '.join(error_details)}"

    # 未知错误
    else:
        logger.error(f"未知错误类型: {error_type}, 消息: {error_message}")
        return 500, "INTERNAL_ERROR", f"内部服务器错误: {error_message}"


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    request_id: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    创建标准化的错误响应格式
    """
    error_response = {
        "error": {
            "code": error_code,
            "message": message,
            "type": "invalid_request_error" if status_code < 500 else "api_error",
        }
    }

    if request_id:
        error_response["error"]["request_id"] = request_id

    if model:
        error_response["error"]["model"] = model

    return error_response


async def handle_proxy_error(request: Request, exc: Exception) -> JSONResponse:
    """
    统一处理代理运行中捕获的异常，特别是那些由LiteLLM或其他依赖库抛出的异常
    """
    request_id = getattr(request.state, "request_id", "N/A")
    logger.error(
        f"❌ [{request_id}] 在处理请求 {request.method} {request.url.path} 时发生未捕获的异常:",
        exc_info=True,  # 完整记录异常堆栈
    )

    # 如果是我们的自定义错误，直接使用其属性
    if isinstance(exc, ProxyError):
        error_response = exc.to_error_response()
        status_code = exc.status_code
        return JSONResponse(
            status_code=status_code, content=error_response.model_dump()
        )

    # 对于其他所有未知异常，映射为标准的内部服务器错误
    # 这里可以根据 exc 的类型进行更细致的判断，例如处理 Pydantic 的 ValidationError
    # 或者 LiteLLM 的特定异常（如果它们有统一的基类）
    status_code = 500
    error_response = ErrorResponse(
        error=ErrorDetail(
            message="代理服务发生内部错误，请检查日志了解详情。",
            type="internal_server_error",
            code="proxy_internal_error",
        )
    )

    return JSONResponse(status_code=status_code, content=error_response.model_dump())


async def handle_streaming_error(
    error: Exception, original_model: str, request_id: Optional[str] = None
) -> str:
    """
    处理流式响应中的错误
    """
    status_code, error_code, message = map_litellm_error_to_http(error)

    # 记录错误
    if status_code >= 500:
        logger.error(f"流式响应错误 [{request_id}]: {message}", exc_info=True)
    else:
        logger.warning(f"流式响应错误 [{request_id}]: {message}")

    # 创建错误响应块
    error_chunk = {
        "id": f"chatcmpl-error-{request_id or 'unknown'}",
        "object": "chat.completion.chunk",
        "created": int(__import__("time").time()),
        "model": original_model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "error"}],
        "error": {"code": error_code, "message": message, "type": "api_error"},
    }

    import json

    return f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"


def setup_error_handlers(app: Any) -> Any:
    """
    为FastAPI应用设置全局错误处理器
    """

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """全局异常处理器"""
        return await handle_proxy_error(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Pydantic验证错误处理器"""
        return await handle_proxy_error(request, exc)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """HTTP异常处理器"""
        return await handle_proxy_error(request, exc)

    return app
