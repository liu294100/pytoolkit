#!/usr/bin/env python3
"""
UWP 网络回环管理器
允许 UWP 应用访问本地代理（回环地址）
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import json
import os
import re
from typing import List, Dict, Set
import ctypes
import locale


class UWPApp:
    """UWP 应用信息"""
    def __init__(self, name: str, package_id: str, display_name: str = "", loopback_enabled: bool = False):
        self.name = name  # 内部名称（小写）
        self.package_id = package_id  # PackageFamilyName
        self.display_name = display_name or name  # 显示名称
        self.loopback_enabled = loopback_enabled


class LoopbackManager:
    """回环管理核心"""
    
    CONFIG_FILE = "uwp_loopback_config.json"
    
    def __init__(self):
        self.apps: List[UWPApp] = []
        self.system_encoding = locale.getpreferredencoding(False) or 'gbk'
        self._load_config()
    
    def _load_config(self):
        """加载已保存的配置"""
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.apps = [UWPApp(**item) for item in data]
        except (FileNotFoundError, json.JSONDecodeError):
            self.apps = []
    
    def _save_config(self):
        """保存配置"""
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump([{
                'name': a.name, 
                'package_id': a.package_id,
                'display_name': a.display_name,
                'loopback_enabled': a.loopback_enabled
            } for a in self.apps], f, indent=2, ensure_ascii=False)
    
    def _run_powershell(self, cmd: str) -> str:
        """执行 PowerShell 命令"""
        try:
            result = subprocess.run(
                ['powershell', '-Command', cmd],
                capture_output=True,
                encoding='utf-8',
                errors='ignore'
            )
            return result.stdout
        except Exception as e:
            print(f"PowerShell 执行失败: {e}")
            return ""
    
    def _run_cmd(self, cmd: list) -> tuple:
        """执行命令行程序"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding=self.system_encoding,
                errors='ignore'
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def _get_enabled_packages(self) -> Set[str]:
        """获取已启用回环的应用列表（返回小写包名集合）"""
        success, output, _ = self._run_cmd(['CheckNetIsolation', 'LoopbackExempt', '-s'])
        
        enabled = set()
        if not success:
            return enabled
        
        # 解析输出：名称: microsoft.xxx_xxx 格式
        for line in output.split('\n'):
            if '名称:' in line or 'Name:' in line:
                # 提取名称部分
                parts = re.split(r'[名称:|Name:]', line)
                if len(parts) > 1:
                    pkg = parts[1].strip().lower()
                    if pkg and pkg != 'appcontainer not found':
                        enabled.add(pkg)
        
        return enabled
    
    def get_uwp_apps(self) -> List[UWPApp]:
        """获取系统已安装的 UWP 应用列表"""
        # 获取已启用列表（小写）
        enabled_packages = self._get_enabled_packages()
        
        # PowerShell 获取应用列表
        cmd = '''
        Get-AppxPackage | Where-Object {$_.SignatureKind -eq 'Store' -or $_.IsFramework -eq $false} | 
        Select-Object Name, PackageFamilyName, DisplayName | ConvertTo-Json -Compress
        '''
        output = self._run_powershell(cmd)
        
        if not output.strip():
            return []
        
        apps = []
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                data = [data]
            
            seen = set()
            for item in data:
                name = item.get('Name', '').lower()
                package_id = item.get('PackageFamilyName', '')
                display_name = item.get('DisplayName', '') or name
                
                if not name or not package_id:
                    continue
                
                # 去重
                if package_id.lower() in seen:
                    continue
                seen.add(package_id.lower())
                
                # 检查是否已启用（小写匹配）
                enabled = package_id.lower() in enabled_packages or name in enabled_packages
                
                apps.append(UWPApp(name, package_id, display_name, enabled))
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
        
        # 按名称排序
        apps.sort(key=lambda x: x.name.lower())
        return apps
    
    def enable_loopback(self, package_id: str) -> tuple:
        """启用应用的回环访问"""
        success, _, error = self._run_cmd(
            ['CheckNetIsolation', 'LoopbackExempt', '-a', f'-n={package_id}']
        )
        return success, error
    
    def disable_loopback(self, package_id: str) -> tuple:
        """禁用应用的回环访问"""
        success, _, error = self._run_cmd(
            ['CheckNetIsolation', 'LoopbackExempt', '-d', f'-n={package_id}']
        )
        return success, error
    
    def enable_all(self) -> int:
        """启用所有 UWP 应用的回环"""
        count = 0
        for app in self.apps:
            success, _ = self.enable_loopback(app.package_id)
            if success:
                app.loopback_enabled = True
                count += 1
        self._save_config()
        return count
    
    def disable_all(self) -> int:
        """禁用所有 UWP 应用的回环"""
        count = 0
        for app in self.apps:
            success, _ = self.disable_loopback(app.package_id)
            if success:
                app.loopback_enabled = False
                count += 1
        self._save_config()
        return count
    
    def add_custom(self, name: str, package_id: str) -> bool:
        """添加自定义应用"""
        for app in self.apps:
            if app.package_id.lower() == package_id.lower():
                return False
        self.apps.append(UWPApp(name.lower(), package_id, name, False))
        self._save_config()
        return True
    
    def remove(self, package_id: str) -> bool:
        """移除应用"""
        self.apps = [a for a in self.apps if a.package_id.lower() != package_id.lower()]
        self._save_config()
        return True
    
    def search_apps(self, keyword: str) -> List[UWPApp]:
        """搜索应用"""
        if not keyword:
            return self.apps
        
        keyword = keyword.lower()
        return [app for app in self.apps 
                if keyword in app.name.lower() 
                or keyword in app.package_id.lower()
                or keyword in app.display_name.lower()]


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
                       rowheight=40,
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
        self.root.geometry('1150x750')
        self.root.minsize(900, 600)
        
        # 主容器
        main = tk.Frame(self.root, bg=self.COLORS['bg_primary'])
        main.pack(fill='both', expand=True, padx=25, pady=25)
        
        # 标题区
        header = tk.Frame(main, bg=self.COLORS['bg_primary'])
        header.pack(fill='x', pady=(0, 20))
        
        tk.Label(header, text="🔧 UWP 回环代理管理器", 
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_primary'],
                font=('Microsoft YaHei UI', 22, 'bold')).pack(side='left')
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(header, textvariable=self.status_var,
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_secondary'],
                font=('Microsoft YaHei UI', 10)).pack(side='right')
        
        # 工具栏
        toolbar = tk.Frame(main, bg=self.COLORS['bg_primary'])
        toolbar.pack(fill='x', pady=(0, 15))
        
        btn_style = {'bd': 0, 'padx': 15, 'pady': 10, 
                    'font': ('Microsoft YaHei UI', 10),
                    'cursor': 'hand2'}
        
        tk.Button(toolbar, text="🔄 扫描应用",
                 bg=self.COLORS['accent'],
                 fg='white',
                 command=self._scan_apps,
                 **btn_style).pack(side='left', padx=(0, 10))
        
        tk.Button(toolbar, text="✅ 全部启用",
                 bg=self.COLORS['success'],
                 fg='white',
                 command=self._enable_all,
                 **btn_style).pack(side='left', padx=(0, 10))
        
        tk.Button(toolbar, text="❌ 全部禁用",
                 bg=self.COLORS['danger'],
                 fg='white',
                 command=self._disable_all,
                 **btn_style).pack(side='left', padx=(0, 10))
        
        tk.Button(toolbar, text="➕ 添加自定义",
                 bg=self.COLORS['bg_card'],
                 fg=self.COLORS['text_primary'],
                 command=self._add_custom,
                 **btn_style).pack(side='left')
        
        # 搜索框
        search_frame = tk.Frame(toolbar, bg=self.COLORS['bg_secondary'])
        search_frame.pack(side='right')
        
        tk.Label(search_frame, text="🔍",
                bg=self.COLORS['bg_secondary'],
                fg=self.COLORS['text_secondary']).pack(side='left', padx=(10, 0))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                bg=self.COLORS['bg_secondary'],
                fg=self.COLORS['text_primary'],
                insertbackground=self.COLORS['text_primary'],
                bd=0, width=25,
                font=('Microsoft YaHei UI', 10))
        search_entry.pack(padx=10, pady=8, side='left')
        
        tk.Button(search_frame, text="✕",
                 bg=self.COLORS['bg_secondary'],
                 fg=self.COLORS['text_secondary'],
                 bd=0, padx=5,
                 command=lambda: self.search_var.set("")).pack(padx=(0, 10))
        
        # 应用列表
        list_frame = tk.Frame(main, bg=self.COLORS['bg_primary'])
        list_frame.pack(fill='both', expand=True)
        
        columns = ('name', 'package_id', 'status', 'action')
        self.tree = ttk.Treeview(list_frame, columns=columns, 
                                show='headings', style='Custom.Treeview')
        
        self.tree.heading('name', text='应用名称')
        self.tree.heading('package_id', text='包标识 (PackageFamilyName)')
        self.tree.heading('status', text='代理状态')
        self.tree.heading('action', text='操作')
        
        self.tree.column('name', width=200, anchor='w')
        self.tree.column('package_id', width=420, anchor='w')
        self.tree.column('status', width=120, anchor='center')
        self.tree.column('action', width=150, anchor='center')
        
        self.tree.pack(fill='both', expand=True)
        
        # 绑定点击事件
        self.tree.bind('<Button-1>', self._on_click)
        
        # 底部说明
        footer = tk.Frame(main, bg=self.COLORS['bg_primary'])
        footer.pack(fill='x', pady=(15, 0))
        
        tk.Label(footer, 
                text="💡 提示：启用后 UWP 应用可以访问本地代理（如 Clash、Fiddler、Charles 等）| 点击操作列切换状态",
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_secondary'],
                font=('Microsoft YaHei UI', 9)).pack(side='left')
        
        # 统计信息
        self.stats_var = tk.StringVar(value="")
        tk.Label(footer, textvariable=self.stats_var,
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_secondary'],
                font=('Microsoft YaHei UI', 9)).pack(side='right')
    
    def _scan_apps(self):
        """扫描系统 UWP 应用"""
        self.status_var.set("正在扫描...")
        self.root.update()
        
        self.all_apps = self.manager.get_uwp_apps()
        self.manager.apps = self.all_apps
        self.manager._save_config()
        self._refresh_list()
        
        enabled_count = sum(1 for app in self.all_apps if app.loopback_enabled)
        self.status_var.set(f"扫描完成")
        self._update_stats()
    
    def _refresh_list(self, apps=None):
        """刷新列表"""
        if apps is None:
            apps = self.all_apps
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for app in apps:
            status = "✅ 已启用" if app.loopback_enabled else "⚪ 未启用"
            action_btn = "禁用" if app.loopback_enabled else "启用"
            
            # 显示名称优先，fallback 到 name
            display = app.display_name if app.display_name and app.display_name != app.name else app.name
            
            item_id = self.tree.insert('', 'end', values=(
                display,
                app.package_id,
                status,
                f"[{action_btn}]"
            ), tags=('enabled' if app.loopback_enabled else 'disabled',))
        
        self.tree.tag_configure('enabled', background='#0d3d2e')
        self.tree.tag_configure('disabled', background='')
        
        self._update_stats()
    
    def _on_search(self, *args):
        """搜索过滤"""
        keyword = self.search_var.get().strip()
        
        if not keyword:
            self._refresh_list(self.all_apps)
            return
        
        filtered = self.manager.search_apps(keyword)
        self._refresh_list(filtered)
        self.status_var.set(f"找到 {len(filtered)} 个匹配项")
    
    def _update_stats(self):
        """更新统计信息"""
        total = len(self.all_apps)
        enabled = sum(1 for app in self.all_apps if app.loopback_enabled)
        self.stats_var.set(f"总计: {total} | 已启用: {enabled}")
    
    def _on_click(self, event):
        """点击事件"""
        region = self.tree.identify('region', event.x, event.y)
        if region != 'cell':
            return
        
        column = self.tree.identify_column(event.x)
        if column != '#4':  # 只有操作列可点击
            return
        
        item = self.tree.identify_row(event.y)
        if not item:
            return
        
        values = self.tree.item(item)['values']
        package_id = values[1]
        app_name = values[0]
        
        # 找到对应应用并切换状态
        for app in self.all_apps:
            if app.package_id == package_id:
                if app.loopback_enabled:
                    success, error = self.manager.disable_loopback(package_id)
                    if success:
                        app.loopback_enabled = False
                        self.status_var.set(f"已禁用: {app_name}")
                    else:
                        messagebox.showerror("错误", f"禁用失败: {error}")
                else:
                    success, error = self.manager.enable_loopback(package_id)
                    if success:
                        app.loopback_enabled = True
                        self.status_var.set(f"已启用: {app_name}")
                    else:
                        messagebox.showerror("错误", f"启用失败: {error}")
                
                self.manager._save_config()
                
                # 保持搜索过滤
                keyword = self.search_var.get().strip()
                if keyword:
                    self._on_search()
                else:
                    self._refresh_list()
                break
    
    def _enable_all(self):
        """启用所有"""
        if not self.all_apps:
            messagebox.showinfo("提示", "请先扫描应用")
            return
        
        if not messagebox.askyesno("确认", "确定要启用所有应用的回环访问吗？"):
            return
        
        self.status_var.set("正在启用...")
        self.root.update()
        
        count = 0
        for app in self.all_apps:
            success, _ = self.manager.enable_loopback(app.package_id)
            if success:
                app.loopback_enabled = True
                count += 1
        
        self.manager._save_config()
        self._refresh_list()
        self.status_var.set(f"已启用 {count} 个应用")
    
    def _disable_all(self):
        """禁用所有"""
        if not self.all_apps:
            messagebox.showinfo("提示", "请先扫描应用")
            return
        
        if not messagebox.askyesno("确认", "确定要禁用所有应用的回环访问吗？"):
            return
        
        self.status_var.set("正在禁用...")
        self.root.update()
        
        count = 0
        for app in self.all_apps:
            success, _ = self.manager.disable_loopback(app.package_id)
            if success:
                app.loopback_enabled = False
                count += 1
        
        self.manager._save_config()
        self._refresh_list()
        self.status_var.set(f"已禁用 {count} 个应用")
    
    def _add_custom(self):
        """添加自定义应用"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加自定义应用")
        dialog.geometry("450x220")
        dialog.configure(bg=self.COLORS['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 200,
            self.root.winfo_rooty() + 150
        ))
        
        tk.Label(dialog, text="应用名称:", bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_primary'],
                font=('Microsoft YaHei UI', 10)).pack(pady=(20, 5))
        
        name_entry = tk.Entry(dialog, width=45,
                             bg=self.COLORS['bg_secondary'],
                             fg=self.COLORS['text_primary'],
                             insertbackground=self.COLORS['text_primary'],
                             font=('Microsoft YaHei UI', 10))
        name_entry.pack(pady=5)
        
        tk.Label(dialog, text="包标识 (PackageFamilyName):", 
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_primary'],
                font=('Microsoft YaHei UI', 10)).pack(pady=(10, 5))
        
        pkg_entry = tk.Entry(dialog, width=45,
                            bg=self.COLORS['bg_secondary'],
                            fg=self.COLORS['text_primary'],
                            insertbackground=self.COLORS['text_primary'],
                            font=('Microsoft YaHei UI', 10))
        pkg_entry.pack(pady=5)
        
        def save():
            name = name_entry.get().strip()
            pkg = pkg_entry.get().strip()
            
            if not name or not pkg:
                messagebox.showwarning("提示", "请填写完整信息")
                return
            
            if self.manager.add_custom(name, pkg):
                self.all_apps = self.manager.apps
                self._refresh_list()
                dialog.destroy()
                messagebox.showinfo("成功", f"已添加: {name}")
            else:
                messagebox.showwarning("提示", "该应用已存在")
        
        btn_frame = tk.Frame(dialog, bg=self.COLORS['bg_primary'])
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="添加", command=save,
                 bg=self.COLORS['accent'],
                 fg='white',
                 bd=0, padx=30, pady=10,
                 font=('Microsoft YaHei UI', 10)).pack(side='left', padx=10)
        
        tk.Button(btn_frame, text="取消", command=dialog.destroy,
                 bg=self.COLORS['bg_card'],
                 fg=self.COLORS['text_primary'],
                 bd=0, padx=30, pady=10,
                 font=('Microsoft YaHei UI', 10)).pack(side='left', padx=10)


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
