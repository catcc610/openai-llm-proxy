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


class ChatMessage(BaseModel):
    """聊天消息模型"""

    role: MessageRole = Field(..., description="消息的角色")
    content: Optional[str] = Field(None, description="消息内容")
    name: Optional[str] = Field(None, description="消息发送者的名称")
    function_call: Optional[Dict[str, Any]] = Field(None, description="函数调用信息")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="工具调用信息")
    tool_call_id: Optional[str] = Field(None, description="工具调用ID")


class FunctionCall(BaseModel):
    """函数调用模型"""

    name: str = Field(..., description="函数名称")
    arguments: str = Field(..., description="函数参数（JSON字符串）")


class ToolCall(BaseModel):
    """工具调用模型"""

    id: str = Field(..., description="工具调用ID")
    type: Literal["function"] = Field("function", description="工具类型")
    function: FunctionCall = Field(..., description="函数调用信息")


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
    user: Optional[str] = Field(None, description="用户标识符")

    # 扩展参数（支持更多提供商）
    repetition_penalty: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="重复惩罚"
    )
    top_k: Optional[int] = Field(None, ge=0, description="Top-K 采样参数")

    # 函数调用（已弃用，但保持兼容性）
    functions: Optional[List[Function]] = Field(
        None, description="可用函数列表（已弃用）"
    )
    function_call: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="函数调用策略（已弃用）"
    )

    def to_litellm_params(self, litellm_model: str) -> Dict[str, Any]:
        """将请求转换为LiteLLM参数格式，自动处理所有字段"""
        # 基础参数
        params: Dict[str, Any] = {
            "model": litellm_model,
            "messages": [msg.model_dump() for msg in self.messages],
        }

        # 自动添加所有非None的字段
        field_mappings: Dict[str, Any] = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stream": self.stream,
            "stop": self.stop,
            "user": self.user,
            "seed": self.seed,
            "logit_bias": self.logit_bias,
            "logprobs": self.logprobs,
            "top_logprobs": self.top_logprobs,
            "n": self.n,
            "repetition_penalty": self.repetition_penalty,
            "top_k": self.top_k,
        }

        # 添加非None的简单字段
        for key, value in field_mappings.items():
            if value is not None:
                params[key] = value

        # 处理复杂对象字段
        if self.tools:
            params["tools"] = [tool.model_dump() for tool in self.tools]
        if self.tool_choice:
            params["tool_choice"] = self.tool_choice
        if self.response_format:
            params["response_format"] = self.response_format.model_dump()
        if self.stream_options:
            params["stream_options"] = self.stream_options.model_dump()
        if self.functions:
            params["functions"] = [func.model_dump() for func in self.functions]
        if self.function_call:
            params["function_call"] = self.function_call

        return params


class LogProbs(BaseModel):
    """LogProbs模型"""

    content: Optional[List[Dict[str, Any]]] = Field(None, description="内容的logprobs")


class ChoiceFinishReason(str, Enum):
    """选择完成原因枚举"""

    STOP = "stop"
    LENGTH = "length"
    FUNCTION_CALL = "function_call"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"


class Choice(BaseModel):
    """选择模型"""

    index: int = Field(..., description="选择的索引")
    message: ChatMessage = Field(..., description="助手的回复消息")
    logprobs: Optional[LogProbs] = Field(None, description="logprobs信息")
    finish_reason: Optional[ChoiceFinishReason] = Field(None, description="完成原因")


class Usage(BaseModel):
    """使用统计模型"""

    prompt_tokens: int = Field(..., description="提示token数量")
    completion_tokens: int = Field(..., description="完成token数量")
    total_tokens: int = Field(..., description="总token数量")


class ChatCompletionResponse(BaseModel):
    """聊天完成响应模型"""

    id: str = Field(..., description="响应ID")
    object: Literal["chat.completion"] = Field(
        "chat.completion", description="对象类型"
    )
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型名称")
    choices: List[Choice] = Field(..., description="选择列表")
    usage: Optional[Usage] = Field(None, description="使用统计")
    system_fingerprint: Optional[str] = Field(None, description="系统指纹")


# 流式响应相关模型
class ChoiceDelta(BaseModel):
    """流式响应的增量选择模型"""

    role: Optional[MessageRole] = Field(None, description="消息角色")
    content: Optional[str] = Field(None, description="内容增量")
    function_call: Optional[Dict[str, Any]] = Field(None, description="函数调用增量")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="工具调用增量")


class StreamChoice(BaseModel):
    """流式响应选择模型"""

    index: int = Field(..., description="选择的索引")
    delta: ChoiceDelta = Field(..., description="消息增量")
    logprobs: Optional[LogProbs] = Field(None, description="logprobs信息")
    finish_reason: Optional[ChoiceFinishReason] = Field(None, description="完成原因")


class ChatCompletionStreamResponse(BaseModel):
    """流式聊天完成响应模型"""

    id: str = Field(..., description="响应ID")
    object: Literal["chat.completion.chunk"] = Field(
        "chat.completion.chunk", description="对象类型"
    )
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型名称")
    choices: List[StreamChoice] = Field(..., description="流式选择列表")
    usage: Optional[Usage] = Field(
        None,
        description="使用统计（仅在stream_options.include_usage=true时的最后一个chunk中返回）",
    )
    system_fingerprint: Optional[str] = Field(None, description="系统指纹")


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
