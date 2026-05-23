"""Shared GUI constants and stylesheet."""

DARK_THEME = """
QMainWindow, QWidget, QDialog { background-color: #1e1e1e; color: #cccccc; font-family: "Segoe UI", sans-serif; font-size: 13px; }
QTableWidget { background-color: #252526; border: 1px solid #333333; gridline-color: #3e3e42; outline: none; alternate-background-color: #1e1e1e;}
QHeaderView::section { background-color: #2d2d2d; border: 1px solid #3e3e42; padding: 4px; font-weight: bold;}
QTableWidget::item { border-bottom: 1px solid #333333; }
QTableWidget::item:hover { background-color: #2a2d2f; }
QTableWidget::item:selected { background-color: #094771; }
QLineEdit { background-color: #333333; border: 1px solid #444444; padding: 4px 8px; color: #fff; border-radius: 12px;}
QLineEdit:focus { border: 1px solid #007acc; background-color: #1e1e1e;}
QSpinBox, QDoubleSpinBox, QComboBox { background-color: #3c3c3c; border: 1px solid #555; padding: 3px; color: #fff; border-radius: 3px;}
QPushButton { background-color: #3c3c3c; border: 1px solid #555; padding: 5px 15px; color: #fff; border-radius: 3px;}
QPushButton:hover { background-color: #4c4c4c; }
"""

DOWN = "down"
TABLE_HEADERS = ["Link ID", "Source", "Target", "Latency (ms)", "Redis / Cal (%)", "Redis Loss (%)"]
