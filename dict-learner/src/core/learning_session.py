#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习会话管理器 - Learning Session Manager
负责管理学习进度、统计数据和用户输入验证
"""

import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from .dictionary_manager import Word, Dictionary

@dataclass
class TypingStats:
    """打字统计数据"""
    total_words: int = 0
    correct_words: int = 0
    incorrect_words: int = 0
    total_characters: int = 0
    correct_characters: int = 0
    total_time: float = 0.0  # 总时间（秒）
    
    @property
    def accuracy(self) -> float:
        """准确率"""
        if self.total_words == 0:
            return 0.0
        return (self.correct_words / self.total_words) * 100
    
    @property
    def wpm(self) -> float:
        """每分钟单词数"""
        if self.total_time == 0:
            return 0.0
        return (self.correct_words / self.total_time) * 60
    
    @property
    def cpm(self) -> float:
        """每分钟字符数"""
        if self.total_time == 0:
            return 0.0
        return (self.correct_characters / self.total_time) * 60

@dataclass
class WordResult:
    """单词练习结果"""
    word: str
    translation: str
    user_input: str
    is_correct: bool
    attempts: int
    time_spent: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SessionResult:
    """会话结果"""
    session_id: str
    dictionary_name: str
    chapter: int
    start_time: str
    end_time: str
    word_results: List[WordResult]
    stats: TypingStats
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "dictionary_name": self.dictionary_name,
            "chapter": self.chapter,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "word_results": [result.to_dict() for result in self.word_results],
            "stats": asdict(self.stats)
        }

class LearningSession:
    """学习会话管理器"""
    
    def __init__(self, dictionary: Dictionary, chapter: int = 0):
        self.dictionary = dictionary
        self.chapter = chapter
        self.words = dictionary.get_chapter_words(chapter)
        self.current_word_index = 0
        self.word_results: List[WordResult] = []
        self.stats = TypingStats()
        
        # 时间记录
        self.session_start_time = None
        self.word_start_time = None
        
        # 会话ID
        self.session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(self)}"
        
        # 错误单词列表（用于复习）
        self.incorrect_words: List[Word] = []
        
        # 当前模式
        self.mode = "practice"  # practice, review, dictation
    
    def start_session(self):
        """开始会话"""
        self.session_start_time = time.time()
        self.current_word_index = 0
        self.word_results.clear()
        self.stats = TypingStats()
        self.incorrect_words.clear()
    
    def start_word(self):
        """开始单词练习"""
        self.word_start_time = time.time()
    
    def get_current_word(self) -> Optional[Word]:
        """获取当前单词"""
        if self.current_word_index < len(self.words):
            return self.words[self.current_word_index]
        return None
    
    def check_input(self, user_input: str) -> bool:
        """检查用户输入"""
        current_word = self.get_current_word()
        if not current_word:
            return False
        
        # 去除首尾空格，转换为小写进行比较
        user_input = user_input.strip().lower()
        correct_word = current_word.word.lower()
        
        return user_input == correct_word
    
    def submit_word(self, user_input: str, attempts: int = 1) -> WordResult:
        """提交单词答案"""
        current_word = self.get_current_word()
        if not current_word:
            raise ValueError("没有当前单词")
        
        # 计算用时
        time_spent = time.time() - self.word_start_time if self.word_start_time else 0
        
        # 检查答案
        is_correct = self.check_input(user_input)
        
        # 创建结果记录
        result = WordResult(
            word=current_word.word,
            translation=current_word.translation,
            user_input=user_input.strip(),
            is_correct=is_correct,
            attempts=attempts,
            time_spent=time_spent,
            timestamp=datetime.now().isoformat()
        )
        
        # 更新统计数据
        self.stats.total_words += 1
        self.stats.total_characters += len(current_word.word)
        self.stats.total_time += time_spent
        
        if is_correct:
            self.stats.correct_words += 1
            self.stats.correct_characters += len(current_word.word)
        else:
            self.stats.incorrect_words += 1
            # 添加到错误单词列表
            if current_word not in self.incorrect_words:
                self.incorrect_words.append(current_word)
        
        # 保存结果
        self.word_results.append(result)
        
        return result
    
    def next_word(self) -> bool:
        """移动到下一个单词"""
        self.current_word_index += 1
        return self.current_word_index < len(self.words)
    
    def previous_word(self) -> bool:
        """移动到上一个单词"""
        if self.current_word_index > 0:
            self.current_word_index -= 1
            return True
        return False
    
    def get_progress(self) -> Dict[str, Any]:
        """获取进度信息"""
        total_words = len(self.words)
        completed_words = len(self.word_results)
        
        return {
            "current_index": self.current_word_index,
            "total_words": total_words,
            "completed_words": completed_words,
            "progress_percentage": (completed_words / total_words * 100) if total_words > 0 else 0,
            "remaining_words": total_words - completed_words
        }
    
    def is_completed(self) -> bool:
        """检查会话是否完成"""
        return self.current_word_index >= len(self.words)
    
    def get_session_result(self) -> SessionResult:
        """获取会话结果"""
        end_time = datetime.now().isoformat()
        start_time = datetime.fromtimestamp(self.session_start_time).isoformat() if self.session_start_time else end_time
        
        return SessionResult(
            session_id=self.session_id,
            dictionary_name=self.dictionary.name,
            chapter=self.chapter,
            start_time=start_time,
            end_time=end_time,
            word_results=self.word_results.copy(),
            stats=self.stats
        )
    
    def start_review_mode(self):
        """开始复习模式（复习错误单词）"""
        if not self.incorrect_words:
            return False
        
        self.mode = "review"
        self.words = self.incorrect_words.copy()
        self.current_word_index = 0
        self.word_results.clear()
        
        # 重置统计数据
        self.stats = TypingStats()
        self.session_start_time = time.time()
        
        return True
    
    def start_dictation_mode(self):
        """开始默写模式"""
        self.mode = "dictation"
        # 在默写模式下，不显示单词，只显示翻译
        self.current_word_index = 0
        
    def get_dictation_hint(self) -> Optional[str]:
        """获取默写提示（翻译）"""
        current_word = self.get_current_word()
        if current_word:
            return current_word.translation
        return None
    
    def reset_session(self):
        """重置会话"""
        self.current_word_index = 0
        self.word_results.clear()
        self.stats = TypingStats()
        self.incorrect_words.clear()
        self.session_start_time = None
        self.word_start_time = None
        self.mode = "practice"

class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.sessions_dir = self.data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[LearningSession] = None
        self.session_history: List[SessionResult] = []
    
    def create_session(self, dictionary: Dictionary, chapter: int = 0) -> LearningSession:
        """创建新会话"""
        self.current_session = LearningSession(dictionary, chapter)
        return self.current_session
    
    def get_current_session(self) -> Optional[LearningSession]:
        """获取当前会话"""
        return self.current_session
    
    def save_session_result(self, session_result: SessionResult) -> bool:
        """保存会话结果"""
        try:
            # 保存到文件
            session_file = self.sessions_dir / f"{session_result.session_id}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_result.to_dict(), f, ensure_ascii=False, indent=2)
            
            # 添加到历史记录
            self.session_history.append(session_result)
            
            return True
        except Exception as e:
            print(f"保存会话结果失败: {e}")
            return False
    
    def load_session_history(self) -> List[SessionResult]:
        """加载会话历史"""
        history = []
        
        try:
            for session_file in self.sessions_dir.glob("*.json"):
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 重建WordResult对象
                word_results = []
                for wr_data in data.get("word_results", []):
                    word_results.append(WordResult(**wr_data))
                
                # 重建TypingStats对象
                stats_data = data.get("stats", {})
                stats = TypingStats(**stats_data)
                
                # 创建SessionResult对象
                session_result = SessionResult(
                    session_id=data["session_id"],
                    dictionary_name=data["dictionary_name"],
                    chapter=data["chapter"],
                    start_time=data["start_time"],
                    end_time=data["end_time"],
                    word_results=word_results,
                    stats=stats
                )
                
                history.append(session_result)
        
        except Exception as e:
            print(f"加载会话历史失败: {e}")
        
        # 按时间排序
        history.sort(key=lambda x: x.start_time, reverse=True)
        self.session_history = history
        
        return history
    
    def get_statistics_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        if not self.session_history:
            return {
                "total_sessions": 0,
                "total_words": 0,
                "average_accuracy": 0,
                "average_wpm": 0,
                "total_time": 0
            }
        
        total_sessions = len(self.session_history)
        total_words = sum(session.stats.total_words for session in self.session_history)
        total_time = sum(session.stats.total_time for session in self.session_history)
        
        accuracies = [session.stats.accuracy for session in self.session_history if session.stats.total_words > 0]
        wpms = [session.stats.wpm for session in self.session_history if session.stats.total_time > 0]
        
        return {
            "total_sessions": total_sessions,
            "total_words": total_words,
            "average_accuracy": sum(accuracies) / len(accuracies) if accuracies else 0,
            "average_wpm": sum(wpms) / len(wpms) if wpms else 0,
            "total_time": total_time
        }