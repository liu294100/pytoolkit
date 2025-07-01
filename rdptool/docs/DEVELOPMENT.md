# RDPTool 开发者指南

## 概述

本文档为 RDPTool 项目的开发者提供详细的开发指南，包括项目结构、开发环境搭建、编码规范、测试指南等。

## 目录

- [项目结构](#项目结构)
- [开发环境搭建](#开发环境搭建)
- [编码规范](#编码规范)
- [测试指南](#测试指南)
- [贡献指南](#贡献指南)
- [发布流程](#发布流程)
- [故障排除](#故障排除)

---

## 项目结构

```
rdptool/
├── main.py                 # 主程序入口
├── proxy_server.py         # 代理服务器实现
├── __version__.py          # 版本信息
├── setup.py               # 安装配置
├── requirements.txt       # 依赖列表
├── README.md              # 项目说明
├── LICENSE                # 许可证
├── .gitignore            # Git忽略文件
├── examples.py           # 使用示例
│
├── core/                 # 核心模块
│   ├── __init__.py
│   ├── config.py         # 配置管理
│   ├── security.py       # 安全模块
│   ├── network.py        # 网络模块
│   ├── protocol.py       # 协议处理
│   └── exceptions.py     # 异常定义
│
├── rdp/                  # 远程桌面模块
│   ├── __init__.py
│   ├── server.py         # RDP服务端
│   ├── client.py         # RDP客户端
│   ├── screen.py         # 屏幕捕获
│   ├── input.py          # 输入处理
│   └── codec.py          # 编解码
│
├── gui/                  # 图形界面
│   ├── __init__.py
│   ├── main_window.py    # 主窗口
│   ├── client_window.py  # 客户端窗口
│   ├── server_window.py  # 服务端窗口
│   └── settings.py       # 设置界面
│
├── utils/                # 工具模块
│   ├── __init__.py
│   ├── logger.py         # 日志工具
│   ├── helpers.py        # 辅助函数
│   └── config.py         # 配置工具
│
├── configs/              # 配置文件模板
│   ├── server_config.json
│   ├── client_config.json
│   └── proxy_config.json
│
├── tests/                # 测试文件
│   ├── __init__.py
│   ├── test_core.py
│   ├── test_network.py
│   ├── test_gui.py
│   ├── test_performance.py
│   └── test_integration.py
│
└── docs/                 # 文档
    ├── API.md
    ├── DEVELOPMENT.md
    └── DEPLOYMENT.md
```

---

## 开发环境搭建

### 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows, macOS, Linux
- **内存**: 最少 4GB RAM
- **存储**: 最少 1GB 可用空间

### 环境准备

#### 1. 克隆项目

```bash
git clone https://github.com/rdptool/rdptool.git
cd rdptool
```

#### 2. 创建虚拟环境

```bash
# 使用 venv
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

#### 3. 安装依赖

```bash
# 安装核心依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -e .[dev]

# 或者安装所有可选依赖
pip install -e .[all]
```

#### 4. 验证安装

```bash
# 运行测试
python -m pytest tests/

# 检查代码风格
flake8 .

# 运行示例
python examples.py
```

### IDE 配置

#### VS Code

推荐的 VS Code 扩展：

- Python
- Python Docstring Generator
- GitLens
- Code Spell Checker

`.vscode/settings.json` 配置：

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

#### PyCharm

1. 打开项目目录
2. 配置 Python 解释器为虚拟环境中的 Python
3. 启用代码检查和格式化
4. 配置测试运行器为 pytest

---

## 编码规范

### Python 代码风格

项目遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 编码规范，并使用以下工具：

- **Black**: 代码格式化
- **Flake8**: 代码检查
- **isort**: 导入排序

#### 配置文件

`pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py38']
include = '\.pyi?$'
exclude = '''
(
  /(
      \.eggs
    | \.git
    | \.hg
    | \.mypy_cache
    | \.tox
    | \.venv
    | _build
    | buck-out
    | build
    | dist
  )/
)
'''

[tool.isort]
profile = "black"
line_length = 88
```

`.flake8`:

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = 
    .git,
    __pycache__,
    .venv,
    build,
    dist
```

### 命名规范

#### 文件和目录

- 使用小写字母和下划线
- 模块名简短且有意义
- 包名使用小写字母，避免下划线

```python
# 好的例子
network_manager.py
config_parser.py
utils/
core/

# 不好的例子
NetworkManager.py
configParser.py
Utils/
Core/
```

#### 类名

- 使用 CapWords 约定（驼峰命名）
- 名称应该清晰表达类的用途

```python
# 好的例子
class NetworkManager:
    pass

class ProxyServer:
    pass

# 不好的例子
class networkmanager:
    pass

class proxy_server:
    pass
```

#### 函数和变量名

- 使用小写字母和下划线
- 名称应该描述性强

```python
# 好的例子
def create_tcp_connection():
    pass

max_connections = 100
server_host = '127.0.0.1'

# 不好的例子
def createTcpConnection():
    pass

maxConn = 100
host = '127.0.0.1'
```

#### 常量

- 使用全大写字母和下划线
- 在模块级别定义

```python
# 好的例子
DEFAULT_PORT = 8888
MAX_RETRY_COUNT = 3
CONNECTION_TIMEOUT = 30.0
```

### 文档字符串

使用 Google 风格的文档字符串：

```python
def create_tcp_connection(host: str, port: int, timeout: float = 10.0) -> tuple:
    """
    创建TCP连接。
    
    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间，默认10秒
        
    Returns:
        tuple: (reader, writer) 元组
        
    Raises:
        ConnectionError: 连接失败时抛出
        ValueError: 参数无效时抛出
        
    Example:
        >>> reader, writer = create_tcp_connection('127.0.0.1', 8080)
        >>> # 使用连接...
        >>> writer.close()
    """
    pass
```

### 类型注解

使用类型注解提高代码可读性：

```python
from typing import List, Dict, Optional, Union, Callable

def process_data(data: List[Dict[str, Union[str, int]]], 
                callback: Optional[Callable[[str], None]] = None) -> bool:
    """
    处理数据列表。
    
    Args:
        data: 数据字典列表
        callback: 可选的回调函数
        
    Returns:
        bool: 处理是否成功
    """
    pass
```

### 异常处理

#### 自定义异常

```python
class RDPToolError(Exception):
    """RDPTool基础异常类。"""
    pass

class ConfigError(RDPToolError):
    """配置相关异常。"""
    pass

class NetworkError(RDPToolError):
    """网络相关异常。"""
    pass
```

#### 异常处理最佳实践

```python
# 好的例子
try:
    config = load_config(config_path)
except FileNotFoundError:
    logger.error(f"配置文件不存在: {config_path}")
    raise ConfigError(f"无法找到配置文件: {config_path}")
except json.JSONDecodeError as e:
    logger.error(f"配置文件格式错误: {e}")
    raise ConfigError(f"配置文件格式无效: {e}")

# 不好的例子
try:
    config = load_config(config_path)
except Exception as e:
    print(f"错误: {e}")
    pass
```

---

## 测试指南

### 测试框架

项目使用 `pytest` 作为测试框架，支持：

- 单元测试
- 集成测试
- 性能测试
- 异步测试

### 测试结构

```
tests/
├── __init__.py           # 测试初始化
├── conftest.py          # pytest配置
├── test_core.py         # 核心模块测试
├── test_network.py      # 网络模块测试
├── test_gui.py          # GUI测试
├── test_performance.py  # 性能测试
├── test_integration.py  # 集成测试
└── fixtures/            # 测试数据
    ├── configs/
    └── data/
```

### 编写测试

#### 单元测试示例

```python
import pytest
from unittest.mock import Mock, patch
from core.security import SecurityManager

class TestSecurityManager:
    """安全管理器测试。"""
    
    def setup_method(self):
        """测试前准备。"""
        self.security_manager = SecurityManager()
    
    def test_generate_key(self):
        """测试密钥生成。"""
        key = self.security_manager.generate_key()
        
        assert isinstance(key, bytes)
        assert len(key) == 32  # 默认密钥长度
    
    def test_encrypt_decrypt(self):
        """测试加密解密。"""
        original_data = b"test data"
        key = self.security_manager.generate_key()
        
        # 加密
        encrypted = self.security_manager.encrypt(original_data, key)
        assert encrypted != original_data
        
        # 解密
        decrypted = self.security_manager.decrypt(encrypted, key)
        assert decrypted == original_data
    
    def test_password_hashing(self):
        """测试密码哈希。"""
        password = "test_password"
        
        # 哈希密码
        hashed = self.security_manager.hash_password(password)
        assert hashed != password
        
        # 验证密码
        assert self.security_manager.verify_password(password, hashed)
        assert not self.security_manager.verify_password("wrong", hashed)
    
    def test_invalid_key_length(self):
        """测试无效密钥长度。"""
        with pytest.raises(ValueError):
            self.security_manager.generate_key(-1)
```

#### 异步测试示例

```python
import pytest
import asyncio
from core.network import NetworkManager

class TestNetworkManager:
    """网络管理器测试。"""
    
    def setup_method(self):
        """测试前准备。"""
        self.network_manager = NetworkManager()
    
    @pytest.mark.asyncio
    async def test_tcp_connection(self):
        """测试TCP连接。"""
        # 启动测试服务器
        async def echo_handler(reader, writer):
            data = await reader.read(100)
            writer.write(data)
            await writer.drain()
            writer.close()
        
        server = await asyncio.start_server(echo_handler, '127.0.0.1', 0)
        host, port = server.sockets[0].getsockname()
        
        try:
            # 测试连接
            reader, writer = await self.network_manager.create_tcp_connection(
                host, port
            )
            
            # 发送数据
            test_data = b"hello"
            writer.write(test_data)
            await writer.drain()
            
            # 接收数据
            response = await reader.read(100)
            assert response == test_data
            
            writer.close()
            await writer.wait_closed()
            
        finally:
            server.close()
            await server.wait_closed()
```

#### Mock 测试示例

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from proxy_server import ProxyServer, ProxyConfig

class TestProxyServer:
    """代理服务器测试。"""
    
    def setup_method(self):
        """测试前准备。"""
        self.config = ProxyConfig(host='127.0.0.1', port=8080)
        self.proxy_server = ProxyServer(self.config)
    
    @patch('proxy_server.asyncio.start_server')
    async def test_start_server(self, mock_start_server):
        """测试服务器启动。"""
        mock_server = AsyncMock()
        mock_start_server.return_value = mock_server
        
        result = await self.proxy_server.start()
        
        assert result is True
        mock_start_server.assert_called_once()
        assert self.proxy_server.is_running
    
    def test_get_stats(self):
        """测试统计信息获取。"""
        stats = self.proxy_server.get_stats()
        
        assert isinstance(stats, dict)
        assert 'connections' in stats
        assert 'bytes_transferred' in stats
```

### 运行测试

#### 基本命令

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/test_core.py

# 运行特定测试类
pytest tests/test_core.py::TestSecurityManager

# 运行特定测试方法
pytest tests/test_core.py::TestSecurityManager::test_encrypt_decrypt

# 显示详细输出
pytest -v

# 显示覆盖率
pytest --cov=.

# 生成HTML覆盖率报告
pytest --cov=. --cov-report=html
```

#### 测试配置

`pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --disable-warnings
    --cov=.
    --cov-report=term-missing
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    gui: marks tests as GUI tests
```

### 测试最佳实践

#### 1. 测试命名

```python
# 好的例子
def test_should_return_true_when_valid_input():
    pass

def test_should_raise_exception_when_invalid_config():
    pass

# 不好的例子
def test1():
    pass

def test_function():
    pass
```

#### 2. 测试组织

```python
class TestConfigManager:
    """配置管理器测试。"""
    
    def setup_method(self):
        """每个测试方法前执行。"""
        self.config_manager = ConfigManager()
    
    def teardown_method(self):
        """每个测试方法后执行。"""
        # 清理资源
        pass
    
    def test_load_valid_config(self):
        """测试加载有效配置。"""
        pass
    
    def test_load_invalid_config(self):
        """测试加载无效配置。"""
        pass
```

#### 3. 使用 Fixtures

```python
# conftest.py
import pytest
from core.security import SecurityManager

@pytest.fixture
def security_manager():
    """安全管理器fixture。"""
    return SecurityManager()

@pytest.fixture
def sample_config():
    """示例配置fixture。"""
    return {
        'server': {
            'host': '127.0.0.1',
            'port': 8888
        }
    }

# 在测试中使用
def test_encryption(security_manager):
    """测试加密功能。"""
    key = security_manager.generate_key()
    # ...
```

---

## 贡献指南

### 贡献流程

1. **Fork 项目**
   ```bash
   # 在 GitHub 上 fork 项目
   git clone https://github.com/your-username/rdptool.git
   cd rdptool
   ```

2. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **开发和测试**
   ```bash
   # 编写代码
   # 添加测试
   # 运行测试
   pytest
   ```

4. **提交更改**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **推送分支**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写详细的描述
   - 等待代码审查

### 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### 类型

- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 代码重构
- `test`: 添加或修改测试
- `chore`: 构建过程或辅助工具的变动

#### 示例

```bash
# 新功能
git commit -m "feat(proxy): add SOCKS5 protocol support"

# 错误修复
git commit -m "fix(network): resolve connection timeout issue"

# 文档更新
git commit -m "docs: update API documentation"

# 重构
git commit -m "refactor(core): improve error handling"
```

### 代码审查

#### 审查清单

- [ ] 代码符合项目编码规范
- [ ] 包含适当的测试
- [ ] 测试通过
- [ ] 文档已更新
- [ ] 没有引入安全漏洞
- [ ] 性能影响可接受
- [ ] 向后兼容性

#### 审查流程

1. **自动检查**
   - CI/CD 流水线运行
   - 代码风格检查
   - 测试执行
   - 安全扫描

2. **人工审查**
   - 代码逻辑审查
   - 架构设计审查
   - 性能影响评估
   - 文档完整性检查

3. **反馈和修改**
   - 根据审查意见修改
   - 重新提交
   - 再次审查

4. **合并**
   - 所有检查通过
   - 获得批准
   - 合并到主分支

---

## 发布流程

### 版本管理

使用 [Semantic Versioning](https://semver.org/) 规范：

- **MAJOR**: 不兼容的 API 更改
- **MINOR**: 向后兼容的功能添加
- **PATCH**: 向后兼容的错误修复

### 发布步骤

1. **更新版本号**
   ```python
   # __version__.py
   __version__ = "1.2.0"
   ```

2. **更新变更日志**
   ```markdown
   # CHANGELOG.md
   ## [1.2.0] - 2024-01-01
   ### Added
   - 新功能描述
   
   ### Fixed
   - 错误修复描述
   ```

3. **创建发布标签**
   ```bash
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```

4. **构建和发布**
   ```bash
   # 构建包
   python setup.py sdist bdist_wheel
   
   # 发布到 PyPI
   twine upload dist/*
   ```

5. **创建 GitHub Release**
   - 在 GitHub 上创建 Release
   - 上传构建文件
   - 发布发布说明

---

## 故障排除

### 常见问题

#### 1. 导入错误

```bash
# 问题
ModuleNotFoundError: No module named 'core'

# 解决方案
# 确保在项目根目录运行
# 或者安装为可编辑包
pip install -e .
```

#### 2. 测试失败

```bash
# 问题
test_network.py::TestNetworkManager::test_tcp_connection FAILED

# 解决方案
# 检查网络连接
# 确保端口未被占用
# 检查防火墙设置
```

#### 3. 依赖冲突

```bash
# 问题
ERROR: pip's dependency resolver does not currently consider all the packages

# 解决方案
# 使用虚拟环境
python -m venv fresh_env
source fresh_env/bin/activate
pip install -r requirements.txt
```

### 调试技巧

#### 1. 使用日志

```python
import logging
from utils.logger import get_logger

logger = get_logger(__name__, level='DEBUG')

def debug_function():
    logger.debug("进入函数")
    try:
        # 代码逻辑
        result = some_operation()
        logger.debug(f"操作结果: {result}")
        return result
    except Exception as e:
        logger.error(f"操作失败: {e}", exc_info=True)
        raise
```

#### 2. 使用断点

```python
# 使用 pdb
import pdb

def problematic_function():
    pdb.set_trace()  # 设置断点
    # 代码逻辑
    pass

# 使用 breakpoint() (Python 3.7+)
def another_function():
    breakpoint()  # 设置断点
    # 代码逻辑
    pass
```

#### 3. 性能分析

```python
import cProfile
import pstats

# 性能分析
def profile_function():
    pr = cProfile.Profile()
    pr.enable()
    
    # 要分析的代码
    your_function()
    
    pr.disable()
    stats = pstats.Stats(pr)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # 显示前10个最耗时的函数
```

### 获取帮助

- **文档**: 查看项目文档和 API 参考
- **Issues**: 在 GitHub 上搜索或创建 issue
- **讨论**: 参与项目讨论区
- **邮件**: 发送邮件到 dev@rdptool.com

---

## 工具和资源

### 开发工具

- **代码编辑器**: VS Code, PyCharm
- **版本控制**: Git, GitHub
- **包管理**: pip, conda
- **虚拟环境**: venv, conda
- **代码质量**: flake8, black, isort
- **测试**: pytest, coverage
- **文档**: Sphinx, MkDocs

### 有用的库

- **异步编程**: asyncio, aiohttp
- **网络**: socket, websockets
- **加密**: cryptography, hashlib
- **GUI**: tkinter, PyQt
- **图像处理**: Pillow, OpenCV
- **系统**: psutil, platform

### 学习资源

- [Python 官方文档](https://docs.python.org/)
- [asyncio 文档](https://docs.python.org/3/library/asyncio.html)
- [pytest 文档](https://docs.pytest.org/)
- [PEP 8 风格指南](https://www.python.org/dev/peps/pep-0008/)
- [Real Python](https://realpython.com/)

---

## 联系方式

- **项目主页**: https://github.com/rdptool/rdptool
- **开发者邮箱**: dev@rdptool.com
- **问题反馈**: https://github.com/rdptool/rdptool/issues
- **讨论区**: https://github.com/rdptool/rdptool/discussions

---

*最后更新: 2024-01-01*