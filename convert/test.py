import requests
import time
import os
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# === 接口信息 ===
url = "http://47.98.198.75:81/api/examination/question/list-page"
headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-SG,zh;q=0.9,en-SG;q=0.8,en;q=0.7,ja-SG;q=0.6,ja;q=0.5,zh-CN;q=0.4",
    "Authorization": "Bearer MTY4NTc3MTVmZDc3NmM1Mg==",
    "Function-Key": "examination-question",
    "Referer": "http://47.98.198.75:81/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}
params = {
    "page": 1,
    "pageSize": 15,
    "simplePage": 0,
    "total": 338,
    "subject_id": 1,
    "knowledge_point_id": 494,
    "period_id": 1,
    "category_id": 2,
    "stem": ""
}

# === 请求函数 ===
def send_request():
    try:
        start = time.time()
        response = requests.get(url, headers=headers, params=params, timeout=5)
        duration = time.time() - start
        size = len(response.content)
        return response.status_code, duration, size
    except Exception as e:
        return "ERROR", 0, 0

# === 压测主函数 ===
def stress_test(concurrent_requests=100):
    success = 0
    fail = 0
    total_time = 0
    total_bytes = 0
    response_times = []

    start_time = time.time()
    cpu_start = psutil.cpu_percent(interval=None)

    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        futures = [executor.submit(send_request) for _ in range(concurrent_requests)]
        for future in as_completed(futures):
            status, duration, size = future.result()
            if status == 200:
                success += 1
                total_time += duration
                response_times.append(duration)
                total_bytes += size
            else:
                fail += 1

    end_time = time.time()
    cpu_end = psutil.cpu_percent(interval=None)

    # === 指标统计 ===
    total_requests = success + fail
    elapsed_time = end_time - start_time
    throughput = success / elapsed_time if elapsed_time > 0 else 0
    avg_time = total_time / success if success > 0 else 0
    error_rate = fail / total_requests if total_requests > 0 else 0
    bandwidth_kbps = (total_bytes * 8) / elapsed_time / 1024 if elapsed_time > 0 else 0

    print("\n=== 🚀 压测结果分析 ===")
    print(f"总请求数       : {total_requests}")
    print(f"成功请求数     : {success}")
    print(f"失败请求数     : {fail}")
    print(f"成功率         : {success / total_requests:.2%}")
    print(f"错误率         : {error_rate:.2%}")
    print(f"总耗时         : {elapsed_time:.3f} 秒")
    print(f"平均响应时间   : {avg_time:.3f} 秒")
    print(f"吞吐率         : {throughput:.2f} requests/sec")
    print(f"网络带宽估算   : {bandwidth_kbps:.2f} kbps")
    print(f"CPU 占用估算   : {cpu_end:.2f}%")

# === 启动压测 ===
if __name__ == "__main__":
    stress_test(concurrent_requests=2000)  # 可调为 50, 200, 500 等进行扩展测试
