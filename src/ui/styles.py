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

QPushButton#exportButton {
    background-color: #3a3a3a;
    border: 1px solid #4a4a4a;
    border-radius: 3px;
    padding: 4px 10px;
    color: #e0e0e0;
    font-weight: 500;
    font-size: 10px;
}

QPushButton#exportButton:hover {
    background-color: #4a4a4a;
}

QPushButton#exportButton:pressed {
    background-color: #2a2a2a;
}

QPushButton#exportButton:disabled {
    background-color: #2a2a2a;
    color: #555;
    border-color: #333;
}

QPushButton#abToggle {
    background-color: #3a4a5a;
    font-size: 10px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 3px;
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

QFrame#unifiedHeader {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #2a2a2a, stop:0.5 #353535, stop:1 #2a2a2a);
    border: none;
    border-bottom: 2px solid #4a7a4a;
    padding: 0px;
}

QLabel#headerLogo {
    color: #6a9a6a;
    font-weight: bold;
    letter-spacing: 2px;
    padding: 0px;
}

QLabel#headerTagline {
    color: #777;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 0px;
}

QPushButton#headerButton {
    background-color: #3a3a3a;
    border: none;
    border-radius: 3px;
    padding: 4px 10px;
    color: #e0e0e0;
    font-weight: 500;
    font-size: 11px;
    min-width: 50px;
}

QPushButton#headerButton:hover {
    background-color: #4a4a4a;
}

QPushButton#headerButton:pressed {
    background-color: #2a2a2a;
}

QPushButton#headerButton:disabled {
    background-color: #2a2a2a;
    color: #555;
}

QPushButton#headerTransmitButton {
    background-color: #3a6a3a;
    border: none;
    border-radius: 3px;
    padding: 4px 12px;
    color: #ffffff;
    font-weight: bold;
    font-size: 11px;
    min-width: 70px;
}

QPushButton#headerTransmitButton:hover {
    background-color: #4a7a4a;
}

QPushButton#headerTransmitButton:pressed {
    background-color: #2a5a2a;
}

QPushButton#headerTransmitButton:disabled {
    background-color: #2a2a2a;
    color: #555;
}
"""
