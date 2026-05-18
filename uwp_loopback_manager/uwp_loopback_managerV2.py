#!/usr/bin/env python3
"""
UWP 网络回环管理器
允许 UWP 应用访问本地代理（回环地址）

实现方式：
1. 使用 NetworkIsolationEnumAppContainers API 获取 UWP 应用列表
2. 使用 NetworkIsolationFreeAppContainers 释放内存
3. 使用 CheckNetIsolation 管理回环权限

参考：
- https://github.com/Richasy/LoopbackManager.Desktop
- https://github.com/Lumysia/UWP-LoopBack-Tool
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import ctypes
from ctypes import wintypes, Structure, POINTER, byref, sizeof, cast, POINTER, c_uint32, c_wchar_p
from typing import List, Set, Optional
import locale


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


# ========== UWP 应用类 ==========
class UWPApp:
    """UWP 应用信息"""
    def __init__(self, name: str, display_name: str, package_name: str, 
                 sid: str, working_dir: str, loopback_enabled: bool = False):
        self.name = name  # appContainerName
        self.display_name = display_name or name  # displayName
        self.package_name = package_name  # packageFullName
        self.sid = sid  # SID 字符串
        self.working_dir = working_dir
        self.loopback_enabled = loopback_enabled
    
    def __repr__(self):
        return f"<UWPApp: {self.display_name}>"


# ========== 回环管理器 ==========
class LoopbackManager:
    """回环管理核心 - 使用 Windows API"""
    
    # NETISO_FLAG
    NETISO_FLAG_FORCE_COMPUTE_BINARIES = 0x1
    NETISO_FLAG_MAX = 0x2
    
    def __init__(self):
        self.apps: List[UWPApp] = []
        self.system_encoding = locale.getpreferredencoding(False) or 'gbk'
        
        # 加载 FirewallAPI.dll
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
        """将 SID 指针转换为字符串"""
        if not sid_ptr:
            return ""
        
        try:
            # 使用 ConvertSidToStringSidW
            advapi32 = ctypes.windll.advapi32
            ConvertSidToStringSidW = advapi32.ConvertSidToStringSidW
            ConvertSidToStringSidW.argtypes = [wintypes.LPVOID, POINTER(wintypes.LPWSTR)]
            ConvertSidToStringSidW.restype = wintypes.BOOL
            
            sid_str = wintypes.LPWSTR()
            if ConvertSidToStringSidW(sid_ptr, byref(sid_str)):
                result = sid_str.value if sid_str.value else ""
                # 释放内存
                ctypes.windll.kernel32.LocalFree(sid_str)
                return result
        except:
            pass
        
        return ""
    
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
        """使用 Windows API 获取 UWP 应用列表"""
        apps = []
        ptr_array = wintypes.LPVOID()
        count = wintypes.DWORD()
        
        try:
            # 调用 API
            retval = self.network_isolation_enum(
                self.NETISO_FLAG_MAX,
                byref(count),
                byref(ptr_array)
            )
            
            if retval != 0 or count.value == 0:
                print(f"NetworkIsolationEnumAppContainers 失败: 返回值 {retval}")
                return apps
            
            # 解析结构体数组
            struct_size = sizeof(INET_FIREWALL_APP_CONTAINER)
            current_ptr = ptr_array.value
            
            # 获取已启用的 SID
            enabled_sids = self._get_enabled_sids()
            
            for i in range(count.value):
                try:
                    # 从内存读取结构体
                    container = INET_FIREWALL_APP_CONTAINER.from_address(current_ptr)
                    
                    # 提取信息
                    name = container.appContainerName if container.appContainerName else ""
                    display_name = container.displayName if container.displayName else name
                    package_name = container.packageFullName if container.packageFullName else ""
                    working_dir = container.workingDirectory if container.workingDirectory else ""
                    sid = self._sid_to_string(container.appContainerSid)
                    
                    # 过滤无效条目
                    if name and sid:
                        enabled = sid in enabled_sids
                        apps.append(UWPApp(
                            name=name,
                            display_name=display_name,
                            package_name=package_name,
                            sid=sid,
                            working_dir=working_dir,
                            loopback_enabled=enabled
                        ))
                    
                    # 移动到下一个结构体
                    current_ptr += struct_size
                    
                except Exception as e:
                    print(f"解析应用 {i} 失败: {e}")
            
            # 释放内存
            self.network_isolation_free(ptr_array)
            
        except Exception as e:
            print(f"获取应用列表失败: {e}")
        
        # 按名称排序
        apps.sort(key=lambda x: x.display_name.lower() if x.display_name else x.name.lower())
        
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
        """启用应用的回环访问"""
        cmd = f'CheckNetIsolation LoopbackExempt -a -p={sid}'
        return self._run_command(cmd)
    
    def disable_loopback(self, sid: str) -> tuple:
        """禁用应用的回环访问"""
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
                if keyword in app.name.lower() 
                or keyword in app.display_name.lower()
                or keyword in app.package_name.lower()]


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
        self.root.geometry('1200x750')
        self.root.minsize(1000, 600)
        
        main = tk.Frame(self.root, bg=self.COLORS['bg_primary'])
        main.pack(fill='both', expand=True, padx=25, pady=25)
        
        # 标题
        header = tk.Frame(main, bg=self.COLORS['bg_primary'])
        header.pack(fill='x', pady=(0, 20))
        
        tk.Label(header, text="🔧 UWP 回环代理管理器", 
                bg=self.COLORS['bg_primary'],
                fg=self.COLORS['text_primary'],
                font=('Microsoft YaHei UI', 22, 'bold')).pack(side='left')
        
        self.status_var = tk.StringVar(value="就绪 - 点击「扫描应用」开始")
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
        
        tk.Button(toolbar, text="🔄 刷新状态",
                 bg=self.COLORS['bg_card'], fg=self.COLORS['text_primary'],
                 command=self._refresh_status, **btn_style).pack(side='left')
        
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
                bd=0, width=30,
                font=('Microsoft YaHei UI', 10)).pack(padx=10, pady=8, side='left')
        
        tk.Button(search_frame, text="✕",
                 bg=self.COLORS['bg_secondary'],
                 fg=self.COLORS['text_secondary'],
                 bd=0, padx=8,
                 command=lambda: self.search_var.set("")).pack(padx=(0, 10))
        
        # 应用列表
        list_frame = tk.Frame(main, bg=self.COLORS['bg_primary'])
        list_frame.pack(fill='both', expand=True)
        
        columns = ('display_name', 'package_name', 'status', 'action')
        self.tree = ttk.Treeview(list_frame, columns=columns, 
                                show='headings', style='Custom.Treeview')
        
        self.tree.heading('display_name', text='应用名称')
        self.tree.heading('package_name', text='包名称')
        self.tree.heading('status', text='代理状态')
        self.tree.heading('action', text='操作')
        
        self.tree.column('display_name', width=280, anchor='w')
        self.tree.column('package_name', width=500, anchor='w')
        self.tree.column('status', width=120, anchor='center')
        self.tree.column('action', width=120, anchor='center')
        
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<Button-1>', self._on_click)
        
        # 底部
        footer = tk.Frame(main, bg=self.COLORS['bg_primary'])
        footer.pack(fill='x', pady=(15, 0))
        
        tk.Label(footer, 
                text="💡 提示：启用后 UWP 应用可以访问本地代理（Clash、Fiddler、Charles）| 点击「操作」列切换状态",
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
        self.status_var.set("正在扫描 UWP 应用...")
        self.root.update()
        
        self.all_apps = self.manager.get_uwp_apps()
        self._refresh_list()
        
        self.status_var.set(f"扫描完成 - 共 {len(self.all_apps)} 个应用")
        self._update_stats()
    
    def _refresh_status(self):
        """仅刷新状态（不重新扫描应用列表）"""
        if not self.all_apps:
            messagebox.showinfo("提示", "请先扫描应用")
            return
        
        self.status_var.set("正在刷新状态...")
        self.root.update()
        
        # 重新获取已启用的 SID
        enabled_sids = self.manager._get_enabled_sids()
        
        # 更新状态
        for app in self.all_apps:
            app.loopback_enabled = app.sid in enabled_sids
        
        self._refresh_list()
        self.status_var.set("状态已刷新")
    
    def _refresh_list(self, apps=None):
        """刷新列表"""
        if apps is None:
            apps = self.all_apps
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for app in apps:
            status = "✅ 已启用" if app.loopback_enabled else "⚪ 未启用"
            action = "禁用" if app.loopback_enabled else "启用"
            
            # 显示名称处理
            display = app.display_name if app.display_name else app.name
            if display.startswith('@'):
                display = app.name
            
            self.tree.insert('', 'end', values=(
                display,
                app.package_name,
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
        package_name = values[1]
        
        for app in self.all_apps:
            if app.package_name == package_name:
                if app.loopback_enabled:
                    success, output = self.manager.disable_loopback(app.sid)
                    if success:
                        app.loopback_enabled = False
                        self.status_var.set(f"已禁用: {app.display_name}")
                    else:
                        messagebox.showerror("错误", f"禁用失败\n{output}")
                else:
                    success, output = self.manager.enable_loopback(app.sid)
                    if success:
                        app.loopback_enabled = True
                        self.status_var.set(f"已启用: {app.display_name}")
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
    
    # DPI 感知
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = UWPManagerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
