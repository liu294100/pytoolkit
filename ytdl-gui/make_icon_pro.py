"""生成 YouTube Downloader Pro 的多尺寸 .ico 图标（红色圆角 + 白色播放三角 + 青紫描边）"""
from PIL import Image, ImageDraw

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# 霓虹描边底板
d.rounded_rectangle((8, 8, SIZE - 8, SIZE - 8), radius=56, fill=(11, 13, 24, 255), outline=(34, 211, 238, 255), width=10)
# 红色圆角播放块
d.rounded_rectangle((44, 64, SIZE - 44, SIZE - 64), radius=34, fill=(255, 46, 77, 255))
# 白色三角
d.polygon([(108, 96), (108, 160), (164, 128)], fill=(255, 255, 255, 255))
# 底部紫色下载条
d.rounded_rectangle((88, 204, SIZE - 88, 216), radius=6, fill=(139, 92, 246, 255))

img.save("youtube_pro.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("youtube_pro.ico 已生成")
