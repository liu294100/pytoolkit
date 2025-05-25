#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM提供商模块
为不同的LLM模型提供统一的接口
"""

import os
import json
from typing import Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod

# 导入各种LLM客户端库
try:
    import openai
except ImportError:
    openai = None

try:
    import anthropics
except ImportError:
    anthropics = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    ollama = None
    OLLAMA_AVAILABLE = False

try:
    import deepseek
    # 检查deepseek模块是否有Client属性
    if hasattr(deepseek, 'Client'):
        DEEPSEEK_AVAILABLE = True
    else:
        print("警告: deepseek模块已安装但缺少Client类")
        DEEPSEEK_AVAILABLE = False
except ImportError:
    deepseek = None
    DEEPSEEK_AVAILABLE = False

try:
    import claudeai
    CLAUDEAI_AVAILABLE = True
except ImportError:
    claudeai = None
    CLAUDEAI_AVAILABLE = False

class LLMProvider(ABC):
    """LLM提供商基类"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查服务是否可用"""
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI API提供商"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4", **kwargs):
        self.model = model
        self.kwargs = kwargs
        
        # 设置API密钥
        if api_key:
            openai.api_key = api_key
        elif os.environ.get("OPENAI_API_KEY"):
            openai.api_key = os.environ.get("OPENAI_API_KEY")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """使用OpenAI API生成文本"""
        try:
            params = {**self.kwargs, **kwargs}
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **params
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API错误: {str(e)}")
            return f"生成失败: {str(e)}"
    
    def is_available(self) -> bool:
        """检查OpenAI API是否可用"""
        return bool(openai.api_key)

class GroqProvider(LLMProvider):
    """Groq API提供商"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama3-8b-8192", **kwargs):
        self.model = model
        self.kwargs = kwargs
        
        # 设置API密钥
        if api_key:
            self.client = Groq(api_key=api_key)
        elif os.environ.get("GROQ_API_KEY"):
            self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        else:
            self.client = None
    
    def generate(self, prompt: str, **kwargs) -> str:
        """使用Groq API生成文本"""
        if not self.client:
            return "Groq API密钥未设置"
            
        try:
            params = {**self.kwargs, **kwargs}
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **params
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq API错误: {str(e)}")
            return f"生成失败: {str(e)}"
    
    def is_available(self) -> bool:
        """检查Groq API是否可用"""
        return self.client is not None

class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) API提供商"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-opus-20240229", **kwargs):
        self.model = model
        self.kwargs = kwargs
        
        # 设置API密钥
        if api_key:
            self.client = anthropics.Anthropic(api_key=api_key)
        elif os.environ.get("ANTHROPIC_API_KEY"):
            self.client = anthropics.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        else:
            self.client = None
    
    def generate(self, prompt: str, **kwargs) -> str:
        """使用Anthropic API生成文本"""
        if not self.client:
            return "Anthropic API密钥未设置"
            
        try:
            params = {**self.kwargs, **kwargs}
            
            response = self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **params
            )
            
            return response.content[0].text
        except Exception as e:
            print(f"Anthropic API错误: {str(e)}")
            return f"生成失败: {str(e)}"
    
    def is_available(self) -> bool:
        """检查Anthropic API是否可用"""
        return self.client is not None

class ClaudeAIProvider(LLMProvider):
    """Claude AI客户端提供商"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-opus-20240229", **kwargs):
        self.model = model
        self.kwargs = kwargs
        
        if not CLAUDEAI_AVAILABLE:
            self.client = None
            return
            
        # 设置API密钥
        if api_key:
            self.client = claudeai.Client(api_key=api_key)
        elif os.environ.get("CLAUDE_API_KEY"):
            self.client = claudeai.Client(api_key=os.environ.get("CLAUDE_API_KEY"))
        else:
            self.client = None
    
    def generate(self, prompt: str, **kwargs) -> str:
        """使用Claude AI客户端生成文本"""
        if not CLAUDEAI_AVAILABLE:
            return "Claude AI客户端未安装"
            
        if not self.client:
            return "Claude API密钥未设置"
            
        try:
            params = {**self.kwargs, **kwargs}
            
            response = self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **params
            )
            
            return response.content[0].text
        except Exception as e:
            print(f"Claude AI错误: {str(e)}")
            return f"生成失败: {str(e)}"
    
    def is_available(self) -> bool:
        """检查Claude AI是否可用"""
        return CLAUDEAI_AVAILABLE and self.client is not None

class GeminiProvider(LLMProvider):
    """Google Gemini API提供商"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro", **kwargs):
        self.model = model
        self.kwargs = kwargs
        
        # 设置API密钥
        if api_key:
            genai.configure(api_key=api_key)
        elif os.environ.get("GOOGLE_API_KEY"):
            genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    
    def generate(self, prompt: str, **kwargs) -> str:
        """使用Google Gemini API生成文本"""
        try:
            params = {**self.kwargs, **kwargs}
            
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt, **params)
            
            return response.text
        except Exception as e:
            print(f"Gemini API错误: {str(e)}")
            return f"生成失败: {str(e)}"
    
    def is_available(self) -> bool:
        """检查Gemini API是否可用"""
        try:
            return bool(genai._client.api_key)
        except:
            return False

class DeepSeekProvider(LLMProvider):
    """DeepSeek API提供商"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat", **kwargs):
        self.model = model
        self.kwargs = kwargs
        
        if not DEEPSEEK_AVAILABLE:
            self.client = None
            return
            
        # 设置API密钥
        if api_key:
            self.client = deepseek.Client(api_key=api_key)
        elif os.environ.get("DEEPSEEK_API_KEY"):
            self.client = deepseek.Client(api_key=os.environ.get("DEEPSEEK_API_KEY"))
        else:
            self.client = None
    
    def generate(self, prompt: str, **kwargs) -> str:
        """使用DeepSeek API生成文本"""
        if not DEEPSEEK_AVAILABLE:
            return "DeepSeek客户端未安装"
            
        if not self.client:
            return "DeepSeek API密钥未设置"
            
        try:
            params = {**self.kwargs, **kwargs}
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **params
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"DeepSeek API错误: {str(e)}")
            return f"生成失败: {str(e)}"
    
    def is_available(self) -> bool:
        """检查DeepSeek API是否可用"""
        return DEEPSEEK_AVAILABLE and self.client is not None

class OllamaProvider(LLMProvider):
    """Ollama本地LLM提供商"""
    
    def __init__(self, model: str = "llama3", **kwargs):
        self.model = model
        self.kwargs = kwargs
    
    def generate(self, prompt: str, **kwargs) -> str:
        """使用Ollama生成文本"""
        if not OLLAMA_AVAILABLE:
            return "Ollama未安装"
            
        try:
            params = {**self.kwargs, **kwargs}
            
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **params
            )
            
            return response['message']['content']
        except Exception as e:
            print(f"Ollama错误: {str(e)}")
            return f"生成失败: {str(e)}"
    
    def is_available(self) -> bool:
        """检查Ollama是否可用"""
        if not OLLAMA_AVAILABLE:
            return False
            
        try:
            # 尝试列出模型以检查Ollama是否运行
            ollama.list()
            return True
        except:
            return False

def get_provider(provider_name: str, config: Dict) -> LLMProvider:
    """获取指定的LLM提供商实例"""
    providers = {
        "openai": OpenAIProvider,
        "groq": GroqProvider,
        "anthropic": AnthropicProvider,
        "claude": ClaudeAIProvider,
        "gemini": GeminiProvider,
        "deepseek": DeepSeekProvider,
        "ollama": OllamaProvider
    }
    
    if provider_name not in providers:
        raise ValueError(f"未知的提供商: {provider_name}")
        
    return providers[provider_name](**config)

def list_available_providers() -> List[str]:
    """列出所有可用的LLM提供商"""
    available = []
    
    # 检查OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        available.append("openai")
        
    # 检查Groq
    if os.environ.get("GROQ_API_KEY"):
        available.append("groq")
        
    # 检查Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        available.append("anthropic")
        
    # 检查Claude
    if CLAUDEAI_AVAILABLE and os.environ.get("CLAUDE_API_KEY"):
        available.append("claude")
        
    # 检查Gemini
    if os.environ.get("GOOGLE_API_KEY"):
        available.append("gemini")
        
    # 检查DeepSeek
    if DEEPSEEK_AVAILABLE and os.environ.get("DEEPSEEK_API_KEY"):
        available.append("deepseek")
        
    # 检查Ollama
    if OLLAMA_AVAILABLE:
        try:
            ollama.list()
            available.append("ollama")
        except:
            pass
            
    return available

# 测试代码
def main():
    """测试各种LLM提供商"""
    from config import API_CONFIG
    
    # 测试提示
    prompt = "分析苹果公司(AAPL)的投资价值，给出买入、卖出或持有的建议。"
    
    # 测试可用的提供商
    available_providers = list_available_providers()
    print(f"可用的LLM提供商: {available_providers}")
    
    # 测试OpenAI
    if "openai" in available_providers:
        provider = get_provider("openai", API_CONFIG["openai"])
        print("\nOpenAI测试:")
        print(provider.generate(prompt))
    
    # 测试Ollama
    if "ollama" in available_providers:
        provider = get_provider("ollama", API_CONFIG["ollama"])
        print("\nOllama测试:")
        print(provider.generate(prompt))

if __name__ == "__main__":
    main()