#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 代理模型测试脚本
测试 config.yaml 中配置的所有模型的回复效果, 并支持多模态、工具调用和流式测试。
"""

import yaml
import asyncio
from openai import AsyncOpenAI
import time
from typing import Dict, List
import json


class ModelTester:
    def __init__(self, config_path: str = "../config/external_llm/external_llm.yaml"):
        """初始化模型测试器"""
        # 加载配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 获取服务器配置
        server_config = self.config.get('server', {})
        host = server_config.get('host', 'localhost')
        port = 9000
        
        # 初始化 OpenAI 客户端，连接到本地代理服务
        self.client = AsyncOpenAI(
            base_url=f"http://{host}:{port}/v1",
            api_key="test-key"  # 代理服务的API密钥，如果不需要认证可以随意设置
        )
        
        # 获取模型列表
        self.models = list(self.config.get('provider_config', {}).keys())
        
        # 为不同测试筛选模型
        self.multimodal_models = [m for m in self.models if 'gemini' in m]
        self.tool_call_models = [m for m in self.models if 'sonnet' in m or 'deepseek' in m]
        self.streaming_test_models = [m for m in self.models if 'flash' in m or 'sonnet' in m or 'deepseek' in m][:2] # 选择最多2个模型进行流式测试

        # 测试问题
        self.test_questions = [
            "请用一句话解释什么是人工智能。"
        ]

        # 多模态测试
        self.multimodal_question = {
            "text": "这张图片里有什么？请用中文描述。",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
        }

        # 工具调用测试
        self.tool_call_question = "旧金山今天天气怎么样？"
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_current_weather",
                    "description": "Get the current weather in a given location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA",
                            },
                            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                        },
                        "required": ["location"],
                    },
                },
            }
        ]

    async def test_single_model(self, model_name: str, question: str) -> Dict:
        """测试单个模型（非流式）"""
        print(f"正在测试模型: {model_name}")
        
        try:
            start_time = time.time()
            
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": question}
                ],
                max_tokens=4096,
                temperature=0.7
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            result = {
                "id": response.id,
                "model": model_name,
                "question": question,
                "response": response.choices[0].message.content,
                "response_time": round(response_time, 2),
                "success": True,
                "error": None,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                }
            }
            
            print(f"✅ {model_name} - 响应时间: {response_time:.2f}秒")
            
        except Exception as e:
            result = {
                "id": None,
                "model": model_name,
                "question": question,
                "response": None,
                "response_time": 0,
                "success": False,
                "error": str(e),
                "usage": None
            }
            print(f"❌ {model_name} - 错误: {str(e)}")
        
        return result

    async def test_streaming_single_model(self, model_name: str, question: str) -> Dict:
        """测试单个模型的流式响应"""
        print(f"正在测试流式模型: {model_name}")
        
        start_time = time.time()
        time_to_first_token = None
        response_id = None
        full_response = ""
        
        try:
            stream = await self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": question}],
                max_tokens=4096,
                temperature=0.7,
                stream=True
            )
            
            async for chunk in stream:
                if time_to_first_token is None and chunk.choices and chunk.choices[0].delta.content:
                    time_to_first_token = time.time() - start_time
                
                if not response_id:
                    response_id = chunk.id

                if chunk.choices and chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
            
            end_time = time.time()
            response_time = end_time - start_time
            
            result = {
                "id": response_id,
                "model": model_name,
                "question": question,
                "response": full_response,
                "response_time": round(response_time, 2),
                "time_to_first_token": round(time_to_first_token, 2) if time_to_first_token else 0,
                "success": True,
                "error": None,
                "usage": None,  # Usage is not easily available in streaming mode with proxy
                "type": "streaming"
            }
            print(f"✅ {model_name} (流式) - TTFT: {result['time_to_first_token']:.2f}s, 总时间: {result['response_time']:.2f}s")
        except Exception as e:
            result = {
                "id": response_id,
                "model": model_name,
                "question": question,
                "response": None,
                "response_time": 0,
                "time_to_first_token": 0,
                "success": False,
                "error": str(e),
                "usage": None,
                "type": "streaming"
            }
            print(f"❌ {model_name} (流式) - 错误: {str(e)}")
        
        return result

    async def test_multimodal_single_model(self, model_name: str) -> Dict:
        """测试单个模型的多模态能力"""
        print(f"正在测试多模态模型: {model_name}")
        question = self.multimodal_question["text"]
        
        try:
            start_time = time.time()
            
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question},
                            {
                                "type": "image_url",
                                "image_url": {"url": self.multimodal_question["image_url"]},
                            },
                        ],
                    }
                ],
                max_tokens=4096,
                temperature=0.7
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            result = {
                "id": response.id,
                "model": model_name,
                "question": question,
                "image_url": self.multimodal_question["image_url"],
                "response": response.choices[0].message.content,
                "response_time": round(response_time, 2),
                "success": True,
                "error": None,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                }
            }
            
            print(f"✅ {model_name} - 响应时间: {response_time:.2f}秒")
            
        except Exception as e:
            result = {
                "id": None,
                "model": model_name,
                "question": question,
                "image_url": self.multimodal_question["image_url"],
                "response": None,
                "response_time": 0,
                "success": False,
                "error": str(e),
                "usage": None
            }
            print(f"❌ {model_name} - 错误: {str(e)}")
        
        return result

    async def test_tool_call_single_model(self, model_name: str) -> Dict:
        """测试单个模型的工具调用能力"""
        print(f"正在测试工具调用模型: {model_name}")
        question = self.tool_call_question
        
        try:
            start_time = time.time()
            
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": question}],
                tools=self.tools,
                tool_choice="auto",
                max_tokens=4096,
                temperature=0.7
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            result = {
                "id": response.id,
                "model": model_name,
                "question": question,
                "response_time": round(response_time, 2),
                "success": True,
                "error": None,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                "tool_calls": None
            }
            
            if tool_calls:
                result["response"] = f"请求工具调用: {tool_calls[0].function.name}"
                result["tool_calls"] = [{"name": tc.function.name, "arguments": tc.function.arguments} for tc in tool_calls]
                print(f"✅ {model_name} - 工具调用成功 in {response_time:.2f}s")
            else:
                result["response"] = response_message.content
                print(f"⚠️ {model_name} - 未返回工具调用 in {response_time:.2f}s")

        except Exception as e:
            result = {
                "id": None,
                "model": model_name,
                "question": question,
                "response": None,
                "response_time": 0,
                "success": False,
                "error": str(e),
                "usage": None,
                "tool_calls": None
            }
            print(f"❌ {model_name} - 错误: {str(e)}")
        
        return result

    async def _run_tests(self, test_name: str, test_function, models: List[str], *args) -> List[Dict]:
        """通用测试执行器"""
        if not models:
            print(f"\n跳过 {test_name} 测试：没有找到符合条件的模型。")
            return []
            
        print(f"\n{'='*20} 开始 {test_name} 测试 {'='*20}")
        print(f"待测模型: {', '.join(models)}")
        
        tasks = [test_function(model, *args) for model in models]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                processed_results.append({
                    "model": models[i], "success": False, "error": str(res)
                })
            else:
                processed_results.append(res)
        return processed_results

    def save_results_to_file(self, all_results: Dict[str, List[Dict]], filename: str = "test_results.json"):
        """保存结果到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 测试完成！详细结果已保存到文件: {filename}")
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")

    async def run_comprehensive_test(self):
        """运行综合测试"""
        print("🚀 开始 LLM 代理模型综合测试")
        print(f"总模型数量: {len(self.models)}")
        print(f"测试问题数量: {len(self.test_questions)}")
        print(f"模型列表: {', '.join(self.models)}")
        
        all_results = {
            "standard_text": [],
            "streaming_comparison": [],
            "multimodal": [],
            "tool_call": []
        }
        
        # 1. 标准文本测试
        for i, question in enumerate(self.test_questions, 1):
            print(f"\n📝 标准测试 问题 {i}/{len(self.test_questions)}: {question}")
            results = await self._run_tests(f"标准测试 (问题 {i})", self.test_single_model, self.models, question)
            all_results["standard_text"].extend(results)

        # 2. 流式 vs 非流式对比测试
        if self.streaming_test_models:
            question = self.test_questions[0]
            print(f"\n💨 开始流式/非流式对比测试 (问题: {question})")
            
            streaming_tasks = [self.test_streaming_single_model(model, question) for model in self.streaming_test_models]
            non_streaming_tasks = [self.test_single_model(model, question) for model in self.streaming_test_models]
            
            results = await asyncio.gather(*streaming_tasks, *non_streaming_tasks, return_exceptions=True)
            all_results["streaming_comparison"] = [res for res in results if not isinstance(res, Exception)]

        # 3. 多模态测试
        results = await self._run_tests("多模态", self.test_multimodal_single_model, self.multimodal_models)
        all_results["multimodal"] = results

        # 4. 工具调用测试
        results = await self._run_tests("工具调用", self.test_tool_call_single_model, self.tool_call_models)
        all_results["tool_call"] = results
        
        # 保存完整结果
        self.save_results_to_file(all_results)
        
        # 打印所有测试的最终摘要
        self.print_final_summary(all_results)

    def print_final_summary(self, all_results: Dict[str, List[Dict]]):
        """打印所有测试的最终摘要"""
        print("\n" + "🎯" * 40)
        print(" " * 30 + "最终测试摘要")
        print("🎯" * 40)

        for test_type, results in all_results.items():
            if not results:
                continue

            print(f"\n--- {test_type.replace('_', ' ').upper()} ---")
            successful_models = [r for r in results if r.get('success')]
            failed_models = [r for r in results if not r.get('success')]
            
            print(f"总测试数: {len(results)}")
            print(f"成功: {len(successful_models)}, 失败: {len(failed_models)}")

            if successful_models:
                # 按响应时间排序并打印Top 3
                sorted_models = sorted(successful_models, key=lambda x: x.get('response_time', float('inf')))
                print("性能最佳 (Top 3):")
                for i, r in enumerate(sorted_models[:3]):
                    model_info = f"{i+1}. {r['model']:<30} | 响应时间: {r['response_time']:.2f}s"
                    if 'time_to_first_token' in r:
                        model_info += f" | TTFT: {r.get('time_to_first_token', 0):.2f}s"
                    if 'tool_calls' in r and r['tool_calls']:
                         model_info += f" | 工具调用: ✅"
                    print(model_info)

            if failed_models:
                print("失败的模型:")
                for r in failed_models:
                    print(f"  - {r['model']}: {r.get('error', 'N/A')}")
        print("\n" + "🎯" * 40)


async def main():
    """主函数"""
    tester = ModelTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main()) 
