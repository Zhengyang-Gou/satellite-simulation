"""Reusable widget that owns the link table, filter box, stats label, and pagination."""

from typing import List, Set

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTableWidgetSelectionRange,
    QVBoxLayout,
    QWidget,
)

from .delegates import LatencyDelegate, RatioDelegate
from .link_state import LinkKey, LinkRecord, is_down, link_key
from .theme import DOWN, TABLE_HEADERS


class LinkTablePanel(QWidget):
    """Link table with filtering, pagination, selection preservation, and stats text."""

    selection_changed = Signal(object)

    def __init__(self, page_size: int = 10, parent=None):
        super().__init__(parent)
        self.page_size = page_size
        self.current_page = 1
        self.records: List[LinkRecord] = []
        self.selected_link_pairs: Set[LinkKey] = set()
        self.redis_in_flight = False
        self.redis_last_error = ""

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addLayout(self._build_toolbar())

        self.table = self._create_table()
        layout.addWidget(self.table)
        layout.addLayout(self._build_pagination_bar())

    def _build_toolbar(self) -> QHBoxLayout:
        toolbar = QHBoxLayout()

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Filter Name or Link, e.g. 0101 or 0101-0102")
        self.txt_search.setFixedWidth(360)
        self.txt_search.textChanged.connect(self._on_search_changed)

        self.lbl_stats = QLabel("Active Links: 0")

        toolbar.addWidget(self.txt_search)
        toolbar.addStretch()
        toolbar.addWidget(self.lbl_stats)
        return toolbar

    def _create_table(self) -> QTableWidget:
        table = QTableWidget(0, len(TABLE_HEADERS))

        table_font = QFont("Consolas", 10)
        table_font.setStyleHint(QFont.Monospace)
        table.setFont(table_font)

        table.setAlternatingRowColors(True)
        table.setHorizontalHeaderLabels(TABLE_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        table.setItemDelegateForColumn(3, LatencyDelegate(25.0, table))
        table.setItemDelegateForColumn(4, RatioDelegate(200.0, table))

        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.wheelEvent = lambda event: event.ignore()
        table.itemSelectionChanged.connect(self._on_table_selection)
        return table

    def _build_pagination_bar(self) -> QHBoxLayout:
        page_layout = QHBoxLayout()

        self.btn_prev = QPushButton("◄ Prev")
        self.btn_prev.clicked.connect(lambda: self.change_page(-1))

        self.lbl_page = QLabel("Page 1 / 1")

        self.btn_next = QPushButton("Next ►")
        self.btn_next.clicked.connect(lambda: self.change_page(1))

        page_layout.addStretch()
        page_layout.addWidget(self.btn_prev)
        page_layout.addWidget(self.lbl_page)
        page_layout.addWidget(self.btn_next)
        page_layout.addStretch()
        return page_layout

    def reset(self) -> None:
        self.records = []
        self.selected_link_pairs.clear()
        self.current_page = 1
        self.redis_in_flight = False
        self.redis_last_error = ""
        self.refresh()

    def set_records(
        self,
        records: List[LinkRecord],
        *,
        redis_in_flight: bool = False,
        redis_last_error: str = "",
    ) -> None:
        self.records = records
        self.redis_in_flight = redis_in_flight
        self.redis_last_error = redis_last_error
        self.refresh()

    def change_page(self, delta: int) -> None:
        self.current_page += delta
        self.refresh()

    def _on_search_changed(self) -> None:
        self.current_page = 1
        self.refresh()

    def _filtered_records(self) -> List[LinkRecord]:
        query = self.txt_search.text().strip().lower()
        if not query:
            return self.records

        result: List[LinkRecord] = []
        for record in self.records:
            src_name = str(record["src_name"]).lower()
            tgt_name = str(record["tgt_name"]).lower()
            forward = f"{src_name}-{tgt_name}"
            reverse = f"{tgt_name}-{src_name}"

            if query in src_name or query in tgt_name or query in forward or query in reverse:
                result.append(record)

        return result

    def refresh(self) -> None:
        filtered = self._filtered_records()
        total_pages = max(1, (len(filtered) + self.page_size - 1) // self.page_size)
        self.current_page = max(1, min(self.current_page, total_pages))

        self.lbl_page.setText(f"Page {self.current_page} / {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)
        self.lbl_stats.setText(self._stats_text())

        start_idx = (self.current_page - 1) * self.page_size
        page_data = filtered[start_idx : start_idx + self.page_size]

        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setSortingEnabled(False)
            self.table.clearSelection()

            if self.table.rowCount() != len(page_data):
                self.table.setRowCount(len(page_data))

            for row, record in enumerate(page_data):
                self._ensure_table_row(row)
                self._write_table_row(row, record)

            for row, record in enumerate(page_data):
                if link_key(record["src"], record["tgt"]) in self.selected_link_pairs:
                    self.table.setRangeSelected(
                        QTableWidgetSelectionRange(row, 0, row, self.table.columnCount() - 1),
                        True,
                    )
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

    def _stats_text(self) -> str:
        active_count = sum(1 for record in self.records if not is_down(record.get("latency")))
        total_count = len(self.records)
        redis_suffix = ""
        if self.redis_last_error:
            redis_suffix = " | Redis: down"
        elif self.redis_in_flight:
            redis_suffix = " | Redis: updating"
        return f"Active Links: {active_count} / {total_count}{redis_suffix}"

    def _ensure_table_row(self, row: int) -> None:
        for col in range(len(TABLE_HEADERS)):
            if self.table.item(row, col) is None:
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

    def _write_table_row(self, row: int, record: LinkRecord) -> None:
        values = [
            record["id"],
            record["src_name"],
            record["tgt_name"],
            record.get("latency", DOWN),
            record.get("redis_ratio_pct", DOWN),
        ]

        for col, value in enumerate(values):
            item = self.table.item(row, col)
            if col in (0, 3, 4):
                if item.data(Qt.EditRole) != value:
                    item.setData(Qt.EditRole, value)
            else:
                text = str(value)
                if item.text() != text:
                    item.setText(text)

        self.table.item(row, 1).setData(Qt.UserRole, record["src"])
        self.table.item(row, 2).setData(Qt.UserRole, record["tgt"])

    def _on_table_selection(self) -> None:
        selected: Set[LinkKey] = set()

        for item in self.table.selectedItems():
            row = item.row()
            src_item = self.table.item(row, 1)
            tgt_item = self.table.item(row, 2)
            if src_item is None or tgt_item is None:
                continue

            src = src_item.data(Qt.UserRole)
            tgt = tgt_item.data(Qt.UserRole)
            if src is not None and tgt is not None:
                selected.add(link_key(int(src), int(tgt)))

        self.selected_link_pairs = selected
        self.selection_changed.emit(set(self.selected_link_pairs))
