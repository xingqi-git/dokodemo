"""全局样式表 — Win10 开始菜单风格（浅色一体感）"""

GLOBAL_QSS = """
/* 主窗口背景（透明，paintEvent 自绘） */
QWidget#mainWidget {
    background-color: transparent;
}

/* ========== 标题栏（浅色一体感） ========== */
QWidget#titleBar {
    background-color: #F3F3F3;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}

QLabel#titleLabel {
    color: #333;
    font-size: 13px;
    font-weight: bold;
    padding-left: 16px;
}

QLabel#dirLabel {
    color: #888;
    font-size: 12px;
}

/* 标题栏按钮 — 最小化 / 最大化 / 关闭 */
QPushButton#titleBtn {
    background-color: transparent;
    border: none;
    color: #333;
    font-size: 12px;
    width: 46px;
    height: 36px;
    border-radius: 0px;
}

QPushButton#titleBtn:hover {
    background-color: rgba(0, 0, 0, 20);
}

QPushButton#titleBtn:pressed {
    background-color: rgba(0, 0, 0, 40);
}

/* 标题栏关闭按钮（hover 变红） */
QPushButton#titleBtn[class="close"]:hover {
    background-color: #E81123;
    color: white;
}

/* 标题栏图标按钮 — 刷新 / 设置（与窗管按钮同尺寸） */
QPushButton#titleIconBtn {
    background-color: transparent;
    border: none;
    color: #333;
    font-size: 14px;
    width: 46px;
    height: 36px;
    border-radius: 0px;
}

QPushButton#titleIconBtn:hover {
    background-color: rgba(0, 0, 0, 20);
}

QPushButton#titleIconBtn:pressed {
    background-color: rgba(0, 0, 0, 40);
}

/* ========== 滚动条 ========== */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px;
}

QScrollBar::handle:vertical {
    background: #C8C8C8;
    border-radius: 5px;
    min-height: 40px;
}

QScrollBar::handle:vertical:hover {
    background: #A8A8A8;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}

/* ========== 输入框 ========== */
QLineEdit {
    border: 1px solid #D0D0D0;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    background: white;
}

QLineEdit:focus {
    border: 1px solid #0078D7;
}

/* ========== 菜单 ========== */
QMenu {
    background-color: #F2F2F2;
    border: 1px solid #D0D0D0;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
    font-size: 13px;
    color: #333;
}

QMenu::item:selected {
    background-color: #E5E5E5;
    color: #000;
}

QMenu::separator {
    height: 1px;
    background: #D0D0D0;
    margin: 4px 8px;
}

/* ========== 对话框 ========== */
QInputDialog, QMessageBox {
    background-color: #F3F3F3;
}

QInputDialog QLabel, QMessageBox QLabel {
    color: #333;
    font-size: 13px;
}

QInputDialog QPushButton, QMessageBox QPushButton {
    background-color: #0078D7;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 20px;
    font-size: 13px;
    min-height: 28px;
    min-width: 70px;
}

QInputDialog QPushButton:hover, QMessageBox QPushButton:hover {
    background-color: #0066B4;
}

QInputDialog QPushButton:pressed, QMessageBox QPushButton:pressed {
    background-color: #005493;
}

/* ========== 分组区域 ========== */
QLabel#sectionTitle {
    color: #333;
    font-size: 14px;
    font-weight: bold;
}

/* 滚动区域和内容区与整体同色 */
QScrollArea {
    background-color: #F3F3F3;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: #F3F3F3;
}

QWidget#groupsContent,
QWidget#allShortcutsSection,
QWidget#groupsSection,
QWidget#allShortcutsFlow,
QWidget#groupsFlow {
    background-color: #F3F3F3;
}
"""
