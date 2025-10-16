import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient


class TestBasicPerformance:
    """测试基本性能指标（不依赖数据库）"""
    
    def test_health_check_latency(self, e2e_client: TestClient):
        """测试健康检查端点的延迟"""
        # 预热
        for _ in range(5):
            e2e_client.get("/health")
        
        # 测量延迟
        latencies = []
        for _ in range(100):
            start_time = time.time()
            response = e2e_client.get("/health")
            end_time = time.time()
            
            if response.status_code == 200:
                latency = (end_time - start_time) * 1000  # 转换为毫秒
                latencies.append(latency)
        
        # 分析结果
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        p99_latency = sorted(latencies)[int(0.99 * len(latencies))]
        
        print(f"\n健康检查性能指标:")
        print(f"平均延迟: {avg_latency:.2f}ms")
        print(f"中位数延迟: {median_latency:.2f}ms") 
        print(f"P95延迟: {p95_latency:.2f}ms")
        print(f"P99延迟: {p99_latency:.2f}ms")
        
        # 性能断言 - 健康检查应该很快
        assert avg_latency < 50, f"健康检查平均延迟过高: {avg_latency:.2f}ms"
        assert p95_latency < 100, f"健康检查P95延迟过高: {p95_latency:.2f}ms"
    
    def test_concurrent_health_checks(self, e2e_client: TestClient):
        """测试并发健康检查性能"""
        
        def make_health_request():
            start_time = time.time()
            response = e2e_client.get("/health")
            end_time = time.time()
            return {
                "status_code": response.status_code,
                "latency": (end_time - start_time) * 1000,
                "success": response.status_code == 200
            }
        
        # 并发测试
        concurrent_levels = [1, 5, 10]
        
        for concurrency in concurrent_levels:
            print(f"\n测试并发级别: {concurrency}")
            
            results = []
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                # 每个并发级别执行50次请求
                futures = []
                for _ in range(50):
                    for _ in range(concurrency):
                        future = executor.submit(make_health_request)
                        futures.append(future)
                
                for future in as_completed(futures):
                    results.append(future.result())
            
            total_time = time.time() - start_time
            
            # 分析结果
            successful_requests = [r for r in results if r["success"]]
            latencies = [r["latency"] for r in successful_requests]
            
            if latencies:
                avg_latency = statistics.mean(latencies)
                throughput = len(successful_requests) / total_time
                
                print(f"成功请求数: {len(successful_requests)}/{len(results)}")
                print(f"平均延迟: {avg_latency:.2f}ms")
                print(f"吞吐量: {throughput:.2f} requests/sec")
                
                # 性能断言
                assert len(successful_requests) / len(results) > 0.95, "成功率应该超过95%"
                assert avg_latency < 200, f"并发{concurrency}时平均延迟过高: {avg_latency:.2f}ms"
    
    def test_openapi_performance(self, e2e_client: TestClient):
        """测试OpenAPI文档生成性能"""
        # 预热
        for _ in range(3):
            e2e_client.get("/openapi.json")
        
        # 测量延迟
        latencies = []
        for _ in range(20):  # OpenAPI生成比较重，测试少一些次数
            start_time = time.time()
            response = e2e_client.get("/openapi.json")
            end_time = time.time()
            
            if response.status_code == 200:
                latency = (end_time - start_time) * 1000  # 转换为毫秒
                latencies.append(latency)
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            max_latency = max(latencies)
            
            print(f"\nOpenAPI文档性能:")
            print(f"平均延迟: {avg_latency:.2f}ms")
            print(f"最大延迟: {max_latency:.2f}ms")
            
            # OpenAPI生成可以稍微慢一些，但不应该太慢
            assert avg_latency < 500, f"OpenAPI生成平均延迟过高: {avg_latency:.2f}ms"
    
    def test_invalid_request_performance(self, e2e_client: TestClient):
        """测试无效请求的处理性能"""
        # 测试404错误处理性能
        latencies_404 = []
        for _ in range(50):
            start_time = time.time()
            response = e2e_client.get("/nonexistent/path")
            end_time = time.time()
            
            if response.status_code == 404:
                latency = (end_time - start_time) * 1000
                latencies_404.append(latency)
        
        # 测试422验证错误处理性能
        latencies_422 = []
        for _ in range(50):
            start_time = time.time()
            response = e2e_client.post("/api/v1/auth/login", json={})
            end_time = time.time()
            
            if response.status_code == 422:
                latency = (end_time - start_time) * 1000
                latencies_422.append(latency)
        
        if latencies_404:
            avg_404_latency = statistics.mean(latencies_404)
            print(f"\n404错误处理性能:")
            print(f"平均延迟: {avg_404_latency:.2f}ms")
            assert avg_404_latency < 50, f"404错误处理延迟过高: {avg_404_latency:.2f}ms"
        
        if latencies_422:
            avg_422_latency = statistics.mean(latencies_422)
            print(f"\n422验证错误处理性能:")
            print(f"平均延迟: {avg_422_latency:.2f}ms")
            assert avg_422_latency < 100, f"422验证错误处理延迟过高: {avg_422_latency:.2f}ms"
    
    def test_authentication_error_performance(self, e2e_client: TestClient):
        """测试认证错误处理性能"""
        # 测试无token的认证错误
        latencies_no_token = []
        for _ in range(50):
            start_time = time.time()
            response = e2e_client.get("/api/v1/auth/me")
            end_time = time.time()
            
            if response.status_code in [401, 403, 422]:
                latency = (end_time - start_time) * 1000
                latencies_no_token.append(latency)
        
        # 测试无效token的认证错误
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        latencies_invalid_token = []
        for _ in range(50):
            start_time = time.time()
            response = e2e_client.get("/api/v1/auth/me", headers=invalid_headers)
            end_time = time.time()
            
            if response.status_code in [401, 403, 422]:
                latency = (end_time - start_time) * 1000
                latencies_invalid_token.append(latency)
        
        if latencies_no_token:
            avg_no_token_latency = statistics.mean(latencies_no_token)
            print(f"\n无token认证错误性能:")
            print(f"平均延迟: {avg_no_token_latency:.2f}ms")
            assert avg_no_token_latency < 50, f"无token认证错误处理延迟过高: {avg_no_token_latency:.2f}ms"
        
        if latencies_invalid_token:
            avg_invalid_token_latency = statistics.mean(latencies_invalid_token)
            print(f"\n无效token认证错误性能:")
            print(f"平均延迟: {avg_invalid_token_latency:.2f}ms")
            # 无效token验证可能涉及解码，允许稍微高一些的延迟
            assert avg_invalid_token_latency < 100, f"无效token认证错误处理延迟过高: {avg_invalid_token_latency:.2f}ms"
    
    def test_memory_usage_basic(self, e2e_client: TestClient):
        """测试基本内存使用情况"""
        import psutil
        import os
        
        # 获取当前进程
        process = psutil.Process(os.getpid())
        
        # 记录初始内存使用
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行大量请求
        print(f"\n内存使用监控:")
        print(f"初始内存使用: {initial_memory:.2f} MB")
        
        for round_num in range(3):
            # 每轮执行100次健康检查
            for _ in range(100):
                e2e_client.get("/health")
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            print(f"第{round_num + 1}轮后内存使用: {current_memory:.2f} MB (+{memory_increase:.2f} MB)")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory
        
        print(f"最终内存使用: {final_memory:.2f} MB")
        print(f"总内存增长: {total_memory_increase:.2f} MB")
        
        # 内存使用断言 - 防止严重的内存泄漏
        assert total_memory_increase < 50, f"基本操作导致过多内存增长: {total_memory_increase:.2f} MB"