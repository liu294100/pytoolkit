#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能测试
"""

import unittest
import time
import threading
import asyncio
import psutil
import gc
from unittest.mock import Mock, patch
import concurrent.futures

from tests import RDPToolTestCase

try:
    from core.network import NetworkManager, ConnectionManager
    from core.security import SecurityManager
    from utils.helpers import calculate_hash, encode_base64, decode_base64
except ImportError as e:
    print(f"导入错误: {e}")
    print("某些性能测试可能会跳过")

class TestPerformanceBase(RDPToolTestCase):
    """性能测试基类"""
    
    def setUp(self):
        super().setUp()
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss
    
    def tearDown(self):
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        execution_time = end_time - self.start_time
        memory_usage = end_memory - self.start_memory
        
        print(f"\n测试执行时间: {execution_time:.3f}秒")
        print(f"内存使用变化: {memory_usage / 1024 / 1024:.2f}MB")
        
        # 强制垃圾回收
        gc.collect()
        
        super().tearDown()
    
    def measure_execution_time(self, func, *args, **kwargs):
        """测量函数执行时间"""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return result, end - start
    
    def measure_memory_usage(self, func, *args, **kwargs):
        """测量函数内存使用"""
        gc.collect()  # 清理垃圾
        start_memory = psutil.Process().memory_info().rss
        
        result = func(*args, **kwargs)
        
        gc.collect()
        end_memory = psutil.Process().memory_info().rss
        
        memory_diff = end_memory - start_memory
        return result, memory_diff

class TestCryptographyPerformance(TestPerformanceBase):
    """加密性能测试"""
    
    def setUp(self):
        super().setUp()
        self.security_manager = SecurityManager()
        self.test_data_sizes = [1024, 10240, 102400, 1048576]  # 1KB, 10KB, 100KB, 1MB
    
    def test_encryption_performance(self):
        """测试加密性能"""
        key = self.security_manager.generate_key()
        
        for size in self.test_data_sizes:
            data = b'A' * size
            
            # 测试加密性能
            encrypted_data, encrypt_time = self.measure_execution_time(
                self.security_manager.encrypt, data, key
            )
            
            # 测试解密性能
            decrypted_data, decrypt_time = self.measure_execution_time(
                self.security_manager.decrypt, encrypted_data, key
            )
            
            # 验证数据完整性
            self.assertEqual(data, decrypted_data)
            
            # 性能断言（这些值可能需要根据实际硬件调整）
            encrypt_speed = size / encrypt_time / 1024 / 1024  # MB/s
            decrypt_speed = size / decrypt_time / 1024 / 1024  # MB/s
            
            print(f"\n数据大小: {size/1024:.1f}KB")
            print(f"加密速度: {encrypt_speed:.2f}MB/s")
            print(f"解密速度: {decrypt_speed:.2f}MB/s")
            
            # 基本性能要求（根据实际情况调整）
            if size >= 1048576:  # 1MB以上的数据
                self.assertGreater(encrypt_speed, 10)  # 至少10MB/s
                self.assertGreater(decrypt_speed, 10)
    
    def test_hashing_performance(self):
        """测试哈希性能"""
        for size in self.test_data_sizes:
            data = b'B' * size
            
            hash_result, hash_time = self.measure_execution_time(
                calculate_hash, data
            )
            
            hash_speed = size / hash_time / 1024 / 1024  # MB/s
            
            print(f"\n哈希数据大小: {size/1024:.1f}KB")
            print(f"哈希速度: {hash_speed:.2f}MB/s")
            
            # 哈希应该比加密快
            if size >= 1048576:
                self.assertGreater(hash_speed, 50)  # 至少50MB/s
    
    def test_base64_performance(self):
        """测试Base64编解码性能"""
        for size in self.test_data_sizes:
            data = b'C' * size
            
            # 测试编码性能
            encoded_data, encode_time = self.measure_execution_time(
                encode_base64, data
            )
            
            # 测试解码性能
            decoded_data, decode_time = self.measure_execution_time(
                decode_base64, encoded_data
            )
            
            # 验证数据完整性
            self.assertEqual(data, decoded_data)
            
            encode_speed = size / encode_time / 1024 / 1024  # MB/s
            decode_speed = size / decode_time / 1024 / 1024  # MB/s
            
            print(f"\nBase64数据大小: {size/1024:.1f}KB")
            print(f"编码速度: {encode_speed:.2f}MB/s")
            print(f"解码速度: {decode_speed:.2f}MB/s")
            
            # Base64应该很快
            if size >= 1048576:
                self.assertGreater(encode_speed, 100)  # 至少100MB/s
                self.assertGreater(decode_speed, 100)

class TestNetworkPerformance(TestPerformanceBase):
    """网络性能测试"""
    
    def setUp(self):
        super().setUp()
        self.network_manager = NetworkManager()
        self.connection_manager = ConnectionManager()
    
    def test_connection_pool_performance(self):
        """测试连接池性能"""
        pool = self.connection_manager
        
        # 测试大量连接的添加性能
        num_connections = 1000
        connections = [Mock() for _ in range(num_connections)]
        
        def add_connections():
            for i, conn in enumerate(connections):
                pool.add_connection(f'conn_{i}', conn)
        
        _, add_time = self.measure_execution_time(add_connections)
        
        print(f"\n添加{num_connections}个连接耗时: {add_time:.3f}秒")
        print(f"平均每个连接: {add_time/num_connections*1000:.3f}毫秒")
        
        # 性能要求
        self.assertLess(add_time, 1.0)  # 1000个连接应在1秒内完成
        
        # 测试连接查找性能
        def lookup_connections():
            for i in range(num_connections):
                conn = pool.get_connection(f'conn_{i}')
                self.assertIsNotNone(conn)
        
        _, lookup_time = self.measure_execution_time(lookup_connections)
        
        print(f"查找{num_connections}个连接耗时: {lookup_time:.3f}秒")
        print(f"平均每次查找: {lookup_time/num_connections*1000:.3f}毫秒")
        
        # 查找应该很快
        self.assertLess(lookup_time, 0.1)  # 1000次查找应在0.1秒内完成
        
        # 测试连接移除性能
        def remove_connections():
            for i in range(num_connections):
                pool.remove_connection(f'conn_{i}')
        
        _, remove_time = self.measure_execution_time(remove_connections)
        
        print(f"移除{num_connections}个连接耗时: {remove_time:.3f}秒")
        
        self.assertLess(remove_time, 1.0)
        self.assertEqual(pool.get_connection_count(), 0)
    
    def test_concurrent_connection_management(self):
        """测试并发连接管理性能"""
        pool = self.connection_manager
        num_threads = 10
        connections_per_thread = 100
        
        def worker(thread_id):
            # 每个线程添加和移除连接
            for i in range(connections_per_thread):
                conn_id = f'thread_{thread_id}_conn_{i}'
                mock_conn = Mock()
                
                # 添加连接
                pool.add_connection(conn_id, mock_conn)
                
                # 查找连接
                found_conn = pool.get_connection(conn_id)
                self.assertEqual(found_conn, mock_conn)
                
                # 移除连接
                pool.remove_connection(conn_id)
        
        # 启动多个线程
        threads = []
        start_time = time.time()
        
        for thread_id in range(num_threads):
            thread = threading.Thread(target=worker, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        total_operations = num_threads * connections_per_thread * 3  # 添加、查找、移除
        operations_per_second = total_operations / total_time
        
        print(f"\n并发测试: {num_threads}个线程，每个{connections_per_thread}个连接")
        print(f"总操作数: {total_operations}")
        print(f"总耗时: {total_time:.3f}秒")
        print(f"操作速率: {operations_per_second:.0f}ops/s")
        
        # 性能要求
        self.assertGreater(operations_per_second, 1000)  # 至少1000ops/s
        self.assertEqual(pool.get_connection_count(), 0)  # 所有连接都应被移除

class TestAsyncPerformance(TestPerformanceBase):
    """异步性能测试"""
    
    def setUp(self):
        super().setUp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        self.loop.close()
        super().tearDown()
    
    async def async_task(self, task_id, delay=0.01):
        """模拟异步任务"""
        await asyncio.sleep(delay)
        return f'Task {task_id} completed'
    
    def test_async_task_performance(self):
        """测试异步任务性能"""
        num_tasks = 1000
        
        async def run_sequential():
            """顺序执行任务"""
            results = []
            for i in range(num_tasks):
                result = await self.async_task(i)
                results.append(result)
            return results
        
        async def run_concurrent():
            """并发执行任务"""
            tasks = [self.async_task(i) for i in range(num_tasks)]
            results = await asyncio.gather(*tasks)
            return results
        
        # 测试顺序执行
        sequential_results, sequential_time = self.measure_execution_time(
            self.loop.run_until_complete, run_sequential()
        )
        
        # 测试并发执行
        concurrent_results, concurrent_time = self.measure_execution_time(
            self.loop.run_until_complete, run_concurrent()
        )
        
        print(f"\n异步任务性能测试 ({num_tasks}个任务):")
        print(f"顺序执行时间: {sequential_time:.3f}秒")
        print(f"并发执行时间: {concurrent_time:.3f}秒")
        print(f"性能提升: {sequential_time/concurrent_time:.1f}倍")
        
        # 验证结果
        self.assertEqual(len(sequential_results), num_tasks)
        self.assertEqual(len(concurrent_results), num_tasks)
        
        # 并发应该明显快于顺序执行
        self.assertLess(concurrent_time, sequential_time / 5)  # 至少快5倍
    
    def test_async_connection_handling(self):
        """测试异步连接处理性能"""
        async def handle_connection(conn_id):
            """模拟处理连接"""
            # 模拟连接处理时间
            await asyncio.sleep(0.001)  # 1ms
            return f'Connection {conn_id} handled'
        
        async def connection_server(num_connections):
            """模拟连接服务器"""
            tasks = []
            for i in range(num_connections):
                task = asyncio.create_task(handle_connection(i))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results
        
        num_connections = 500
        
        results, execution_time = self.measure_execution_time(
            self.loop.run_until_complete, connection_server(num_connections)
        )
        
        connections_per_second = num_connections / execution_time
        
        print(f"\n异步连接处理测试:")
        print(f"连接数: {num_connections}")
        print(f"处理时间: {execution_time:.3f}秒")
        print(f"处理速率: {connections_per_second:.0f}连接/秒")
        
        # 验证结果
        self.assertEqual(len(results), num_connections)
        
        # 性能要求
        self.assertGreater(connections_per_second, 100)  # 至少100连接/秒

class TestMemoryPerformance(TestPerformanceBase):
    """内存性能测试"""
    
    def test_large_data_processing(self):
        """测试大数据处理的内存效率"""
        data_sizes = [1024*1024, 10*1024*1024, 50*1024*1024]  # 1MB, 10MB, 50MB
        
        for size in data_sizes:
            def process_large_data():
                # 创建大数据
                data = bytearray(size)
                
                # 模拟数据处理
                for i in range(0, len(data), 1024):
                    data[i] = i % 256
                
                # 计算校验和
                checksum = sum(data) % 65536
                
                return checksum
            
            result, memory_usage = self.measure_memory_usage(process_large_data)
            
            print(f"\n处理{size/1024/1024:.1f}MB数据:")
            print(f"内存使用: {memory_usage/1024/1024:.2f}MB")
            print(f"内存效率: {memory_usage/size:.2f}倍")
            
            # 内存使用不应超过数据大小的2倍
            self.assertLess(memory_usage, size * 2)
    
    def test_memory_leak_detection(self):
        """测试内存泄漏检测"""
        initial_memory = psutil.Process().memory_info().rss
        
        # 执行多次操作，检查内存是否持续增长
        for iteration in range(10):
            # 创建和销毁大量对象
            objects = []
            for i in range(1000):
                obj = {
                    'id': i,
                    'data': b'x' * 1024,  # 1KB数据
                    'timestamp': time.time()
                }
                objects.append(obj)
            
            # 清理对象
            del objects
            gc.collect()
            
            current_memory = psutil.Process().memory_info().rss
            memory_growth = current_memory - initial_memory
            
            print(f"迭代 {iteration + 1}: 内存增长 {memory_growth/1024/1024:.2f}MB")
        
        final_memory = psutil.Process().memory_info().rss
        total_growth = final_memory - initial_memory
        
        print(f"\n总内存增长: {total_growth/1024/1024:.2f}MB")
        
        # 内存增长应该在合理范围内（小于10MB）
        self.assertLess(total_growth, 10 * 1024 * 1024)

class TestConcurrencyPerformance(TestPerformanceBase):
    """并发性能测试"""
    
    def test_thread_pool_performance(self):
        """测试线程池性能"""
        def cpu_intensive_task(n):
            """CPU密集型任务"""
            result = 0
            for i in range(n):
                result += i * i
            return result
        
        task_size = 10000
        num_tasks = 100
        
        # 单线程执行
        start_time = time.time()
        sequential_results = []
        for i in range(num_tasks):
            result = cpu_intensive_task(task_size)
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        # 多线程执行
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cpu_intensive_task, task_size) for _ in range(num_tasks)]
            parallel_results = [future.result() for future in futures]
        parallel_time = time.time() - start_time
        
        print(f"\n线程池性能测试 ({num_tasks}个任务):")
        print(f"单线程时间: {sequential_time:.3f}秒")
        print(f"多线程时间: {parallel_time:.3f}秒")
        print(f"加速比: {sequential_time/parallel_time:.2f}倍")
        
        # 验证结果
        self.assertEqual(len(sequential_results), num_tasks)
        self.assertEqual(len(parallel_results), num_tasks)
        self.assertEqual(sequential_results, parallel_results)
        
        # 多线程应该有一定的性能提升
        self.assertLess(parallel_time, sequential_time)
    
    def test_io_intensive_performance(self):
        """测试IO密集型任务性能"""
        def io_intensive_task(task_id):
            """IO密集型任务（模拟文件操作）"""
            time.sleep(0.01)  # 模拟IO等待
            return f'Task {task_id} completed'
        
        num_tasks = 50
        
        # 顺序执行
        start_time = time.time()
        sequential_results = []
        for i in range(num_tasks):
            result = io_intensive_task(i)
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        # 并发执行
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(io_intensive_task, i) for i in range(num_tasks)]
            parallel_results = [future.result() for future in futures]
        parallel_time = time.time() - start_time
        
        print(f"\nIO密集型任务性能测试 ({num_tasks}个任务):")
        print(f"顺序执行时间: {sequential_time:.3f}秒")
        print(f"并发执行时间: {parallel_time:.3f}秒")
        print(f"加速比: {sequential_time/parallel_time:.2f}倍")
        
        # 验证结果
        self.assertEqual(len(sequential_results), num_tasks)
        self.assertEqual(len(parallel_results), num_tasks)
        
        # IO密集型任务的并发执行应该有显著提升
        self.assertLess(parallel_time, sequential_time / 3)  # 至少快3倍

class TestStressTest(TestPerformanceBase):
    """压力测试"""
    
    def test_high_connection_load(self):
        """测试高连接负载"""
        connection_manager = ConnectionManager()
        
        # 模拟大量连接
        num_connections = 5000
        connections = []
        
        start_time = time.time()
        
        # 快速添加大量连接
        for i in range(num_connections):
            mock_conn = Mock()
            conn_id = f'stress_conn_{i}'
            connection_manager.add_connection(conn_id, mock_conn)
            connections.append(conn_id)
        
        add_time = time.time() - start_time
        
        # 检查连接数
        self.assertEqual(connection_manager.get_connection_count(), num_connections)
        
        # 随机访问连接
        import random
        start_time = time.time()
        
        for _ in range(1000):
            random_id = random.choice(connections)
            conn = connection_manager.get_connection(random_id)
            self.assertIsNotNone(conn)
        
        access_time = time.time() - start_time
        
        # 清理所有连接
        start_time = time.time()
        connection_manager.cleanup_all()
        cleanup_time = time.time() - start_time
        
        print(f"\n压力测试结果 ({num_connections}个连接):")
        print(f"添加时间: {add_time:.3f}秒 ({num_connections/add_time:.0f}连接/秒)")
        print(f"随机访问时间: {access_time:.3f}秒 ({1000/access_time:.0f}访问/秒)")
        print(f"清理时间: {cleanup_time:.3f}秒")
        
        # 性能要求
        self.assertLess(add_time, 5.0)  # 5000个连接应在5秒内添加完成
        self.assertLess(access_time, 1.0)  # 1000次随机访问应在1秒内完成
        self.assertLess(cleanup_time, 2.0)  # 清理应在2秒内完成
        
        self.assertEqual(connection_manager.get_connection_count(), 0)

if __name__ == '__main__':
    # 设置性能测试环境
    import warnings
    warnings.filterwarnings('ignore')  # 忽略性能测试中的警告
    
    unittest.main(verbosity=2)