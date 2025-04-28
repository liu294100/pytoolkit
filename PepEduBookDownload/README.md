# 教材下载器

## 安装指南

1. 确保已安装Python 3.6或更高版本
2. 安装依赖包：
```
python -m pip install requests img2pdf
```

## GUI版本使用方法

1. 运行程序：
```
python textbook_downloader_gui.py
```
2. 在界面中输入教材URL（例如：https://book.pep.com.cn/12345678）
3. 选择保存路径（PDF格式）
4. 点击"下载并转换为PDF"按钮

## 命令行版本使用方法

1. 运行程序：
```
python textbook_downloader_cli.py <教材URL> <保存路径>
```
示例：
```
python textbook_downloader_cli.py https://book.pep.com.cn/12345678 textbook.pdf
```

## 注意事项

- 需要稳定的网络连接
- 下载速度取决于网络状况
- 程序会在当前目录创建临时文件夹，处理完成后自动删除
- 如果遇到错误，请检查URL是否正确