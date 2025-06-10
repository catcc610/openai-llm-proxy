"""
中间件模块
处理请求ID生成、日志记录等
"""

import uuid
import time
import logging
from typing import Callable, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求生成唯一的请求ID"""

    def __init__(self, app: Any, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成或获取请求ID
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())

        # 将请求ID存储到request.state中
        request.state.request_id = request_id

        # 记录请求开始
        start_time = time.time()
        logger.info(f"🔍 [{request_id}] {request.method} {request.url.path} - 开始处理")

        try:
            # 处理请求
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 添加请求ID到响应头
            response.headers[self.header_name] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            # 记录请求完成
            logger.info(
                f"✅ [{request_id}] {response.status_code} - 处理完成 ({process_time:.3f}s)"
            )

            return response

        except Exception as e:
            # 计算处理时间
            process_time = time.time() - start_time

            # 记录错误
            logger.error(
                f"❌ [{request_id}] 请求处理失败 ({process_time:.3f}s): {str(e)}"
            )

            # 重新抛出异常，让错误处理器处理
            raise


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    def __init__(
        self, app: Any, log_body: bool = False, max_body_size: int = 1024
    ) -> None:
        super().__init__(app)
        self.log_body = log_body
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")

        # 记录请求详情
        logger.debug(f"📥 [{request_id}] 请求详情:")
        logger.debug(f"   - 方法: {request.method}")
        logger.debug(f"   - 路径: {request.url.path}")
        logger.debug(f"   - 查询参数: {dict(request.query_params)}")
        logger.debug(f"   - 用户代理: {request.headers.get('user-agent', 'unknown')}")
        logger.debug(
            f"   - 客户端IP: {request.client.host if request.client else 'unknown'}"
        )

        # 记录请求体（如果启用且为POST/PUT请求）
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) <= self.max_body_size:
                    logger.debug(
                        f"   - 请求体: {body.decode('utf-8', errors='ignore')}"
                    )
                else:
                    logger.debug(f"   - 请求体: (太大，{len(body)} 字节)")
            except Exception as e:
                logger.debug(f"   - 请求体读取失败: {str(e)}")

        # 处理请求
        response = await call_next(request)

        # 记录响应详情
        logger.debug(f"📤 [{request_id}] 响应详情:")
        logger.debug(f"   - 状态码: {response.status_code}")
        logger.debug(
            f"   - 内容类型: {response.headers.get('content-type', 'unknown')}"
        )

        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """自定义CORS中间件（如果需要更精细的控制）"""

    def __init__(
        self,
        app: Any,
        allow_origins: list[str] | None = None,
        allow_methods: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 处理预检请求
        if request.method == "OPTIONS":
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(
                self.allow_methods
            )
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-Request-ID"
            )
            return response

        # 处理普通请求
        response = await call_next(request)

        # 添加CORS头
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Request-ID"
        )

        return response
