#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDPTool - 多协议远程桌面工具
安装配置文件
"""

import os
import sys
from setuptools import setup, find_packages

# 确保Python版本
if sys.version_info < (3, 8):
    raise RuntimeError("RDPTool requires Python 3.8 or higher")

# 读取README文件
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# 读取版本信息
version = {}
with open(os.path.join(here, 'rdptool', '__version__.py')) as f:
    exec(f.read(), version)

# 核心依赖（必需）
core_requirements = [
    'psutil>=5.8.0',
]

# 可选依赖组
extra_requirements = {
    'image': [
        'Pillow>=9.0.0',
        'opencv-python>=4.5.0',
        'mss>=6.1.0',
        'numpy>=1.21.0',
    ],
    'input': [
        'pynput>=1.7.0',
        'pyautogui>=0.9.53',
    ],
    'crypto': [
        'cryptography>=3.4.0',
        'pycryptodome>=3.15.0',
    ],
    'network': [
        'websockets>=10.0',
        'paramiko>=2.8.0',
        'requests>=2.25.0',
        'aiohttp>=3.8.0',
        'uvloop>=0.17.0; sys_platform != "win32"',
    ],
    'compression': [
        'lz4>=3.1.0',
        'zstandard>=0.15.0',
    ],
    'proxy': [
        'socks>=1.7.1',
        'pysocks>=1.7.1',
    ],
    'gui': [
        'tkinter-tooltip>=2.0.0',
    ],
    'config': [
        'PyYAML>=5.4.0',
        'toml>=0.10.0',
    ],
    'logging': [
        'coloredlogs>=15.0',
        'rich>=10.0.0',
    ],
    'dev': [
        'pytest>=6.0.0',
        'pytest-asyncio>=0.18.0',
        'pytest-cov>=2.12.0',
        'black>=21.0.0',
        'flake8>=3.9.0',
        'mypy>=0.910',
        'isort>=5.9.0',
        'memory-profiler>=0.60.0',
        'line-profiler>=3.3.0',
    ],
    'docs': [
        'sphinx>=4.0.0',
        'sphinx-rtd-theme>=0.5.0',
    ],
}

# 完整安装（所有可选依赖）
extra_requirements['full'] = [
    dep for deps in extra_requirements.values() 
    if deps != extra_requirements['dev'] and deps != extra_requirements['docs']
    for dep in deps
]

# 所有依赖（包括开发和文档）
extra_requirements['all'] = [
    dep for deps in extra_requirements.values() for dep in deps
]

setup(
    name='rdptool',
    version=version['__version__'],
    description='多协议远程桌面工具 - 纯Python实现',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='RDPTool Team',
    author_email='rdptool@example.com',
    url='https://github.com/example/rdptool',
    project_urls={
        'Bug Reports': 'https://github.com/example/rdptool/issues',
        'Source': 'https://github.com/example/rdptool',
        'Documentation': 'https://rdptool.readthedocs.io/',
    },
    packages=find_packages(exclude=['tests', 'tests.*', 'docs', 'docs.*']),
    include_package_data=True,
    python_requires='>=3.8',
    install_requires=core_requirements,
    extras_require=extra_requirements,
    entry_points={
        'console_scripts': [
            'rdptool=rdptool.main:main',
            'rdp-server=rdptool.server:main',
            'rdp-client=rdptool.client:main',
            'rdp-proxy=rdptool.proxy_server:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet :: Proxy Servers',
        'Topic :: System :: Networking',
        'Topic :: Desktop Environment :: Screen Savers',
        'Topic :: System :: Systems Administration',
        'Topic :: Security :: Cryptography',
    ],
    keywords='remote desktop proxy socks http websocket ssh tunnel rdp vnc',
    license='MIT',
    zip_safe=False,
    package_data={
        'rdptool': [
            'configs/*.json',
            'configs/*.yaml',
            'templates/*.html',
            'static/*',
        ],
    },
)

# 安装后提示信息
print("""
🎉 RDPTool 安装完成！

快速开始：
  rdptool --help                    # 查看帮助
  rdptool server                    # 启动服务端
  rdptool client --gui              # 启动客户端GUI
  rdptool proxy                     # 启动代理服务

配置生成：
  rdptool config --type server      # 生成服务端配置
  rdptool config --type client      # 生成客户端配置
  rdptool config --type proxy       # 生成代理配置

更多信息：
  文档: https://rdptool.readthedocs.io/
  源码: https://github.com/example/rdptool
  问题: https://github.com/example/rdptool/issues

注意：某些功能需要安装可选依赖，使用以下命令安装：
  pip install rdptool[full]         # 完整功能
  pip install rdptool[image,crypto] # 特定功能组
""")