#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途牛牛帮助中心爬虫配置管理模块
Futu Help Center Crawler Configuration Management
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class CrawlerConfig:
    """爬虫配置类"""
    # 基本参数
    max_depth: int = 3
    max_articles_per_category: int = 50
    max_workers: int = 3
    delay_min: float = 1.0
    delay_max: float = 3.0
    output_dir: str = "docs_deep"
    
    # 网络参数
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # 内容过滤参数
    min_content_length: int = 100
    max_content_length: int = 50000
    
    # 目标URL列表
    target_urls: List[str] = None
    
    # 用户代理
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    def __post_init__(self):
        """初始化后处理"""
        if self.target_urls is None:
            self.target_urls = self.get_default_urls()
    
    @staticmethod
    def get_default_urls() -> List[str]:
        """获取默认URL列表"""
        return [
            # 简体中文版本
            "https://support.futunn.com/categories/2186",  # 基础知识入门
            "https://support.futunn.com/categories/2185",  # 市场介绍
            "https://support.futunn.com/categories/2187",  # 客户端功能
            "https://support.futunn.com/categories/2188",  # 交易相关
            "https://support.futunn.com/categories/2189",  # 账户相关
            
            # 繁体中文（香港）版本
            "https://support.futunn.com/hant/categories/2186",  # 基础知识入門
            "https://support.futunn.com/hant/categories/2185",  # 市場介紹
            "https://support.futunn.com/hant/categories/2187",  # 客戶端功能
            "https://support.futunn.com/hant/categories/2188",  # 交易相關
            "https://support.futunn.com/hant/categories/2189",  # 賬戶相關
            
            # 英语版本
            "https://support.futunn.com/en/categories/2186",  # Getting started
            "https://support.futunn.com/en/categories/2185",  # Market Introduction
            "https://support.futunn.com/en/categories/2187",  # App Features
            "https://support.futunn.com/en/categories/2188",  # Trading
            "https://support.futunn.com/en/categories/2189",  # Account
        ]
    
    def validate(self) -> bool:
        """验证配置参数"""
        if self.max_depth < 1 or self.max_depth > 5:
            raise ValueError("max_depth must be between 1 and 5")
        
        if self.max_articles_per_category < 1:
            raise ValueError("max_articles_per_category must be positive")
        
        if self.max_workers < 1 or self.max_workers > 20:
            raise ValueError("max_workers must be between 1 and 20")
        
        if self.delay_min >= self.delay_max:
            raise ValueError("delay_min must be less than delay_max")
        
        if self.delay_min < 0:
            raise ValueError("delay_min must be non-negative")
        
        if not self.target_urls:
            raise ValueError("target_urls cannot be empty")
        
        # 验证URL格式
        for url in self.target_urls:
            if not url.startswith('https://support.futunn.com/'):
                raise ValueError(f"Invalid URL: {url}")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CrawlerConfig':
        """从字典创建配置"""
        return cls(**data)
    
    def save_to_file(self, file_path: str) -> None:
        """保存配置到文件"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'CrawlerConfig':
        """从文件加载配置"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Config file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = cls.from_dict(data)
        config.validate()
        return config

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.default_config_file = os.path.join(config_dir, "crawler_config.json")
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
    
    def get_default_config(self) -> CrawlerConfig:
        """获取默认配置"""
        return CrawlerConfig()
    
    def load_config(self, config_file: Optional[str] = None) -> CrawlerConfig:
        """加载配置"""
        config_file = config_file or self.default_config_file
        
        try:
            return CrawlerConfig.load_from_file(config_file)
        except FileNotFoundError:
            # 如果配置文件不存在，创建默认配置
            config = self.get_default_config()
            self.save_config(config, config_file)
            return config
    
    def save_config(self, config: CrawlerConfig, config_file: Optional[str] = None) -> None:
        """保存配置"""
        config_file = config_file or self.default_config_file
        config.validate()
        config.save_to_file(config_file)
    
    def create_preset_configs(self) -> None:
        """创建预设配置文件"""
        presets = {
            "quick": CrawlerConfig(
                max_depth=2,
                max_articles_per_category=20,
                max_workers=5,
                delay_min=0.5,
                delay_max=1.5
            ),
            "standard": CrawlerConfig(
                max_depth=3,
                max_articles_per_category=50,
                max_workers=3,
                delay_min=1.0,
                delay_max=3.0
            ),
            "deep": CrawlerConfig(
                max_depth=4,
                max_articles_per_category=100,
                max_workers=2,
                delay_min=2.0,
                delay_max=5.0
            ),
            "comprehensive": CrawlerConfig(
                max_depth=5,
                max_articles_per_category=200,
                max_workers=1,
                delay_min=3.0,
                delay_max=6.0
            )
        }
        
        for name, config in presets.items():
            preset_file = os.path.join(self.config_dir, f"preset_{name}.json")
            self.save_config(config, preset_file)
    
    def list_config_files(self) -> List[str]:
        """列出所有配置文件"""
        if not os.path.exists(self.config_dir):
            return []
        
        config_files = []
        for file in os.listdir(self.config_dir):
            if file.endswith('.json'):
                config_files.append(os.path.join(self.config_dir, file))
        
        return sorted(config_files)
    
    def get_preset_names(self) -> List[str]:
        """获取预设配置名称列表"""
        preset_names = []
        for file_path in self.list_config_files():
            file_name = os.path.basename(file_path)
            if file_name.startswith('preset_') and file_name.endswith('.json'):
                preset_name = file_name[7:-5]  # 移除 'preset_' 前缀和 '.json' 后缀
                preset_names.append(preset_name)
        
        return preset_names

# 全局配置管理器实例
config_manager = ConfigManager()

def get_config(config_file: Optional[str] = None) -> CrawlerConfig:
    """获取配置的便捷函数"""
    return config_manager.load_config(config_file)

def save_config(config: CrawlerConfig, config_file: Optional[str] = None) -> None:
    """保存配置的便捷函数"""
    config_manager.save_config(config, config_file)

if __name__ == '__main__':
    # 测试配置管理
    print("创建默认配置...")
    config = CrawlerConfig()
    print(f"默认配置: {config}")
    
    print("\n创建预设配置...")
    config_manager.create_preset_configs()
    
    print("\n可用的预设配置:")
    for preset in config_manager.get_preset_names():
        print(f"  - {preset}")
    
    print("\n测试配置验证...")
    try:
        invalid_config = CrawlerConfig(max_depth=10)  # 无效深度
        invalid_config.validate()
    except ValueError as e:
        print(f"配置验证失败（预期）: {e}")
    
    print("\n配置管理测试完成！")