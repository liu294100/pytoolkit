#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置文件管理模块

提供配置文件的加载、保存和管理功能：
- 支持多种格式（JSON、YAML、INI）
- 配置验证
- 默认值处理
- 环境变量替换
"""

import json
import configparser
from pathlib import Path
from typing import Dict, Any, Optional, Union
import os
import re
from copy import deepcopy

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

class ConfigError(Exception):
    """配置错误异常"""
    pass

class ConfigManager:
    """
    配置管理器
    
    支持多种配置文件格式和高级功能
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {}
        self.schema: Optional[Dict[str, Any]] = None
        
        if config_file:
            self.load(config_file)
    
    def load(self, config_file: str) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_file: 配置文件路径
        
        Returns:
            配置数据字典
        
        Raises:
            ConfigError: 配置文件加载失败
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise ConfigError(f"配置文件不存在: {config_file}")
        
        try:
            # 根据文件扩展名选择解析器
            suffix = config_path.suffix.lower()
            
            if suffix == '.json':
                self.config_data = self._load_json(config_path)
            elif suffix in ['.yaml', '.yml'] and HAS_YAML:
                self.config_data = self._load_yaml(config_path)
            elif suffix in ['.ini', '.cfg']:
                self.config_data = self._load_ini(config_path)
            else:
                # 尝试自动检测格式
                self.config_data = self._auto_detect_format(config_path)
            
            # 处理环境变量替换
            self.config_data = self._expand_env_vars(self.config_data)
            
            # 验证配置
            if self.schema:
                self._validate_config(self.config_data)
            
            self.config_file = config_file
            return self.config_data
            
        except Exception as e:
            raise ConfigError(f"加载配置文件失败: {e}")
    
    def save(self, config_file: Optional[str] = None) -> None:
        """
        保存配置文件
        
        Args:
            config_file: 配置文件路径，如果为None则使用当前文件
        
        Raises:
            ConfigError: 配置文件保存失败
        """
        target_file = config_file or self.config_file
        
        if not target_file:
            raise ConfigError("未指定配置文件路径")
        
        try:
            config_path = Path(target_file)
            
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 根据文件扩展名选择格式
            suffix = config_path.suffix.lower()
            
            if suffix == '.json':
                self._save_json(config_path)
            elif suffix in ['.yaml', '.yml'] and HAS_YAML:
                self._save_yaml(config_path)
            elif suffix in ['.ini', '.cfg']:
                self._save_ini(config_path)
            else:
                # 默认使用JSON格式
                self._save_json(config_path)
            
            self.config_file = target_file
            
        except Exception as e:
            raise ConfigError(f"保存配置文件失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config_data
        
        # 创建嵌套结构
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置最终值
        config[keys[-1]] = value
    
    def update(self, other_config: Dict[str, Any]) -> None:
        """
        更新配置
        
        Args:
            other_config: 其他配置数据
        """
        self.config_data = merge_config(self.config_data, other_config)
    
    def set_schema(self, schema: Dict[str, Any]) -> None:
        """
        设置配置模式
        
        Args:
            schema: 配置模式定义
        """
        self.schema = schema
    
    def _load_json(self, config_path: Path) -> Dict[str, Any]:
        """加载JSON配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_yaml(self, config_path: Path) -> Dict[str, Any]:
        """加载YAML配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _load_ini(self, config_path: Path) -> Dict[str, Any]:
        """加载INI配置文件"""
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        # 转换为字典格式
        result = {}
        for section_name in config.sections():
            section = {}
            for key, value in config[section_name].items():
                # 尝试转换数据类型
                section[key] = self._convert_value(value)
            result[section_name] = section
        
        return result
    
    def _save_json(self, config_path: Path) -> None:
        """保存JSON配置文件"""
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, ensure_ascii=False, indent=2)
    
    def _save_yaml(self, config_path: Path) -> None:
        """保存YAML配置文件"""
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True)
    
    def _save_ini(self, config_path: Path) -> None:
        """保存INI配置文件"""
        config = configparser.ConfigParser()
        
        for section_name, section_data in self.config_data.items():
            if isinstance(section_data, dict):
                config.add_section(section_name)
                for key, value in section_data.items():
                    config.set(section_name, key, str(value))
        
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)
    
    def _auto_detect_format(self, config_path: Path) -> Dict[str, Any]:
        """自动检测配置文件格式"""
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # 尝试JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # 尝试YAML
        if HAS_YAML:
            try:
                result = yaml.safe_load(content)
                if isinstance(result, dict):
                    return result
            except yaml.YAMLError:
                pass
        
        # 尝试INI
        try:
            config = configparser.ConfigParser()
            config.read_string(content)
            
            result = {}
            for section_name in config.sections():
                section = {}
                for key, value in config[section_name].items():
                    section[key] = self._convert_value(value)
                result[section_name] = section
            
            return result
        except configparser.Error:
            pass
        
        raise ConfigError("无法识别配置文件格式")
    
    def _convert_value(self, value: str) -> Any:
        """转换配置值的数据类型"""
        # 布尔值
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        elif value.lower() in ('false', 'no', 'off', '0'):
            return False
        
        # 数字
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # 字符串
        return value
    
    def _expand_env_vars(self, config: Any) -> Any:
        """展开环境变量"""
        if isinstance(config, dict):
            return {k: self._expand_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._expand_env_vars(item) for item in config]
        elif isinstance(config, str):
            # 替换 ${VAR} 或 $VAR 格式的环境变量
            def replace_env_var(match):
                var_name = match.group(1) or match.group(2)
                return os.environ.get(var_name, match.group(0))
            
            pattern = r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)'
            return re.sub(pattern, replace_env_var, config)
        else:
            return config
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """验证配置"""
        # 简单的配置验证实现
        # 可以扩展为更复杂的JSON Schema验证
        if not self.schema:
            return
        
        def validate_section(data, schema_section, path=""):
            for key, expected_type in schema_section.items():
                current_path = f"{path}.{key}" if path else key
                
                if key not in data:
                    if isinstance(expected_type, dict) and 'required' in expected_type:
                        if expected_type['required']:
                            raise ConfigError(f"缺少必需的配置项: {current_path}")
                    continue
                
                value = data[key]
                
                if isinstance(expected_type, dict):
                    if 'type' in expected_type:
                        expected_type_name = expected_type['type']
                        if expected_type_name == 'dict' and isinstance(value, dict):
                            if 'properties' in expected_type:
                                validate_section(value, expected_type['properties'], current_path)
                        elif not isinstance(value, eval(expected_type_name)):
                            raise ConfigError(f"配置项 {current_path} 类型错误，期望 {expected_type_name}")
                elif not isinstance(value, expected_type):
                    raise ConfigError(f"配置项 {current_path} 类型错误，期望 {expected_type.__name__}")
        
        validate_section(config, self.schema)

def load_config(config_file: str) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_file: 配置文件路径
    
    Returns:
        配置数据字典
    """
    manager = ConfigManager()
    return manager.load(config_file)

def save_config(config_data: Dict[str, Any], config_file: str) -> None:
    """
    保存配置文件
    
    Args:
        config_data: 配置数据
        config_file: 配置文件路径
    """
    manager = ConfigManager()
    manager.config_data = config_data
    manager.save(config_file)

def merge_config(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并配置
    
    Args:
        base_config: 基础配置
        override_config: 覆盖配置
    
    Returns:
        合并后的配置
    """
    result = deepcopy(base_config)
    
    def merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = merge_dict(base[key], value)
            else:
                base[key] = deepcopy(value)
        return base
    
    return merge_dict(result, override_config)

def get_default_config() -> Dict[str, Any]:
    """
    获取默认配置
    
    Returns:
        默认配置字典
    """
    return {
        'server': {
            'host': '0.0.0.0',
            'port': 8888,
            'protocol': 'tcp',
            'max_clients': 10,
            'timeout': 30
        },
        'client': {
            'auto_reconnect': True,
            'reconnect_interval': 5,
            'heartbeat_interval': 30,
            'timeout': 30
        },
        'screen': {
            'method': 'pil',
            'format': 'jpeg',
            'quality': 80,
            'fps': 30,
            'scale_factor': 1.0,
            'monitor_index': 0
        },
        'input': {
            'enable_mouse': True,
            'enable_keyboard': True,
            'security_enabled': True,
            'mouse_sensitivity': 1.0
        },
        'security': {
            'encryption_type': 'aes_256_cbc',
            'auth_method': 'password',
            'require_encryption': True,
            'session_timeout': 3600,
            'max_login_attempts': 3
        },
        'logging': {
            'level': 'INFO',
            'file': 'rdptool.log',
            'max_file_size': 10485760,  # 10MB
            'backup_count': 5,
            'console_output': True
        },
        'performance': {
            'enable_monitoring': True,
            'stats_interval': 60,
            'max_memory_usage': 512,  # MB
            'max_cpu_usage': 80  # %
        }
    }

def create_config_template(config_file: str) -> None:
    """
    创建配置文件模板
    
    Args:
        config_file: 配置文件路径
    """
    default_config = get_default_config()
    save_config(default_config, config_file)

def validate_config_file(config_file: str) -> bool:
    """
    验证配置文件
    
    Args:
        config_file: 配置文件路径
    
    Returns:
        是否有效
    """
    try:
        config = load_config(config_file)
        
        # 基本验证
        required_sections = ['server', 'client', 'screen', 'input', 'security', 'logging']
        for section in required_sections:
            if section not in config:
                return False
        
        return True
        
    except Exception:
        return False

# 配置模式定义
CONFIG_SCHEMA = {
    'server': {
        'type': 'dict',
        'required': True,
        'properties': {
            'host': {'type': 'str', 'required': True},
            'port': {'type': 'int', 'required': True},
            'protocol': {'type': 'str', 'required': True},
            'max_clients': {'type': 'int', 'required': False}
        }
    },
    'client': {
        'type': 'dict',
        'required': True,
        'properties': {
            'auto_reconnect': {'type': 'bool', 'required': False},
            'reconnect_interval': {'type': 'int', 'required': False}
        }
    },
    'logging': {
        'type': 'dict',
        'required': True,
        'properties': {
            'level': {'type': 'str', 'required': True},
            'file': {'type': 'str', 'required': False}
        }
    }
}

# 导出功能
__all__ = [
    'ConfigManager',
    'ConfigError',
    'load_config',
    'save_config',
    'merge_config',
    'get_default_config',
    'create_config_template',
    'validate_config_file',
    'CONFIG_SCHEMA'
]