import os
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import re
from tqdm import tqdm

# 配置参数
URL = "https://bibleproject.com/locale/downloads/zhs/"  # 目标网页
DOWNLOAD_DIR = "g:/videos"  # 下载目录
MAX_WORKERS = 10  # 最大并发线程数
PROXY = "http://127.0.0.1:7880"  # Clash 代理地址

def sanitize_filename(filename):
    """清理文件名，去除非法字符"""
    return re.sub(r'[^\w\-_\. ]', '_', filename)

def download_video(category, title, url):
    """下载单个视频，显示进度条，如果文件已存在则跳过"""
    sanitized_category = sanitize_filename(category)
    sanitized_title = sanitize_filename(title)
    category_dir = os.path.join(DOWNLOAD_DIR, sanitized_category)
    os.makedirs(category_dir, exist_ok=True)
    filename = os.path.join(category_dir, f"{sanitized_title}.mp4")
    
    if os.path.exists(filename):
        print(f"{title} 已存在，跳过下载")
        return
    
    try:
        # 设置代理
        proxies = {"http": PROXY, "https": PROXY}
        response = requests.get(url, stream=True, proxies=proxies)
        response.raise_for_status()
        
        # 获取文件总大小
        total_size = int(response.headers.get('content-length', 0))
        
        # 使用 tqdm 显示下载进度条
        with open(filename, "wb") as f, tqdm(
            desc=f"{category}/{title}",
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                pbar.update(len(chunk))
        print(f"已下载: {category}/{title}")
    except Exception as e:
        print(f"下载失败 {category}/{title}: {e}")

def main():
    """主函数：抓取网页并下载视频"""
    # 确保下载目录存在
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # 获取网页内容，使用代理
    proxies = {"http": PROXY, "https": PROXY}
    response = requests.get(URL, proxies=proxies)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    
    # 提取所有类别组
    categories = soup.find_all("div", class_="intl-downloads-group")
    
    # 并发下载视频
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for category in categories:
            # 提取类别标题
            category_title_div = category.find("div", class_="intl-downloads-group-title")
            category_title = category_title_div.text.strip() if category_title_div else "未知类别"
            
            # 提取类别下的视频项
            items = category.find_all("div", class_="intl-downloads-item")
            for item in items:
                title_div = item.find("div", class_="intl-downloads-item-title")
                title = title_div.text.strip() if title_div else "未知标题"
                a_tag = item.find("a")
                if a_tag and "href" in a_tag.attrs:
                    url = a_tag["href"]
                    executor.submit(download_video, category_title, title, url)
                else:
                    print(f"未找到 {category_title}/{title} 的下载链接")

if __name__ == "__main__":
    main()