"""Application styling."""

STYLESHEET = """
QMainWindow {
    background-color: #1e1e1e;
}

QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: system-ui, sans-serif;
    font-size: 13px;
}

QSplitter {
    background-color: #1e1e1e;
}

QSplitter::handle {
    background-color: #3a3a3a;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #5a5a5a;
}

QLabel {
    color: #e0e0e0;
    padding: 2px;
}

QLabel#title {
    font-size: 11px;
    font-weight: bold;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 8px 12px 4px 12px;
}

QLabel#imageLabel {
    background-color: #2a2a2a;
    border: 2px dashed #444;
    border-radius: 8px;
    color: #666;
    font-size: 14px;
}

QLabel#imageLabel:hover {
    border-color: #666;
    background-color: #2d2d2d;
}

QPushButton {
    background-color: #3a3a3a;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    color: #e0e0e0;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #4a4a4a;
}

QPushButton:pressed {
    background-color: #2a2a2a;
}

QPushButton#transmitButton {
    background-color: #2d5a27;
    font-size: 15px;
    font-weight: bold;
    padding: 14px 28px;
}

QPushButton#transmitButton:hover {
    background-color: #3a7a32;
}

QPushButton#transmitButton:pressed {
    background-color: #1e4a1a;
}

QPushButton#transmitButton:disabled {
    background-color: #2a2a2a;
    color: #555;
}

QPushButton#abToggle {
    background-color: #3a4a5a;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 4px;
}

QPushButton#abToggle:hover {
    background-color: #4a5a6a;
}

QPushButton#abToggle:pressed {
    background-color: #2a3a4a;
}

QPushButton#abToggle:disabled {
    background-color: #2a2a2a;
    color: #555;
}

QSlider::groove:horizontal {
    background: #3a3a3a;
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #888;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #aaa;
}

QSlider::sub-page:horizontal {
    background: #5a8a5a;
    border-radius: 3px;
}

QComboBox {
    background-color: #3a3a3a;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    min-width: 100px;
    font-weight: 500;
}

QComboBox:hover {
    background-color: #4a4a4a;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #888;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #2a2a2a;
    border: 1px solid #444;
    selection-background-color: #4a7a4a;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #3a3a3a;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #4a7a4a;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background: #2a2a2a;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #4a4a4a;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #5a5a5a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QGroupBox {
    background-color: #252525;
    border: 1px solid #3a3a3a;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    color: #888;
    font-size: 11px;
    font-weight: bold;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    background-color: #3a3a3a;
}

QCheckBox::indicator:checked {
    background-color: #5a8a5a;
}

QCheckBox::indicator:hover {
    background-color: #4a4a4a;
}

QProgressBar {
    background-color: #2a2a2a;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #5a8a5a;
    border-radius: 4px;
}
"""
