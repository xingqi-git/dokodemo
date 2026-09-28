from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu, QAction, QInputDialog, QMessageBox
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QMimeData, QPoint, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QFontMetrics, QDrag, QColor, QBrush

from .shortcut import get_shortcut_icon, launch_shortcut, open_shortcut_location, rename_shortcut
from .config import ICON_SIZE, ALL_SHORTCUTS_ID


class ShortcutItem(QWidget):
    """单个快捷方式项：图标 + 两行名称，支持单击启动和拖拽"""

    shortcutLaunched = pyqtSignal()  # 快捷方式被点击启动
    shortcutRenamed = pyqtSignal(str, str, str)  # old_path, new_path, new_name
    shortcutMoveToGroup = pyqtSignal(str, int, str)  # from_group, index, to_group_id (ALL_SHORTCUTS_ID 表示移出)

    def __init__(self, shortcut_path, display_name, group_id="", index=0, group_list=None, parent=None):
        super().__init__(parent)
        self.shortcut_path = shortcut_path
        self.display_name = display_name
        self.group_id = group_id
        self.index = index
        self.group_list = group_list or []  # [(id, name), ...]
        self._drag_start_pos = None

        self.setFixedSize(self._calc_size())
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(display_name)  # 悬停显示全名

        self._init_ui()

    def _calc_size(self):
        """计算组件尺寸：图标 + 文字区域"""
        width = ICON_SIZE + 16  # 左右各8px边距
        height = ICON_SIZE + 40 + 8  # 图标 + 两行文字 + 底部边距
        return QSize(width, height)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # 图标（先显示占位，异步加载真实图标）
        self.icon_label = QLabel(self)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(ICON_SIZE, ICON_SIZE)
        self.icon_label.setScaledContents(True)
        self.icon_label.setAttribute(Qt.WA_TranslucentBackground)
        self._set_placeholder_icon()
        layout.addWidget(self.icon_label)

        # 名称（两行，超出省略）
        self.name_label = QLabel(self)
        self.name_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.name_label.setWordWrap(False)
        self.name_label.setFixedWidth(ICON_SIZE + 8)
        self.name_label.setAttribute(Qt.WA_TranslucentBackground)
        self._update_name()
        layout.addWidget(self.name_label)

        # 延迟加载真实图标，避免阻塞启动
        self._icon_loaded = False
        QTimer.singleShot(0, self._load_real_icon)

    def _set_placeholder_icon(self):
        """显示占位图标"""
        pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor("#E0E0E0")))
        painter.setPen(Qt.NoPen)
        margin = int(ICON_SIZE * 0.2)
        painter.drawRoundedRect(
            margin, margin, ICON_SIZE - 2 * margin, ICON_SIZE - 2 * margin,
            int(ICON_SIZE * 0.1), int(ICON_SIZE * 0.1)
        )
        painter.end()
        self.icon_label.setPixmap(pixmap)

    def _load_real_icon(self):
        """异步加载真实图标"""
        if self._icon_loaded:
            return
        self._icon_loaded = True
        try:
            pixmap = get_shortcut_icon(self.shortcut_path, ICON_SIZE)
            self.icon_label.setPixmap(pixmap)
        except Exception:
            pass

    def _update_name(self):
        """绘制两行省略的名称"""
        font = self.name_label.font()
        fm = QFontMetrics(font)
        text = self.display_name

        line_height = fm.height()
        max_width = ICON_SIZE + 8

        # 第一行
        first_line = ""
        second_line = ""
        remaining = text

        for i in range(len(remaining)):
            test = remaining[:i + 1]
            if fm.width(test) > max_width:
                first_line = remaining[:i]
                remaining = remaining[i:]
                break
        else:
            first_line = text
            remaining = ""

        # 第二行（带省略号）
        if remaining:
            for i in range(len(remaining)):
                test = remaining[:i + 1] + "..."
                if fm.width(test) > max_width:
                    second_line = remaining[:max(0, i)] + "..."
                    break
            else:
                second_line = remaining

            display_text = f"{first_line}\n{second_line}"
        else:
            display_text = first_line

        self.name_label.setText(display_text)
        self.name_label.setStyleSheet("color: #333; font-size: 12px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_start_pos:
            distance = (event.pos() - self._drag_start_pos).manhattanLength()
            if distance >= 15:  # 拖拽阈值
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_start_pos:
            distance = (event.pos() - self._drag_start_pos).manhattanLength()
            if distance < 15:
                # 单击启动
                if launch_shortcut(self.shortcut_path):
                    self.shortcutLaunched.emit()
            self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def _start_drag(self):
        """启动拖拽"""
        try:
            mime_data = QMimeData()
            mime_data.setData("application/x-shortcut-item",
                              f"{self.group_id}|{self.index}".encode("utf-8"))
            mime_data.setText(self.display_name)

            drag = QDrag(self)
            drag.setMimeData(mime_data)

            # 拖拽预览图
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

            drag.exec_(Qt.MoveAction)
        except Exception as e:
            import traceback
            print(f"[ShortcutItem._start_drag] 异常: {e}")
            traceback.print_exc()

    def enterEvent(self, event):
        self.setStyleSheet("""
            ShortcutItem {
                background-color: rgba(255, 255, 255, 180);
                border-radius: 8px;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("""
            ShortcutItem {
                background-color: transparent;
                border-radius: 8px;
            }
        """)
        super().leaveEvent(event)

    def contextMenuEvent(self, event):
        """右键菜单：打开所在位置、移动到、重命名"""
        menu = QMenu(self)

        open_location_action = QAction("打开所在位置", self)
        open_location_action.triggered.connect(self._on_open_location)
        menu.addAction(open_location_action)

        menu.addSeparator()

        # 移动到子菜单
        move_menu = menu.addMenu("移动到")
        if self.group_id == ALL_SHORTCUTS_ID:
            # 未分组：只显示各分组
            if self.group_list:
                for gid, gname in self.group_list:
                    action = QAction(gname, self)
                    action.triggered.connect(
                        lambda checked, gid=gid: self._on_move_to_group(gid)
                    )
                    move_menu.addAction(action)
            else:
                no_group_action = QAction("（暂无分组）", self)
                no_group_action.setEnabled(False)
                move_menu.addAction(no_group_action)
        else:
            # 在分组内：显示"移出分组" + 其他分组
            remove_action = QAction("移出分组", self)
            remove_action.triggered.connect(
                lambda: self._on_move_to_group(ALL_SHORTCUTS_ID)
            )
            move_menu.addAction(remove_action)

            move_menu.addSeparator()

            other_groups = [(gid, gname) for gid, gname in self.group_list if gid != self.group_id]
            if other_groups:
                for gid, gname in other_groups:
                    action = QAction(gname, self)
                    action.triggered.connect(
                        lambda checked, gid=gid: self._on_move_to_group(gid)
                    )
                    move_menu.addAction(action)
            else:
                no_group_action = QAction("（暂无其他分组）", self)
                no_group_action.setEnabled(False)
                move_menu.addAction(no_group_action)

        menu.addSeparator()

        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(self._on_rename)
        menu.addAction(rename_action)

        menu.exec_(event.globalPos())

    def _on_open_location(self):
        open_shortcut_location(self.shortcut_path)

    def _on_move_to_group(self, to_group_id):
        """移动到指定分组（ALL_SHORTCUTS_ID 表示移出到全部快捷方式）"""
        self.shortcutMoveToGroup.emit(self.group_id, self.index, to_group_id)

    def _on_rename(self):
        new_name, ok = QInputDialog.getText(
            self, "重命名快捷方式", "请输入新的名称:",
            text=self.display_name
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(self, "提示", "名称不能为空")
            return
        if new_name == self.display_name:
            return
        new_path = rename_shortcut(self.shortcut_path, new_name)
        if new_path:
            old_path = self.shortcut_path
            self.shortcut_path = new_path
            self.display_name = new_name
            self._update_name()
            self.setToolTip(new_name)
            self.shortcutRenamed.emit(old_path, new_path, new_name)
        else:
            QMessageBox.warning(self, "提示", "重命名失败，可能名称已存在或不合法")
