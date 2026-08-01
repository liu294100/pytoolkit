"""频道列表组件"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QComboBox, QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ..models import Channel, ChannelGroup


class ChannelListWidget(QWidget):
    """频道列表组件"""
    
    # 信号
    channel_selected = Signal(ChannelGroup)  # 选中频道分组
    channel_double_clicked = Signal(ChannelGroup)  # 双击播放
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups: list[ChannelGroup] = []
        self._filtered_groups: list[ChannelGroup] = []
        self._available_groups: list[str] = []
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 搜索栏
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)
        
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索频道...")
        self._search_input.textChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self._search_input)
        
        self._btn_clear = QPushButton("✕")
        self._btn_clear.setFixedSize(28, 28)
        self._btn_clear.clicked.connect(self._clear_search)
        search_layout.addWidget(self._btn_clear)
        
        layout.addLayout(search_layout)
        
        # 分组筛选
        group_layout = QHBoxLayout()
        group_layout.setSpacing(5)
        
        group_label = QLabel("分组:")
        group_label.setFixedWidth(40)
        group_layout.addWidget(group_label)
        
        self._group_combo = QComboBox()
        self._group_combo.addItem("全部", "")
        self._group_combo.currentIndexChanged.connect(self._on_filter_changed)
        group_layout.addWidget(self._group_combo)
        
        layout.addLayout(group_layout)
        
        # 频道列表
        self._list_widget = QListWidget()
        self._list_widget.setAlternatingRowColors(True)
        self._list_widget.itemClicked.connect(self._on_item_clicked)
        self._list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list_widget)
        
        # 统计信息
        self._status_label = QLabel("共 0 个频道")
        self._status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._status_label)
    
    def set_channels(self, groups: list[ChannelGroup]):
        """设置频道列表（已聚合的分组）"""
        self._groups = groups
        self._update_group_filter()
        self._apply_filter()
    
    def set_raw_channels(self, channels: list[Channel]):
        """设置原始频道列表（自动聚合）"""
        groups = ChannelGroup.group_channels(channels)
        self.set_channels(groups)
    
    def _update_group_filter(self):
        """更新分组筛选下拉框"""
        self._group_combo.blockSignals(True)
        current_group = self._group_combo.currentData()
        
        self._group_combo.clear()
        self._group_combo.addItem("全部", "")
        
        # 获取所有分组
        groups = sorted(set(g.group for g in self._groups if g.group))
        self._available_groups = groups
        
        for group in groups:
            self._group_combo.addItem(group, group)
        
        # 恢复选择
        if current_group:
            index = self._group_combo.findData(current_group)
            if index >= 0:
                self._group_combo.setCurrentIndex(index)
        
        self._group_combo.blockSignals(False)
    
    def _apply_filter(self):
        """应用筛选"""
        keyword = self._search_input.text().strip().lower()
        group_filter = self._group_combo.currentData() or ""
        
        self._filtered_groups = []
        for group in self._groups:
            # 关键词筛选
            if keyword and keyword not in group.name.lower():
                continue
            
            # 分组筛选
            if group_filter and group.group != group_filter:
                continue
            
            self._filtered_groups.append(group)
        
        self._update_list()
    
    def _update_list(self):
        """更新列表显示"""
        self._list_widget.clear()
        
        for group in self._filtered_groups:
            item = QListWidgetItem()
            
            # 显示名称和信号源数量
            source_info = f" ({group.source_count})" if group.source_count > 1 else ""
            display_text = f"{group.name}{source_info}"
            item.setText(display_text)
            
            # 保存数据
            item.setData(Qt.ItemDataRole.UserRole, group)
            
            # 工具提示
            tooltip = f"频道: {group.name}\n分组: {group.group}\n信号源: {group.source_count} 个"
            if group.tvg_id:
                tooltip += f"\ntvg-id: {group.tvg_id}"
            item.setToolTip(tooltip)
            
            self._list_widget.addItem(item)
        
        # 更新状态
        total = len(self._groups)
        filtered = len(self._filtered_groups)
        if total == filtered:
            self._status_label.setText(f"共 {total} 个频道")
        else:
            self._status_label.setText(f"显示 {filtered} / {total} 个频道")
    
    def _on_filter_changed(self):
        """筛选条件变化"""
        self._apply_filter()
    
    def _clear_search(self):
        """清空搜索"""
        self._search_input.clear()
        self._group_combo.setCurrentIndex(0)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """单击项目"""
        group = item.data(Qt.ItemDataRole.UserRole)
        if group:
            self.channel_selected.emit(group)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击项目"""
        group = item.data(Qt.ItemDataRole.UserRole)
        if group:
            self.channel_double_clicked.emit(group)
    
    def select_channel(self, group: ChannelGroup):
        """选中指定频道"""
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) is group:
                self._list_widget.setCurrentItem(item)
                break
    
    def get_selected_channel(self) -> ChannelGroup | None:
        """获取当前选中的频道"""
        item = self._list_widget.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
    
    @property
    def channel_count(self) -> int:
        """频道总数"""
        return len(self._groups)
    
    @property
    def filtered_count(self) -> int:
        """筛选后频道数"""
        return len(self._filtered_groups)
