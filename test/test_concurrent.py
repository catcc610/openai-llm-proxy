#!/usr/bin/env python3
"""
LLM流式请求并发测试 - 首字符响应时间统计
50个并发流式请求，只统计第一个字符的响应时间
"""

import asyncio
import aiohttp
import time
import json
import csv
from datetime import datetime
from typing import List
from pydantic import BaseModel


class FirstTokenResult(BaseModel):
    """首字符响应结果"""
    task_id: int
    success: bool
    first_token_time: float  # 第一个字符的响应时间 (秒)
    first_char: str
    error_msg: str = ""
    status_code: int = 0


async def parse_sse_line(line: str) -> dict | None:
    """解析SSE行数据"""
    if not line.startswith("data: "):
        return None
    
    data_content = line[6:].strip()
    
    if data_content == "[DONE]":
        return {"done": True}
    
    try:
        return json.loads(data_content)
    except json.JSONDecodeError:
        return None


async def make_stream_request(session: aiohttp.ClientSession, url: str, task_id: int) -> FirstTokenResult:
    """发送单个流式请求，只获取第一个字符的时间"""
    start_time = time.time()
    
    payload = {
        "model": "deepseek-v3-0324", 
        "messages": [
            {"role": "user", "content": "请用中文回答：如何学习python 50个字"}
        ],
        "temperature": 0.7,
        "max_tokens": 200,
        "stream": True
    }
    
    try:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                return FirstTokenResult(
                    task_id=task_id,
                    success=False,
                    first_token_time=0.0,
                    first_char="",
                    error_msg=error_text,
                    status_code=response.status
                )
            
            # 只读取到第一个有效字符就停止
            async for line in response.content:
                line_str = line.decode('utf-8').strip()
                
                if not line_str:
                    continue
                    
                parsed = await parse_sse_line(line_str)
                if not parsed:
                    continue
                    
                if parsed.get("done"):
                    break
                
                choices = parsed.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    
                    if content and content.strip():  # 找到第一个非空字符
                        first_token_time = time.time() - start_time
                        first_char = content.strip()[0]
                        
                        return FirstTokenResult(
                            task_id=task_id,
                            success=True,
                            first_token_time=first_token_time,
                            first_char=first_char
                        )
            
            # 如果没有收到任何内容
            return FirstTokenResult(
                task_id=task_id,
                success=False,
                first_token_time=0.0,
                first_char="",
                error_msg="未收到任何内容"
            )
                
    except Exception as e:
        return FirstTokenResult(
            task_id=task_id,
            success=False,
            first_token_time=0.0,
            first_char="",
            error_msg=str(e)
        )


async def concurrent_stream_test(base_url: str = "http://localhost:9000"):
    """50个并发流式请求测试"""
    url = f"{base_url}/v1/chat/completions"
    concurrent_count = 50
    
    print(f"🌊 开始50个并发流式请求测试")
    print(f"📍 测试接口: {url}")
    print(f"🎯 目标: 只统计每个请求的第一个字符响应时间")
    print("-" * 60)
    
    # 创建HTTP会话
    connector = aiohttp.TCPConnector(limit=100)
    timeout = aiohttp.ClientTimeout(total=120)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        
        # 健康检查
        try:
            async with session.get(f"{base_url}/health") as response:
                if response.status != 200:
                    print("❌ 服务不可用")
                    return
                print("✅ 服务健康检查通过")
        except Exception as e:
            print(f"❌ 服务连接失败: {e}")
            return
        
        # 启动50个并发流式请求
        print(f"\n🚀 启动 {concurrent_count} 个并发流式请求...")
        start_time = time.time()
        
        tasks = [
            make_stream_request(session, url, task_id) 
            for task_id in range(1, concurrent_count + 1)
        ]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # 分析和记录结果
        await analyze_and_save_results(results, total_time)


async def analyze_and_save_results(results: List[FirstTokenResult], total_time: float):
    """分析结果并保存到文档"""
    
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    success_rate = len(successful) / len(results) * 100
    
    # 首字符响应时间统计
    if successful:
        first_token_times = [r.first_token_time for r in successful]
        avg_time = sum(first_token_times) / len(first_token_times)
        min_time = min(first_token_times)
        max_time = max(first_token_times)
        
        # 计算百分位数
        sorted_times = sorted(first_token_times)
        p50_time = sorted_times[len(sorted_times) // 2]
        p95_time = sorted_times[int(len(sorted_times) * 0.95)]
        p99_time = sorted_times[int(len(sorted_times) * 0.99)]
    else:
        avg_time = min_time = max_time = p50_time = p95_time = p99_time = 0
    
    # 控制台输出
    print(f"\n📊 测试结果:")
    print(f"🔢 并发数: 50")
    print(f"⏱️  总耗时: {total_time:.3f}s")
    print(f"✅ 成功率: {success_rate:.1f}% ({len(successful)}/{len(results)})")
    
    print(f"\n⚡ 首字符响应时间统计:")
    print(f"   平均: {avg_time:.3f}s")
    print(f"   最小: {min_time:.3f}s") 
    print(f"   最大: {max_time:.3f}s")
    print(f"   P50: {p50_time:.3f}s")
    print(f"   P95: {p95_time:.3f}s")
    print(f"   P99: {p99_time:.3f}s")
    
    if failed:
        print(f"\n❌ 失败请求: {len(failed)}")
    
    # 保存详细结果到CSV
    await save_results_to_csv(results, total_time)
    
    # 保存汇总报告到文本文件
    await save_summary_report(results, total_time, avg_time, min_time, max_time, p95_time, p99_time, success_rate)


async def save_results_to_csv(results: List[FirstTokenResult], total_time: float):
    """保存详细结果到CSV文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"llm_stream_test_{timestamp}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # 写入表头
        writer.writerow([
            'Task_ID', 'Success', 'First_Token_Time_Seconds', 
            'First_Char', 'Error_Message', 'Status_Code'
        ])
        
        # 写入数据
        for result in results:
            writer.writerow([
                result.task_id,
                result.success,
                f"{result.first_token_time:.4f}",
                result.first_char,
                result.error_msg,
                result.status_code
            ])
    
    print(f"📄 详细结果已保存至: {filename}")


async def save_summary_report(results: List[FirstTokenResult], total_time: float, 
                            avg_time: float, min_time: float, max_time: float,
                            p95_time: float, p99_time: float, success_rate: float):
    """保存汇总报告到文本文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"llm_stream_summary_{timestamp}.txt"
    
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("LLM流式请求并发测试报告\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"并发数: 50\n")
        f.write(f"总耗时: {total_time:.3f}秒\n")
        f.write(f"成功率: {success_rate:.1f}% ({len(successful)}/{len(results)})\n\n")
        
        f.write("首字符响应时间统计:\n")
        f.write(f"  平均时间: {avg_time:.3f}秒\n")
        f.write(f"  最小时间: {min_time:.3f}秒\n")
        f.write(f"  最大时间: {max_time:.3f}秒\n")
        f.write(f"  P95时间: {p95_time:.3f}秒\n")
        f.write(f"  P99时间: {p99_time:.3f}秒\n\n")
        
        if failed:
            f.write(f"失败请求详情:\n")
            for fail in failed:
                f.write(f"  Task {fail.task_id}: {fail.error_msg}\n")
        
        f.write(f"\n成功请求的首字符:\n")
        first_chars = [r.first_char for r in successful]
        f.write(f"  收到的首字符: {''.join(first_chars)}\n")
    
    print(f"📋 汇总报告已保存至: {filename}")


async def main():
    """主函数"""
    await concurrent_stream_test()


if __name__ == "__main__":
    asyncio.run(main())