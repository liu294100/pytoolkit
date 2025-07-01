#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
输入控制模块

提供远程输入控制功能：
- 鼠标移动、点击、滚轮
- 键盘按键、组合键
- 输入事件队列和批处理
- 安全限制和权限控制
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from queue import Queue, Empty

try:
    from pynput import mouse, keyboard
    from pynput.mouse import Button, Listener as MouseListener
    from pynput.keyboard import Key, Listener as KeyboardListener
except ImportError:
    mouse = None
    keyboard = None
    Button = None
    Key = None
    MouseListener = None
    KeyboardListener = None

logger = logging.getLogger(__name__)

class InputType(Enum):
    """输入类型"""
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_SCROLL = "mouse_scroll"
    MOUSE_DRAG = "mouse_drag"
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    KEY_TYPE = "key_type"
    HOTKEY = "hotkey"

class MouseButton(Enum):
    """鼠标按键"""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"

@dataclass
class InputEvent:
    """输入事件"""
    type: InputType
    data: Dict[str, Any]
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class InputConfig:
    """输入配置"""
    enable_mouse: bool = True
    enable_keyboard: bool = True
    enable_hotkeys: bool = True
    max_queue_size: int = 1000
    batch_size: int = 10
    batch_timeout: float = 0.1
    security_enabled: bool = True
    allowed_keys: Optional[List[str]] = None
    blocked_keys: Optional[List[str]] = None

class InputController:
    """输入控制器"""
    
    def __init__(self, config: InputConfig):
        self.config = config
        self.mouse_controller = None
        self.keyboard_controller = None
        self.event_queue = Queue(maxsize=config.max_queue_size)
        self.is_processing = False
        self.process_thread = None
        self.listeners = []
        
        # 检查依赖
        self._check_dependencies()
        
        # 初始化控制器
        self._init_controllers()
        
        # 安全设置
        self._init_security()
    
    def _check_dependencies(self):
        """检查依赖库"""
        if not mouse or not keyboard:
            raise ImportError("pynput库未安装，请运行: pip install pynput")
    
    def _init_controllers(self):
        """初始化控制器"""
        try:
            if self.config.enable_mouse:
                self.mouse_controller = mouse.Controller()
            
            if self.config.enable_keyboard:
                self.keyboard_controller = keyboard.Controller()
                
            logger.info("输入控制器初始化成功")
            
        except Exception as e:
            logger.error(f"输入控制器初始化失败: {e}")
            raise
    
    def _init_security(self):
        """初始化安全设置"""
        if not self.config.security_enabled:
            return
        
        # 默认阻止的危险按键
        default_blocked = [
            'cmd', 'ctrl+alt+del', 'alt+f4', 'ctrl+shift+esc',
            'win+l', 'win+r', 'alt+tab'
        ]
        
        if self.config.blocked_keys is None:
            self.config.blocked_keys = default_blocked
        else:
            self.config.blocked_keys.extend(default_blocked)
    
    def start_processing(self):
        """开始处理输入事件"""
        if self.is_processing:
            logger.warning("输入处理已在运行")
            return
        
        self.is_processing = True
        self.process_thread = threading.Thread(target=self._process_events, daemon=True)
        self.process_thread.start()
        
        logger.info("开始处理输入事件")
    
    def stop_processing(self):
        """停止处理输入事件"""
        if not self.is_processing:
            return
        
        self.is_processing = False
        
        if self.process_thread and self.process_thread.is_alive():
            self.process_thread.join(timeout=2.0)
        
        # 清空队列
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except Empty:
                break
        
        logger.info("输入事件处理已停止")
    
    def _process_events(self):
        """处理事件循环"""
        batch = []
        last_batch_time = time.time()
        
        while self.is_processing:
            try:
                # 获取事件
                timeout = self.config.batch_timeout
                event = self.event_queue.get(timeout=timeout)
                batch.append(event)
                
                # 检查批处理条件
                current_time = time.time()
                should_process = (
                    len(batch) >= self.config.batch_size or
                    current_time - last_batch_time >= self.config.batch_timeout
                )
                
                if should_process:
                    self._process_batch(batch)
                    batch.clear()
                    last_batch_time = current_time
                    
            except Empty:
                # 超时，处理当前批次
                if batch:
                    self._process_batch(batch)
                    batch.clear()
                    last_batch_time = time.time()
            except Exception as e:
                logger.error(f"处理输入事件错误: {e}")
    
    def _process_batch(self, events: List[InputEvent]):
        """处理事件批次"""
        for event in events:
            try:
                self._execute_event(event)
            except Exception as e:
                logger.error(f"执行输入事件错误: {e}")
    
    def _execute_event(self, event: InputEvent):
        """执行单个事件"""
        if not self._is_event_allowed(event):
            logger.warning(f"事件被安全策略阻止: {event.type}")
            return
        
        if event.type == InputType.MOUSE_MOVE:
            self._execute_mouse_move(event.data)
        elif event.type == InputType.MOUSE_CLICK:
            self._execute_mouse_click(event.data)
        elif event.type == InputType.MOUSE_SCROLL:
            self._execute_mouse_scroll(event.data)
        elif event.type == InputType.MOUSE_DRAG:
            self._execute_mouse_drag(event.data)
        elif event.type == InputType.KEY_PRESS:
            self._execute_key_press(event.data)
        elif event.type == InputType.KEY_RELEASE:
            self._execute_key_release(event.data)
        elif event.type == InputType.KEY_TYPE:
            self._execute_key_type(event.data)
        elif event.type == InputType.HOTKEY:
            self._execute_hotkey(event.data)
    
    def _is_event_allowed(self, event: InputEvent) -> bool:
        """检查事件是否被允许"""
        if not self.config.security_enabled:
            return True
        
        # 检查鼠标事件
        if event.type.value.startswith('mouse') and not self.config.enable_mouse:
            return False
        
        # 检查键盘事件
        if event.type.value.startswith('key') and not self.config.enable_keyboard:
            return False
        
        # 检查阻止的按键
        if event.type in [InputType.KEY_PRESS, InputType.HOTKEY]:
            key_name = event.data.get('key', '').lower()
            if self.config.blocked_keys and key_name in self.config.blocked_keys:
                return False
        
        return True
    
    def _execute_mouse_move(self, data: Dict[str, Any]):
        """执行鼠标移动"""
        if not self.mouse_controller:
            return
        
        x = data.get('x', 0)
        y = data.get('y', 0)
        relative = data.get('relative', False)
        
        if relative:
            current_pos = self.mouse_controller.position
            x += current_pos[0]
            y += current_pos[1]
        
        self.mouse_controller.position = (x, y)
    
    def _execute_mouse_click(self, data: Dict[str, Any]):
        """执行鼠标点击"""
        if not self.mouse_controller:
            return
        
        button_name = data.get('button', 'left')
        clicks = data.get('clicks', 1)
        
        # 转换按键
        if button_name == 'left':
            button = Button.left
        elif button_name == 'right':
            button = Button.right
        elif button_name == 'middle':
            button = Button.middle
        else:
            button = Button.left
        
        # 执行点击
        for _ in range(clicks):
            self.mouse_controller.click(button)
            if clicks > 1:
                time.sleep(0.05)  # 多次点击间隔
    
    def _execute_mouse_scroll(self, data: Dict[str, Any]):
        """执行鼠标滚轮"""
        if not self.mouse_controller:
            return
        
        dx = data.get('dx', 0)
        dy = data.get('dy', 0)
        
        self.mouse_controller.scroll(dx, dy)
    
    def _execute_mouse_drag(self, data: Dict[str, Any]):
        """执行鼠标拖拽"""
        if not self.mouse_controller:
            return
        
        start_x = data.get('start_x', 0)
        start_y = data.get('start_y', 0)
        end_x = data.get('end_x', 0)
        end_y = data.get('end_y', 0)
        button_name = data.get('button', 'left')
        
        # 转换按键
        if button_name == 'left':
            button = Button.left
        elif button_name == 'right':
            button = Button.right
        else:
            button = Button.left
        
        # 执行拖拽
        self.mouse_controller.position = (start_x, start_y)
        self.mouse_controller.press(button)
        self.mouse_controller.position = (end_x, end_y)
        self.mouse_controller.release(button)
    
    def _execute_key_press(self, data: Dict[str, Any]):
        """执行按键按下"""
        if not self.keyboard_controller:
            return
        
        key = self._parse_key(data.get('key', ''))
        if key:
            self.keyboard_controller.press(key)
    
    def _execute_key_release(self, data: Dict[str, Any]):
        """执行按键释放"""
        if not self.keyboard_controller:
            return
        
        key = self._parse_key(data.get('key', ''))
        if key:
            self.keyboard_controller.release(key)
    
    def _execute_key_type(self, data: Dict[str, Any]):
        """执行文本输入"""
        if not self.keyboard_controller:
            return
        
        text = data.get('text', '')
        if text:
            self.keyboard_controller.type(text)
    
    def _execute_hotkey(self, data: Dict[str, Any]):
        """执行组合键"""
        if not self.keyboard_controller:
            return
        
        keys = data.get('keys', [])
        if not keys:
            return
        
        # 解析按键
        parsed_keys = []
        for key_name in keys:
            key = self._parse_key(key_name)
            if key:
                parsed_keys.append(key)
        
        if not parsed_keys:
            return
        
        # 按下所有按键
        for key in parsed_keys:
            self.keyboard_controller.press(key)
        
        # 释放所有按键（逆序）
        for key in reversed(parsed_keys):
            self.keyboard_controller.release(key)
    
    def _parse_key(self, key_name: str):
        """解析按键名称"""
        if not key_name:
            return None
        
        key_name = key_name.lower().strip()
        
        # 特殊按键映射
        special_keys = {
            'ctrl': Key.ctrl,
            'alt': Key.alt,
            'shift': Key.shift,
            'cmd': Key.cmd,
            'win': Key.cmd,
            'enter': Key.enter,
            'space': Key.space,
            'tab': Key.tab,
            'esc': Key.esc,
            'escape': Key.esc,
            'backspace': Key.backspace,
            'delete': Key.delete,
            'home': Key.home,
            'end': Key.end,
            'page_up': Key.page_up,
            'page_down': Key.page_down,
            'up': Key.up,
            'down': Key.down,
            'left': Key.left,
            'right': Key.right,
            'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
            'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
            'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
        }
        
        if key_name in special_keys:
            return special_keys[key_name]
        
        # 普通字符
        if len(key_name) == 1:
            return key_name
        
        return None
    
    # 公共接口方法
    def add_event(self, event: InputEvent) -> bool:
        """添加输入事件"""
        try:
            self.event_queue.put_nowait(event)
            return True
        except:
            logger.warning("输入事件队列已满")
            return False
    
    def mouse_move(self, x: int, y: int, relative: bool = False):
        """鼠标移动"""
        event = InputEvent(
            type=InputType.MOUSE_MOVE,
            data={'x': x, 'y': y, 'relative': relative}
        )
        return self.add_event(event)
    
    def mouse_click(self, button: str = 'left', clicks: int = 1):
        """鼠标点击"""
        event = InputEvent(
            type=InputType.MOUSE_CLICK,
            data={'button': button, 'clicks': clicks}
        )
        return self.add_event(event)
    
    def mouse_scroll(self, dx: int = 0, dy: int = 0):
        """鼠标滚轮"""
        event = InputEvent(
            type=InputType.MOUSE_SCROLL,
            data={'dx': dx, 'dy': dy}
        )
        return self.add_event(event)
    
    def key_press(self, key: str):
        """按键按下"""
        event = InputEvent(
            type=InputType.KEY_PRESS,
            data={'key': key}
        )
        return self.add_event(event)
    
    def key_release(self, key: str):
        """按键释放"""
        event = InputEvent(
            type=InputType.KEY_RELEASE,
            data={'key': key}
        )
        return self.add_event(event)
    
    def key_type(self, text: str):
        """输入文本"""
        event = InputEvent(
            type=InputType.KEY_TYPE,
            data={'text': text}
        )
        return self.add_event(event)
    
    def hotkey(self, *keys):
        """组合键"""
        event = InputEvent(
            type=InputType.HOTKEY,
            data={'keys': list(keys)}
        )
        return self.add_event(event)
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """获取鼠标位置"""
        if self.mouse_controller:
            return self.mouse_controller.position
        return (0, 0)
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self.event_queue.qsize()
    
    def clear_queue(self):
        """清空队列"""
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except Empty:
                break
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'is_processing': self.is_processing,
            'queue_size': self.get_queue_size(),
            'max_queue_size': self.config.max_queue_size,
            'config': {
                'enable_mouse': self.config.enable_mouse,
                'enable_keyboard': self.config.enable_keyboard,
                'enable_hotkeys': self.config.enable_hotkeys,
                'security_enabled': self.config.security_enabled
            }
        }

# 工具函数
def create_input_controller(**kwargs) -> InputController:
    """创建输入控制器"""
    config = InputConfig(**kwargs)
    return InputController(config)