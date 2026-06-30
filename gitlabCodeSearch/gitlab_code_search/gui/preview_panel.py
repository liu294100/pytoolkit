"""Code preview panel with syntax highlighting and line numbers."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import (
    QFont, QFontMetrics, QColor, QPainter, QTextFormat,
    QTextCharFormat, QSyntaxHighlighter, QTextDocument,
    QPalette,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPlainTextEdit, QLabel, QTextEdit,
)


class LineNumberArea(QWidget):
    """Line number gutter for the code editor."""

    def __init__(self, editor: CodePreview):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return self._editor.line_number_area_size()

    def paintEvent(self, event):
        self._editor.line_number_area_paint(event)


class CodePreview(QPlainTextEdit):
    """Code preview with line numbers and highlight support.
    
    Optimized: only loads context lines around the match, not entire file.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Monospace font
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        # Line number area
        self._line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)

        self._first_line_number = 1  # Offset for displayed line numbers
        self._highlight_line = -1    # Line to highlight (0-indexed in document)

        self._update_line_number_width()

    def set_content(self, text: str, first_line: int = 1, highlight_line: int = -1) -> None:
        """Set code content with line offset and highlight.
        
        Args:
            text: Code text to display
            first_line: Line number of the first line displayed
            highlight_line: Absolute line number to highlight
        """
        self._first_line_number = first_line
        self._highlight_line = highlight_line - first_line if highlight_line >= first_line else -1
        self.setPlainText(text)
        self._update_line_number_width()

        # Highlight the target line
        if self._highlight_line >= 0:
            self._highlight_current_line()
            # Scroll to highlighted line
            block = self.document().findBlockByLineNumber(self._highlight_line)
            cursor = self.textCursor()
            cursor.setPosition(block.position())
            self.setTextCursor(cursor)
            self.centerCursor()

    def _highlight_current_line(self) -> None:
        """Highlight the matched line with a background color."""
        selections = []

        if self._highlight_line >= 0:
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(44, 49, 58))  # Dark highlight
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)

            block = self.document().findBlockByLineNumber(self._highlight_line)
            cursor = self.textCursor()
            cursor.setPosition(block.position())
            selection.cursor = cursor
            selections.append(selection)

        self.setExtraSelections(selections)

    # --- Line Number Area ---

    def line_number_area_size(self):
        digits = max(1, len(str(self._first_line_number + self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance("9") * (digits + 1)
        return space

    def _update_line_number_width(self, _=0):
        self.setViewportMargins(self.line_number_area_size(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_size(), cr.height())
        )

    def line_number_area_paint(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor(30, 30, 30))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(self._first_line_number + block_number)

                if block_number == self._highlight_line:
                    painter.setPen(QColor(255, 200, 50))  # Highlight color
                    painter.fillRect(
                        0, top, self._line_number_area.width(), 
                        self.fontMetrics().height(),
                        QColor(44, 49, 58)
                    )
                else:
                    painter.setPen(QColor(120, 120, 120))

                painter.drawText(
                    0, top,
                    self._line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, number,
                )

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

        painter.end()


class PreviewPanel(QWidget):
    """Right panel showing code preview with context."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._context_lines = 10
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # File path header
        self._file_label = QLabel("No file selected")
        self._file_label.setStyleSheet(
            "padding: 6px 8px; font-weight: bold; border-bottom: 1px solid #3c3c3c;"
        )
        self._file_label.setWordWrap(True)
        layout.addWidget(self._file_label)

        # Code preview
        self._code_view = CodePreview()
        layout.addWidget(self._code_view)

    def show_code(self, content: str, line_number: int, match_text: str, file_path: str = "") -> None:
        """Display code with context around the matched line.
        
        Only shows ±context_lines around the match for performance.
        """
        self._file_label.setText(f"{file_path}  (Line {line_number})")

        lines = content.split("\n")
        total_lines = len(lines)

        # Calculate context window
        start = max(0, line_number - 1 - self._context_lines)
        end = min(total_lines, line_number + self._context_lines)

        # Extract context
        context_text = "\n".join(lines[start:end])
        first_line_num = start + 1

        self._code_view.set_content(context_text, first_line_num, line_number)

    def clear(self) -> None:
        """Clear preview."""
        self._file_label.setText("No file selected")
        self._code_view.setPlainText("")

    def set_context_lines(self, n: int) -> None:
        self._context_lines = n
