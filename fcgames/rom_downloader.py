"""
PlayOldGame ROM 下载器
通过 Playwright 抓包下载在线模拟器的 ROM 文件

使用方法:
    python rom_downloader.py <游戏页面URL>
    python rom_downloader.py "https://www.playoldgame.com/playemu/play.html?system=neshack&url=..."

依赖安装:
    pip install playwright py7zr
    python -m playwright install chromium
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

# 修复 Windows 控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


async def download_rom(url: str, output_dir: str = ".", proxy: str = None, headless: bool = False):
    """
    从 playoldgame.com 下载 ROM 文件
    
    Args:
        url: 游戏页面 URL
        output_dir: 输出目录
        proxy: 代理地址，如 "http://127.0.0.1:1234"
        headless: 是否无头模式运行
    
    Returns:
        下载的文件路径列表
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] 请先安装 playwright: pip install playwright")
        print("        然后安装浏览器: python -m playwright install chromium")
        return []
    
    # 从 URL 解析游戏名称
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    rom_name = params.get('rom', ['unknown_rom'])[0]
    rom_name = unquote(rom_name)  # URL 解码
    ext = params.get('ext', ['nes'])[0]
    
    print(f"[INFO] 游戏名称: {rom_name}")
    print(f"[INFO] 文件格式: .{ext}")
    
    downloaded_files = []
    
    async with async_playwright() as p:
        # 启动配置
        launch_options = {
            'headless': headless,
        }
        
        # 尝试使用系统 Chrome
        chrome_paths = [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser',
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        ]
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                launch_options['executable_path'] = chrome_path
                print(f"[INFO] 使用浏览器: {chrome_path}")
                break
        
        # 代理配置
        if proxy:
            launch_options['proxy'] = {'server': proxy}
            print(f"[INFO] 使用代理: {proxy}")
        
        print("[INFO] 启动浏览器...")
        browser = await p.chromium.launch(**launch_options)
        context = await browser.new_context()
        page = await context.new_page()
        
        async def handle_response(response):
            """拦截网络响应"""
            resp_url = response.url
            content_type = response.headers.get('content-type', '')
            
            # 检测 ROM 文件的特征
            is_rom = any([
                'rom-serve' in resp_url,
                f'.{ext}' in resp_url.lower(),
                'application/octet-stream' in content_type,
                'application/x-7z-compressed' in content_type,
                'application/zip' in content_type,
            ])
            
            if is_rom and response.status == 200:
                try:
                    body = await response.body()
                    if len(body) > 1000:  # 忽略太小的文件
                        # 确定文件名（清理非法字符）
                        safe_name = "".join(c for c in rom_name if c not in r'\/:*?"<>|')
                        filename = f"{safe_name}.{ext}"
                        filepath = os.path.join(output_dir, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(body)
                        
                        print(f"[OK] 下载成功: {filename} ({len(body):,} bytes)")
                        downloaded_files.append(filepath)
                except Exception as e:
                    print(f"[WARN] 保存失败: {e}")
        
        # 注册响应监听器
        page.on('response', handle_response)
        
        print(f"[INFO] 访问页面...")
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
        except Exception as e:
            print(f"[WARN] 页面加载超时，继续等待: {type(e).__name__}")
        
        # 等待 ROM 加载完成
        print("[INFO] 等待 ROM 加载...")
        await asyncio.sleep(10)
        
        await browser.close()
        print("[INFO] 浏览器已关闭")
    
    return downloaded_files


def extract_archive(filepath: str) -> list:
    """
    解压压缩包，返回解压出的文件列表
    """
    extracted = []
    output_dir = os.path.dirname(filepath) or '.'
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    
    # 检测文件类型
    with open(filepath, 'rb') as f:
        header = f.read(10)
    
    # 7z 格式
    if header[:2] == b'7z':
        try:
            import py7zr
            print(f"[INFO] 解压 7z 文件: {filepath}")
            with py7zr.SevenZipFile(filepath, 'r') as archive:
                names = archive.getnames()
                if not names:
                    print("[WARN] 压缩包为空或无法读取文件列表")
                    return extracted
                    
                archive.extractall(path=output_dir)
                for name in names:
                    extracted_path = os.path.join(output_dir, name)
                    if os.path.exists(extracted_path):
                        extracted.append(extracted_path)
                        size = os.path.getsize(extracted_path)
                        print(f"   [OK] {name} ({size:,} bytes)")
                    else:
                        # 文件名可能有编码问题，尝试重命名
                        # 查找目录下的新文件
                        for f in os.listdir(output_dir):
                            full = os.path.join(output_dir, f)
                            if full not in extracted and f.endswith('.nes'):
                                extracted.append(full)
                                size = os.path.getsize(full)
                                print(f"   [OK] {f} ({size:,} bytes)")
                                
        except ImportError:
            print("[ERROR] 请安装 py7zr: pip install py7zr")
        except Exception as e:
            print(f"[WARN] 7z 解压失败: {e}")
            # 尝试用系统 7z
            try:
                import subprocess
                seven_zip = r'C:\Program Files\7-Zip\7z.exe'
                if os.path.exists(seven_zip):
                    print("[INFO] 尝试使用系统 7-Zip...")
                    result = subprocess.run(
                        [seven_zip, 'x', filepath, f'-o{output_dir}', '-y'],
                        capture_output=True
                    )
                    if result.returncode == 0:
                        for f in os.listdir(output_dir):
                            if f.endswith('.nes'):
                                extracted.append(os.path.join(output_dir, f))
                                print(f"   [OK] {f}")
            except Exception as e2:
                print(f"[ERROR] 系统 7-Zip 也失败: {e2}")
    
    # ZIP 格式
    elif header[:4] == b'PK\x03\x04':
        import zipfile
        print(f"[INFO] 解压 ZIP 文件: {filepath}")
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                zf.extractall(output_dir)
                for name in zf.namelist():
                    extracted_path = os.path.join(output_dir, name)
                    if os.path.exists(extracted_path):
                        extracted.append(extracted_path)
                        print(f"   [OK] {name}")
        except Exception as e:
            print(f"[ERROR] ZIP 解压失败: {e}")
    
    # NES ROM（无需解压）
    elif header[:4] == b'NES\x1a':
        print(f"[OK] 已经是 NES ROM 文件，无需解压")
        # 重命名为 .nes 扩展名
        if not filepath.endswith('.nes'):
            new_path = os.path.splitext(filepath)[0] + '.nes'
            os.rename(filepath, new_path)
            filepath = new_path
        extracted.append(filepath)
    
    else:
        print(f"[WARN] 未知文件格式，头部: {header[:10]}")
        # 可能是没有正确识别的压缩包，尝试当作 7z 处理
        try:
            import py7zr
            with py7zr.SevenZipFile(filepath, 'r') as archive:
                archive.extractall(path=output_dir)
                for f in os.listdir(output_dir):
                    if f.endswith('.nes'):
                        extracted.append(os.path.join(output_dir, f))
        except:
            pass
    
    return extracted


async def main():
    parser = argparse.ArgumentParser(
        description='PlayOldGame ROM 下载器 - 通过抓包下载在线模拟器的 ROM 文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python %(prog)s "https://www.playoldgame.com/playemu/play.html?system=neshack&url=..."
  python %(prog)s "URL" --proxy http://127.0.0.1:7890
  python %(prog)s "URL" -o ./roms --headless
        '''
    )
    parser.add_argument('url', help='游戏页面 URL')
    parser.add_argument('-o', '--output', default='.', help='输出目录 (默认: 当前目录)')
    parser.add_argument('-p', '--proxy', help='代理地址，如 http://127.0.0.1:7890')
    parser.add_argument('--headless', action='store_true', help='无头模式（不显示浏览器窗口）')
    parser.add_argument('--no-extract', action='store_true', help='不自动解压')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    print("=" * 50)
    print("PlayOldGame ROM Downloader")
    print("=" * 50)
    
    # 下载
    files = await download_rom(
        url=args.url,
        output_dir=args.output,
        proxy=args.proxy,
        headless=args.headless
    )
    
    if not files:
        print("[ERROR] 未能下载任何文件")
        return 1
    
    # 解压
    all_roms = []
    if not args.no_extract:
        print("\n" + "-" * 50)
        print("[INFO] 开始解压...")
        for f in files:
            extracted = extract_archive(f)
            all_roms.extend(extracted)
    else:
        all_roms = files
    
    if all_roms:
        print("\n" + "-" * 50)
        print("[OK] ROM 文件已就绪:")
        for rom in all_roms:
            size = os.path.getsize(rom)
            print(f"   {rom} ({size:,} bytes)")
    
    print("\n" + "=" * 50)
    print("[DONE] 完成!")
    return 0


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
