#!/usr/bin/env python3
"""
LLM代理服务模型测试脚本
测试配置文件中所有模型的各种功能：流式、非流式、工具调用、多模态
"""

import asyncio
import json
import time
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from openai import OpenAI
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """测试结果数据类"""

    model: str
    test_type: str
    success: bool
    response_time: float
    error: Optional[str] = None
    response_preview: Optional[str] = None


class ModelTester:
    """模型测试器"""

    def __init__(
        self, base_url: str = "http://localhost:9000/v1", api_key: str = "dummy"
    ):
        """初始化测试器"""
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.results: List[TestResult] = []

        # 不支持多模态的模型列表
        self.no_multimodal_models = {"deepseek-v3-0324"}

        # 测试用的图片
        # 1. 真实图片URL
        self.test_image_url = (
            "https://mag.npf.co.jp/wp-content/uploads/2023/10/27750021_m.jpg"
        )

        # 2. 黄色图片的base64 (100x100像素的黄色PNG)
        self.yellow_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = Path("../external_llm/external_llm.yaml")
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.info(
            f"✅ 加载配置文件成功，找到 {len(config.get('model_config', {}))} 个模型"
        )
        return config

    def get_test_models(self) -> List[str]:
        """获取需要测试的模型列表"""
        config = self.load_config()
        models = list(config.get("model_config", {}).keys())
        logger.info(f"📋 待测试模型: {', '.join(models)}")
        return models

    async def test_basic_chat(self, model: str) -> TestResult:
        """测试基础聊天功能（非流式）"""
        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": "请简单介绍一下你自己，不超过50字"}
                ],
                max_tokens=100,
                temperature=0.7,
            )

            response_time = time.time() - start_time
            content = response.choices[0].message.content

            return TestResult(
                model=model,
                test_type="基础聊天",
                success=True,
                response_time=response_time,
                response_preview=content[:100] if content else "无内容",
            )

        except Exception as e:
            return TestResult(
                model=model,
                test_type="基础聊天",
                success=False,
                response_time=time.time() - start_time,
                error=str(e),
            )

    async def test_streaming_chat(self, model: str) -> TestResult:
        """测试流式聊天功能"""
        start_time = time.time()

        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "请用一句话描述人工智能的未来"}],
                max_tokens=100,
                temperature=0.7,
                stream=True,
            )

            content_parts = []
            first_chunk_time = None

            for chunk in stream:
                if first_chunk_time is None:
                    first_chunk_time = time.time() - start_time

                if chunk.choices[0].delta.content:
                    content_parts.append(chunk.choices[0].delta.content)

            total_time = time.time() - start_time
            full_content = "".join(content_parts)

            return TestResult(
                model=model,
                test_type="流式聊天",
                success=True,
                response_time=total_time,
                response_preview=f"首Token: {first_chunk_time:.2f}s | 内容: {full_content[:50]}...",
            )

        except Exception as e:
            return TestResult(
                model=model,
                test_type="流式聊天",
                success=False,
                response_time=time.time() - start_time,
                error=str(e),
            )

    async def test_tool_calling(self, model: str) -> TestResult:
        """测试工具调用功能"""
        start_time = time.time()

        # 定义测试工具
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "获取指定城市的天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "城市名称"},
                            "unit": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"],
                                "description": "温度单位",
                            },
                        },
                        "required": ["city"],
                    },
                },
            }
        ]

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "请帮我查询北京的天气"}],
                tools=tools,
                tool_choice="auto",
                max_tokens=200,
            )

            response_time = time.time() - start_time
            message = response.choices[0].message

            if message.tool_calls:
                tool_call = message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = tool_call.function.arguments

                return TestResult(
                    model=model,
                    test_type="工具调用",
                    success=True,
                    response_time=response_time,
                    response_preview=f"调用函数: {function_name}({function_args})",
                )
            else:
                return TestResult(
                    model=model,
                    test_type="工具调用",
                    success=False,
                    response_time=response_time,
                    error="模型未调用工具",
                )

        except Exception as e:
            return TestResult(
                model=model,
                test_type="工具调用",
                success=False,
                response_time=time.time() - start_time,
                error=str(e),
            )

    async def test_multimodal(self, model: str) -> TestResult:
        """测试多模态功能"""
        # 检查模型是否支持多模态
        if model in self.no_multimodal_models:
            return TestResult(
                model=model,
                test_type="多模态",
                success=False,
                response_time=0.0,
                error="模型不支持多模态功能",
            )

        start_time = time.time()

        try:
            # 测试1: 使用真实图片URL
            response1 = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请描述这张图片的内容，包括主要元素和场景。",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": self.test_image_url,
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=200,
            )

            # 测试2: 使用base64黄色图片
            response2 = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "这张图片是什么颜色？请简单描述。",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{self.yellow_image_base64}",
                                    "detail": "low",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=100,
            )

            response_time = time.time() - start_time

            # 合并两个测试的结果
            content1 = response1.choices[0].message.content or ""
            content2 = response2.choices[0].message.content or ""

            combined_preview = (
                f"URL图片: {content1[:80]}... | Base64图片: {content2[:80]}..."
            )

            return TestResult(
                model=model,
                test_type="多模态",
                success=True,
                response_time=response_time,
                response_preview=combined_preview,
            )

        except Exception as e:
            return TestResult(
                model=model,
                test_type="多模态",
                success=False,
                response_time=time.time() - start_time,
                error=str(e),
            )

    async def test_model_comprehensive(self, model: str) -> List[TestResult]:
        """对单个模型进行全面测试"""
        logger.info(f"🧪 开始测试模型: {model}")

        # 并发执行所有测试
        tasks = [
            self.test_basic_chat(model),
            self.test_streaming_chat(model),
            self.test_tool_calling(model),
            self.test_multimodal(model),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                test_types = ["基础聊天", "流式聊天", "工具调用", "多模态"]
                processed_results.append(
                    TestResult(
                        model=model,
                        test_type=test_types[i],
                        success=False,
                        response_time=0.0,
                        error=f"测试异常: {str(result)}",
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def print_results(self, results: List[TestResult]) -> None:
        """打印测试结果"""
        print("\n" + "=" * 80)
        print("🧪 LLM代理服务模型测试报告")
        print("=" * 80)

        # 按模型分组
        models = {}
        for result in results:
            if result.model not in models:
                models[result.model] = []
            models[result.model].append(result)

        # 统计信息
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success)

        print("\n📊 总体统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功数: {successful_tests}")
        print(f"   失败数: {total_tests - successful_tests}")
        print(f"   成功率: {successful_tests / total_tests * 100:.1f}%")

        # 详细结果
        for model, model_results in models.items():
            print(f"\n🤖 模型: {model}")
            print("-" * 60)

            for result in model_results:
                status = "✅" if result.success else "❌"
                print(
                    f"   {status} {result.test_type:<12} | "
                    f"耗时: {result.response_time:.2f}s"
                )

                if result.success and result.response_preview:
                    print(f"      📝 响应: {result.response_preview}")
                elif not result.success and result.error:
                    print(f"      ⚠️  错误: {result.error}")

        print("\n" + "=" * 80)

    def save_results_json(
        self, results: List[TestResult], filename: str = "test_results.json"
    ) -> None:
        """保存测试结果为JSON文件"""
        results_data = []
        for result in results:
            results_data.append(
                {
                    "model": result.model,
                    "test_type": result.test_type,
                    "success": result.success,
                    "response_time": result.response_time,
                    "error": result.error,
                    "response_preview": result.response_preview,
                    "timestamp": time.time(),
                }
            )

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 测试结果已保存到: {filename}")

    async def run_all_tests(self) -> None:
        """运行所有模型的全面测试"""
        try:
            models = self.get_test_models()
            if not models:
                logger.error("❌ 没有找到需要测试的模型")
                return

            logger.info(f"🚀 开始测试 {len(models)} 个模型...")

            all_results = []
            for model in models:
                try:
                    model_results = await self.test_model_comprehensive(model)
                    all_results.extend(model_results)

                    # 模型间添加短暂延迟，避免请求过于频繁
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"❌ 测试模型 {model} 时发生异常: {e}")

            # 输出结果
            self.print_results(all_results)
            self.save_results_json(all_results)

            logger.info("✅ 所有测试完成")

        except Exception as e:
            logger.error(f"❌ 测试过程中发生异常: {e}")


async def main():
    """主函数"""
    print("🧪 LLM代理服务模型测试工具")
    print("=" * 50)

    # 检查服务是否运行
    tester = ModelTester()
    try:
        # 简单的健康检查
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:9000/health", timeout=5.0)
            if response.status_code != 200:
                logger.error("❌ LLM代理服务未正常运行，请先启动服务")
                return
    except Exception as e:
        logger.error(f"❌ 无法连接到LLM代理服务: {e}")
        logger.info("💡 请确保服务已启动: python main.py")
        return

    logger.info("✅ LLM代理服务连接正常")

    # 运行测试
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
