#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主GUI界面 - Main GUI Interface
Dict Learner 的主要图形用户界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any

# 导入核心模块
try:
    from core.dictionary_manager import DictionaryManager, Dictionary
    from core.learning_session import LearningSession, SessionManager
    from core.audio_manager import AudioManager
except ImportError as e:
    print(f"模块导入失败: {e}")
    print("请确保所有核心模块都在正确的位置")

class LanguageManager:
    """语言管理器"""
    
    def __init__(self):
        self.current_language = 'zh'
        self.texts = {
            'zh': {
                'title': 'Dict Learner - 单词记忆与英语肌肉记忆锻炼软件',
                'dictionary_selection': '词典选择',
                'select_dictionary': '选择词典',
                'chapter_selection': '章节选择',
                'chapter': '章节',
                'start_learning': '开始学习',
                'practice_mode': '练习模式',
                'review_mode': '复习模式',
                'dictation_mode': '默写模式',
                'current_word': '当前单词',
                'translation': '翻译',
                'phonetic': '音标',
                'input_word': '请输入单词',
                'submit': '提交',
                'next_word': '下一个',
                'previous_word': '上一个',
                'play_pronunciation': '播放发音',
                'statistics': '统计信息',
                'progress': '进度',
                'accuracy': '准确率',
                'wpm': '每分钟单词数',
                'time_spent': '用时',
                'correct': '正确',
                'incorrect': '错误',
                'try_again': '请重试',
                'session_complete': '会话完成',
                'start_review': '开始复习',
                'start_dictation': '开始默写',
                'settings': '设置',
                'audio_settings': '音频设置',
                'volume': '音量',
                'speech_rate': '语速',
                'auto_pronunciation': '自动发音',
                'theme': '主题',
                'light_theme': '浅色主题',
                'dark_theme': '深色主题',
                'language': '语言',
                'chinese': '中文',
                'english': 'English',
                'save_settings': '保存设置',
                'load_custom_dict': '加载自定义词典',
                'export_results': '导出结果',
                'view_history': '查看历史',
                'clear_history': '清除历史',
                'about': '关于',
                'help': '帮助',
                'exit': '退出',
                'file': '文件',
                'edit': '编辑',
                'view': '查看',
                'tools': '工具',
                'words_completed': '已完成单词',
                'words_remaining': '剩余单词',
                'session_time': '会话时间',
                'average_time_per_word': '平均每词用时',
                'total_attempts': '总尝试次数',
                'error_words': '错误单词',
                'ready': '就绪',
                'learning': '学习中',
                'paused': '已暂停',
                'completed': '已完成'
            },
            'en': {
                'title': 'Dict Learner - Words Learning and English Muscle Memory Training',
                'dictionary_selection': 'Dictionary Selection',
                'select_dictionary': 'Select Dictionary',
                'chapter_selection': 'Chapter Selection',
                'chapter': 'Chapter',
                'start_learning': 'Start Learning',
                'practice_mode': 'Practice Mode',
                'review_mode': 'Review Mode',
                'dictation_mode': 'Dictation Mode',
                'current_word': 'Current Word',
                'translation': 'Translation',
                'phonetic': 'Phonetic',
                'input_word': 'Enter the word',
                'submit': 'Submit',
                'next_word': 'Next',
                'previous_word': 'Previous',
                'play_pronunciation': 'Play Pronunciation',
                'statistics': 'Statistics',
                'progress': 'Progress',
                'accuracy': 'Accuracy',
                'wpm': 'Words Per Minute',
                'time_spent': 'Time Spent',
                'correct': 'Correct',
                'incorrect': 'Incorrect',
                'try_again': 'Try Again',
                'session_complete': 'Session Complete',
                'start_review': 'Start Review',
                'start_dictation': 'Start Dictation',
                'settings': 'Settings',
                'audio_settings': 'Audio Settings',
                'volume': 'Volume',
                'speech_rate': 'Speech Rate',
                'auto_pronunciation': 'Auto Pronunciation',
                'theme': 'Theme',
                'light_theme': 'Light Theme',
                'dark_theme': 'Dark Theme',
                'language': 'Language',
                'chinese': '中文',
                'english': 'English',
                'save_settings': 'Save Settings',
                'load_custom_dict': 'Load Custom Dictionary',
                'export_results': 'Export Results',
                'view_history': 'View History',
                'clear_history': 'Clear History',
                'about': 'About',
                'help': 'Help',
                'exit': 'Exit',
                'file': 'File',
                'edit': 'Edit',
                'view': 'View',
                'tools': 'Tools',
                'words_completed': 'Words Completed',
                'words_remaining': 'Words Remaining',
                'session_time': 'Session Time',
                'average_time_per_word': 'Average Time Per Word',
                'total_attempts': 'Total Attempts',
                'error_words': 'Error Words',
                'ready': 'Ready',
                'learning': 'Learning',
                'paused': 'Paused',
                'completed': 'Completed'
            }
        }
    
    def set_language(self, language: str):
        """设置语言"""
        if language in self.texts:
            self.current_language = language
    
    def get_text(self, key: str) -> str:
        """获取文本"""
        return self.texts[self.current_language].get(key, key)

class DictLearnerGUI:
    """Dict Learner 主GUI类"""
    
    def __init__(self, language: str = 'zh', default_dict: Optional[str] = None):
        self.root = tk.Tk()
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
        self.auto_pronunciation = True
        
        # GUI变量
        self.word_input_var = tk.StringVar()
        self.progress_var = tk.StringVar()
        self.stats_var = tk.StringVar()
        self.status_var = tk.StringVar()
        
        # 设置默认词典
        if default_dict:
            self.dict_manager.load_dictionary(default_dict)
            self.current_dictionary = self.dict_manager.get_current_dictionary()
        
        self._setup_gui()
        self._update_interface_language()
        self._update_status()
    
    def _setup_gui(self):
        """设置GUI界面"""
        # 主窗口设置
        self.root.title(self.language_manager.get_text('title'))
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 创建菜单栏
        self._create_menu_bar()
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建左侧面板（词典选择和设置）
        self._create_left_panel()
        
        # 创建中间面板（学习区域）
        self._create_center_panel()
        
        # 创建右侧面板（统计信息）
        self._create_right_panel()
        
        # 创建底部状态栏
        self._create_status_bar()
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.language_manager.get_text('file'), menu=file_menu)
        file_menu.add_command(label=self.language_manager.get_text('load_custom_dict'), command=self._load_custom_dictionary)
        file_menu.add_command(label=self.language_manager.get_text('export_results'), command=self._export_results)
        file_menu.add_separator()
        file_menu.add_command(label=self.language_manager.get_text('exit'), command=self.root.quit)
        
        # 查看菜单
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.language_manager.get_text('view'), menu=view_menu)
        view_menu.add_command(label=self.language_manager.get_text('view_history'), command=self._view_history)
        view_menu.add_command(label=self.language_manager.get_text('clear_history'), command=self._clear_history)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.language_manager.get_text('tools'), menu=tools_menu)
        tools_menu.add_command(label=self.language_manager.get_text('settings'), command=self._open_settings)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.language_manager.get_text('help'), menu=help_menu)
        help_menu.add_command(label=self.language_manager.get_text('about'), command=self._show_about)
    
    def _create_left_panel(self):
        """创建左侧面板"""
        left_frame = ttk.LabelFrame(self.main_frame, text=self.language_manager.get_text('dictionary_selection'), padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        # 词典选择
        ttk.Label(left_frame, text=self.language_manager.get_text('select_dictionary')).pack(anchor=tk.W)
        
        self.dict_combobox = ttk.Combobox(left_frame, state="readonly", width=20)
        self.dict_combobox.pack(fill=tk.X, pady=(5, 10))
        self.dict_combobox.bind('<<ComboboxSelected>>', self._on_dictionary_selected)
        
        # 章节选择
        ttk.Label(left_frame, text=self.language_manager.get_text('chapter_selection')).pack(anchor=tk.W)
        
        self.chapter_frame = ttk.Frame(left_frame)
        self.chapter_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.chapter_spinbox = ttk.Spinbox(self.chapter_frame, from_=1, to=1, width=10, state="readonly")
        self.chapter_spinbox.pack(side=tk.LEFT)
        self.chapter_spinbox.bind('<ButtonRelease-1>', self._on_chapter_changed)
        
        # 学习模式选择
        ttk.Label(left_frame, text="学习模式").pack(anchor=tk.W, pady=(10, 5))
        
        self.mode_var = tk.StringVar(value="practice")
        ttk.Radiobutton(left_frame, text=self.language_manager.get_text('practice_mode'), 
                       variable=self.mode_var, value="practice").pack(anchor=tk.W)
        ttk.Radiobutton(left_frame, text=self.language_manager.get_text('review_mode'), 
                       variable=self.mode_var, value="review").pack(anchor=tk.W)
        ttk.Radiobutton(left_frame, text=self.language_manager.get_text('dictation_mode'), 
                       variable=self.mode_var, value="dictation").pack(anchor=tk.W)
        
        # 开始学习按钮
        self.start_button = ttk.Button(left_frame, text=self.language_manager.get_text('start_learning'), 
                                      command=self._start_learning)
        self.start_button.pack(fill=tk.X, pady=(20, 0))
        
        # 加载词典列表
        self._load_dictionary_list()
    
    def _create_center_panel(self):
        """创建中间面板"""
        center_frame = ttk.Frame(self.main_frame)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # 学习区域
        learning_frame = ttk.LabelFrame(center_frame, text="学习区域", padding=20)
        learning_frame.pack(fill=tk.BOTH, expand=True)
        
        # 当前单词显示
        self.word_display_frame = ttk.Frame(learning_frame)
        self.word_display_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 单词标签
        self.word_label = ttk.Label(self.word_display_frame, text="", font=('Arial', 24, 'bold'))
        self.word_label.pack()
        
        # 音标标签
        self.phonetic_label = ttk.Label(self.word_display_frame, text="", font=('Arial', 14))
        self.phonetic_label.pack()
        
        # 翻译标签
        self.translation_label = ttk.Label(self.word_display_frame, text="", font=('Arial', 16))
        self.translation_label.pack(pady=(10, 0))
        
        # 输入区域
        input_frame = ttk.Frame(learning_frame)
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(input_frame, text=self.language_manager.get_text('input_word')).pack()
        
        self.word_entry = ttk.Entry(input_frame, textvariable=self.word_input_var, font=('Arial', 16))
        self.word_entry.pack(fill=tk.X, pady=(5, 10))
        self.word_entry.bind('<Return>', self._on_submit_word)
        self.word_entry.bind('<KeyRelease>', self._on_key_release)
        
        # 按钮区域
        button_frame = ttk.Frame(learning_frame)
        button_frame.pack(fill=tk.X)
        
        self.submit_button = ttk.Button(button_frame, text=self.language_manager.get_text('submit'), 
                                       command=self._submit_word)
        self.submit_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.pronunciation_button = ttk.Button(button_frame, text=self.language_manager.get_text('play_pronunciation'), 
                                             command=self._play_pronunciation)
        self.pronunciation_button.pack(side=tk.LEFT, padx=5)
        
        self.next_button = ttk.Button(button_frame, text=self.language_manager.get_text('next_word'), 
                                     command=self._next_word, state=tk.DISABLED)
        self.next_button.pack(side=tk.RIGHT)
        
        self.prev_button = ttk.Button(button_frame, text=self.language_manager.get_text('previous_word'), 
                                     command=self._previous_word, state=tk.DISABLED)
        self.prev_button.pack(side=tk.RIGHT, padx=(0, 5))
        
        # 反馈区域
        self.feedback_label = ttk.Label(learning_frame, text="", font=('Arial', 14))
        self.feedback_label.pack(pady=(20, 0))
    
    def _create_right_panel(self):
        """创建右侧面板"""
        right_frame = ttk.LabelFrame(self.main_frame, text=self.language_manager.get_text('statistics'), padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # 进度信息
        progress_frame = ttk.LabelFrame(right_frame, text=self.language_manager.get_text('progress'), padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_label = ttk.Label(progress_frame, text="0/0", font=('Arial', 12))
        self.progress_label.pack()
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        # 统计信息
        stats_frame = ttk.LabelFrame(right_frame, text="实时统计", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.accuracy_label = ttk.Label(stats_frame, text=f"{self.language_manager.get_text('accuracy')}: 0%")
        self.accuracy_label.pack(anchor=tk.W)
        
        self.wpm_label = ttk.Label(stats_frame, text=f"{self.language_manager.get_text('wpm')}: 0")
        self.wpm_label.pack(anchor=tk.W)
        
        self.time_label = ttk.Label(stats_frame, text=f"{self.language_manager.get_text('time_spent')}: 0s")
        self.time_label.pack(anchor=tk.W)
        
        # 错误单词列表
        error_frame = ttk.LabelFrame(right_frame, text=self.language_manager.get_text('error_words'), padding=10)
        error_frame.pack(fill=tk.BOTH, expand=True)
        
        self.error_listbox = tk.Listbox(error_frame, height=8)
        self.error_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 复习按钮
        self.review_button = ttk.Button(right_frame, text=self.language_manager.get_text('start_review'), 
                                       command=self._start_review, state=tk.DISABLED)
        self.review_button.pack(fill=tk.X, pady=(10, 0))
    
    def _create_status_bar(self):
        """创建状态栏"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X, padx=5, pady=2)
    
    def _load_dictionary_list(self):
        """加载词典列表"""
        dict_list = self.dict_manager.get_dictionary_list()
        dict_names = [f"{d['name']} ({d['total_words']}词)" for d in dict_list]
        
        self.dict_combobox['values'] = dict_names
        self.dict_ids = [d['id'] for d in dict_list]
        
        if dict_names:
            self.dict_combobox.current(0)
            self._on_dictionary_selected()
    
    def _on_dictionary_selected(self, event=None):
        """词典选择事件"""
        selection = self.dict_combobox.current()
        if selection >= 0 and selection < len(self.dict_ids):
            dict_id = self.dict_ids[selection]
            if self.dict_manager.load_dictionary(dict_id):
                self.current_dictionary = self.dict_manager.get_current_dictionary()
                self._update_chapter_selection()
    
    def _update_chapter_selection(self):
        """更新章节选择"""
        if self.current_dictionary:
            self.chapter_spinbox.config(to=self.current_dictionary.chapters)
            self.chapter_spinbox.set("1")
            self.current_chapter = 0
    
    def _on_chapter_changed(self, event=None):
        """章节改变事件"""
        try:
            chapter_num = int(self.chapter_spinbox.get())
            self.current_chapter = chapter_num - 1  # 转换为0基索引
        except ValueError:
            pass
    
    def _start_learning(self):
        """开始学习"""
        if not self.current_dictionary:
            messagebox.showwarning("警告", "请先选择词典")
            return
        
        # 创建学习会话
        self.current_session = self.session_manager.create_session(self.current_dictionary, self.current_chapter)
        
        # 根据模式设置会话
        mode = self.mode_var.get()
        if mode == "review":
            # 检查是否有错误单词可以复习
            if not hasattr(self, 'previous_errors') or not self.previous_errors:
                messagebox.showinfo("提示", "没有错误单词需要复习，将开始正常练习")
                mode = "practice"
            else:
                self.current_session.incorrect_words = self.previous_errors
                self.current_session.start_review_mode()
        elif mode == "dictation":
            self.current_session.start_dictation_mode()
        
        # 开始会话
        self.current_session.start_session()
        self.is_learning = True
        
        # 更新界面
        self._update_learning_interface()
        self._show_current_word()
        
        # 禁用开始按钮，启用其他按钮
        self.start_button.config(state=tk.DISABLED)
        self.submit_button.config(state=tk.NORMAL)
        self.pronunciation_button.config(state=tk.NORMAL)
        
        # 焦点到输入框
        self.word_entry.focus_set()
        
        self._update_status("学习中")
    
    def _show_current_word(self):
        """显示当前单词"""
        if not self.current_session:
            return
        
        current_word = self.current_session.get_current_word()
        if not current_word:
            self._complete_session()
            return
        
        # 开始计时
        self.current_session.start_word()
        
        # 根据模式显示不同内容
        mode = self.mode_var.get()
        if mode == "dictation":
            # 默写模式只显示翻译
            self.word_label.config(text="???")
            self.translation_label.config(text=current_word.translation)
        else:
            # 练习和复习模式显示单词
            self.word_label.config(text=current_word.word)
            self.translation_label.config(text=current_word.translation)
        
        # 显示音标
        self.phonetic_label.config(text=current_word.phonetic)
        
        # 清空输入框和反馈
        self.word_input_var.set("")
        self.feedback_label.config(text="")
        
        # 自动播放发音
        if self.auto_pronunciation and mode != "dictation":
            self._play_pronunciation()
        
        # 更新进度
        self._update_progress()
    
    def _submit_word(self):
        """提交单词"""
        if not self.current_session or not self.is_learning:
            return
        
        user_input = self.word_input_var.get().strip()
        if not user_input:
            return
        
        # 检查答案
        is_correct = self.current_session.check_input(user_input)
        
        if is_correct:
            # 正确答案
            result = self.current_session.submit_word(user_input)
            self.feedback_label.config(text=self.language_manager.get_text('correct'), foreground="green")
            
            # 播放成功音效
            self.audio_manager.play_success_sound()
            
            # 自动进入下一个单词
            self.root.after(1000, self._next_word)
            
        else:
            # 错误答案
            self.feedback_label.config(text=self.language_manager.get_text('try_again'), foreground="red")
            
            # 播放错误音效
            self.audio_manager.play_error_sound()
            
            # 清空输入框
            self.word_input_var.set("")
    
    def _on_submit_word(self, event=None):
        """回车提交单词"""
        self._submit_word()
    
    def _on_key_release(self, event=None):
        """按键释放事件"""
        # 可以在这里添加实时输入检查
        pass
    
    def _next_word(self):
        """下一个单词"""
        if not self.current_session:
            return
        
        if self.current_session.next_word():
            self._show_current_word()
        else:
            self._complete_session()
    
    def _previous_word(self):
        """上一个单词"""
        if not self.current_session:
            return
        
        if self.current_session.previous_word():
            self._show_current_word()
    
    def _play_pronunciation(self):
        """播放发音"""
        if not self.current_session:
            return
        
        current_word = self.current_session.get_current_word()
        if current_word:
            # 在新线程中播放，避免阻塞UI
            threading.Thread(target=lambda: self.audio_manager.play_word_pronunciation(current_word.word), 
                           daemon=True).start()
    
    def _update_progress(self):
        """更新进度"""
        if not self.current_session:
            return
        
        progress = self.current_session.get_progress()
        
        # 更新进度标签
        self.progress_label.config(text=f"{progress['completed_words']}/{progress['total_words']}")
        
        # 更新进度条
        self.progress_bar.config(value=progress['progress_percentage'])
        
        # 更新统计信息
        stats = self.current_session.stats
        self.accuracy_label.config(text=f"{self.language_manager.get_text('accuracy')}: {stats.accuracy:.1f}%")
        self.wpm_label.config(text=f"{self.language_manager.get_text('wpm')}: {stats.wpm:.1f}")
        self.time_label.config(text=f"{self.language_manager.get_text('time_spent')}: {stats.total_time:.1f}s")
        
        # 更新错误单词列表
        self.error_listbox.delete(0, tk.END)
        for word in self.current_session.incorrect_words:
            self.error_listbox.insert(tk.END, word.word)
        
        # 启用复习按钮
        if self.current_session.incorrect_words:
            self.review_button.config(state=tk.NORMAL)
    
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
        
        # 显示完成信息
        stats = session_result.stats
        message = f"""{self.language_manager.get_text('session_complete')}!

统计信息:
{self.language_manager.get_text('accuracy')}: {stats.accuracy:.1f}%
{self.language_manager.get_text('wpm')}: {stats.wpm:.1f}
总用时: {stats.total_time:.1f}秒
错误单词: {stats.incorrect_words}个"""
        
        messagebox.showinfo(self.language_manager.get_text('session_complete'), message)
        
        # 重置界面
        self._reset_learning_interface()
        
        self._update_status("已完成")
    
    def _start_review(self):
        """开始复习"""
        if hasattr(self, 'previous_errors') and self.previous_errors:
            self.mode_var.set("review")
            self._start_learning()
        else:
            messagebox.showinfo("提示", "没有错误单词需要复习")
    
    def _update_learning_interface(self):
        """更新学习界面"""
        # 启用学习相关控件
        self.word_entry.config(state=tk.NORMAL)
        self.submit_button.config(state=tk.NORMAL)
        self.pronunciation_button.config(state=tk.NORMAL)
    
    def _reset_learning_interface(self):
        """重置学习界面"""
        # 清空显示
        self.word_label.config(text="")
        self.phonetic_label.config(text="")
        self.translation_label.config(text="")
        self.feedback_label.config(text="")
        self.word_input_var.set("")
        
        # 重置进度
        self.progress_label.config(text="0/0")
        self.progress_bar.config(value=0)
        
        # 重置统计
        self.accuracy_label.config(text=f"{self.language_manager.get_text('accuracy')}: 0%")
        self.wpm_label.config(text=f"{self.language_manager.get_text('wpm')}: 0")
        self.time_label.config(text=f"{self.language_manager.get_text('time_spent')}: 0s")
        
        # 启用开始按钮
        self.start_button.config(state=tk.NORMAL)
        
        # 禁用学习控件
        self.submit_button.config(state=tk.DISABLED)
        self.pronunciation_button.config(state=tk.DISABLED)
        self.next_button.config(state=tk.DISABLED)
        self.prev_button.config(state=tk.DISABLED)
    
    def _update_interface_language(self):
        """更新界面语言"""
        # 这里可以更新所有界面文本
        self.root.title(self.language_manager.get_text('title'))
    
    def _update_status(self, status: str = None):
        """更新状态栏"""
        if status:
            self.status_var.set(status)
        else:
            self.status_var.set(self.language_manager.get_text('ready'))
    
    def _load_custom_dictionary(self):
        """加载自定义词典"""
        file_path = filedialog.askopenfilename(
            title="选择词典文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            # 这里可以添加加载自定义词典的逻辑
            messagebox.showinfo("提示", "自定义词典加载功能正在开发中")
    
    def _export_results(self):
        """导出结果"""
        messagebox.showinfo("提示", "结果导出功能正在开发中")
    
    def _view_history(self):
        """查看历史"""
        messagebox.showinfo("提示", "历史查看功能正在开发中")
    
    def _clear_history(self):
        """清除历史"""
        if messagebox.askyesno("确认", "确定要清除所有历史记录吗？"):
            messagebox.showinfo("提示", "历史清除功能正在开发中")
    
    def _open_settings(self):
        """打开设置"""
        messagebox.showinfo("提示", "设置功能正在开发中")
    
    def _show_about(self):
        """显示关于信息"""
        about_text = """Dict Learner v1.0.0

单词记忆与英语肌肉记忆锻炼软件
基于 qwerty-learner 项目的 Python 实现

作者: AI Assistant
许可证: MIT License"""
        messagebox.showinfo("关于", about_text)
    
    def run(self):
        """运行应用程序"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            # 清理资源
            if self.audio_manager:
                self.audio_manager.cleanup()