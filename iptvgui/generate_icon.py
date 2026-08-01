"""生成 IPTV Player 图标"""

import struct
import zlib
from pathlib import Path


def create_png(width: int, height: int, pixels: list[list[tuple[int, int, int, int]]]) -> bytes:
    """创建 PNG 图像数据"""
    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk_len = struct.pack(">I", len(data))
        chunk_crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xffffffff)
        return chunk_len + chunk_type + data + chunk_crc
    
    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = png_chunk(b'IHDR', ihdr_data)
    
    # IDAT chunk (image data)
    raw_data = b''
    for row in pixels:
        raw_data += b'\x00'  # filter type: none
        for r, g, b, a in row:
            raw_data += bytes([r, g, b, a])
    
    compressed = zlib.compress(raw_data, 9)
    idat = png_chunk(b'IDAT', compressed)
    
    # IEND chunk
    iend = png_chunk(b'IEND', b'')
    
    return signature + ihdr + idat + iend


def create_ico(png_data_list: list[tuple[int, bytes]]) -> bytes:
    """创建 ICO 文件（多尺寸）"""
    num_images = len(png_data_list)
    
    # ICO header: reserved(2) + type(2) + count(2)
    header = struct.pack("<HHH", 0, 1, num_images)
    
    # Calculate offsets
    dir_entry_size = 16
    data_offset = 6 + num_images * dir_entry_size
    
    directory = b''
    image_data = b''
    
    for size, png_data in png_data_list:
        # Directory entry
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        entry = struct.pack("<BBBBHHII", 
            w, h,           # width, height (0 = 256)
            0,              # color palette
            0,              # reserved
            1,              # color planes
            32,             # bits per pixel
            len(png_data),  # size of image data
            data_offset + len(image_data)  # offset
        )
        directory += entry
        image_data += png_data
    
    return header + directory + image_data


def draw_icon(size: int) -> list[list[tuple[int, int, int, int]]]:
    """绘制 IPTV 图标"""
    pixels = [[(0, 0, 0, 0) for _ in range(size)] for _ in range(size)]
    
    # 颜色定义
    bg_color = (30, 30, 46, 255)        # 深蓝灰背景
    primary = (233, 69, 96, 255)        # 红色 #e94560
    secondary = (85, 170, 255, 255)     # 蓝色
    white = (255, 255, 255, 255)
    
    cx, cy = size // 2, size // 2
    
    # 辅助函数
    def set_pixel(x: int, y: int, color: tuple):
        if 0 <= x < size and 0 <= y < size:
            pixels[y][x] = color
    
    def fill_circle(cx: int, cy: int, r: int, color: tuple):
        for y in range(max(0, cy - r), min(size, cy + r + 1)):
            for x in range(max(0, cx - r), min(size, cx + r + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2:
                    set_pixel(x, y, color)
    
    def fill_rounded_rect(x1: int, y1: int, x2: int, y2: int, r: int, color: tuple):
        for y in range(y1, y2):
            for x in range(x1, x2):
                # 检查是否在圆角矩形内
                in_rect = True
                # 四个角的检查
                corners = [
                    (x1 + r, y1 + r),  # 左上
                    (x2 - r, y1 + r),  # 右上
                    (x1 + r, y2 - r),  # 左下
                    (x2 - r, y2 - r),  # 右下
                ]
                for (ccx, ccy) in corners:
                    dx = abs(x - ccx)
                    dy = abs(y - ccy)
                    if x < x1 + r and y < y1 + r and (x - corners[0][0])**2 + (y - corners[0][1])**2 > r**2:
                        in_rect = False
                    elif x >= x2 - r and y < y1 + r and (x - corners[1][0])**2 + (y - corners[1][1])**2 > r**2:
                        in_rect = False
                    elif x < x1 + r and y >= y2 - r and (x - corners[2][0])**2 + (y - corners[2][1])**2 > r**2:
                        in_rect = False
                    elif x >= x2 - r and y >= y2 - r and (x - corners[3][0])**2 + (y - corners[3][1])**2 > r**2:
                        in_rect = False
                if in_rect:
                    set_pixel(x, y, color)
    
    def fill_triangle(x1, y1, x2, y2, x3, y3, color):
        """填充三角形"""
        min_x = max(0, min(x1, x2, x3))
        max_x = min(size, max(x1, x2, x3))
        min_y = max(0, min(y1, y2, y3))
        max_y = min(size, max(y1, y2, y3))
        
        def sign(px, py, ax, ay, bx, by):
            return (px - bx) * (ay - by) - (ax - bx) * (py - by)
        
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                d1 = sign(x, y, x1, y1, x2, y2)
                d2 = sign(x, y, x2, y2, x3, y3)
                d3 = sign(x, y, x3, y3, x1, y1)
                has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
                has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
                if not (has_neg and has_pos):
                    set_pixel(x, y, color)
    
    # 根据尺寸调整比例
    scale = size / 64
    margin = int(4 * scale)
    corner_r = int(8 * scale)
    
    # 1. 绘制圆角矩形背景
    fill_rounded_rect(margin, margin, size - margin, size - margin, corner_r, bg_color)
    
    # 2. 绘制电视机外框（内部矩形）
    tv_margin = int(10 * scale)
    tv_r = int(4 * scale)
    fill_rounded_rect(tv_margin, tv_margin, size - tv_margin, size - tv_margin - int(6*scale), tv_r, (45, 45, 65, 255))
    
    # 3. 绘制屏幕
    screen_margin = int(14 * scale)
    screen_bottom = size - tv_margin - int(10 * scale)
    fill_rounded_rect(screen_margin, screen_margin + int(2*scale), size - screen_margin, screen_bottom, int(3*scale), (20, 20, 35, 255))
    
    # 4. 绘制播放按钮（三角形）
    play_cx = cx
    play_cy = cy - int(4 * scale)
    play_size = int(12 * scale)
    
    # 播放三角形
    x1 = play_cx - int(play_size * 0.4)
    y1 = play_cy - int(play_size * 0.6)
    x2 = play_cx - int(play_size * 0.4)
    y2 = play_cy + int(play_size * 0.6)
    x3 = play_cx + int(play_size * 0.6)
    y3 = play_cy
    fill_triangle(x1, y1, x2, y2, x3, y3, primary)
    
    # 5. 绘制底部信号条
    bar_y = size - margin - int(8 * scale)
    bar_height = int(3 * scale)
    bar_width = int(30 * scale)
    bar_x = cx - bar_width // 2
    
    # 信号强度条
    for i in range(4):
        bw = int(5 * scale)
        bh = int((2 + i * 1.5) * scale)
        bx = bar_x + i * int(7 * scale)
        by = bar_y + bar_height - bh
        for y in range(by, by + bh):
            for x in range(bx, bx + bw):
                color = primary if i < 3 else secondary
                set_pixel(x, y, color)
    
    return pixels


def main():
    output_dir = Path(__file__).parent / "resources"
    output_dir.mkdir(exist_ok=True)
    
    # 生成多尺寸 PNG
    sizes = [16, 32, 48, 64, 128, 256]
    png_list = []
    
    for size in sizes:
        print(f"Generating {size}x{size} icon...")
        pixels = draw_icon(size)
        png_data = create_png(size, size, pixels)
        png_list.append((size, png_data))
        
        # 保存单独的 PNG（可选）
        if size == 256:
            (output_dir / "icon.png").write_bytes(png_data)
            print(f"  Saved: resources/icon.png")
    
    # 生成 ICO 文件
    ico_data = create_ico(png_list)
    ico_path = output_dir / "icon.ico"
    ico_path.write_bytes(ico_data)
    print(f"  Saved: resources/icon.ico")
    
    print("\nIcon generation completed!")
    print(f"  ICO file: {ico_path}")


if __name__ == "__main__":
    main()
