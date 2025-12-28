from PIL import Image, ImageDraw, ImageFont
import platform
import os

def get_sys_font(font_size):
    system = platform.system()
    fonts = []
    if system == "Windows":
        # Standard Windows Font Paths
        win_dir = os.environ.get('WINDIR', 'C:\\Windows')
        fonts_dir = os.path.join(win_dir, 'Fonts')
        
        fonts = [
            os.path.join(fonts_dir, "msyh.ttc"),      # Microsoft YaHei
            os.path.join(fonts_dir, "msyh.ttf"),
            os.path.join(fonts_dir, "msyhbd.ttc"),    # YaHei Bold
            os.path.join(fonts_dir, "simhei.ttf"),    # SimHei
            os.path.join(fonts_dir, "simsun.ttc"),    # SimSun
            "msyh.ttc",
            "simhei.ttf",
            "arial.ttf"
        ]
    elif system == "Darwin":
        fonts = ["PingFang.ttc", "Arial.ttf", "/System/Library/Fonts/PingFang.ttc"]
    else:
        fonts = ["wqy-microhei.ttc", "DejaVuSans.ttf", "arial.ttf"]
        
    for font_path in fonts:
        try:
            if os.path.exists(font_path) or not os.path.isabs(font_path):
                 return ImageFont.truetype(font_path, font_size)
        except IOError:
            continue
            
    # Fallback
    print("Warning: Failed to load specified Chinese fonts. Falling back to default.")
    try:
        return ImageFont.load_default()
    except:
        return None

def add_watermark(
    image_path,
    output_path,
    text="Watermark",
    font_size=36,
    opacity=128,
    angle=30,     # 旋转角度
    space=None,   # 水印间距, None for auto
    color=(100, 100, 100) # Default Dark Grey
):
    # 打开原图
    base = Image.open(image_path).convert("RGBA")
    width, height = base.size

    # 创建一个透明图层，用于绘制所有的水印
    txt_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
    
    # 字体
    font = get_sys_font(font_size)
    if font is None:
        print("Warning: Could not load any font.")
        font = ImageFont.load_default()

    # 计算文字尺寸
    dummy_draw = ImageDraw.Draw(txt_layer)
    try:
        left, top, right, bottom = dummy_draw.textbbox((0, 0), text, font=font)
        text_width = right - left
        text_height = bottom - top
    except AttributeError:
        # For older Pillow versions
        text_width, text_height = dummy_draw.textsize(text, font=font)

    # 创建单个水印的临时图片（足够大以容纳旋转）
    # 增加一些padding防止旋转后被裁剪
    diagonal = int((text_width**2 + text_height**2)**0.5)
    watermark_size = int(diagonal * 1.5)
    
    watermark_img = Image.new("RGBA", (watermark_size, watermark_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_img)
    
    # 在中心绘制文字 - 使用深灰色/黑色以保证在发票(白底)上可见
    # 用户要求"肉眼可见", 一般发票是白底, 白字看不见. 改为半透明黑色.
    # Color: (R, G, B, A) -> (r, g, b, opacity)
    if isinstance(color, str):
        # Handle string colors if passed (e.g. "#000000") - simple fallback
        if color.startswith("#"):
             # simplistic hex parse or just default
             pass 
        fill_color = (0, 0, 0, opacity) # Fallback
    else:
        fill_color = (color[0], color[1], color[2], opacity)

    draw.text(
        ((watermark_size - text_width) / 2, (watermark_size - text_height) / 2),
        text,
        fill=fill_color,
        font=font
    )
    
    # 旋转单个水印
    rotated_watermark = watermark_img.rotate(angle, expand=1)
    rw_width, rw_height = rotated_watermark.size

    # 自动计算间距 if space is None
    if space is None:
        space = int(min(width, height) / 5) # Default to 1/5th of min dimension
        space = max(space, rw_width // 2)   # Ensure at least half width
        space = max(space, 100)             # Minimum 100px

    # 平铺绘制
    # 为了保证覆盖，从负坐标开始画
    # 使用 denser spacing ensuring full coverage
    for y in range(-rw_height, height + rw_height, space):
        for x in range(-rw_width, width + rw_width, space):
            txt_layer.paste(rotated_watermark, (x, y), rotated_watermark)

    # 合成
    watermarked = Image.alpha_composite(base, txt_layer)

    # 保存
    # If input was JPG, save as JPG (convert to RGB)
    ext = os.path.splitext(output_path)[1].lower()
    if ext in ['.jpg', '.jpeg']:
        watermarked.convert("RGB").save(output_path, quality=95)
    else:
        watermarked.save(output_path)
        
    print(f"水印添加完成: {output_path}")


# 示例
if __name__ == "__main__":
    import os
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct paths relative to the script directory
    input_image = os.path.join(script_dir, "source.jpg")
    output_image = os.path.join(script_dir, "source_watermarked.jpg")
    
    if os.path.exists(input_image):
        add_watermark(
            image_path=input_image,
            output_path=output_image,
            text="© LiuFei 2025",
            font_size=40,
            opacity=100,
            angle=30,
            space=200
        )
    else:
        print(f"Error: Input file not found at {input_image}")
