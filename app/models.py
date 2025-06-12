"""
OpenAI API兼容的Pydantic模型定义
严格遵循OpenAI API v1/chat/completions格式
"""

from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class MessageRole(str, Enum):
    """消息角色枚举 - 支持标准角色和部分提供商扩展角色"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ImageUrl(BaseModel):
    """图片URL模型"""

    url: str = Field(..., description="图片URL或base64编码")
    detail: Optional[Literal["low", "high", "auto"]] = Field(
        "auto", description="图片处理精度"
    )


class ContentPart(BaseModel):
    """消息内容部分模型 - 支持文本和图片"""

    type: Literal["text", "image_url"] = Field(..., description="内容类型")
    text: str | None = Field(None, description="文本内容")
    image_url: ImageUrl | None = Field(None, description="图片URL信息")


class FunctionCall(BaseModel):
    """函数调用模型"""

    name: str = Field(..., description="函数名称")
    arguments: str = Field(..., description="函数参数（JSON字符串）")


class ToolCall(BaseModel):
    """工具调用模型"""

    id: str = Field(..., description="工具调用ID")
    type: Literal["function"] = Field("function", description="工具类型")
    function: FunctionCall = Field(..., description="函数调用信息")


class ChatMessage(BaseModel):
    """聊天消息模型 - 支持多模态内容"""

    role: MessageRole = Field(..., description="消息的角色")
    content: str | list[ContentPart] | None = Field(
        None, description="消息内容 - 可以是字符串或多模态内容列表"
    )
    name: str | None = Field(None, description="消息发送者的名称")
    function_call: FunctionCall | None = Field(None, description="函数调用信息")
    tool_calls: list[ToolCall] | None = Field(None, description="工具调用信息")
    tool_call_id: str | None = Field(None, description="工具调用ID")


class Function(BaseModel):
    """函数定义模型"""

    name: str = Field(..., description="函数名称")
    description: Optional[str] = Field(None, description="函数描述")
    parameters: Optional[Dict[str, Any]] = Field(None, description="函数参数schema")


class Tool(BaseModel):
    """工具定义模型"""

    type: Literal["function"] = Field("function", description="工具类型")
    function: Function = Field(..., description="函数定义")


class ResponseFormat(BaseModel):
    """响应格式模型"""

    type: Literal["text", "json_object"] = Field("text", description="响应格式类型")


class StreamOptions(BaseModel):
    """流式选项模型"""

    include_usage: bool = Field(
        False, description="是否在流式响应的最后一个chunk中包含使用量信息"
    )


class ChatCompletionRequest(BaseModel):
    """聊天完成请求模型"""

    model_config = ConfigDict(extra="allow")  # 允许额外字段以兼容更多提供商参数

    # 必需参数
    model: str = Field(..., description="使用的模型名称", min_length=1)
    messages: List[ChatMessage] = Field(..., description="对话消息列表", min_length=1)

    # 可选参数
    frequency_penalty: Optional[float] = Field(
        None, ge=-2.0, le=2.0, description="频率惩罚"
    )
    logit_bias: Optional[Dict[str, float]] = Field(None, description="logit偏置")
    logprobs: Optional[bool] = Field(None, description="是否返回logprobs")
    top_logprobs: Optional[int] = Field(
        None, ge=0, le=20, description="返回的top logprobs数量"
    )
    max_tokens: Optional[int] = Field(None, ge=1, description="最大生成token数")
    n: Optional[int] = Field(1, ge=1, le=128, description="生成的选择数量")
    presence_penalty: Optional[float] = Field(
        None, ge=-2.0, le=2.0, description="存在惩罚"
    )
    response_format: Optional[ResponseFormat] = Field(None, description="响应格式")
    seed: Optional[int] = Field(None, description="随机种子")
    stop: Optional[Union[str, List[str]]] = Field(None, description="停止词")
    stream: Optional[bool] = Field(False, description="是否流式返回")
    stream_options: Optional[StreamOptions] = Field(None, description="流式选项")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="温度参数")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="核采样参数")
    tools: Optional[List[Tool]] = Field(None, description="可用工具列表")
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="工具选择策略"
    )
    user: str | None = Field(None, description="用户标识符")

    # 扩展参数（支持更多提供商）
    repetition_penalty: float | None = Field(
        None, ge=0.0, le=2.0, description="重复惩罚"
    )
    top_k: int | None = Field(None, ge=0, description="Top-K 采样参数")

    # 函数调用（已弃用，但保持兼容性）
    functions: list[Function] | None = Field(None, description="可用函数列表（已弃用）")
    function_call: str | dict[str, Any] | None = Field(
        None, description="函数调用策略（已弃用）"
    )

    def to_litellm_params(self, litellm_model: str) -> dict[str, Any]:
        """将请求转换为LiteLLM参数格式，使用model_dump简化并确保可扩展性"""

        # 使用 model_dump 获取所有已设置的非None值
        # exclude_defaults=True 确保了只有用户明确设置的参数才会被传递
        params: dict[str, Any] = self.model_dump(exclude_unset=True, exclude_none=True)

        # 强制设置/覆盖核心参数
        params["model"] = litellm_model

        # LiteLLM 需要消息是纯字典列表
        params["messages"] = [
            msg.model_dump(exclude_none=True) for msg in self.messages
        ]

        # 移除本方法不需要传递给LiteLLM的自定义字段
        # (如果未来添加了更多仅用于本代理的字段，可在此处添加)

        return params


# 错误响应模型
class ErrorDetail(BaseModel):
    """错误详情模型"""

    message: str = Field(..., description="错误消息")
    type: str = Field(..., description="错误类型")
    param: Optional[str] = Field(None, description="相关参数")
    code: Optional[str] = Field(None, description="错误代码")


class ErrorResponse(BaseModel):
    """错误响应模型"""

    error: ErrorDetail = Field(..., description="错误详情")
