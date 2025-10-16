import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient


class TestPermissionPerformance:
    """测试权限检查性能基准"""
    
    def test_single_permission_check_latency(self, e2e_client: TestClient, regular_user_token: str):
        """测试单个权限检查的延迟"""
        headers = {"Authorization": f"Bearer {regular_user_token}"}
        
        # 预热
        for _ in range(5):
            e2e_client.get("/api/v1/auth/me", headers=headers)
        
        # 测量延迟
        latencies = []
        for _ in range(100):
            start_time = time.time()
            response = e2e_client.get("/api/v1/auth/me", headers=headers)
            end_time = time.time()
            
            if response.status_code == 200:
                latency = (end_time - start_time) * 1000  # 转换为毫秒
                latencies.append(latency)
        
        # 分析结果
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        p99_latency = sorted(latencies)[int(0.99 * len(latencies))]
        
        print(f"\n权限检查性能指标:")
        print(f"平均延迟: {avg_latency:.2f}ms")
        print(f"中位数延迟: {median_latency:.2f}ms") 
        print(f"P95延迟: {p95_latency:.2f}ms")
        print(f"P99延迟: {p99_latency:.2f}ms")
        
        # 性能断言 - 根据实际需求调整阈值
        assert avg_latency < 100, f"平均权限检查延迟过高: {avg_latency:.2f}ms"
        assert p95_latency < 200, f"P95权限检查延迟过高: {p95_latency:.2f}ms"
    
    def test_concurrent_permission_checks(self, e2e_client: TestClient):
        """测试并发权限检查性能"""
        # 创建多个用户token
        tokens = []
        for i in range(10):
            register_data = {
                "username": f"perf_user_{i}",
                "email": f"perf{i}@test.com",
                "password": "PerfPassword123",
                "confirm_password": "PerfPassword123"
            }
            
            register_response = e2e_client.post("/api/v1/auth/register", json=register_data)
            if register_response.status_code == 200:
                login_response = e2e_client.post("/api/v1/auth/login", json={
                    "username": f"perf_user_{i}",
                    "password": "PerfPassword123"
                })
                if login_response.status_code == 200:
                    tokens.append(login_response.json()["access_token"])
        
        def make_request(token):
            headers = {"Authorization": f"Bearer {token}"}
            start_time = time.time()
            response = e2e_client.get("/api/v1/auth/me", headers=headers)
            end_time = time.time()
            return {
                "status_code": response.status_code,
                "latency": (end_time - start_time) * 1000,
                "success": response.status_code == 200
            }
        
        # 并发测试
        concurrent_levels = [1, 5, 10]
        
        for concurrency in concurrent_levels:
            if len(tokens) < concurrency:
                continue
                
            print(f"\n测试并发级别: {concurrency}")
            
            results = []
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                # 每个并发级别执行50次请求
                futures = []
                for _ in range(50):
                    for i in range(concurrency):
                        if i < len(tokens):
                            future = executor.submit(make_request, tokens[i])
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
                assert avg_latency < 500, f"并发{concurrency}时平均延迟过高: {avg_latency:.2f}ms"
    
    def test_permission_caching_effectiveness(self, e2e_client: TestClient, regular_user_token: str):
        """测试权限缓存的有效性"""
        headers = {"Authorization": f"Bearer {regular_user_token}"}
        
        # 第一次请求 - 可能会查询数据库
        start_time = time.time()
        response1 = e2e_client.get("/api/v1/auth/me", headers=headers)
        first_request_time = time.time() - start_time
        
        assert response1.status_code == 200
        
        # 连续的相同请求 - 应该使用缓存
        cached_request_times = []
        for _ in range(10):
            start_time = time.time()
            response = e2e_client.get("/api/v1/auth/me", headers=headers)
            request_time = time.time() - start_time
            
            if response.status_code == 200:
                cached_request_times.append(request_time * 1000)  # 转换为毫秒
        
        if cached_request_times:
            avg_cached_time = statistics.mean(cached_request_times)
            first_request_time_ms = first_request_time * 1000
            
            print(f"\n权限缓存效果:")
            print(f"首次请求时间: {first_request_time_ms:.2f}ms")
            print(f"缓存请求平均时间: {avg_cached_time:.2f}ms")
            print(f"性能提升: {first_request_time_ms / avg_cached_time:.2f}x")
            
            # 缓存应该能带来性能提升（如果实现了缓存）
            if avg_cached_time < first_request_time_ms * 0.8:
                print("✅ 权限缓存有效")
            else:
                print("⚠️ 权限缓存效果不明显，建议检查缓存实现")
    
    def test_database_connection_pool_under_load(self, e2e_client: TestClient):
        """测试高负载下数据库连接池的表现"""
        # 创建多个用户进行测试
        tokens = []
        for i in range(20):
            register_data = {
                "username": f"db_test_user_{i}",
                "email": f"dbtest{i}@test.com",
                "password": "DbTestPassword123",
                "confirm_password": "DbTestPassword123"
            }
            
            register_response = e2e_client.post("/api/v1/auth/register", json=register_data)
            if register_response.status_code == 200:
                login_response = e2e_client.post("/api/v1/auth/login", json={
                    "username": f"db_test_user_{i}",
                    "password": "DbTestPassword123"
                })
                if login_response.status_code == 200:
                    tokens.append(login_response.json()["access_token"])
        
        def stress_test_request(token_index):
            if token_index < len(tokens):
                headers = {"Authorization": f"Bearer {tokens[token_index]}"}
                results = []
                
                # 每个线程执行10个请求
                for _ in range(10):
                    start_time = time.time()
                    try:
                        response = e2e_client.get("/api/v1/auth/me", headers=headers)
                        end_time = time.time()
                        
                        results.append({
                            "status_code": response.status_code,
                            "latency": (end_time - start_time) * 1000,
                            "success": response.status_code == 200,
                            "error": None
                        })
                    except Exception as e:
                        results.append({
                            "status_code": None,
                            "latency": None, 
                            "success": False,
                            "error": str(e)
                        })
                
                return results
            return []
        
        # 高并发压力测试
        print(f"\n数据库连接池压力测试 (20个并发用户)")
        
        all_results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(stress_test_request, i) for i in range(20)]
            
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        total_time = time.time() - start_time
        
        # 分析结果
        successful_requests = [r for r in all_results if r["success"]]
        failed_requests = [r for r in all_results if not r["success"]]
        
        print(f"总请求数: {len(all_results)}")
        print(f"成功请求数: {len(successful_requests)}")
        print(f"失败请求数: {len(failed_requests)}")
        print(f"成功率: {len(successful_requests)/len(all_results)*100:.1f}%")
        print(f"总耗时: {total_time:.2f}s")
        print(f"平均吞吐量: {len(all_results)/total_time:.2f} requests/sec")
        
        if successful_requests:
            latencies = [r["latency"] for r in successful_requests if r["latency"] is not None]
            if latencies:
                avg_latency = statistics.mean(latencies)
                max_latency = max(latencies)
                print(f"平均延迟: {avg_latency:.2f}ms")
                print(f"最大延迟: {max_latency:.2f}ms")
        
        # 错误分析
        if failed_requests:
            error_types = {}
            for req in failed_requests:
                if req["error"]:
                    error_type = type(req["error"]).__name__
                    error_types[error_type] = error_types.get(error_type, 0) + 1
                elif req["status_code"]:
                    error_types[f"HTTP_{req['status_code']}"] = error_types.get(f"HTTP_{req['status_code']}", 0) + 1
            
            print(f"错误类型分布: {error_types}")
        
        # 性能断言
        success_rate = len(successful_requests) / len(all_results)
        assert success_rate > 0.90, f"高负载下成功率过低: {success_rate*100:.1f}%"
        
        if latencies:
            assert avg_latency < 1000, f"高负载下平均延迟过高: {avg_latency:.2f}ms"
    
    def test_memory_usage_under_permission_load(self, e2e_client: TestClient):
        """测试权限检查的内存使用情况"""
        import psutil
        import os
        
        # 获取当前进程
        process = psutil.Process(os.getpid())
        
        # 创建用户和token
        tokens = []
        for i in range(5):
            register_data = {
                "username": f"memory_test_{i}",
                "email": f"memory{i}@test.com",
                "password": "MemoryPassword123",
                "confirm_password": "MemoryPassword123"
            }
            
            register_response = e2e_client.post("/api/v1/auth/register", json=register_data)
            if register_response.status_code == 200:
                login_response = e2e_client.post("/api/v1/auth/login", json={
                    "username": f"memory_test_{i}",
                    "password": "MemoryPassword123"
                })
                if login_response.status_code == 200:
                    tokens.append(login_response.json()["access_token"])
        
        # 记录初始内存使用
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行大量权限检查
        print(f"\n内存使用监控:")
        print(f"初始内存使用: {initial_memory:.2f} MB")
        
        for round_num in range(5):
            # 每轮执行100次请求
            for _ in range(100):
                for token in tokens:
                    headers = {"Authorization": f"Bearer {token}"}
                    e2e_client.get("/api/v1/auth/me", headers=headers)
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            print(f"第{round_num + 1}轮后内存使用: {current_memory:.2f} MB (+{memory_increase:.2f} MB)")
            
            # 检查内存泄漏
            if memory_increase > 50:  # 如果内存增长超过50MB
                print(f"⚠️ 潜在内存泄漏：内存增长 {memory_increase:.2f} MB")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory
        
        print(f"最终内存使用: {final_memory:.2f} MB")
        print(f"总内存增长: {total_memory_increase:.2f} MB")
        
        # 内存使用断言 - 防止严重的内存泄漏
        assert total_memory_increase < 100, f"权限检查导致严重内存增长: {total_memory_increase:.2f} MB"