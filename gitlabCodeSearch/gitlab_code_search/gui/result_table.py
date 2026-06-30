"""Results table widget with sorting, copy, and CSV export."""
from __future__ import annotations

import csv
import os
from typing import Optional

from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QKeySequence, QShortcut, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView, QHeaderView,
    QAbstractItemView, QApplication, QFileDialog, QLabel,
)

from ..model.result import SearchResultItem


class ResultTableModel(QAbstractTableModel):
    """High-performance table model for search results.
    
    Uses a flat list with direct index access for O(1) row retrieval.
    Batch inserts to minimize model reset signals.
    """

    COLUMNS = ["Project", "Branch", "File", "Line", "Preview"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[SearchResultItem] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._items)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        item = self._items[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return item.project
            elif col == 1:
                return item.branch
            elif col == 2:
                return item.file
            elif col == 3:
                return str(item.line_number)
            elif col == 4:
                return item.line_content.strip()

        elif role == Qt.ItemDataRole.ToolTipRole:
            return f"{item.project}/{item.file_path_full}:{item.line_number}"

        elif role == Qt.ItemDataRole.UserRole:
            return item

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section]
        return None

    def add_items(self, items: list[SearchResultItem]) -> None:
        """Batch insert items. Efficient for streaming results."""
        if not items:
            return
        start = len(self._items)
        self.beginInsertRows(QModelIndex(), start, start + len(items) - 1)
        self._items.extend(items)
        self.endInsertRows()

    def clear(self) -> None:
        """Clear all items."""
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def get_item(self, row: int) -> Optional[SearchResultItem]:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def get_all_items(self) -> list[SearchResultItem]:
        return self._items


class ResultTable(QWidget):
    """Center panel with sortable, copyable results table."""

    row_selected = Signal(object)        # SearchResultItem
    row_double_clicked = Signal(object)  # SearchResultItem

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header label
        self._header = QLabel("Results")
        self._header.setStyleSheet("font-weight: bold; padding: 4px 8px;")
        layout.addWidget(self._header)

        # Table model
        self._model = ResultTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        # Table view
        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)

        # Column sizing
        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        # Row height for density
        self._table.verticalHeader().setDefaultSectionSize(24)

        # Signals
        self._table.selectionModel().currentRowChanged.connect(self._on_row_changed)
        self._table.doubleClicked.connect(self._on_double_click)

        layout.addWidget(self._table)

    def _setup_shortcuts(self) -> None:
        """Ctrl+C to copy selected row."""
        copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self._table)
        copy_shortcut.activated.connect(self._copy_selected)

    def _on_row_changed(self, current: QModelIndex, previous: QModelIndex) -> None:
        if current.isValid():
            source_index = self._proxy.mapToSource(current)
            item = self._model.get_item(source_index.row())
            if item:
                self.row_selected.emit(item)

    def _on_double_click(self, index: QModelIndex) -> None:
        source_index = self._proxy.mapToSource(index)
        item = self._model.get_item(source_index.row())
        if item:
            self.row_double_clicked.emit(item)

    def _copy_selected(self) -> None:
        """Copy selected row as tab-separated text."""
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return
        source_index = self._proxy.mapToSource(indexes[0])
        item = self._model.get_item(source_index.row())
        if item:
            text = f"{item.project}\t{item.branch}\t{item.file_path_full}\t{item.line_number}\t{item.line_content.strip()}"
            QApplication.clipboard().setText(text)

    def add_items(self, items: list[SearchResultItem]) -> None:
        """Add batch of results (called from streaming worker)."""
        self._model.add_items(items)
        self._header.setText(f"Results ({self._model.rowCount()})")

    def clear(self) -> None:
        """Clear all results."""
        self._model.clear()
        self._header.setText("Results")

    def row_count(self) -> int:
        return self._model.rowCount()

    def export_csv(self) -> None:
        """Export results to CSV file."""
        items = self._model.get_all_items()
        if not items:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "search_results.csv", "CSV Files (*.csv)"
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Project", "Branch", "File", "Line", "Content", "Full Path"])
            for item in items:
                writer.writerow([
                    item.project, item.branch, item.file,
                    item.line_number, item.line_content.strip(), item.file_path_full,
                ])
