#!/usr/bin/env python3
"""
UWP 网络回环管理器 (UWP Loopback Manager)
允许 UWP 应用访问本地代理（回环地址）

参考：
- https://github.com/Richasy/LoopbackManager.Desktop
- https://github.com/Lumysia/UWP-LoopBack-Tool

功能：
- 使用 Treeview 高性能列表（支持数百应用无卡顿）
- 响应式布局，窗口缩放自适应
- 搜索实时过滤（防抖 + Treeview 刷新）
- 多语言支持：中文、英文、日语、韩语、俄语
- 显示友好名称
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import ctypes
from ctypes import wintypes, Structure, POINTER, byref, sizeof
from typing import List, Set, Dict, Tuple
import locale
import threading


# ========== 多语言支持 ==========
LANGUAGES = {
    'zh': {
        'title': '🔄 网络回环管理器',
        'subtitle': '勾选需要启用本地网络回环的应用，然后点击保存',
        'search_label': '🔍 搜索应用',
        'clear': '清空',
        'col_enable': '启用',
        'col_app_name': '应用名称',
        'col_friendly_name': '友好名称',
        'col_package': '包名称',
        'col_status': '状态',
        'status_ready': '就绪',
        'status_scanning': '正在扫描应用...',
        'status_scan_done': '扫描完成',
        'status_saving': '正在保存...',
        'status_found': '找到 {} 个匹配',
        'status_saved': '保存完成：启用 {}，禁用 {}',
        'stats': '总计: {} | 已启用: {} | 已选择: {}',
        'btn_refresh': '🔄 刷新列表',
        'btn_select_all': '全选',
        'btn_deselect_all': '取消全选',
        'btn_save': '💾 保存更改',
        'tip': '💡 提示：启用后应用可以访问本地代理（127.0.0.1），如 Clash、Fiddler 等',
        'enabled': '✅ 已启用',
        'disabled': '⚪ 未启用',
        'admin_title': '权限提示',
        'admin_msg': '需要管理员权限才能修改回环设置！\n请右键以管理员身份运行。',
        'info': '提示',
        'scan_first': '请先扫描应用',
        'no_changes': '没有需要保存的更改',
        'confirm_title': '确认保存',
        'confirm_msg': '即将进行以下操作：\n\n',
        'confirm_enable': '  ✅ 启用 {} 个应用\n',
        'confirm_disable': '  ❌ 禁用 {} 个应用\n',
        'confirm_ask': '\n确定要保存吗？',
        'save_done_title': '保存完成',
        'save_done_msg': '保存完成！\n\n',
        'save_ok_enable': '  ✅ 成功启用: {}\n',
        'save_ok_disable': '  ❌ 成功禁用: {}\n',
        'save_failed': '  ⚠️ 失败: {}\n',
        'lang_label': '🌐 语言',
        'window_title': '网络回环管理器',
    },
    'en': {
        'title': '🔄 UWP Loopback Manager',
        'subtitle': 'Check the apps that need loopback access, then click Save',
        'search_label': '🔍 Search',
        'clear': 'Clear',
        'col_enable': 'Enable',
        'col_app_name': 'App Name',
        'col_friendly_name': 'Friendly Name',
        'col_package': 'Package',
        'col_status': 'Status',
        'status_ready': 'Ready',
        'status_scanning': 'Scanning apps...',
        'status_scan_done': 'Scan complete',
        'status_saving': 'Saving...',
        'status_found': 'Found {} matches',
        'status_saved': 'Saved: enabled {}, disabled {}',
        'stats': 'Total: {} | Enabled: {} | Selected: {}',
        'btn_refresh': '🔄 Refresh',
        'btn_select_all': 'Select All',
        'btn_deselect_all': 'Deselect All',
        'btn_save': '💾 Save Changes',
        'tip': '💡 Tip: Enabled apps can access localhost (127.0.0.1), e.g. Clash, Fiddler',
        'enabled': '✅ Enabled',
        'disabled': '⚪ Disabled',
        'admin_title': 'Permission Required',
        'admin_msg': 'Administrator privileges are required!\nPlease run as administrator.',
        'info': 'Info',
        'scan_first': 'Please scan apps first',
        'no_changes': 'No changes to save',
        'confirm_title': 'Confirm Save',
        'confirm_msg': 'The following operations will be performed:\n\n',
        'confirm_enable': '  ✅ Enable {} apps\n',
        'confirm_disable': '  ❌ Disable {} apps\n',
        'confirm_ask': '\nProceed?',
        'save_done_title': 'Save Complete',
        'save_done_msg': 'Save complete!\n\n',
        'save_ok_enable': '  ✅ Enabled: {}\n',
        'save_ok_disable': '  ❌ Disabled: {}\n',
        'save_failed': '  ⚠️ Failed: {}\n',
        'lang_label': '🌐 Lang',
        'window_title': 'UWP Loopback Manager',
    },
    'ja': {
        'title': '🔄 ループバック管理',
        'subtitle': 'ループバックアクセスが必要なアプリにチェックを入れ、保存をクリック',
        'search_label': '🔍 検索',
        'clear': 'クリア',
        'col_enable': '有効',
        'col_app_name': 'アプリ名',
        'col_friendly_name': '表示名',
        'col_package': 'パッケージ',
        'col_status': '状態',
        'status_ready': '準備完了',
        'status_scanning': 'スキャン中...',
        'status_scan_done': 'スキャン完了',
        'status_saving': '保存中...',
        'status_found': '{} 件見つかりました',
        'status_saved': '保存完了：有効 {}、無効 {}',
        'stats': '合計: {} | 有効: {} | 選択: {}',
        'btn_refresh': '🔄 更新',
        'btn_select_all': '全選択',
        'btn_deselect_all': '全解除',
        'btn_save': '💾 保存',
        'tip': '💡 ヒント：有効化するとアプリはローカルプロキシにアクセスできます',
        'enabled': '✅ 有効',
        'disabled': '⚪ 無効',
        'admin_title': '権限が必要',
        'admin_msg': '管理者権限が必要です！\n管理者として実行してください。',
        'info': '情報',
        'scan_first': '先にアプリをスキャンしてください',
        'no_changes': '変更はありません',
        'confirm_title': '保存の確認',
        'confirm_msg': '以下の操作を実行します：\n\n',
        'confirm_enable': '  ✅ {} 個のアプリを有効化\n',
        'confirm_disable': '  ❌ {} 個のアプリを無効化\n',
        'confirm_ask': '\n続行しますか？',
        'save_done_title': '保存完了',
        'save_done_msg': '保存完了！\n\n',
        'save_ok_enable': '  ✅ 有効化成功: {}\n',
        'save_ok_disable': '  ❌ 無効化成功: {}\n',
        'save_failed': '  ⚠️ 失敗: {}\n',
        'lang_label': '🌐 言語',
        'window_title': 'UWP ループバック管理',
    },
    'ko': {
        'title': '🔄 루프백 관리자',
        'subtitle': '루프백 액세스가 필요한 앱을 선택하고 저장을 클릭하세요',
        'search_label': '🔍 검색',
        'clear': '지우기',
        'col_enable': '활성화',
        'col_app_name': '앱 이름',
        'col_friendly_name': '표시 이름',
        'col_package': '패키지',
        'col_status': '상태',
        'status_ready': '준비됨',
        'status_scanning': '스캔 중...',
        'status_scan_done': '스캔 완료',
        'status_saving': '저장 중...',
        'status_found': '{} 개 발견',
        'status_saved': '저장 완료: 활성화 {}, 비활성화 {}',
        'stats': '총: {} | 활성화: {} | 선택: {}',
        'btn_refresh': '🔄 새로고침',
        'btn_select_all': '모두 선택',
        'btn_deselect_all': '모두 해제',
        'btn_save': '💾 저장',
        'tip': '💡 팁: 활성화하면 앱이 로컬 프록시에 접근할 수 있습니다',
        'enabled': '✅ 활성화',
        'disabled': '⚪ 비활성화',
        'admin_title': '권한 필요',
        'admin_msg': '관리자 권한이 필요합니다!\n관리자로 실행해 주세요.',
        'info': '알림',
        'scan_first': '먼저 앱을 스캔하세요',
        'no_changes': '변경 사항이 없습니다',
        'confirm_title': '저장 확인',
        'confirm_msg': '다음 작업이 수행됩니다:\n\n',
        'confirm_enable': '  ✅ {} 개 앱 활성화\n',
        'confirm_disable': '  ❌ {} 개 앱 비활성화\n',
        'confirm_ask': '\n계속하시겠습니까?',
        'save_done_title': '저장 완료',
        'save_done_msg': '저장 완료!\n\n',
        'save_ok_enable': '  ✅ 활성화 성공: {}\n',
        'save_ok_disable': '  ❌ 비활성화 성공: {}\n',
        'save_failed': '  ⚠️ 실패: {}\n',
        'lang_label': '🌐 언어',
        'window_title': 'UWP 루프백 관리자',
    },
    'ru': {
        'title': '🔄 Менеджер Loopback',
        'subtitle': 'Отметьте приложения для доступа к localhost, затем сохраните',
        'search_label': '🔍 Поиск',
        'clear': 'Очистить',
        'col_enable': 'Вкл.',
        'col_app_name': 'Имя приложения',
        'col_friendly_name': 'Понятное имя',
        'col_package': 'Пакет',
        'col_status': 'Статус',
        'status_ready': 'Готов',
        'status_scanning': 'Сканирование...',
        'status_scan_done': 'Сканирование завершено',
        'status_saving': 'Сохранение...',
        'status_found': 'Найдено: {}',
        'status_saved': 'Сохранено: вкл. {}, выкл. {}',
        'stats': 'Всего: {} | Включено: {} | Выбрано: {}',
        'btn_refresh': '🔄 Обновить',
        'btn_select_all': 'Выбрать все',
        'btn_deselect_all': 'Снять все',
        'btn_save': '💾 Сохранить',
        'tip': '💡 Подсказка: включённые приложения могут обращаться к localhost (127.0.0.1)',
        'enabled': '✅ Включено',
        'disabled': '⚪ Выключено',
        'admin_title': 'Требуются права',
        'admin_msg': 'Требуются права администратора!\nЗапустите от имени администратора.',
        'info': 'Информация',
        'scan_first': 'Сначала отсканируйте приложения',
        'no_changes': 'Нет изменений для сохранения',
        'confirm_title': 'Подтверждение',
        'confirm_msg': 'Будут выполнены следующие операции:\n\n',
        'confirm_enable': '  ✅ Включить: {} приложений\n',
        'confirm_disable': '  ❌ Выключить: {} приложений\n',
        'confirm_ask': '\nПродолжить?',
        'save_done_title': 'Сохранено',
        'save_done_msg': 'Сохранение завершено!\n\n',
        'save_ok_enable': '  ✅ Включено: {}\n',
        'save_ok_disable': '  ❌ Выключено: {}\n',
        'save_failed': '  ⚠️ Ошибка: {}\n',
        'lang_label': '🌐 Язык',
        'window_title': 'UWP Loopback Manager',
    },
}


# ========== 应用名称映射表（常见应用的友好名称）==========
APP_NAME_MAP = {
    'microsoft.edge': 'Edge',
    'microsoft.microsoftedge.stable': 'Edge',
    'microsoft.windowsstore': 'Microsoft Store',
    'microsoft.windowscalculator': 'Calculator',
    'microsoft.windowsnotepad': 'Notepad',
    'microsoft.microsoftstickynotes': 'Sticky Notes',
    'microsoft.paint': 'Paint',
    'microsoft.photos': 'Photos',
    'microsoft.windows.photos': 'Photos',
    'microsoft.zunemusic': 'Groove Music',
    'microsoft.zunevideo': 'Groove Video',
    'microsoft.windowsmaps': 'Maps',
    'microsoft.bingweather': 'Weather',
    'microsoft.bingnews': 'News',
    'microsoft.microsoftsolitairecollection': 'Solitaire',
    'microsoft.skypeapp': 'Skype',
    'microsoft.teams': 'Microsoft Teams',
    'microsoft.teamsmeetingaddon': 'Teams Meeting',
    'microsoft.microsoftofficehub': 'Office Hub',
    'microsoft.office.onenote': 'OneNote',
    'microsoft.outlookforwindows': 'Outlook',
    'microsoft.todos': 'Microsoft To Do',
    'microsoft.onedrive': 'OneDrive',
    'microsoft.onedrivesync': 'OneDrive Sync',
    'microsoft.desktopappinstaller': 'App Installer (winget)',
    'microsoft.windowsfeedbackhub': 'Feedback Hub',
    'microsoft.gethelp': 'Get Help',
    'microsoft.windowsalarms': 'Alarms & Clock',
    'microsoft.windowssoundrecorder': 'Sound Recorder',
    'microsoft.windowscamera': 'Camera',
    'microsoft.windowscommunicationsapps': 'Mail & Calendar',
    'microsoft.people': 'People',
    'microsoft.mspaint': 'Paint 3D',
    'microsoft.screensketch': 'Snipping Tool',
    'microsoft.yourphone': 'Phone Link',
    'microsoft.windows.terminal': 'Windows Terminal',
    'microsoft.powertoys': 'PowerToys',
    'microsoft.xboxapp': 'Xbox',
    'microsoft.xboxgameoverlay': 'Xbox Game Bar',
    'microsoft.xboxgamingoverlay': 'Xbox Gaming Overlay',
    'microsoft.xboxidentityprovider': 'Xbox Identity',
    'microsoft.xbox.tcui': 'Xbox Services',
    'microsoft.gamingapp': 'Xbox Gaming',
    'microsoft.microsoft3dviewer': '3D Viewer',
    'microsoft.mixedreality.portal': 'Mixed Reality Portal',
    'microsoft.bingsearch': 'Bing Search',
    'microsoft.microsoftedgedevtoolsclient': 'Edge DevTools',
    'microsoft.ui.xaml': 'UI XAML Framework',
    'microsoft.windowsappruntime': 'Windows App Runtime',
    'microsoft.windows.devhome': 'Dev Home',
    'microsoft.widgetplatform': 'Widgets',
    'microsoft.microsoftpcmanager': 'PC Manager',
    'tencent.qq': 'QQ',
    'tencent.wechat': 'WeChat',
    'tencent.wechatapp': 'WeChat',
    'tencentmeeting': 'Tencent Meeting',
    'tencent.qqmusic': 'QQ Music',
    'tencent.qqlive': 'Tencent Video',
    'tencent.tim': 'TIM',
    'kingsoft.wps': 'WPS Office',
    'kingsoft.wpsoffice': 'WPS Office',
    'netease.cloudmusic': 'NetEase Music',
    'netease.mail': 'NetEase Mail',
    'netease.youdao': 'Youdao Dict',
    'bilibili': 'Bilibili',
    'bilibili.uwp': 'Bilibili UWP',
    'discord': 'Discord',
    'telegram': 'Telegram',
    'whatsapp': 'WhatsApp',
    'signal': 'Signal',
    'slack': 'Slack',
    'zoom': 'Zoom',
    'spotify': 'Spotify',
    'spotify.music': 'Spotify',
    'netflix': 'Netflix',
    'openai.chatgpt': 'ChatGPT',
    'openai.codex': 'ChatGPT Copilot',
    'intel.arc': 'Intel Arc Control',
    'intel.graphics': 'Intel Graphics',
    'clipchamp': 'Clipchamp',
    'adobe.photoshop': 'Photoshop',
    'adobe.illustrator': 'Illustrator',
    'adobe.premiere': 'Premiere Pro',
    'adobe.acrobat': 'Adobe Acrobat',
    'dropbox': 'Dropbox',
    'evernote': 'Evernote',
    'notion': 'Notion',
    'steam': 'Steam',
    'epicgames': 'Epic Games',
    'douyin': 'Douyin/TikTok',
    'kuaishou': 'Kuaishou',
    'xiaohongshu': 'Xiaohongshu',
}


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
    __slots__ = ('name', 'display_name', 'package_name', 'sid',
                 'description', 'loopback_enabled', 'temp_enabled',
                 'friendly_name', '_search_text')

    def __init__(self, name: str, display_name: str, package_name: str,
                 sid: str, description: str = "", loopback_enabled: bool = False):
        self.name = name
        self.display_name = display_name or name
        self.package_name = package_name
        self.sid = sid
        self.description = description
        self.loopback_enabled = loopback_enabled
        self.temp_enabled = loopback_enabled
        self.friendly_name = self._get_friendly_name()
        # 预计算搜索文本（性能优化：避免每次搜索重复 lower()）
        self._search_text = '\0'.join([
            self.name.lower(),
            self.display_name.lower(),
            self.package_name.lower(),
            self.friendly_name.lower(),
            self.sid.lower(),
        ])

    def matches(self, keyword: str) -> bool:
        """快速匹配搜索关键词（keyword 必须是小写）"""
        return keyword in self._search_text

    def _get_friendly_name(self) -> str:
        """获取友好名称"""
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
            parts = self.package_name.split('_')
            if parts:
                main_part = parts[0]
                if '.' in main_part:
                    segments = main_part.split('.')
                    for seg in reversed(segments):
                        if seg and len(seg) > 2 and seg not in ('app', 'uwp', 'desktop'):
                            return seg.capitalize()
                return main_part

        # 4. 从容器名提取
        if self.name:
            name = self.name.replace('_', ' ').replace('.', ' ')
            words = name.split()
            if words:
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
            self.network_isolation_enum.argtypes = [
                wintypes.DWORD, POINTER(wintypes.DWORD), POINTER(wintypes.LPVOID)
            ]
            self.network_isolation_enum.restype = wintypes.DWORD

            self.network_isolation_free = self.firewall_api.NetworkIsolationFreeAppContainers
            self.network_isolation_free.argtypes = [wintypes.LPVOID]
            self.network_isolation_free.restype = wintypes.DWORD
        except Exception as e:
            print(f"Failed to load FirewallAPI.dll: {e}")

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
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW,
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
                self.NETISO_FLAG_MAX, byref(count), byref(ptr_array)
            )
            if retval != 0 or count.value == 0:
                return apps

            struct_size = sizeof(INET_FIREWALL_APP_CONTAINER)
            current_ptr = ptr_array.value
            enabled_sids = self._get_enabled_sids()

            for i in range(count.value):
                try:
                    container = INET_FIREWALL_APP_CONTAINER.from_address(current_ptr)
                    name = container.appContainerName or ""
                    display_name = container.displayName or ""
                    package_name = container.packageFullName or ""
                    description = container.description or ""
                    sid = self._sid_to_string(container.appContainerSid)

                    if name and sid:
                        apps.append(UWPApp(
                            name=name,
                            display_name=display_name,
                            package_name=package_name,
                            sid=sid,
                            description=description,
                            loopback_enabled=sid in enabled_sids,
                        ))
                    current_ptr += struct_size
                except:
                    current_ptr += struct_size

            self.network_isolation_free(ptr_array)
        except Exception as e:
            print(f"Failed to enumerate apps: {e}")

        # 去重：保留第一个出现的 SID（某些系统存在重复 SID）
        seen_sids = set()
        unique_apps = []
        for app in apps:
            if app.sid not in seen_sids:
                seen_sids.add(app.sid)
                unique_apps.append(app)
        unique_apps.sort(key=lambda x: x.friendly_name.lower())
        self.apps = unique_apps
        return unique_apps

    def _run_command(self, cmd: str) -> Tuple[bool, str]:
        """执行命令"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True,
                encoding=self.system_encoding, errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            output = result.stdout + result.stderr
            success = '完成' in output or 'OK' in output or result.returncode == 0
            return success, output
        except Exception as e:
            return False, str(e)

    def enable_loopback(self, sid: str) -> Tuple[bool, str]:
        return self._run_command(f'CheckNetIsolation LoopbackExempt -a -p={sid}')

    def disable_loopback(self, sid: str) -> Tuple[bool, str]:
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


# ========== GUI（使用 Treeview 高性能列表）==========
class UWPManagerGUI:
    """
    使用 ttk.Treeview 替代逐行创建 widget 的方式：
    - 渲染数百行无卡顿
    - 列自动对齐
    - 支持响应式缩放
    - 搜索结果即时刷新
    """

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
        'row_even': '#2d2d30',
        'row_odd': '#353538',
        'row_selected': '#094771',
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.manager = LoopbackManager()
        self.all_apps: List[UWPApp] = []
        self.filtered_apps: List[UWPApp] = []
        self._search_timer = None
        self._search_keyword = ""
        self._current_lang = 'zh'
        self.i18n = LANGUAGES[self._current_lang]

        # sid -> checked state mapping
        self._checked: Dict[str, bool] = {}

        self._setup_styles()
        self._build_ui()
        self._check_admin()
        # 启动时自动扫描应用列表
        self.root.after(100, self._refresh_list)

    def _t(self, key: str) -> str:
        """获取当前语言文本"""
        return self.i18n.get(key, key)

    def _get_filter_labels(self) -> list:
        """获取当前语言的筛选标签"""
        return self._filter_labels_map.get(self._current_lang, self._filter_labels_map['en'])

    def _get_filter_key(self) -> str:
        """获取当前筛选下拉框选中的 key（all/enabled/disabled）"""
        labels = self._get_filter_labels()
        current = self.filter_combo.get()
        try:
            idx = labels.index(current)
            return self._filter_keys[idx]
        except (ValueError, IndexError):
            return 'all'

    def _check_admin(self):
        """检查管理员权限"""
        try:
            if not ctypes.windll.shell32.IsUserAnAdmin():
                messagebox.showwarning(self._t('admin_title'), self._t('admin_msg'))
        except:
            pass

    def _setup_styles(self):
        """配置 ttk 样式"""
        style = ttk.Style()
        style.theme_use('clam')

        # Treeview 样式
        style.configure('App.Treeview',
                        background=self.COLORS['bg_secondary'],
                        foreground=self.COLORS['text_primary'],
                        fieldbackground=self.COLORS['bg_secondary'],
                        borderwidth=0,
                        font=('Microsoft YaHei UI', 10),
                        rowheight=32)
        style.configure('App.Treeview.Heading',
                        background=self.COLORS['bg_card'],
                        foreground=self.COLORS['text_primary'],
                        borderwidth=0,
                        font=('Microsoft YaHei UI', 10, 'bold'),
                        relief='flat')
        style.map('App.Treeview.Heading',
                  background=[('active', self.COLORS['bg_card'])])
        style.map('App.Treeview',
                  background=[('selected', self.COLORS['row_selected'])],
                  foreground=[('selected', self.COLORS['text_primary'])])

        # Scrollbar
        style.configure('App.Vertical.TScrollbar',
                        background=self.COLORS['bg_card'],
                        troughcolor=self.COLORS['bg_secondary'],
                        arrowcolor=self.COLORS['text_primary'],
                        borderwidth=0)
        style.map('App.Vertical.TScrollbar',
                  background=[('active', self.COLORS['accent'])])

        # Combobox
        style.configure('Lang.TCombobox',
                        fieldbackground=self.COLORS['bg_secondary'],
                        background=self.COLORS['bg_card'],
                        foreground=self.COLORS['text_primary'],
                        borderwidth=0)

    def _build_ui(self):
        """构建界面 - 完全响应式布局"""
        self.root.configure(bg=self.COLORS['bg_primary'])
        self.root.geometry('1250x750')
        self.root.minsize(900, 500)

        # 主容器使用 grid 实现响应式
        main = tk.Frame(self.root, bg=self.COLORS['bg_primary'])
        main.pack(fill='both', expand=True, padx=20, pady=15)
        main.grid_rowconfigure(3, weight=1)  # 列表区域可伸缩
        main.grid_columnconfigure(0, weight=1)

        # ===== Row 0: 标题区 =====
        header = tk.Frame(main, bg=self.COLORS['bg_primary'])
        header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        header.grid_columnconfigure(1, weight=1)

        title_frame = tk.Frame(header, bg=self.COLORS['bg_primary'])
        title_frame.grid(row=0, column=0, sticky='w')

        self.title_label = tk.Label(title_frame, text=self._t('title'),
                                    bg=self.COLORS['bg_primary'],
                                    fg=self.COLORS['text_primary'],
                                    font=('Microsoft YaHei UI', 22, 'bold'))
        self.title_label.pack(anchor='w')

        self.subtitle_label = tk.Label(title_frame, text=self._t('subtitle'),
                                       bg=self.COLORS['bg_primary'],
                                       fg=self.COLORS['text_secondary'],
                                       font=('Microsoft YaHei UI', 10))
        self.subtitle_label.pack(anchor='w', pady=(3, 0))

        # 右侧：语言选择 + 状态
        right_frame = tk.Frame(header, bg=self.COLORS['bg_primary'])
        right_frame.grid(row=0, column=1, sticky='e')

        self.lang_label = tk.Label(right_frame, text=self._t('lang_label'),
                                   bg=self.COLORS['bg_primary'],
                                   fg=self.COLORS['text_secondary'],
                                   font=('Microsoft YaHei UI', 9))
        self.lang_label.pack(side='left', padx=(0, 5))

        self.lang_var = tk.StringVar(value='中文')
        lang_names = {'zh': '中文', 'en': 'English', 'ja': '日本語', 'ko': '한국어', 'ru': 'Русский'}
        self._lang_name_to_code = {v: k for k, v in lang_names.items()}
        self.lang_combo = ttk.Combobox(right_frame, textvariable=self.lang_var,
                                       values=list(lang_names.values()),
                                       state='readonly', width=10,
                                       style='Lang.TCombobox',
                                       font=('Microsoft YaHei UI', 9))
        self.lang_combo.pack(side='left', padx=(0, 15))
        self.lang_combo.bind('<<ComboboxSelected>>', self._on_lang_change)

        self.status_var = tk.StringVar(value=self._t('status_ready'))
        self.status_label = tk.Label(right_frame, textvariable=self.status_var,
                                     bg=self.COLORS['bg_primary'],
                                     fg=self.COLORS['text_secondary'],
                                     font=('Microsoft YaHei UI', 10))
        self.status_label.pack(side='left')

        # ===== Row 1: 搜索栏 =====
        search_frame = tk.Frame(main, bg=self.COLORS['bg_primary'])
        search_frame.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        search_frame.grid_columnconfigure(1, weight=1)

        self.search_label = tk.Label(search_frame, text=self._t('search_label'),
                                     bg=self.COLORS['bg_primary'],
                                     fg=self.COLORS['text_secondary'],
                                     font=('Microsoft YaHei UI', 10))
        self.search_label.grid(row=0, column=0, padx=(0, 8))

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self._on_search)
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                     bg=self.COLORS['bg_secondary'],
                                     fg=self.COLORS['text_primary'],
                                     insertbackground=self.COLORS['text_primary'],
                                     bd=0, font=('Microsoft YaHei UI', 10))
        self.search_entry.grid(row=0, column=1, sticky='ew', ipady=7, padx=(0, 8))

        self.clear_btn = tk.Button(search_frame, text=self._t('clear'),
                                   bg=self.COLORS['bg_card'],
                                   fg=self.COLORS['text_primary'],
                                   bd=0, padx=12, pady=5,
                                   font=('Microsoft YaHei UI', 9),
                                   cursor='hand2',
                                   command=lambda: self.search_var.set(""))
        self.clear_btn.grid(row=0, column=2, padx=(0, 10))

        self.stats_var = tk.StringVar(value="")
        self.stats_label = tk.Label(search_frame, textvariable=self.stats_var,
                                    bg=self.COLORS['bg_primary'],
                                    fg=self.COLORS['text_secondary'],
                                    font=('Microsoft YaHei UI', 9))
        self.stats_label.grid(row=0, column=3, sticky='e')

        # ===== Row 2: 过滤下拉框 =====
        filter_frame = tk.Frame(main, bg=self.COLORS['bg_primary'])
        filter_frame.grid(row=2, column=0, sticky='ew', pady=(0, 5))

        self._filter_keys = ['all', 'enabled', 'disabled']
        self._filter_labels_map = {
            'zh': ['全部', '已启用', '未启用'],
            'en': ['All', 'Enabled', 'Disabled'],
            'ja': ['すべて', '有効', '無効'],
            'ko': ['전체', '활성화', '비활성화'],
            'ru': ['Все', 'Включено', 'Выключено'],
        }

        self.filter_label_widget = tk.Label(filter_frame, text="筛选:",
                 bg=self.COLORS['bg_primary'],
                 fg=self.COLORS['text_secondary'],
                 font=('Microsoft YaHei UI', 9))
        self.filter_label_widget.pack(side='left', padx=(0, 5))

        self.filter_combo = ttk.Combobox(filter_frame,
                                         values=self._get_filter_labels(),
                                         state='readonly', width=10,
                                         style='Lang.TCombobox',
                                         font=('Microsoft YaHei UI', 9))
        self.filter_combo.set(self._get_filter_labels()[0])
        self.filter_combo.pack(side='left', padx=(0, 10))
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self._do_search())

        # ===== Row 3: Treeview 列表（核心性能优化）=====
        tree_frame = tk.Frame(main, bg=self.COLORS['bg_secondary'])
        tree_frame.grid(row=3, column=0, sticky='nsew', pady=(0, 10))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columns = ('enable', 'app_name', 'friendly_name', 'package', 'status')
        self.tree = ttk.Treeview(tree_frame, columns=columns,
                                 show='headings', selectmode='extended',
                                 style='App.Treeview')

        # 列标题
        self.tree.heading('enable', text=self._t('col_enable'))
        self.tree.heading('app_name', text=self._t('col_app_name'))
        self.tree.heading('friendly_name', text=self._t('col_friendly_name'))
        self.tree.heading('package', text=self._t('col_package'))
        self.tree.heading('status', text=self._t('col_status'))

        # 列宽度（响应式：minwidth + stretch）
        self.tree.column('enable', width=60, minwidth=50, stretch=False, anchor='center')
        self.tree.column('app_name', width=220, minwidth=120, stretch=True, anchor='w')
        self.tree.column('friendly_name', width=160, minwidth=100, stretch=True, anchor='w')
        self.tree.column('package', width=380, minwidth=150, stretch=True, anchor='w')
        self.tree.column('status', width=100, minwidth=80, stretch=False, anchor='center')

        # 滚动条
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview,
                            style='App.Vertical.TScrollbar')
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        # 行标签颜色
        self.tree.tag_configure('even', background=self.COLORS['row_even'])
        self.tree.tag_configure('odd', background=self.COLORS['row_odd'])
        self.tree.tag_configure('enabled_text', foreground=self.COLORS['success'])
        self.tree.tag_configure('disabled_text', foreground=self.COLORS['text_secondary'])

        # 双击或回车切换勾选
        self.tree.bind('<Double-1>', self._on_tree_toggle)
        self.tree.bind('<Return>', self._on_tree_toggle)
        self.tree.bind('<space>', self._on_tree_toggle)

        # ===== Row 4: 底部按钮区 =====
        footer = tk.Frame(main, bg=self.COLORS['bg_primary'])
        footer.grid(row=4, column=0, sticky='ew')
        footer.grid_columnconfigure(0, weight=1)

        self.tip_label = tk.Label(footer, text=self._t('tip'),
                                  bg=self.COLORS['bg_primary'],
                                  fg=self.COLORS['text_secondary'],
                                  font=('Microsoft YaHei UI', 9))
        self.tip_label.grid(row=0, column=0, sticky='w')

        btn_frame = tk.Frame(footer, bg=self.COLORS['bg_primary'])
        btn_frame.grid(row=0, column=1, sticky='e')

        self.btn_refresh = tk.Button(btn_frame, text=self._t('btn_refresh'),
                                     bg=self.COLORS['bg_card'],
                                     fg=self.COLORS['text_primary'],
                                     bd=0, padx=16, pady=8,
                                     font=('Microsoft YaHei UI', 10),
                                     cursor='hand2',
                                     command=self._refresh_list)
        self.btn_refresh.pack(side='left', padx=(0, 8))

        self.btn_select_all = tk.Button(btn_frame, text=self._t('btn_select_all'),
                                        bg=self.COLORS['bg_card'],
                                        fg=self.COLORS['text_primary'],
                                        bd=0, padx=16, pady=8,
                                        font=('Microsoft YaHei UI', 10),
                                        cursor='hand2',
                                        command=lambda: self._select_all(True))
        self.btn_select_all.pack(side='left', padx=(0, 8))

        self.btn_deselect_all = tk.Button(btn_frame, text=self._t('btn_deselect_all'),
                                          bg=self.COLORS['bg_card'],
                                          fg=self.COLORS['text_primary'],
                                          bd=0, padx=16, pady=8,
                                          font=('Microsoft YaHei UI', 10),
                                          cursor='hand2',
                                          command=lambda: self._select_all(False))
        self.btn_deselect_all.pack(side='left', padx=(0, 8))

        self.btn_save = tk.Button(btn_frame, text=self._t('btn_save'),
                                  bg=self.COLORS['accent'],
                                  fg='white',
                                  bd=0, padx=24, pady=8,
                                  font=('Microsoft YaHei UI', 11, 'bold'),
                                  cursor='hand2',
                                  command=self._save_changes)
        self.btn_save.pack(side='left')

    # ========== 语言切换 ==========
    def _on_lang_change(self, event=None):
        """切换语言，刷新所有 UI 文本"""
        name = self.lang_var.get()
        code = self._lang_name_to_code.get(name, 'zh')
        if code == self._current_lang:
            return
        self._current_lang = code
        self.i18n = LANGUAGES[code]
        self._refresh_ui_text()

    def _refresh_ui_text(self):
        """刷新所有 UI 上的文本"""
        self.root.title(self._t('window_title'))
        self.title_label.config(text=self._t('title'))
        self.subtitle_label.config(text=self._t('subtitle'))
        self.lang_label.config(text=self._t('lang_label'))
        self.search_label.config(text=self._t('search_label'))
        self.clear_btn.config(text=self._t('clear'))
        self.tip_label.config(text=self._t('tip'))
        self.btn_refresh.config(text=self._t('btn_refresh'))
        self.btn_select_all.config(text=self._t('btn_select_all'))
        self.btn_deselect_all.config(text=self._t('btn_deselect_all'))
        self.btn_save.config(text=self._t('btn_save'))
        self.status_var.set(self._t('status_ready'))

        # 更新筛选下拉框
        labels = self._get_filter_labels()
        old_key = self._get_filter_key()
        self.filter_combo.config(values=labels)
        idx = self._filter_keys.index(old_key) if old_key in self._filter_keys else 0
        self.filter_combo.set(labels[idx])

        # 更新 Treeview 列标题
        self.tree.heading('enable', text=self._t('col_enable'))
        self.tree.heading('app_name', text=self._t('col_app_name'))
        self.tree.heading('friendly_name', text=self._t('col_friendly_name'))
        self.tree.heading('package', text=self._t('col_package'))
        self.tree.heading('status', text=self._t('col_status'))

        # 重新渲染列表以更新状态文本
        self._render_tree()
        self._update_stats()

    # ========== Treeview 操作 ==========
    def _on_tree_toggle(self, event=None):
        """双击/回车/空格切换选中行的启用状态"""
        selected = self.tree.selection()
        if not selected:
            return
        for item_id in selected:
            idx = int(item_id)
            if idx < 0 or idx >= len(self.filtered_apps):
                continue
            app = self.filtered_apps[idx]
            current = self._checked.get(app.sid, app.loopback_enabled)
            self._checked[app.sid] = not current
            app.temp_enabled = not current
            # 更新该行显示
            self._update_tree_row(item_id, app, idx)
        self._update_stats()

    def _update_tree_row(self, item_id: str, app: 'UWPApp', idx: int):
        """更新 Treeview 中某一行的内容"""
        checked = self._checked.get(app.sid, app.loopback_enabled)
        enable_mark = '☑' if checked else '☐'
        display_name = app.display_name if app.display_name and not app.display_name.startswith('@') else app.name
        status_text = self._t('enabled') if app.loopback_enabled else self._t('disabled')
        tag = 'even' if idx % 2 == 0 else 'odd'

        self.tree.item(item_id, values=(enable_mark, display_name,
                                        app.friendly_name, app.package_name,
                                        status_text), tags=(tag,))

    def _render_tree(self):
        """高性能渲染：清空并重新填充 Treeview"""
        # 批量删除
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)

        for i, app in enumerate(self.filtered_apps):
            checked = self._checked.get(app.sid, app.loopback_enabled)
            enable_mark = '☑' if checked else '☐'
            display_name = app.display_name if app.display_name and not app.display_name.startswith('@') else app.name
            status_text = self._t('enabled') if app.loopback_enabled else self._t('disabled')
            tag = 'even' if i % 2 == 0 else 'odd'

            # 使用索引作为 iid，避免重复 SID 冲突
            self.tree.insert('', 'end', iid=str(i),
                             values=(enable_mark, display_name,
                                     app.friendly_name, app.package_name,
                                     status_text),
                             tags=(tag,))

    # ========== 搜索与过滤 ==========
    def _on_search(self, *args):
        """搜索输入回调（防抖 200ms）"""
        if self._search_timer:
            self.root.after_cancel(self._search_timer)
        self._search_timer = self.root.after(200, self._do_search)

    def _do_search(self):
        """执行搜索 + 筛选"""
        keyword = self.search_var.get().strip().lower()

        # 获取筛选条件
        filter_key = self._get_filter_key()

        # 先按搜索关键词过滤
        if keyword:
            results = [app for app in self.all_apps if app.matches(keyword)]
        else:
            results = list(self.all_apps)

        # 再按启用状态筛选
        if filter_key == 'enabled':
            results = [app for app in results if app.loopback_enabled]
        elif filter_key == 'disabled':
            results = [app for app in results if not app.loopback_enabled]

        self.filtered_apps = results
        self._render_tree()

        if keyword:
            self.status_var.set(self._t('status_found').format(len(results)))
        else:
            self.status_var.set(self._t('status_ready'))
        self._update_stats()

    # ========== 刷新列表 ==========
    def _refresh_list(self):
        """异步扫描应用列表（避免 UI 冻结）"""
        self.status_var.set(self._t('status_scanning'))
        self.btn_refresh.config(state='disabled')
        self.root.update_idletasks()

        def scan():
            apps = self.manager.get_uwp_apps()
            # 回到主线程更新 UI
            self.root.after(0, lambda: self._on_scan_done(apps))

        threading.Thread(target=scan, daemon=True).start()

    def _on_scan_done(self, apps: List[UWPApp]):
        """扫描完成回调"""
        self.all_apps = apps
        self.filtered_apps = apps

        # 初始化 checked 状态
        self._checked = {app.sid: app.loopback_enabled for app in apps}

        self._search_keyword = ""
        self.search_var.set("")
        self.filter_combo.set(self._get_filter_labels()[0])

        self._render_tree()
        self.status_var.set(self._t('status_scan_done'))
        self.btn_refresh.config(state='normal')
        self._update_stats()

    # ========== 统计 ==========
    def _update_stats(self):
        """更新统计信息"""
        total = len(self.all_apps)
        enabled = sum(1 for app in self.all_apps if app.loopback_enabled)
        selected = sum(1 for v in self._checked.values() if v)
        self.stats_var.set(self._t('stats').format(total, enabled, selected))

    # ========== 全选/取消全选 ==========
    def _select_all(self, select: bool):
        """全选/取消全选（只操作当前过滤后的列表）"""
        for app in self.filtered_apps:
            self._checked[app.sid] = select
            app.temp_enabled = select
        self._render_tree()
        self._update_stats()

    # ========== 保存 ==========
    def _save_changes(self):
        """保存更改"""
        if not self.all_apps:
            messagebox.showinfo(self._t('info'), self._t('scan_first'))
            return

        # 同步 checked 状态到 app.temp_enabled
        for app in self.all_apps:
            app.temp_enabled = self._checked.get(app.sid, app.loopback_enabled)

        changed = [app for app in self.all_apps if app.temp_enabled != app.loopback_enabled]
        if not changed:
            messagebox.showinfo(self._t('info'), self._t('no_changes'))
            return

        enable_count = sum(1 for app in changed if app.temp_enabled)
        disable_count = sum(1 for app in changed if not app.temp_enabled)

        msg = self._t('confirm_msg')
        if enable_count > 0:
            msg += self._t('confirm_enable').format(enable_count)
        if disable_count > 0:
            msg += self._t('confirm_disable').format(disable_count)
        msg += self._t('confirm_ask')

        if not messagebox.askyesno(self._t('confirm_title'), msg):
            return

        self.status_var.set(self._t('status_saving'))
        self.btn_save.config(state='disabled')
        self.root.update_idletasks()

        def do_save():
            result = self.manager.save_changes(self.all_apps)
            self.root.after(0, lambda: self._on_save_done(result))

        threading.Thread(target=do_save, daemon=True).start()

    def _on_save_done(self, result: Dict[str, int]):
        """保存完成回调"""
        # 同步 checked 状态
        for app in self.all_apps:
            self._checked[app.sid] = app.loopback_enabled

        self._render_tree()
        self.btn_save.config(state='normal')

        result_msg = self._t('save_done_msg')
        if result['enabled'] > 0:
            result_msg += self._t('save_ok_enable').format(result['enabled'])
        if result['disabled'] > 0:
            result_msg += self._t('save_ok_disable').format(result['disabled'])
        if result['failed'] > 0:
            result_msg += self._t('save_failed').format(result['failed'])

        self.status_var.set(self._t('status_saved').format(result['enabled'], result['disabled']))
        messagebox.showinfo(self._t('save_done_title'), result_msg)
        self._update_stats()


# ========== 入口 ==========
def main():
    root = tk.Tk()
    root.title('网络回环管理器')

    # DPI 感知
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

    app = UWPManagerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
