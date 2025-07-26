#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频管理器 - Audio Manager
负责单词发音、TTS功能和音频播放
"""

import os
import threading
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import time

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("警告: pygame未安装，音频功能将受限")

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    print("警告: pyttsx3未安装，离线TTS功能将不可用")

try:
    from gtts import gTTS
    import requests
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    print("警告: gtts未安装，在线TTS功能将不可用")

class AudioManager:
    """音频管理器"""
    
    def __init__(self):
        self.is_initialized = False
        self.tts_engine = None
        self.audio_cache_dir = Path(__file__).parent.parent.parent / "data" / "audio_cache"
        self.audio_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 音频设置
        self.volume = 0.7
        self.speech_rate = 150  # 语速
        self.voice_language = "en"  # 默认英语
        
        # 初始化音频系统
        self._initialize_audio()
        self._initialize_tts()
    
    def _initialize_audio(self):
        """初始化音频系统"""
        if not PYGAME_AVAILABLE:
            print("pygame不可用，音频播放功能将受限")
            return
        
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.is_initialized = True
            print("音频系统初始化成功")
        except Exception as e:
            print(f"音频系统初始化失败: {e}")
            self.is_initialized = False
    
    def _initialize_tts(self):
        """初始化TTS引擎"""
        if not PYTTSX3_AVAILABLE:
            return
        
        try:
            self.tts_engine = pyttsx3.init()
            
            # 设置语音属性
            voices = self.tts_engine.getProperty('voices')
            if voices:
                # 尝试找到英语语音
                for voice in voices:
                    if 'english' in voice.name.lower() or 'en' in voice.id.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
            
            # 设置语速和音量
            self.tts_engine.setProperty('rate', self.speech_rate)
            self.tts_engine.setProperty('volume', self.volume)
            
            print("TTS引擎初始化成功")
        except Exception as e:
            print(f"TTS引擎初始化失败: {e}")
            self.tts_engine = None
    
    def set_volume(self, volume: float):
        """设置音量 (0.0 - 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        if self.tts_engine:
            self.tts_engine.setProperty('volume', self.volume)
    
    def set_speech_rate(self, rate: int):
        """设置语速"""
        self.speech_rate = max(50, min(300, rate))
        if self.tts_engine:
            self.tts_engine.setProperty('rate', self.speech_rate)
    
    def set_voice_language(self, language: str):
        """设置语音语言"""
        self.voice_language = language
        
        if self.tts_engine:
            voices = self.tts_engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if language.lower() in voice.id.lower() or language.lower() in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
    
    def play_word_pronunciation(self, word: str, use_online: bool = True) -> bool:
        """播放单词发音"""
        # 首先尝试从缓存加载
        cached_file = self._get_cached_audio_file(word)
        if cached_file and cached_file.exists():
            return self._play_audio_file(cached_file)
        
        # 尝试在线TTS
        if use_online and GTTS_AVAILABLE:
            if self._generate_online_tts(word):
                cached_file = self._get_cached_audio_file(word)
                if cached_file and cached_file.exists():
                    return self._play_audio_file(cached_file)
        
        # 回退到离线TTS
        return self._play_offline_tts(word)
    
    def _get_cached_audio_file(self, word: str) -> Path:
        """获取缓存的音频文件路径"""
        safe_filename = "".join(c for c in word if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return self.audio_cache_dir / f"{safe_filename}_{self.voice_language}.mp3"
    
    def _generate_online_tts(self, word: str) -> bool:
        """生成在线TTS音频"""
        try:
            # 检查网络连接
            response = requests.get("https://www.google.com", timeout=3)
            if response.status_code != 200:
                return False
            
            # 生成TTS
            tts = gTTS(text=word, lang=self.voice_language, slow=False)
            
            # 保存到缓存
            cached_file = self._get_cached_audio_file(word)
            tts.save(str(cached_file))
            
            return True
        except Exception as e:
            print(f"在线TTS生成失败: {e}")
            return False
    
    def _play_offline_tts(self, word: str) -> bool:
        """播放离线TTS"""
        if not self.tts_engine:
            print("TTS引擎不可用")
            return False
        
        try:
            # 在新线程中播放，避免阻塞UI
            def speak():
                self.tts_engine.say(word)
                self.tts_engine.runAndWait()
            
            thread = threading.Thread(target=speak, daemon=True)
            thread.start()
            
            return True
        except Exception as e:
            print(f"离线TTS播放失败: {e}")
            return False
    
    def _play_audio_file(self, file_path: Path) -> bool:
        """播放音频文件"""
        if not self.is_initialized or not PYGAME_AVAILABLE:
            print("音频系统未初始化")
            return False
        
        try:
            # 在新线程中播放音频
            def play():
                pygame.mixer.music.load(str(file_path))
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play()
                
                # 等待播放完成
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            
            thread = threading.Thread(target=play, daemon=True)
            thread.start()
            
            return True
        except Exception as e:
            print(f"音频文件播放失败: {e}")
            return False
    
    def play_success_sound(self):
        """播放成功音效"""
        # 可以播放预设的成功音效，这里用TTS代替
        self._play_offline_tts("Correct")
    
    def play_error_sound(self):
        """播放错误音效"""
        # 可以播放预设的错误音效，这里用TTS代替
        self._play_offline_tts("Try again")
    
    def speak_text(self, text: str, use_online: bool = False) -> bool:
        """朗读文本"""
        if use_online and GTTS_AVAILABLE:
            return self._speak_text_online(text)
        else:
            return self._speak_text_offline(text)
    
    def _speak_text_online(self, text: str) -> bool:
        """在线朗读文本"""
        try:
            # 检查网络连接
            response = requests.get("https://www.google.com", timeout=3)
            if response.status_code != 200:
                return self._speak_text_offline(text)
            
            # 生成临时音频文件
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                tts = gTTS(text=text, lang=self.voice_language, slow=False)
                tts.save(temp_file.name)
                
                # 播放音频
                result = self._play_audio_file(Path(temp_file.name))
                
                # 清理临时文件
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
                
                return result
        except Exception as e:
            print(f"在线文本朗读失败: {e}")
            return self._speak_text_offline(text)
    
    def _speak_text_offline(self, text: str) -> bool:
        """离线朗读文本"""
        if not self.tts_engine:
            return False
        
        try:
            def speak():
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            
            thread = threading.Thread(target=speak, daemon=True)
            thread.start()
            
            return True
        except Exception as e:
            print(f"离线文本朗读失败: {e}")
            return False
    
    def clear_audio_cache(self) -> bool:
        """清理音频缓存"""
        try:
            for audio_file in self.audio_cache_dir.glob("*.mp3"):
                audio_file.unlink()
            return True
        except Exception as e:
            print(f"清理音频缓存失败: {e}")
            return False
    
    def get_cache_size(self) -> int:
        """获取缓存大小（字节）"""
        total_size = 0
        try:
            for audio_file in self.audio_cache_dir.glob("*.mp3"):
                total_size += audio_file.stat().st_size
        except Exception as e:
            print(f"获取缓存大小失败: {e}")
        return total_size
    
    def get_available_voices(self) -> list:
        """获取可用的语音列表"""
        voices = []
        if self.tts_engine:
            try:
                engine_voices = self.tts_engine.getProperty('voices')
                for voice in engine_voices:
                    voices.append({
                        'id': voice.id,
                        'name': voice.name,
                        'language': getattr(voice, 'languages', ['unknown'])
                    })
            except Exception as e:
                print(f"获取语音列表失败: {e}")
        return voices
    
    def test_audio_system(self) -> Dict[str, bool]:
        """测试音频系统"""
        results = {
            'pygame_available': PYGAME_AVAILABLE,
            'pygame_initialized': self.is_initialized,
            'pyttsx3_available': PYTTSX3_AVAILABLE,
            'tts_engine_ready': self.tts_engine is not None,
            'gtts_available': GTTS_AVAILABLE,
            'network_available': False
        }
        
        # 测试网络连接
        if GTTS_AVAILABLE:
            try:
                response = requests.get("https://www.google.com", timeout=3)
                results['network_available'] = response.status_code == 200
            except:
                results['network_available'] = False
        
        return results
    
    def cleanup(self):
        """清理资源"""
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except:
                pass
        
        if PYGAME_AVAILABLE and self.is_initialized:
            try:
                pygame.mixer.quit()
            except:
                pass