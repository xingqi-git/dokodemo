"""全局样式表"""

GLOBAL_QSS = """
/* 主窗口背景 */
QWidget#mainWidget {
    background-color: #F5F7FA;
}

/* 标题栏 */
QWidget#titleBar {
    background-color: #2C3E50;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}

QLabel#titleLabel {
    color: white;
    font-size: 14px;
    font-weight: bold;
    padding-left: 16px;
}

/* 标题栏按钮 */
QPushButton#titleBtn {
    background-color: transparent;
    border: none;
    color: white;
    font-size: 16px;
    width: 40px;
    height: 36px;
    border-radius: 0px;
}

QPushButton#titleBtn:hover {
    background-color: rgba(255, 255, 255, 30);
}

QPushButton#closeBtn:hover {
    background-color: #E74C3C;
}

/* 工具栏 */
QWidget#toolBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E0E0E0;
}

QPushButton#toolBtn {
    background-color: #4A90D9;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 3px 12px;
    font-size: 12px;
    min-height: 22px;
}

QPushButton#toolBtn:hover {
    background-color: #3A7BC8;
}

QPushButton#toolBtn:pressed {
    background-color: #2E6BAE;
}

QPushButton#toolBtnSecondary {
    background-color: #F0F0F0;
    color: #333;
    border: 1px solid #D0D0D0;
    border-radius: 4px;
    padding: 3px 12px;
    font-size: 12px;
    min-height: 22px;
}

QPushButton#toolBtnSecondary:hover {
    background-color: #E8E8E8;
}

/* 图标大小滑块 */
QLabel#sliderLabel {
    color: #555;
    font-size: 12px;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #E0E0E0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #4A90D9;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #3A7BC8;
}

/* 滚动条 */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px;
}

QScrollBar::handle:vertical {
    background: #C0C0C0;
    border-radius: 5px;
    min-height: 40px;
}

QScrollBar::handle:vertical:hover {
    background: #A0A0A0;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}

/* 输入框 */
QLineEdit {
    border: 1px solid #D0D0D0;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    background: white;
}

QLineEdit:focus {
    border: 1px solid #4A90D9;
}

/* 菜单 */
QMenu {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
    font-size: 13px;
}

QMenu::item:selected {
    background-color: #4A90D9;
    color: white;
}

QMenu::separator {
    height: 1px;
    background: #E0E0E0;
    margin: 4px 8px;
}

/* 对话框 */
QInputDialog, QMessageBox {
    background-color: #F5F7FA;
}

QInputDialog QLabel, QMessageBox QLabel {
    color: #333;
    font-size: 13px;
}

QInputDialog QPushButton, QMessageBox QPushButton {
    background-color: #4A90D9;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 20px;
    font-size: 13px;
    min-height: 28px;
    min-width: 70px;
}

QInputDialog QPushButton:hover, QMessageBox QPushButton:hover {
    background-color: #3A7BC8;
}
"""
