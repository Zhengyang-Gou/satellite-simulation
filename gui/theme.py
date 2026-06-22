"""Shared GUI constants and stylesheet."""

DARK_THEME = """
QMainWindow, QWidget, QDialog {
    background-color: #111318;
    color: #e3e3e3;
    font-family: "Segoe UI", "Roboto", "Noto Sans", sans-serif;
    font-size: 13px;
}
QMenuBar {
    background-color: #111318;
    border-bottom: 1px solid #2b3038;
    padding: 3px 8px;
}
QMenuBar::item {
    background: transparent;
    border-radius: 6px;
    padding: 6px 10px;
}
QMenuBar::item:selected {
    background-color: #22252b;
}
QMenu {
    background-color: #1a1c20;
    border: 1px solid #343842;
    padding: 6px;
}
QMenu::item {
    border-radius: 5px;
    padding: 7px 28px 7px 12px;
}
QMenu::item:selected {
    background-color: #2d3340;
}
QToolBar {
    background-color: #15181d;
    border: none;
    border-bottom: 1px solid #2b3038;
    spacing: 8px;
    padding: 8px 10px;
}
QToolBar QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    color: #d7dce3;
    padding: 7px 10px;
}
QToolBar QToolButton:hover {
    background-color: #22252b;
    border-color: #343842;
}
QToolBar QToolButton:pressed,
QToolBar QToolButton:checked {
    background-color: #263243;
    border-color: #5f7fae;
    color: #a8c7fa;
}
QStatusBar {
    background-color: #111318;
    border-top: 1px solid #2b3038;
    color: #aeb4be;
}
QSplitter::handle {
    background-color: #20242b;
}
QSplitter::handle:vertical {
    height: 5px;
}
QGroupBox {
    background-color: #1a1c20;
    border: 1px solid #343842;
    border-radius: 8px;
    margin-top: 16px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
    color: #e3e3e3;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #a8c7fa;
}
QLabel {
    color: #d7dce3;
    background-color: transparent;
}
QLabel#hintLabel {
    color: #aeb4be;
}
QLabel#metricChip,
QLabel#activeChip,
QLabel#redisChip {
    background-color: #20242b;
    border: 1px solid #343842;
    border-radius: 8px;
    padding: 5px 10px;
    color: #d7dce3;
}
QLabel#activeChip {
    color: #81c995;
}
QLabel#redisChip {
    color: #a8c7fa;
}
QLineEdit,
QSpinBox,
QDoubleSpinBox,
QComboBox {
    background-color: #1a1c20;
    border: 1px solid #343842;
    border-radius: 7px;
    color: #e3e3e3;
    min-height: 26px;
    padding: 5px 9px;
    selection-background-color: #3f5f89;
}
QLineEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QComboBox:focus {
    background-color: #20242b;
    border: 1px solid #8ab4f8;
}
QLineEdit:disabled,
QSpinBox:disabled,
QDoubleSpinBox:disabled {
    background-color: #17191d;
    color: #6f7782;
    border-color: #272b33;
}
QCheckBox {
    spacing: 8px;
    color: #d7dce3;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #58606c;
    background-color: #1a1c20;
}
QCheckBox::indicator:checked {
    background-color: #8ab4f8;
    border-color: #8ab4f8;
}
QPushButton {
    background-color: #22252b;
    border: 1px solid #3b414c;
    border-radius: 7px;
    color: #e3e3e3;
    min-height: 28px;
    padding: 6px 14px;
}
QPushButton:hover {
    background-color: #2a2f38;
    border-color: #4a5260;
}
QPushButton:pressed {
    background-color: #303743;
}
QPushButton:disabled {
    background-color: #191c21;
    border-color: #272b33;
    color: #69717c;
}
QPushButton#primaryButton {
    background-color: #8ab4f8;
    border-color: #8ab4f8;
    color: #0b1117;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background-color: #a8c7fa;
}
QTableWidget {
    background-color: #15181d;
    border: 1px solid #2b3038;
    border-radius: 8px;
    gridline-color: #2b3038;
    outline: none;
    alternate-background-color: #1a1d23;
    color: #e3e3e3;
}
QHeaderView::section {
    background-color: #20242b;
    border: none;
    border-right: 1px solid #2b3038;
    border-bottom: 1px solid #343842;
    color: #aeb4be;
    font-weight: 600;
    padding: 8px 6px;
}
QTableWidget::item {
    border-bottom: 1px solid #242932;
    padding: 4px;
}
QTableWidget::item:hover {
    background-color: #202732;
}
QTableWidget::item:selected {
    background-color: #263243;
    color: #e8f0fe;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #111318;
    border: none;
    width: 10px;
    height: 10px;
}
QScrollBar::handle {
    background-color: #3b414c;
    border-radius: 5px;
}
QScrollBar::handle:hover {
    background-color: #4d5563;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}
"""

DOWN = "down"
TABLE_HEADERS = [
    "链路ID",
    "源卫星ID",
    "目标卫星ID",
    "计算时延 (ms)",
    "Redis 时延 / 计算时延 (%)",
    "Redis 丢包 (%)",
]
