"""UI 组件"""

from .main_window import MainWindow
from .player_widget import PlayerWidget
from .channel_list import ChannelListWidget
from .epg_panel import EpgPanel
from .epg_dialog import EpgDialog
from .source_dialog import SourceDialog
from .proxy_dialog import ProxyDialog

__all__ = [
    "MainWindow",
    "PlayerWidget",
    "ChannelListWidget",
    "EpgPanel",
    "EpgDialog",
    "SourceDialog",
    "ProxyDialog",
]
