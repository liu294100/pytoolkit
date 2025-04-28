import requests
import re
import os
import img2pdf
import argparse
from urllib.parse import urlparse

def get_textbook_info(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.content.decode('utf-8')
        
        # 提取标题
        title_match = re.findall(r'<title>(.+?)</title>', html, re.S)
        title = title_match[0].replace('/', '_') if title_match else 'textbook'
        
        # 提取页面数量
        page_count_match = re.findall(r'BookInfo\.getPageCount\s*=\s*function\s*\(\s*\)\s*{\s*return\s*(\d+);', html)
        page_count = int(page_count_match[0]) if page_count_match else 10
        
        # 提取教材ID
        parsed_url = urlparse(url)
        book_id = parsed_url.path.split('/')[1]
        
        return title, page_count, book_id
    except Exception as e:
        raise Exception(f"无法获取教材信息: {str(e)}")

def download_textbook(url, save_path):
    try:
        # 获取教材信息
        title, page_count, book_id = get_textbook_info(url)
        
        # 创建临时文件夹
        temp_dir = f"temp_{title}"
        os.makedirs(temp_dir, exist_ok=True)
        
        print(f"开始下载教材 '{title}'，共 {page_count} 页...")
        
        # 下载图片
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        for page in range(1, page_count + 1):
            jpg_url = f'https://book.pep.com.cn/{book_id}/files/mobile/{page}.jpg'
            response = requests.get(jpg_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            jpg_path = os.path.join(temp_dir, f"{page}.jpg")
            with open(jpg_path, 'wb') as f:
                f.write(response.content)
            
            print(f"已下载第 {page}/{page_count} 页")
            time.sleep(0.5)  # 避免请求过快
        
        # 转换为PDF
        print("正在转换为PDF...")
        jpg_files = [os.path.join(temp_dir, f"{i}.jpg") for i in range(1, page_count + 1)]
        with open(save_path, 'wb') as f:
            f.write(img2pdf.convert(jpg_files))
        
        # 清理临时文件夹
        for jpg in jpg_files:
            os.remove(jpg)
        os.rmdir(temp_dir)
        
        print(f"教材 '{title}' 已成功保存为 {save_path}")
    except Exception as e:
        print(f"错误: {str(e)}")
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='教材下载器命令行版')
    parser.add_argument('url', help='教材URL，例如: https://book.pep.com.cn/12345678')
    parser.add_argument('save_path', help='PDF保存路径')
    args = parser.parse_args()
    
    download_textbook(args.url, args.save_path)