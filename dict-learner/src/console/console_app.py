#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
控制台应用 - Console Application
Dict Learner 的命令行界面
"""

import os
import sys
import time
import threading
from typing import Optional, List
from pathlib import Path

# 导入核心模块
try:
    from core.dictionary_manager import DictionaryManager, Dictionary
    from core.learning_session import LearningSession, SessionManager
    from core.audio_manager import AudioManager
except ImportError as e:
    print(f"模块导入失败: {e}")
    print("请确保所有核心模块都在正确的位置")
    sys.exit(1)

class ConsoleColors:
    """控制台颜色常量"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class LanguageManager:
    """语言管理器"""
    
    def __init__(self):
        self.current_language = 'zh'
        self.texts = {
            'zh': {
                'welcome': '欢迎使用 Dict Learner - 单词记忆与英语肌肉记忆锻炼软件',
                'select_dictionary': '请选择词典',
                'select_chapter': '请选择章节 (1-{max_chapters})',
                'select_mode': '请选择学习模式',
                'practice_mode': '练习模式',
                'review_mode': '复习模式',
                'dictation_mode': '默写模式',
                'start_learning': '开始学习',
                'current_word': '当前单词',
                'translation': '翻译',
                'phonetic': '音标',
                'input_word': '请输入单词',
                'correct': '正确！',
                'incorrect': '错误，请重试',
                'try_again': '请重试',
                'session_complete': '会话完成！',
                'progress': '进度',
                'accuracy': '准确率',
                'wpm': '每分钟单词数',
                'time_spent': '用时',
                'total_attempts': '总尝试次数',
                'error_words': '错误单词',
                'press_enter': '按回车继续...',
                'press_q_quit': '输入 q 退出，回车继续',
                'invalid_input': '无效输入，请重试',
                'no_dictionaries': '没有找到可用的词典',
                'loading_dictionary': '正在加载词典...',
                'dictionary_loaded': '词典加载成功',
                'starting_session': '正在开始学习会话...',
                'session_started': '学习会话已开始',
                'play_pronunciation': '播放发音 (按 p)',
                'next_word': '下一个单词 (按 n)',
                'previous_word': '上一个单词 (按 b)',
                'skip_word': '跳过单词 (按 s)',
                'quit_session': '退出会话 (按 q)',
                'commands_help': '可用命令: p=发音, n=下一个, b=上一个, s=跳过, q=退出',
                'statistics': '统计信息',
                'final_stats': '最终统计',
                'words_completed': '完成单词数',
                'words_remaining': '剩余单词数',
                'session_time': '会话时间',
                'average_time_per_word': '平均每词用时',
                'review_errors': '是否复习错误单词？ (y/n)',
                'no_errors_to_review': '没有错误单词需要复习',
                'starting_review': '开始复习错误单词...',
                'goodbye': '感谢使用 Dict Learner！'
            },
            'en': {
                'welcome': 'Welcome to Dict Learner - Words Learning and English Muscle Memory Training',
                'select_dictionary': 'Please select a dictionary',
                'select_chapter': 'Please select a chapter (1-{max_chapters})',
                'select_mode': 'Please select learning mode',
                'practice_mode': 'Practice Mode',
                'review_mode': 'Review Mode',
                'dictation_mode': 'Dictation Mode',
                'start_learning': 'Start Learning',
                'current_word': 'Current Word',
                'translation': 'Translation',
                'phonetic': 'Phonetic',
                'input_word': 'Enter the word',
                'correct': 'Correct!',
                'incorrect': 'Incorrect, please try again',
                'try_again': 'Try again',
                'session_complete': 'Session Complete!',
                'progress': 'Progress',
                'accuracy': 'Accuracy',
                'wpm': 'Words Per Minute',
                'time_spent': 'Time Spent',
                'total_attempts': 'Total Attempts',
                'error_words': 'Error Words',
                'press_enter': 'Press Enter to continue...',
                'press_q_quit': 'Enter q to quit, Enter to continue',
                'invalid_input': 'Invalid input, please try again',
                'no_dictionaries': 'No dictionaries found',
                'loading_dictionary': 'Loading dictionary...',
                'dictionary_loaded': 'Dictionary loaded successfully',
                'starting_session': 'Starting learning session...',
                'session_started': 'Learning session started',
                'play_pronunciation': 'Play pronunciation (press p)',
                'next_word': 'Next word (press n)',
                'previous_word': 'Previous word (press b)',
                'skip_word': 'Skip word (press s)',
                'quit_session': 'Quit session (press q)',
                'commands_help': 'Available commands: p=pronunciation, n=next, b=back, s=skip, q=quit',
                'statistics': 'Statistics',
                'final_stats': 'Final Statistics',
                'words_completed': 'Words Completed',
                'words_remaining': 'Words Remaining',
                'session_time': 'Session Time',
                'average_time_per_word': 'Average Time Per Word',
                'review_errors': 'Review error words? (y/n)',
                'no_errors_to_review': 'No error words to review',
                'starting_review': 'Starting review of error words...',
                'goodbye': 'Thank you for using Dict Learner!'
            }
        }
    
    def set_language(self, language: str):
        """设置语言"""
        if language in self.texts:
            self.current_language = language
    
    def get_text(self, key: str, **kwargs) -> str:
        """获取文本"""
        text = self.texts[self.current_language].get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        return text

class DictLearnerConsole:
    """Dict Learner 控制台应用类"""
    
    def __init__(self, language: str = 'zh', default_dict: Optional[str] = None):
        self.language_manager = LanguageManager()
        self.language_manager.set_language(language)
        
        # 核心管理器
        self.dict_manager = DictionaryManager()
        self.session_manager = SessionManager()
        self.audio_manager = AudioManager()
        
        # 当前状态
        self.current_session: Optional[LearningSession] = None
        self.current_dictionary: Optional[Dictionary] = None
        self.current_chapter = 0
        self.is_learning = False
        self.previous_errors = []
        
        # 设置默认词典
        if default_dict:
            self.dict_manager.load_dictionary(default_dict)
            self.current_dictionary = self.dict_manager.get_current_dictionary()
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """打印标题"""
        print(f"{ConsoleColors.HEADER}{ConsoleColors.BOLD}")
        print("=" * 80)
        print(self.language_manager.get_text('welcome').center(80))
        print("=" * 80)
        print(f"{ConsoleColors.ENDC}")
    
    def print_colored(self, text: str, color: str = ConsoleColors.ENDC):
        """打印彩色文本"""
        print(f"{color}{text}{ConsoleColors.ENDC}")
    
    def get_user_input(self, prompt: str, valid_options: Optional[List[str]] = None) -> str:
        """获取用户输入"""
        while True:
            try:
                user_input = input(f"{ConsoleColors.OKCYAN}{prompt}: {ConsoleColors.ENDC}").strip()
                
                if valid_options:
                    if user_input.lower() in [opt.lower() for opt in valid_options]:
                        return user_input.lower()
                    else:
                        self.print_colored(self.language_manager.get_text('invalid_input'), ConsoleColors.WARNING)
                        continue
                
                return user_input
            except KeyboardInterrupt:
                print("\n")
                self.print_colored(self.language_manager.get_text('goodbye'), ConsoleColors.OKGREEN)
                sys.exit(0)
    
    def select_dictionary(self) -> bool:
        """选择词典"""
        dict_list = self.dict_manager.get_dictionary_list()
        
        if not dict_list:
            self.print_colored(self.language_manager.get_text('no_dictionaries'), ConsoleColors.FAIL)
            return False
        
        print(f"\n{ConsoleColors.OKBLUE}{self.language_manager.get_text('select_dictionary')}:{ConsoleColors.ENDC}")
        
        for i, dict_info in enumerate(dict_list, 1):
            print(f"{i}. {dict_info['name']} ({dict_info['total_words']}词)")
        
        while True:
            try:
                choice = int(self.get_user_input("请输入选择 (1-{})".format(len(dict_list))))
                if 1 <= choice <= len(dict_list):
                    dict_id = dict_list[choice - 1]['id']
                    
                    self.print_colored(self.language_manager.get_text('loading_dictionary'), ConsoleColors.WARNING)
                    
                    if self.dict_manager.load_dictionary(dict_id):
                        self.current_dictionary = self.dict_manager.get_current_dictionary()
                        self.print_colored(self.language_manager.get_text('dictionary_loaded'), ConsoleColors.OKGREEN)
                        return True
                    else:
                        self.print_colored("词典加载失败", ConsoleColors.FAIL)
                        return False
                else:
                    self.print_colored(self.language_manager.get_text('invalid_input'), ConsoleColors.WARNING)
            except ValueError:
                self.print_colored(self.language_manager.get_text('invalid_input'), ConsoleColors.WARNING)
    
    def select_chapter(self) -> bool:
        """选择章节"""
        if not self.current_dictionary:
            return False
        
        max_chapters = self.current_dictionary.chapters
        prompt = self.language_manager.get_text('select_chapter', max_chapters=max_chapters)
        
        while True:
            try:
                choice = int(self.get_user_input(prompt))
                if 1 <= choice <= max_chapters:
                    self.current_chapter = choice - 1  # 转换为0基索引
                    return True
                else:
                    self.print_colored(self.language_manager.get_text('invalid_input'), ConsoleColors.WARNING)
            except ValueError:
                self.print_colored(self.language_manager.get_text('invalid_input'), ConsoleColors.WARNING)
    
    def select_mode(self) -> str:
        """选择学习模式"""
        print(f"\n{ConsoleColors.OKBLUE}{self.language_manager.get_text('select_mode')}:{ConsoleColors.ENDC}")
        print(f"1. {self.language_manager.get_text('practice_mode')}")
        print(f"2. {self.language_manager.get_text('review_mode')}")
        print(f"3. {self.language_manager.get_text('dictation_mode')}")
        
        while True:
            try:
                choice = int(self.get_user_input("请输入选择 (1-3)"))
                if choice == 1:
                    return "practice"
                elif choice == 2:
                    if self.previous_errors:
                        return "review"
                    else:
                        self.print_colored(self.language_manager.get_text('no_errors_to_review'), ConsoleColors.WARNING)
                        return "practice"
                elif choice == 3:
                    return "dictation"
                else:
                    self.print_colored(self.language_manager.get_text('invalid_input'), ConsoleColors.WARNING)
            except ValueError:
                self.print_colored(self.language_manager.get_text('invalid_input'), ConsoleColors.WARNING)
    
    def start_learning_session(self, mode: str):
        """开始学习会话"""
        self.print_colored(self.language_manager.get_text('starting_session'), ConsoleColors.WARNING)
        
        # 创建学习会话
        self.current_session = self.session_manager.create_session(self.current_dictionary, self.current_chapter)
        
        # 根据模式设置会话
        if mode == "review":
            self.current_session.incorrect_words = self.previous_errors
            self.current_session.start_review_mode()
        elif mode == "dictation":
            self.current_session.start_dictation_mode()
        
        # 开始会话
        self.current_session.start_session()
        self.is_learning = True
        
        self.print_colored(self.language_manager.get_text('session_started'), ConsoleColors.OKGREEN)
        time.sleep(1)
        
        # 开始学习循环
        self._learning_loop(mode)
    
    def _learning_loop(self, mode: str):
        """学习循环"""
        while self.is_learning and self.current_session:
            current_word = self.current_session.get_current_word()
            
            if not current_word:
                self._complete_session()
                break
            
            # 显示当前单词
            self._show_current_word(current_word, mode)
            
            # 开始计时
            self.current_session.start_word()
            
            # 获取用户输入
            user_input = self._get_word_input(current_word, mode)
            
            if user_input == "quit":
                self.is_learning = False
                break
            elif user_input == "skip":
                self.current_session.next_word()
                continue
            elif user_input == "next":
                self.current_session.next_word()
                continue
            elif user_input == "back":
                self.current_session.previous_word()
                continue
            elif user_input == "pronunciation":
                self._play_pronunciation(current_word)
                continue
            
            # 检查答案
            if user_input:
                is_correct = self.current_session.check_input(user_input)
                
                if is_correct:
                    result = self.current_session.submit_word(user_input)
                    self.print_colored(self.language_manager.get_text('correct'), ConsoleColors.OKGREEN)
                    
                    # 播放成功音效
                    threading.Thread(target=self.audio_manager.play_success_sound, daemon=True).start()
                    
                    # 显示统计信息
                    self._show_progress()
                    
                    # 自动进入下一个单词
                    time.sleep(1)
                    self.current_session.next_word()
                    
                else:
                    self.print_colored(self.language_manager.get_text('incorrect'), ConsoleColors.FAIL)
                    
                    # 播放错误音效
                    threading.Thread(target=self.audio_manager.play_error_sound, daemon=True).start()
                    
                    # 显示正确答案
                    self.print_colored(f"正确答案: {current_word.word}", ConsoleColors.WARNING)
                    
                    input(self.language_manager.get_text('press_enter'))
    
    def _show_current_word(self, word, mode: str):
        """显示当前单词"""
        self.clear_screen()
        self.print_header()
        
        # 显示进度
        progress = self.current_session.get_progress()
        print(f"{ConsoleColors.OKBLUE}{self.language_manager.get_text('progress')}: {progress['completed_words']}/{progress['total_words']} ({progress['progress_percentage']:.1f}%){ConsoleColors.ENDC}")
        print()
        
        # 根据模式显示不同内容
        if mode == "dictation":
            # 默写模式只显示翻译
            print(f"{ConsoleColors.BOLD}{self.language_manager.get_text('current_word')}: ???{ConsoleColors.ENDC}")
            print(f"{ConsoleColors.OKGREEN}{self.language_manager.get_text('translation')}: {word.translation}{ConsoleColors.ENDC}")
        else:
            # 练习和复习模式显示单词
            print(f"{ConsoleColors.BOLD}{self.language_manager.get_text('current_word')}: {word.word}{ConsoleColors.ENDC}")
            print(f"{ConsoleColors.OKGREEN}{self.language_manager.get_text('translation')}: {word.translation}{ConsoleColors.ENDC}")
        
        # 显示音标
        if word.phonetic:
            print(f"{ConsoleColors.OKCYAN}{self.language_manager.get_text('phonetic')}: {word.phonetic}{ConsoleColors.ENDC}")
        
        print()
        
        # 显示命令帮助
        print(f"{ConsoleColors.WARNING}{self.language_manager.get_text('commands_help')}{ConsoleColors.ENDC}")
        print()
        
        # 自动播放发音（非默写模式）
        if mode != "dictation":
            self._play_pronunciation(word)
    
    def _get_word_input(self, word, mode: str) -> str:
        """获取单词输入"""
        while True:
            user_input = self.get_user_input(self.language_manager.get_text('input_word')).strip()
            
            # 处理特殊命令
            if user_input.lower() in ['q', 'quit']:
                return "quit"
            elif user_input.lower() in ['s', 'skip']:
                return "skip"
            elif user_input.lower() in ['n', 'next']:
                return "next"
            elif user_input.lower() in ['b', 'back']:
                return "back"
            elif user_input.lower() in ['p', 'pronunciation']:
                return "pronunciation"
            elif user_input:
                return user_input
    
    def _play_pronunciation(self, word):
        """播放发音"""
        def play_audio():
            self.audio_manager.play_word_pronunciation(word.word)
        
        threading.Thread(target=play_audio, daemon=True).start()
    
    def _show_progress(self):
        """显示进度信息"""
        if not self.current_session:
            return
        
        progress = self.current_session.get_progress()
        stats = self.current_session.stats
        
        print(f"\n{ConsoleColors.OKBLUE}{self.language_manager.get_text('statistics')}:{ConsoleColors.ENDC}")
        print(f"{self.language_manager.get_text('accuracy')}: {stats.accuracy:.1f}%")
        print(f"{self.language_manager.get_text('wpm')}: {stats.wpm:.1f}")
        print(f"{self.language_manager.get_text('time_spent')}: {stats.total_time:.1f}s")
        print(f"{self.language_manager.get_text('words_completed')}: {progress['completed_words']}")
        print(f"{self.language_manager.get_text('words_remaining')}: {progress['total_words'] - progress['completed_words']}")
    
    def _complete_session(self):
        """完成会话"""
        if not self.current_session:
            return
        
        self.is_learning = False
        
        # 获取会话结果
        session_result = self.current_session.get_session_result()
        
        # 保存结果
        self.session_manager.save_session_result(session_result)
        
        # 保存错误单词用于复习
        self.previous_errors = self.current_session.incorrect_words.copy()
        
        # 显示最终统计
        self._show_final_stats(session_result)
        
        # 询问是否复习错误单词
        if self.previous_errors:
            review_choice = self.get_user_input(
                self.language_manager.get_text('review_errors'), 
                ['y', 'n', 'yes', 'no']
            )
            
            if review_choice in ['y', 'yes']:
                self.print_colored(self.language_manager.get_text('starting_review'), ConsoleColors.WARNING)
                time.sleep(1)
                self.start_learning_session("review")
    
    def _show_final_stats(self, session_result):
        """显示最终统计"""
        self.clear_screen()
        self.print_header()
        
        stats = session_result.stats
        
        print(f"{ConsoleColors.OKGREEN}{ConsoleColors.BOLD}{self.language_manager.get_text('session_complete')}{ConsoleColors.ENDC}")
        print()
        
        print(f"{ConsoleColors.OKBLUE}{self.language_manager.get_text('final_stats')}:{ConsoleColors.ENDC}")
        print(f"{self.language_manager.get_text('accuracy')}: {stats.accuracy:.1f}%")
        print(f"{self.language_manager.get_text('wpm')}: {stats.wpm:.1f}")
        print(f"总用时: {stats.total_time:.1f}秒")
        print(f"正确单词: {stats.correct_words}")
        print(f"错误单词: {stats.incorrect_words}")
        print(f"总尝试次数: {stats.total_attempts}")
        
        if session_result.incorrect_words:
            print(f"\n{ConsoleColors.WARNING}错误单词列表:{ConsoleColors.ENDC}")
            for word in session_result.incorrect_words:
                print(f"- {word.word} ({word.translation})")
        
        print()
        input(self.language_manager.get_text('press_enter'))
    
    def run(self):
        """运行应用程序"""
        try:
            self.clear_screen()
            self.print_header()
            
            # 选择词典
            if not self.current_dictionary:
                if not self.select_dictionary():
                    return
            
            # 选择章节
            if not self.select_chapter():
                return
            
            # 选择模式并开始学习
            mode = self.select_mode()
            self.start_learning_session(mode)
            
        except KeyboardInterrupt:
            print("\n")
            self.print_colored(self.language_manager.get_text('goodbye'), ConsoleColors.OKGREEN)
        finally:
            # 清理资源
            if self.audio_manager:
                self.audio_manager.cleanup()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dict Learner Console Application')
    parser.add_argument('--language', '-l', choices=['zh', 'en'], default='zh',
                       help='Interface language (zh/en)')
    parser.add_argument('--dictionary', '-d', type=str,
                       help='Default dictionary to load')
    
    args = parser.parse_args()
    
    app = DictLearnerConsole(language=args.language, default_dict=args.dictionary)
    app.run()

if __name__ == "__main__":
    main()