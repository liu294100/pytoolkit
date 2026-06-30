#!/usr/bin/env python3
"""
UWP 网络回环管理器
允许 UWP 应用访问本地代理（回环地址）
参考: https://github.com/Lumysia/UWP-LoopBack-Tool
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import json
import locale
import ctypes
from typing import Dict, List, Set
from winreg import (
    OpenKey, CloseKey, EnumKey, EnumValue, QueryInfoKey,
    HKEY_CURRENT_USER, KEY_READ
)


class UWPApp:
    """UWP 应用信息"""
    def __init__(self, name: str, sid: str, display_name: str = "", loopback_enabled: bool = False):
        self.name = name  # 应用名称
        self.sid = sid  # AppContainer SID
        self.display_name = display_name or name
        self.loopback_enabled = loopback_enabled
    
    def to_dict(self):
        return {
            'name': self.name,
            'sid': self.sid,
            'display_name': self.display_name,
            'loopback_enabled': self.loopback_enabled
        }


class LoopbackManager:
    """回环管理核心 - 使用注册表获取应用列表"""
    
    # 注册表路径
    REG_ROOT = HKEY_CURRENT_USER
    REG_PATH = r'SOFTWARE\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppContainer\Mappings'
    
    CONFIG_FILE = "uwp_loopback_config.json"
    
    def __init__(self):
        self.apps: List[UWPApp] = []
        self.system_encoding = locale.getpreferredencoding(False) or 'gbk'
    
    def _rename_app(self, app_name: str) -> str:
        """清理应用名称"""
        if '@' in app_name:
            # 从 @{xxx.xxx_...} 格式提取
            parts = app_name.split('_')
            if len(parts) > 0:
                name = parts[0]
                if '{' in name:
                    name = name.split('{')[1].replace('.', ' ')
                return name
        
        # 下划线替换为空格
        return app_name.replace('_', ' ')
    
    def _get_apps_from_registry(self) -> Dict[str, str]:
        """从注册表获取所有 UWP 应用的名称和 SID"""
        apps = {}
        
        try:
            # 打开注册表键
            key_handle = OpenKey(self.REG_ROOT, self.REG_PATH, 0, KEY_READ)
            
            # 获取子键数量
            subkey_count = QueryInfoKey(key_handle)[0]
            
            for i in range(subkey_count):
                try:
                    # 枚举子键（SID）
                    sid = EnumKey(key_handle, i)
                    
                    # 打开子键获取应用名称
                    try:
                        subkey = OpenKey(key_handle, sid, 0, KEY_READ)
                        app_name_raw = EnumValue(subkey, 0)[1]  # 第一个值是应用名称
                        app_name = self._rename_app(app_name_raw)
                        CloseKey(subkey)
                        
                        if app_name:
                            apps[app_name] = sid
                    except:
                        pass
                except:
                    pass
            
            CloseKey(key_handle)
        except Exception as e:
            print(f"读取注册表失败: {e}")
        
        return apps
    
    def _get_enabled_sids(self) -> Set[str]:
        """获取已启用回环的应用 SID 列表"""
        enabled = set()
        
        try:
            result = subprocess.run(
                ['CheckNetIsolation', 'LoopbackExempt', '-s'],
                capture_output=True,
                encoding=self.system_encoding,
                errors='ignore'
            )
            
            output = result.stdout
            # 解析 SID
            for line in output.split('\n'):
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
        """获取所有 UWP 应用及其回环状态"""
        # 从注册表获取应用列表
        apps_dict = self._get_apps_from_registry()
        
        # 获取已启用的 SID
        enabled_sids = self._get_enabled_sids()
        
        # 构建应用列表
        apps = []
        for name, sid in apps_dict.items():
            enabled = sid in enabled_sids
            apps.append(UWPApp(name, sid, name, enabled))
        
        # 按名称排序
        apps.sort(key=lambda x: x.name.lower())
        
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
        """启用应用的回环访问（使用 SID）"""
        cmd = f'CheckNetIsolation LoopbackExempt -a -p={sid}'
        return self._run_command(cmd)
    
    def disable_loopback(self, sid: str) -> tuple:
        """禁用应用的回环访问（使用 SID）"""
        cmd = f'CheckNetIsolation LoopbackExempt -d -p={sid}'
        return self._run_command(cmd)
    
    def enable_all(self) -> tuple:
        """启用所有应用"""
        success_count = 0
        fail_count = 0
        
        for app in self.apps:
            success, _ = self.enable_loopback(app.sid)
            if success:
                app.loopback_enabled = True
                success_count += 1
            else:
                fail_count += 1
        
        return success_count, fail_count
    
    def disable_all(self) -> tuple:
        """禁用所有应用"""
        success_count = 0
        fail_count = 0
        
        for app in self.apps:
            success, _ = self.disable_loopback(app.sid)
            if success:
                app.loopback_enabled = False
                success_count += 1
            else:
                fail_count += 1
        
        return success_count, fail_count
    
    def search_apps(self, keyword: str) -> List[UWPApp]:
        """搜索应用"""
        if not keyword:
            return self.apps
        
        keyword = keyword.lower()
        return [app for app in self.apps 
                if keyword in app.name.lower()]
    
    def save_config(self):
        """保存配置"""
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump([app.to_dict() for app in self.apps], f, indent=2, ensure_ascii=False)
    
    def load_config(self) -> List[UWPApp]:
        """加载配置"""
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [UWPApp(**item) for item in data]
        except:
            return []


# ========== GUI ==========
class UWPManagerGUI:
    """现代化界面"""
    
    COLORS = {
        'bg_primary': '#0f0f1a',
        'bg_secondary': '#1a1a2e',
        'bg_card': '#16213e',
        'accent': '#4f46e5',
        'accent_hover': '#6366f1',
        'success': '#10b981',
        'warning': '#f59e0b',
        'danger': '#ef4444',
        'text_primary': '#f3f4f6',
        'text_secondary': '#9ca3af',
        'border': '#374151',
    }
    
    def __init__(self, root):
        self.root = root
        self.manager = LoopbackManager()
        self.all_apps: List[UWPApp] = []
        
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
        
        style.configure('Custom.Treeview',
                       background=self.COLORS['bg_secondary'],
                       foreground=self.COLORS['text_primary'],
                       fieldbackground=self.COLORS['bg_secondary'],
                       borderwidth=0,
                       rowheight=38,
                       font=('Microsoft YaHei UI', 10))
        
        style.configure('Custom.Treeview.Heading',
                       background=self.COLORS['bg_card'],
                       foreground=self.COLORS['text_primary'],
                       borderwidth=0,
                       font=('Microsoft YaHei UI', 11, 'bold'))
        
        style.map('Custom.Treeview',
                 background=[('selected', self.COLORS['accent'])])
    
    def _build_ui(self):
        """构建界面"""
        self.root.configure(bg=self.COLORS['bg_primary'])
        self.root.geometry('1100x750')
        self.root.minsize(900, 600)
        
        main = tk.Frame(self.root, bg=self.COLORS['bg_primary'])
        main.pack(fill='both', expand=True, padx=25, pady=25)
        
        # 标题
        header = tk.Frame(main, bg=self.COLORS['bg_primary'])
        header.pack(fill='x', pady=(0, 20))
        
        tk.Label(header, text="🔧 UWP 回环代理管理器", 
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_primary'],
                font=('Microsoft YaHei UI', 22, 'bold')).pack(side='left')
        
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(header, textvariable=self.status_var,
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_secondary'],
                font=('Microsoft YaHei UI', 10)).pack(side='right')
        
        # 工具栏
        toolbar = tk.Frame(main, bg=self.COLORS['bg_primary'])
        toolbar.pack(fill='x', pady=(0, 15))
        
        btn_style = {'bd': 0, 'padx': 15, 'pady': 10, 
                    'font': ('Microsoft YaHei UI', 10), 'cursor': 'hand2'}
        
        tk.Button(toolbar, text="🔄 扫描应用",
                 bg=self.COLORS['accent'], fg='white',
                 command=self._scan_apps, **btn_style).pack(side='left', padx=(0, 10))
        
        tk.Button(toolbar, text="✅ 全部启用",
                 bg=self.COLORS['success'], fg='white',
                 command=self._enable_all, **btn_style).pack(side='left', padx=(0, 10))
        
        tk.Button(toolbar, text="❌ 全部禁用",
                 bg=self.COLORS['danger'], fg='white',
                 command=self._disable_all, **btn_style).pack(side='left', padx=(0, 10))
        
        # 搜索框
        search_frame = tk.Frame(toolbar, bg=self.COLORS['bg_secondary'])
        search_frame.pack(side='right')
        
        tk.Label(search_frame, text="🔍", bg=self.COLORS['bg_secondary'],
                fg=self.COLORS['text_secondary']).pack(side='left', padx=(10, 0))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        
        tk.Entry(search_frame, textvariable=self.search_var,
                bg=self.COLORS['bg_secondary'],
                fg=self.COLORS['text_primary'],
                insertbackground=self.COLORS['text_primary'],
                bd=0, width=25,
                font=('Microsoft YaHei UI', 10)).pack(padx=10, pady=8, side='left')
        
        tk.Button(search_frame, text="✕",
                 bg=self.COLORS['bg_secondary'],
                 fg=self.COLORS['text_secondary'],
                 bd=0, padx=5,
                 command=lambda: self.search_var.set("")).pack(padx=(0, 10))
        
        # 应用列表
        list_frame = tk.Frame(main, bg=self.COLORS['bg_primary'])
        list_frame.pack(fill='both', expand=True)
        
        columns = ('name', 'sid', 'status', 'action')
        self.tree = ttk.Treeview(list_frame, columns=columns, 
                                show='headings', style='Custom.Treeview')
        
        self.tree.heading('name', text='应用名称')
        self.tree.heading('sid', text='SID')
        self.tree.heading('status', text='代理状态')
        self.tree.heading('action', text='操作')
        
        self.tree.column('name', width=250, anchor='w')
        self.tree.column('sid', width=450, anchor='w')
        self.tree.column('status', width=100, anchor='center')
        self.tree.column('action', width=120, anchor='center')
        
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<Button-1>', self._on_click)
        
        # 底部
        footer = tk.Frame(main, bg=self.COLORS['bg_primary'])
        footer.pack(fill='x', pady=(15, 0))
        
        tk.Label(footer, 
                text="💡 提示：启用后 UWP 应用可以访问本地代理（Clash、Fiddler、Charles）| 点击操作列切换",
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_secondary'],
                font=('Microsoft YaHei UI', 9)).pack(side='left')
        
        self.stats_var = tk.StringVar(value="")
        tk.Label(footer, textvariable=self.stats_var,
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_secondary'],
                font=('Microsoft YaHei UI', 9)).pack(side='right')
    
    def _scan_apps(self):
        """扫描应用"""
        self.status_var.set("正在从注册表扫描应用...")
        self.root.update()
        
        self.all_apps = self.manager.get_uwp_apps()
        self._refresh_list()
        
        enabled_count = sum(1 for app in self.all_apps if app.loopback_enabled)
        self.status_var.set("扫描完成")
        self._update_stats()
    
    def _refresh_list(self, apps=None):
        """刷新列表"""
        if apps is None:
            apps = self.all_apps
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for app in apps:
            status = "✅ 已启用" if app.loopback_enabled else "⚪ 未启用"
            action = "禁用" if app.loopback_enabled else "启用"
            
            self.tree.insert('', 'end', values=(
                app.name,
                app.sid,
                status,
                f"[{action}]"
            ), tags=('enabled' if app.loopback_enabled else 'disabled',))
        
        self.tree.tag_configure('enabled', background='#0d3d2e')
        self.tree.tag_configure('disabled', background='')
        self._update_stats()
    
    def _on_search(self, *args):
        """搜索"""
        keyword = self.search_var.get().strip()
        
        if not keyword:
            self._refresh_list()
            return
        
        filtered = self.manager.search_apps(keyword)
        self._refresh_list(filtered)
        self.status_var.set(f"找到 {len(filtered)} 个匹配")
    
    def _update_stats(self):
        """更新统计"""
        total = len(self.all_apps)
        enabled = sum(1 for app in self.all_apps if app.loopback_enabled)
        self.stats_var.set(f"总计: {total} | 已启用: {enabled}")
    
    def _on_click(self, event):
        """点击操作"""
        region = self.tree.identify('region', event.x, event.y)
        if region != 'cell':
            return
        
        column = self.tree.identify_column(event.x)
        if column != '#4':
            return
        
        item = self.tree.identify_row(event.y)
        if not item:
            return
        
        values = self.tree.item(item)['values']
        sid = values[1]
        app_name = values[0]
        
        for app in self.all_apps:
            if app.sid == sid:
                if app.loopback_enabled:
                    success, output = self.manager.disable_loopback(sid)
                    if success:
                        app.loopback_enabled = False
                        self.status_var.set(f"已禁用: {app_name}")
                    else:
                        messagebox.showerror("错误", f"禁用失败\n{output}")
                else:
                    success, output = self.manager.enable_loopback(sid)
                    if success:
                        app.loopback_enabled = True
                        self.status_var.set(f"已启用: {app_name}")
                    else:
                        messagebox.showerror("错误", f"启用失败\n{output}")
                
                keyword = self.search_var.get().strip()
                self._refresh_list(self.manager.search_apps(keyword) if keyword else None)
                break
    
    def _enable_all(self):
        """全部启用"""
        if not self.all_apps:
            messagebox.showinfo("提示", "请先扫描应用")
            return
        
        if not messagebox.askyesno("确认", f"确定要启用全部 {len(self.all_apps)} 个应用吗？"):
            return
        
        self.status_var.set("正在启用...")
        self.root.update()
        
        success, fail = self.manager.enable_all()
        self._refresh_list()
        self.status_var.set(f"完成：成功 {success}，失败 {fail}")
    
    def _disable_all(self):
        """全部禁用"""
        if not self.all_apps:
            messagebox.showinfo("提示", "请先扫描应用")
            return
        
        if not messagebox.askyesno("确认", f"确定要禁用全部 {len(self.all_apps)} 个应用吗？"):
            return
        
        self.status_var.set("正在禁用...")
        self.root.update()
        
        success, fail = self.manager.disable_all()
        self._refresh_list()
        self.status_var.set(f"完成：成功 {success}，失败 {fail}")


def main():
    root = tk.Tk()
    root.title("UWP 回环代理管理器")
    
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = UWPManagerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
