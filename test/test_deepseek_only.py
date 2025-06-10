"""
简化的DeepSeek模型测试脚本
只测试火山引擎的DeepSeek模型
"""

import asyncio
import time
from typing import Optional

try:
    import openai
    from openai import OpenAI, AsyncOpenAI
except ImportError:
    print("❌ 未安装openai包，请运行: uv add openai")
    exit(1)


# 配置
BASE_URL = "http://localhost:9000/v1"
API_KEY = "dummy"
MODEL_NAME = "deepseek-v3-0324"
TIMEOUT = 30


class DeepSeekTester:
    """DeepSeek模型测试器"""
    
    def __init__(self):
        self.client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=TIMEOUT)
        self.async_client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=TIMEOUT)
    
    def test_basic_chat(self) -> bool:
        """测试基本聊天功能"""
        print("🧪 测试基本聊天...")
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是一个有用的AI助手，请用中文回答。"},
                    {"role": "user", "content": "介绍一下你自己，不超过100字。"}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            response_time = time.time() - start_time
            content = response.choices[0].message.content or ""
            
            print(f"✅ 基本聊天测试成功 ({response_time:.2f}s)")
            print(f"📝 回复内容: {content[:100]}...")
            return True
            
        except Exception as e:
            print(f"❌ 基本聊天测试失败: {e}")
            return False
    
    def test_streaming_chat(self) -> bool:
        """测试流式聊天"""
        print("\n🧪 测试流式聊天...")
        start_time = time.time()
        
        try:
            stream = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": "写一个Python函数计算斐波那契数列"}],
                max_tokens=300,
                stream=True
            )
            
            content_parts = []
            first_token_time = None
            
            for chunk in stream:
                if first_token_time is None:
                    first_token_time = time.time()
                    
                if chunk.choices[0].delta.content:
                    content_parts.append(chunk.choices[0].delta.content)
            
            total_time = time.time() - start_time
            full_content = "".join(content_parts)
            
            print(f"✅ 流式聊天测试成功 ({total_time:.2f}s)")
            print(f"📝 生成内容长度: {len(full_content)} 字符")
            return True
            
        except Exception as e:
            print(f"❌ 流式聊天测试失败: {e}")
            return False
    
    async def test_async_chat(self) -> bool:
        """测试异步聊天"""
        print("\n🧪 测试异步聊天...")
        start_time = time.time()
        
        try:
            response = await self.async_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": "用一句话解释什么是人工智能"}],
                max_tokens=100
            )
            
            response_time = time.time() - start_time
            content = response.choices[0].message.content or ""
            
            print(f"✅ 异步聊天测试成功 ({response_time:.2f}s)")
            print(f"📝 回复内容: {content}")
            return True
            
        except Exception as e:
            print(f"❌ 异步聊天测试失败: {e}")
            return False
    
    async def test_concurrent_requests(self, num_requests: int = 3) -> bool:
        """测试并发请求"""
        print(f"\n🧪 测试并发请求 ({num_requests}个)...")
        start_time = time.time()
        
        try:
            tasks = []
            for i in range(num_requests):
                task = self.async_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": f"这是第{i+1}个并发请求，请简单回复"}],
                    max_tokens=50
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            successful_responses = [r for r in responses if not isinstance(r, Exception)]
            
            total_time = time.time() - start_time
            success_rate = len(successful_responses) / num_requests * 100
            
            print(f"✅ 并发请求测试完成 ({total_time:.2f}s)")
            print(f"📊 成功率: {success_rate:.1f}% ({len(successful_responses)}/{num_requests})")
            
            return len(successful_responses) == num_requests
            
        except Exception as e:
            print(f"❌ 并发请求测试失败: {e}")
            return False
    
    def test_model_list(self) -> bool:
        """测试模型列表"""
        print("\n🧪 测试模型列表...")
        
        try:
            models = self.client.models.list()
            model_names = [model.id for model in models.data]
            
            print(f"✅ 模型列表获取成功")
            print(f"📝 可用模型: {model_names}")
            
            if MODEL_NAME in model_names:
                print(f"✅ 目标模型 {MODEL_NAME} 在列表中")
                return True
            else:
                print(f"❌ 目标模型 {MODEL_NAME} 不在列表中")
                return False
                
        except Exception as e:
            print(f"❌ 模型列表测试失败: {e}")
            return False


async def main():
    """主测试函数"""
    print("🚀 DeepSeek模型测试开始")
    print("=" * 50)
    print(f"🎯 测试模型: {MODEL_NAME}")
    print(f"🔗 服务地址: {BASE_URL}")
    print("=" * 50)
    
    tester = DeepSeekTester()
    results = []
    
    try:
        # 运行所有测试
        results.append(("模型列表", tester.test_model_list()))
        results.append(("基本聊天", tester.test_basic_chat()))
        results.append(("流式聊天", tester.test_streaming_chat()))
        results.append(("异步聊天", await tester.test_async_chat()))
        results.append(("并发请求", await tester.test_concurrent_requests(3)))
        
        # 统计结果
        total_tests = len(results)
        passed_tests = sum(1 for _, success in results if success)
        
        print("\n" + "=" * 50)
        print("📊 测试结果总结")
        print("=" * 50)
        print(f"总测试数: {total_tests}")
        print(f"通过数: {passed_tests} ✅")
        print(f"失败数: {total_tests - passed_tests} ❌")
        print(f"成功率: {passed_tests/total_tests*100:.1f}%")
        
        # 显示失败的测试
        failed_tests = [name for name, success in results if not success]
        if failed_tests:
            print(f"\n❌ 失败的测试: {', '.join(failed_tests)}")
        else:
            print(f"\n🎉 所有测试都通过了！")
        
    except Exception as e:
        print(f"\n💥 测试运行出错: {e}")
    finally:
        await tester.async_client.close()


if __name__ == "__main__":
    asyncio.run(main()) 