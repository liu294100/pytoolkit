#!/usr/bin/env python3
"""
UWP 网络回环管理器
允许 UWP 应用访问本地代理（回环地址）

功能：
- 勾选应用启用回环
- 保存按钮批量更新
- 搜索过滤应用
- 显示友好中文名称

参考：
- https://github.com/Richasy/LoopbackManager.Desktop
- https://github.com/Lumysia/UWP-LoopBack-Tool
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import ctypes
from ctypes import wintypes, Structure, POINTER, byref, sizeof
from typing import List, Set, Dict
import locale
import re
from winreg import OpenKey, QueryValueEx, HKEY_LOCAL_MACHINE, KEY_READ
import threading
import time


# ========== Windows API 结构体 ==========
class INET_FIREWALL_AC_CAPABILITIES(Structure):
    _fields_ = [
        ("count", wintypes.DWORD),
        ("capabilities", wintypes.LPVOID),
    ]


class INET_FIREWALL_AC_BINARIES(Structure):
    _fields_ = [
        ("count", wintypes.DWORD),
        ("binaries", wintypes.LPVOID),
    ]


class INET_FIREWALL_APP_CONTAINER(Structure):
    _fields_ = [
        ("appContainerSid", wintypes.LPVOID),
        ("userSid", wintypes.LPVOID),
        ("appContainerName", wintypes.LPWSTR),
        ("displayName", wintypes.LPWSTR),
        ("description", wintypes.LPWSTR),
        ("capabilities", INET_FIREWALL_AC_CAPABILITIES),
        ("binaries", INET_FIREWALL_AC_BINARIES),
        ("workingDirectory", wintypes.LPWSTR),
        ("packageFullName", wintypes.LPWSTR),
    ]


# ========== 应用名称映射表（常见应用的中文名称）==========
APP_NAME_MAP = {
    # Microsoft 应用
    'microsoft.edge': 'Edge 浏览器',
    'microsoft.microsoftedge.stable': 'Edge 浏览器',
    'microsoft.windowsstore': 'Microsoft Store 应用商店',
    'microsoft.windowscalculator': '计算器',
    'microsoft.windowsnotepad': '记事本',
    'microsoft.microsoftstickynotes': '便签',
    'microsoft.paint': '画图',
    'microsoft.photos': '照片查看器',
    'microsoft.windows.photos': '照片查看器',
    'microsoft.zunemusic': 'Groove 音乐',
    'microsoft.zunevideo': 'Groove 视频',
    'microsoft.windowsmaps': '地图',
    'microsoft.bingweather': '天气',
    'microsoft.bingnews': '新闻',
    'microsoft.microsoftsolitairecollection': '纸牌游戏',
    'microsoft.skypeapp': 'Skype',
    'microsoft.teams': 'Microsoft Teams',
    'microsoft.teamsmeetingaddon': 'Teams 会议插件',
    'microsoft.microsoftofficehub': 'Office 中心',
    'microsoft.office.onenote': 'OneNote 笔记',
    'microsoft.outlookforwindows': 'Outlook 邮件',
    'microsoft.todos': 'Microsoft To Do 待办事项',
    'microsoft.onedrive': 'OneDrive 云盘',
    'microsoft.onedrivesync': 'OneDrive 同步',
    'microsoft.desktopappinstaller': '应用安装器 (winget)',
    'microsoft.windowsfeedbackhub': '反馈中心',
    'microsoft.gethelp': '获取帮助',
    'microsoft.windowsalarms': '闹钟和时钟',
    'microsoft.windowssoundrecorder': '录音机',
    'microsoft.windowscamera': '相机',
    'microsoft.windowscommunicationsapps': '邮件和日历',
    'microsoft.people': '人脉通讯录',
    'microsoft.mspaint': '画图 3D',
    'microsoft.screensketch': '截图工具',
    'microsoft.yourphone': '手机连接',
    'microsoft.windows.terminal': 'Windows Terminal 终端',
    'microsoft.powertoys': 'PowerToys 工具集',
    'microsoft.xboxapp': 'Xbox 游戏',
    'microsoft.xboxgameoverlay': 'Xbox 游戏栏',
    'microsoft.xboxgamingoverlay': 'Xbox 游戏覆盖',
    'microsoft.xboxidentityprovider': 'Xbox 身份验证',
    'microsoft.xbox.tcui': 'Xbox 服务',
    'microsoft.gamingapp': 'Xbox 游戏应用',
    'microsoft.microsoft3dviewer': '3D 查看器',
    'microsoft.mixedreality.portal': '混合现实门户',
    'microsoft.bingsearch': 'Bing 搜索',
    'microsoft.microsoftedgedevtoolsclient': 'Edge 开发者工具',
    'microsoft.ui.xaml': 'UI 框架组件',
    'microsoft.windowsappruntime': 'Windows 应用运行时',
    'microsoft.windows.devhome': '开发者主页',
    'microsoft.widgetplatform': '小组件',
    'microsoft.microsoftpcmanager': '微软电脑管家',
    
    # 国内应用
    'tencent.qq': 'QQ',
    'tencent.wechat': '微信',
    'tencent.wechatapp': '微信',
    'tencentmeeting': '腾讯会议',
    'tencent.qqmusic': 'QQ音乐',
    'tencent.qqlive': '腾讯视频',
    'tencent.tim': 'TIM',
    '5319dwwrittenote.notebook': '随手记',
    'kingsoft.wps': 'WPS Office',
    'kingsoft.wpsoffice': 'WPS Office',
    'douban.doubanmovie': '豆瓣电影',
    'douban.doubanmusic': '豆瓣FM',
    'netease.cloudmusic': '网易云音乐',
    'netease.mail': '网易邮箱大师',
    'netease.youdao': '有道词典',
    'bilibili': '哔哩哔哩',
    'bilibili.uwp': '哔哩哔哩 UWP',
    'youku.video': '优酷视频',
    'iqiyi.video': '爱奇艺视频',
    'qq.video': '腾讯视频',
    'sohu.video': '搜狐视频',
    'taobao.mobiletaobao': '手机淘宝',
    'jd.mobilejd': '京东',
    'alipay': '支付宝',
    'zhihu': '知乎',
    'weibo': '微博',
    'dianping': '大众点评',
    'meituan': '美团',
    'ele.me': '饿了么',
    'diditaxi': '滴滴出行',
    'douyin': '抖音',
    'tiktok': '抖音国际版',
    'kuaishou': '快手',
    'xiaohongshu': '小红书',
    
    # 开发工具
    'github.atom': 'Atom 编辑器',
    'microsoft.visualstudio': 'Visual Studio',
    'microsoft.visualstudiocode': 'VS Code 编辑器',
    'jetbrains.intellij': 'IntelliJ IDEA',
    'jetbrains.pycharm': 'PyCharm',
    'jetbrains.webstorm': 'WebStorm',
    'notepadplusplus': 'Notepad++ 编辑器',
    'sublimetext': 'Sublime Text',
    
    # 通讯社交
    'discord': 'Discord',
    'telegram': 'Telegram',
    'whatsapp': 'WhatsApp',
    'signal': 'Signal',
    'slack': 'Slack',
    'zoom': 'Zoom 会议',
    'teams': 'Microsoft Teams',
    
    # 媒体娱乐
    'spotify': 'Spotify 音乐',
    'netflix': 'Netflix',
    'youtube': 'YouTube',
    'spotify.music': 'Spotify 音乐',
    'apple.music': 'Apple Music',
    
    # OpenAI
    'openai.chatgpt': 'ChatGPT',
    'openai.codex': 'ChatGPT Copilot',
    'codex': 'ChatGPT Copilot',
    
    # Intel
    'intel.arc': 'Intel Arc 显卡控制中心',
    'intel.graphics': 'Intel 显卡控制中心',
    
    # Clipchamp
    'clipchamp': 'Clipchamp 视频编辑器',
    
    # 其他
    'adobe.photoshop': 'Photoshop',
    'adobe.illustrator': 'Illustrator',
    'adobe.premiere': 'Premiere Pro',
    'adobe.acrobat': 'Adobe Acrobat',
    'dropbox': 'Dropbox',
    'evernote': '印象笔记',
    'notion': 'Notion',
    'spotify': 'Spotify',
    'steam': 'Steam 游戏',
    'epicgames': 'Epic Games',
    'origin': 'EA Origin',
    'uplay': 'Ubisoft Uplay',
    'battle': '战网',
}


# ========== UWP 应用类 ==========
class UWPApp:
    """UWP 应用信息"""
    def __init__(self, name: str, display_name: str, package_name: str, 
                 sid: str, description: str = "", loopback_enabled: bool = False):
        self.name = name
        self.display_name = display_name or name
        self.package_name = package_name
        self.sid = sid
        self.description = description
        self.loopback_enabled = loopback_enabled
        self.temp_enabled = loopback_enabled
        
        # 生成友好名称
        self.friendly_name = self._get_friendly_name()
    
    def _get_friendly_name(self) -> str:
        """获取友好的中文名称"""
        name_lower = self.name.lower()
        
        # 1. 从映射表查找
        for key, friendly in APP_NAME_MAP.items():
            if key in name_lower:
                return friendly
        
        # 2. 如果显示名称不是资源路径，直接使用
        if self.display_name and not self.display_name.startswith('@'):
            return self.display_name
        
        # 3. 从包名提取
        if self.package_name:
            # 提取主要部分（去掉 publisher ID）
            parts = self.package_name.split('_')
            if parts:
                main_part = parts[0]
                # 处理常见格式
                if '.' in main_part:
                    segments = main_part.split('.')
                    # 取最后一个有意义的部分
                    for seg in reversed(segments):
                        if seg and len(seg) > 2 and seg not in ['app', 'uwp', 'desktop']:
                            # 首字母大写
                            return seg.capitalize()
                return main_part
        
        # 4. 从容器名提取
        if self.name:
            name = self.name.replace('_', ' ').replace('.', ' ')
            words = name.split()
            if words:
                # 取最后一个词
                last_word = words[-1]
                if len(last_word) > 2:
                    return last_word.capitalize()
        
        return self.name


# ========== 回环管理器 ==========
class LoopbackManager:
    """回环管理核心"""
    
    NETISO_FLAG_MAX = 0x2
    
    def __init__(self):
        self.apps: List[UWPApp] = []
        self.system_encoding = locale.getpreferredencoding(False) or 'gbk'
        
        try:
            self.firewall_api = ctypes.windll.FirewallAPI
            self.network_isolation_enum = self.firewall_api.NetworkIsolationEnumAppContainers
            self.network_isolation_enum.argtypes = [wintypes.DWORD, POINTER(wintypes.DWORD), POINTER(wintypes.LPVOID)]
            self.network_isolation_enum.restype = wintypes.DWORD
            
            self.network_isolation_free = self.firewall_api.NetworkIsolationFreeAppContainers
            self.network_isolation_free.argtypes = [wintypes.LPVOID]
            self.network_isolation_free.restype = wintypes.DWORD
        except Exception as e:
            print(f"加载 FirewallAPI.dll 失败: {e}")
    
    def _sid_to_string(self, sid_ptr) -> str:
        """SID 指针转字符串"""
        if not sid_ptr:
            return ""
        
        try:
            advapi32 = ctypes.windll.advapi32
            ConvertSidToStringSidW = advapi32.ConvertSidToStringSidW
            ConvertSidToStringSidW.argtypes = [wintypes.LPVOID, POINTER(wintypes.LPWSTR)]
            ConvertSidToStringSidW.restype = wintypes.BOOL
            
            sid_str = wintypes.LPWSTR()
            if ConvertSidToStringSidW(sid_ptr, byref(sid_str)):
                result = sid_str.value if sid_str.value else ""
                ctypes.windll.kernel32.LocalFree(sid_str)
                return result
        except:
            pass
        return ""
    
    def _get_enabled_sids(self) -> Set[str]:
        """获取已启用的 SID"""
        enabled = set()
        try:
            result = subprocess.run(
                ['CheckNetIsolation', 'LoopbackExempt', '-s'],
                capture_output=True,
                encoding=self.system_encoding,
                errors='ignore'
            )
            
            for line in result.stdout.split('\n'):
                if 'SID:' in line:
                    parts = line.split('SID:')
                    if len(parts) > 1:
                        sid = parts[1].strip()
                        if sid.startswith('S-1-15-2-'):
                            enabled.add(sid)
        except:
            pass
        return enabled
    
    def get_uwp_apps(self) -> List[UWPApp]:
        """获取 UWP 应用列表"""
        apps = []
        ptr_array = wintypes.LPVOID()
        count = wintypes.DWORD()
        
        try:
            retval = self.network_isolation_enum(
                self.NETISO_FLAG_MAX,
                byref(count),
                byref(ptr_array)
            )
            
            if retval != 0 or count.value == 0:
                return apps
            
            struct_size = sizeof(INET_FIREWALL_APP_CONTAINER)
            current_ptr = ptr_array.value
            enabled_sids = self._get_enabled_sids()
            
            for i in range(count.value):
                try:
                    container = INET_FIREWALL_APP_CONTAINER.from_address(current_ptr)
                    
                    name = container.appContainerName if container.appContainerName else ""
                    display_name = container.displayName if container.displayName else ""
                    package_name = container.packageFullName if container.packageFullName else ""
                    description = container.description if container.description else ""
                    sid = self._sid_to_string(container.appContainerSid)
                    
                    if name and sid:
                        enabled = sid in enabled_sids
                        apps.append(UWPApp(
                            name=name,
                            display_name=display_name,
                            package_name=package_name,
                            sid=sid,
                            description=description,
                            loopback_enabled=enabled
                        ))
                    
                    current_ptr += struct_size
                except:
                    pass
            
            self.network_isolation_free(ptr_array)
        except Exception as e:
            print(f"获取应用列表失败: {e}")
        
        # 按友好名称排序
        apps.sort(key=lambda x: x.friendly_name.lower())
        self.apps = apps
        return apps
    
    def _run_command(self, cmd: str) -> tuple:
        """执行命令"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                encoding=self.system_encoding,
                errors='ignore'
            )
            output = result.stdout + result.stderr
            success = '完成' in output or 'OK' in output or result.returncode == 0
            return success, output
        except Exception as e:
            return False, str(e)
    
    def enable_loopback(self, sid: str) -> tuple:
        """启用回环"""
        return self._run_command(f'CheckNetIsolation LoopbackExempt -a -p={sid}')
    
    def disable_loopback(self, sid: str) -> tuple:
        """禁用回环"""
        return self._run_command(f'CheckNetIsolation LoopbackExempt -d -p={sid}')
    
    def save_changes(self, apps: List[UWPApp]) -> Dict[str, int]:
        """保存变更"""
        result = {'enabled': 0, 'disabled': 0, 'failed': 0}
        
        for app in apps:
            if app.temp_enabled == app.loopback_enabled:
                continue
            
            if app.temp_enabled:
                success, _ = self.enable_loopback(app.sid)
                if success:
                    app.loopback_enabled = True
                    result['enabled'] += 1
                else:
                    result['failed'] += 1
            else:
                success, _ = self.disable_loopback(app.sid)
                if success:
                    app.loopback_enabled = False
                    result['disabled'] += 1
                else:
                    result['failed'] += 1
        
        return result
    
    def search_apps(self, keyword: str) -> List[UWPApp]:
        """搜索应用"""
        if not keyword:
            return self.apps
        
        keyword = keyword.lower()
        return [app for app in self.apps 
                if keyword in app.name.lower() 
                or keyword in app.display_name.lower()
                or keyword in app.package_name.lower()
                or keyword in app.friendly_name.lower()]


# ========== GUI ==========
class UWPManagerGUI:
    """现代化界面"""
    
    COLORS = {
        'bg_primary': '#1e1e1e',
        'bg_secondary': '#2d2d30',
        'bg_card': '#3e3e42',
        'accent': '#0078d4',
        'accent_hover': '#1e90ff',
        'success': '#4caf50',
        'warning': '#ff9800',
        'danger': '#f44336',
        'text_primary': '#ffffff',
        'text_secondary': '#b0b0b0',
        'border': '#4e4e52',
    }
    
    def __init__(self, root):
        self.root = root
        self.manager = LoopbackManager()
        self.all_apps: List[UWPApp] = []
        self.filtered_apps: List[UWPApp] = []
        self.checkboxes: Dict[str, tk.IntVar] = {}
        self._search_timer = None  # 防抖定时器
        self._search_keyword = ""  # 当前搜索关键词
        
        self._setup_styles()
        self._build_ui()
        self._check_admin()
    
    def _check_admin(self):
        """检查管理员权限"""
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                messagebox.showwarning(
                    "权限提示",
                    "需要管理员权限才能修改回环设置！\n请右键以管理员身份运行。"
                )
        except:
            pass
    
    def _setup_styles(self):
        """配置样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Custom.Vertical.TScrollbar',
                       background=self.COLORS['bg_card'],
                       troughcolor=self.COLORS['bg_secondary'],
                       arrowcolor=self.COLORS['text_primary'])
    
    def _build_ui(self):
        """构建界面"""
        self.root.configure(bg=self.COLORS['bg_primary'])
        self.root.geometry('1250x750')
        self.root.minsize(1000, 600)
        
        main = tk.Frame(self.root, bg=self.COLORS['bg_primary'])
        main.pack(fill='both', expand=True, padx=25, pady=25)
        
        # ===== 标题区 =====
        header = tk.Frame(main, bg=self.COLORS['bg_primary'])
        header.pack(fill='x', pady=(0, 15))
        
        title_frame = tk.Frame(header, bg=self.COLORS['bg_primary'])
        title_frame.pack(side='left')
        
        tk.Label(title_frame, text="🔄 网络回环管理器", 
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_primary'],
                font=('Microsoft YaHei UI', 24, 'bold')).pack(anchor='w')
        
        tk.Label(title_frame, 
                text="勾选需要启用本地网络回环的应用，然后点击保存",
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_secondary'],
                font=('Microsoft YaHei UI', 10)).pack(anchor='w', pady=(5, 0))
        
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(header, textvariable=self.status_var,
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_secondary'],
                font=('Microsoft YaHei UI', 10)).pack(side='right')
        
        # ===== 搜索栏 =====
        search_frame = tk.Frame(main, bg=self.COLORS['bg_primary'])
        search_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(search_frame, text="🔍 搜索应用",
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_secondary'],
                font=('Microsoft YaHei UI', 10)).pack(side='left', padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                bg=self.COLORS['bg_secondary'],
                fg=self.COLORS['text_primary'],
                insertbackground=self.COLORS['text_primary'],
                bd=0, width=40,
                font=('Microsoft YaHei UI', 10))
        search_entry.pack(side='left', ipady=8, padx=(0, 10))
        
        tk.Button(search_frame, text="清空",
                 bg=self.COLORS['bg_card'],
                 fg=self.COLORS['text_primary'],
                 bd=0, padx=15, pady=6,
                 font=('Microsoft YaHei UI', 9),
                 cursor='hand2',
                 command=lambda: self.search_var.set("")).pack(side='left')
        
        self.stats_var = tk.StringVar(value="")
        tk.Label(search_frame, textvariable=self.stats_var,
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_secondary'],
                font=('Microsoft YaHei UI', 10)).pack(side='right')
        
        # ===== 应用列表 =====
        list_frame = tk.Frame(main, bg=self.COLORS['bg_primary'])
        list_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # 列标题
        header_frame = tk.Frame(list_frame, bg=self.COLORS['bg_card'])
        header_frame.pack(fill='x')
        
        tk.Label(header_frame, text="  启用",
                bg=self.COLORS['bg_card'],
                fg=self.COLORS['text_primary'],
                font=('Microsoft YaHei UI', 11, 'bold'),
                width=6).pack(side='left')
        
        tk.Label(header_frame, text="应用名称",
                bg=self.COLORS['bg_card'],
                fg=self.COLORS['text_primary'],
                font=('Microsoft YaHei UI', 11, 'bold'),
                width=25).pack(side='left', padx=(5, 0))
        
        tk.Label(header_frame, text="友好名称",
                bg=self.COLORS['bg_card'],
                fg=self.COLORS['text_primary'],
                font=('Microsoft YaHei UI', 11, 'bold'),
                width=20).pack(side='left', padx=(5, 0))
        
        tk.Label(header_frame, text="包名称",
                bg=self.COLORS['bg_card'],
                fg=self.COLORS['text_primary'],
                font=('Microsoft YaHei UI', 11, 'bold'),
                width=40).pack(side='left', padx=(5, 0))
        
        tk.Label(header_frame, text="状态",
                bg=self.COLORS['bg_card'],
                fg=self.COLORS['text_primary'],
                font=('Microsoft YaHei UI', 11, 'bold'),
                width=10).pack(side='right', padx=(0, 10))
        
        # 可滚动列表
        list_container = tk.Frame(list_frame, bg=self.COLORS['bg_secondary'])
        list_container.pack(fill='both', expand=True)
        
        self.canvas = tk.Canvas(list_container, 
                               bg=self.COLORS['bg_secondary'],
                               highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, 
                                 orient='vertical',
                                 command=self.canvas.yview,
                                 style='Custom.Vertical.TScrollbar')
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.COLORS['bg_secondary'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # ===== 底部按钮区 =====
        footer = tk.Frame(main, bg=self.COLORS['bg_primary'])
        footer.pack(fill='x')
        
        tk.Label(footer, 
                text="💡 提示：启用后应用可以访问本地代理（127.0.0.1），如 Clash、Fiddler 等",
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_secondary'],
                font=('Microsoft YaHei UI', 9)).pack(side='left')
        
        btn_frame = tk.Frame(footer, bg=self.COLORS['bg_primary'])
        btn_frame.pack(side='right')
        
        tk.Button(btn_frame, text="🔄 刷新列表",
                 bg=self.COLORS['bg_card'],
                 fg=self.COLORS['text_primary'],
                 bd=0, padx=20, pady=10,
                 font=('Microsoft YaHei UI', 10),
                 cursor='hand2',
                 command=self._refresh_list).pack(side='left', padx=(0, 10))
        
        tk.Button(btn_frame, text="全选",
                 bg=self.COLORS['bg_card'],
                 fg=self.COLORS['text_primary'],
                 bd=0, padx=20, pady=10,
                 font=('Microsoft YaHei UI', 10),
                 cursor='hand2',
                 command=lambda: self._select_all(True)).pack(side='left', padx=(0, 10))
        
        tk.Button(btn_frame, text="取消全选",
                 bg=self.COLORS['bg_card'],
                 fg=self.COLORS['text_primary'],
                 bd=0, padx=20, pady=10,
                 font=('Microsoft YaHei UI', 10),
                 cursor='hand2',
                 command=lambda: self._select_all(False)).pack(side='left', padx=(0, 10))
        
        tk.Button(btn_frame, text="💾 保存更改",
                 bg=self.COLORS['accent'],
                 fg='white',
                 bd=0, padx=30, pady=10,
                 font=('Microsoft YaHei UI', 11, 'bold'),
                 cursor='hand2',
                 command=self._save_changes).pack(side='left')
    
    def _on_mousewheel(self, event):
        """鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _refresh_list(self):
        """刷新应用列表"""
        self.status_var.set("正在扫描应用...")
        self.root.update()
        
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.checkboxes.clear()
        
        self.all_apps = self.manager.get_uwp_apps()
        self.filtered_apps = self.all_apps
        
        self._render_apps()
        
        self.status_var.set(f"扫描完成")
        self._update_stats()
    
    def _render_apps(self, apps=None):
        """渲染应用列表"""
        if apps is None:
            apps = self.filtered_apps
        
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.checkboxes.clear()
        
        for i, app in enumerate(apps):
            app.temp_enabled = app.loopback_enabled
            
            row_bg = self.COLORS['bg_secondary'] if i % 2 == 0 else self.COLORS['bg_card']
            row = tk.Frame(self.scrollable_frame, bg=row_bg)
            row.pack(fill='x', pady=0)
            
            # 复选框
            var = tk.IntVar(value=1 if app.loopback_enabled else 0)
            self.checkboxes[app.sid] = var
            
            cb = tk.Checkbutton(row, variable=var,
                               bg=row_bg,
                               activebackground=row_bg,
                               selectcolor=self.COLORS['bg_card'],
                               cursor='hand2')
            cb.pack(side='left', padx=(10, 5), pady=10)
            
            def on_change(sid=app.sid, v=var):
                for a in apps:
                    if a.sid == sid:
                        a.temp_enabled = v.get() == 1
                        break
            
            var.trace('w', lambda *args, sid=app.sid, v=var: on_change(sid, v))
            
            # 应用名称（原始名称）
            display_name = app.display_name if app.display_name and not app.display_name.startswith('@') else app.name
            if len(display_name) > 30:
                display_name = display_name[:27] + '...'
            
            tk.Label(row, text=display_name,
                    bg=row_bg,
                    fg=self.COLORS['text_primary'],
                    font=('Microsoft YaHei UI', 10),
                    width=25,
                    anchor='w').pack(side='left', padx=(5, 0))
            
            # 友好名称（中文）
            friendly_name = app.friendly_name
            if len(friendly_name) > 20:
                friendly_name = friendly_name[:17] + '...'
            
            tk.Label(row, text=friendly_name,
                    bg=row_bg,
                    fg='#5dade2',  # 蓝色高亮
                    font=('Microsoft YaHei UI', 10, 'bold'),
                    width=20,
                    anchor='w').pack(side='left', padx=(5, 0))
            
            # 包名称
            package_short = app.package_name[:45] + '...' if len(app.package_name) > 45 else app.package_name
            tk.Label(row, text=package_short,
                    bg=row_bg,
                    fg=self.COLORS['text_secondary'],
                    font=('Microsoft YaHei UI', 9),
                    width=40,
                    anchor='w').pack(side='left', padx=(5, 0))
            
            # 当前状态
            status_text = "✅ 已启用" if app.loopback_enabled else "⚪ 未启用"
            status_color = self.COLORS['success'] if app.loopback_enabled else self.COLORS['text_secondary']
            
            tk.Label(row, text=status_text,
                    bg=row_bg,
                    fg=status_color,
                    font=('Microsoft YaHei UI', 10),
                    width=10).pack(side='right', padx=(0, 10))
        
        self._update_stats()
    
    def _on_search(self, *args):
        """搜索过滤（带防抖）"""
        # 取消之前的定时器
        if self._search_timer:
            self.root.after_cancel(self._search_timer)
        
        # 延迟 200ms 执行搜索
        self._search_timer = self.root.after(200, self._do_search)
    
    def _do_search(self):
        """执行搜索"""
        keyword = self.search_var.get().strip().lower()  # 转小写
        
        # 如果关键词没变，不重新渲染
        if keyword == self._search_keyword:
            return
        
        self._search_keyword = keyword
        
        if not keyword:
            self.filtered_apps = self.all_apps
        else:
            # 不区分大小写搜索
            self.filtered_apps = [
                app for app in self.all_apps
                if keyword in app.name.lower()
                or keyword in app.display_name.lower()
                or keyword in app.package_name.lower()
                or keyword in app.friendly_name.lower()
                or keyword in app.sid.lower()
            ]
        
        self._render_apps(self.filtered_apps)
        
        if keyword:
            self.status_var.set(f"找到 {len(self.filtered_apps)} 个匹配")
        else:
            self.status_var.set("就绪")
    
    def _update_stats(self):
        """更新统计"""
        total = len(self.all_apps)
        enabled = sum(1 for app in self.all_apps if app.loopback_enabled)
        selected = sum(1 for var in self.checkboxes.values() if var.get() == 1)
        self.stats_var.set(f"总计: {total} | 已启用: {enabled} | 已选择: {selected}")
    
    def _select_all(self, select: bool):
        """全选/取消全选"""
        for var in self.checkboxes.values():
            var.set(1 if select else 0)
    
    def _save_changes(self):
        """保存更改"""
        if not self.all_apps:
            messagebox.showinfo("提示", "请先扫描应用")
            return
        
        changed = [app for app in self.all_apps if app.temp_enabled != app.loopback_enabled]
        
        if not changed:
            messagebox.showinfo("提示", "没有需要保存的更改")
            return
        
        enable_count = sum(1 for app in changed if app.temp_enabled)
        disable_count = sum(1 for app in changed if not app.temp_enabled)
        
        msg = f"即将进行以下操作：\n\n"
        if enable_count > 0:
            msg += f"  ✅ 启用 {enable_count} 个应用\n"
        if disable_count > 0:
            msg += f"  ❌ 禁用 {disable_count} 个应用\n"
        msg += f"\n确定要保存吗？"
        
        if not messagebox.askyesno("确认保存", msg):
            return
        
        self.status_var.set("正在保存...")
        self.root.update()
        
        result = self.manager.save_changes(self.all_apps)
        
        self._render_apps(self.filtered_apps)
        
        result_msg = f"保存完成！\n\n"
        if result['enabled'] > 0:
            result_msg += f"  ✅ 成功启用: {result['enabled']}\n"
        if result['disabled'] > 0:
            result_msg += f"  ❌ 成功禁用: {result['disabled']}\n"
        if result['failed'] > 0:
            result_msg += f"  ⚠️ 失败: {result['failed']}\n"
        
        self.status_var.set(f"保存完成：启用 {result['enabled']}，禁用 {result['disabled']}")
        messagebox.showinfo("保存完成", result_msg)


def main():
    root = tk.Tk()
    root.title("网络回环管理器")
    
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = UWPManagerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
