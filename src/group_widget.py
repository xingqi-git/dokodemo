from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QMenu, QAction, QInputDialog, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QFont, QPainter, QColor

from .shortcut_item import ShortcutItem
from .flow_layout import FlowLayout
from .config import UNGROUPED_ID, PRESET_COLORS


class GroupWidget(QFrame):
    """
    分组组件：标题栏 + 快捷方式流式布局
    支持组内拖拽排序、接收外部拖拽、右键菜单
    """

    shortcutMoved = pyqtSignal(str, int, str, int)  # from_group, from_idx, to_group, to_idx
    groupDragStarted = pyqtSignal(str)  # group_id
    groupRenamed = pyqtSignal(str, str)  # group_id, new_name
    groupColorChanged = pyqtSignal(str, int)  # group_id, color_index
    groupDeleted = pyqtSignal(str)  # group_id

    def __init__(self, group_id, group_name, color_index, shortcuts, icon_size=64, parent=None):
        super().__init__(parent)
        self.group_id = group_id
        self.group_name = group_name
        self.color_index = color_index
        self.icon_size = icon_size
        self.shortcuts = shortcuts  # [{path, name}, ...]
        self._is_ungrouped = (group_id == UNGROUPED_ID)
        self._drag_start_pos = None
        self._drop_indicator = -1  # 插入位置指示

        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(120)

        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 12)
        main_layout.setSpacing(8)

        # 标题栏
        self.title_bar = QWidget(self)
        self.title_bar.setFixedHeight(40)
        self.title_bar.setCursor(Qt.OpenHandCursor if not self._is_ungrouped else Qt.ArrowCursor)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(16, 0, 12, 0)
        title_layout.setSpacing(8)

        self.title_label = QLabel(self.group_name, self.title_bar)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        self.title_label.setFont(title_font)
        title_layout.addWidget(self.title_label)

        title_layout.addStretch()

        # 数量标签
        self.count_label = QLabel(f"{len(self.shortcuts)} 项", self.title_bar)
        title_layout.addWidget(self.count_label)

        main_layout.addWidget(self.title_bar)

        # 快捷方式流式布局区域
        self.flow_widget = QWidget(self)
        self.flow_layout = FlowLayout(self.flow_widget, margin=12, spacing=6)
        self.flow_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        main_layout.addWidget(self.flow_widget)

        self._populate_shortcuts()

    def _apply_style(self):
        """根据配色应用样式"""
        color = PRESET_COLORS[self.color_index % len(PRESET_COLORS)]
        self.setStyleSheet(f"""
            GroupWidget {{
                background-color: {color['light']};
                border: 1px solid {color['primary']};
                border-radius: 12px;
            }}
        """)
        self.title_label.setStyleSheet(f"color: {color['dark']};")
        self.title_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {color['primary']};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
        """)
        self.count_label.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 11px;")

    def _populate_shortcuts(self):
        """填充快捷方式（流式布局自动换行）"""
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for i, sc in enumerate(self.shortcuts):
            item = ShortcutItem(
                sc["path"], sc["name"],
                self.icon_size,
                self.group_id, i,
                self.flow_widget
            )
            self.flow_layout.addWidget(item)

        self.count_label.setText(f"{len(self.shortcuts)} 项")

    def update_icon_size(self, size):
        """更新图标大小"""
        self.icon_size = size
        self._populate_shortcuts()

    def update_shortcuts(self, shortcuts):
        """更新快捷方式列表（全量重建）"""
        self.shortcuts = shortcuts
        self._populate_shortcuts()

    def update_color(self, color_index):
        """更新配色"""
        self.color_index = color_index
        self._apply_style()

    def update_name(self, name):
        """更新分组名称"""
        self.group_name = name
        self.title_label.setText(name)

    # ---- 拖拽：分组整体拖拽 ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._is_ungrouped:
            if self.title_bar.geometry().contains(event.pos()):
                self._drag_start_pos = event.pos()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_start_pos:
            distance = (event.pos() - self._drag_start_pos).manhattanLength()
            if distance >= 15:
                self._start_group_drag()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def _start_group_drag(self):
        """启动分组拖拽"""
        mime_data = QMimeData()
        mime_data.setData("application/x-group-item", self.group_id.encode("utf-8"))
        mime_data.setText(self.group_name)

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        pixmap = self.grab()
        pixmap = pixmap.scaledToWidth(200, Qt.SmoothTransformation)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(20, 20))

        self.groupDragStarted.emit(self.group_id)
        drag.exec_(Qt.MoveAction)

    # ---- 拖拽：接收快捷方式 ----
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-shortcut-item"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-shortcut-item"):
            self._drop_indicator = self._calc_drop_index(event.pos())
            event.acceptProposedAction()
            self.update()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-shortcut-item"):
            data = bytes(event.mimeData().data("application/x-shortcut-item")).decode("utf-8")
            parts = data.split("|")
            if len(parts) == 2:
                from_group = parts[0]
                from_idx = int(parts[1])
                to_idx = self._calc_drop_index(event.pos())

                # 同组内拖拽，源位置在目标之前则索引减一
                if from_group == self.group_id and from_idx < to_idx:
                    to_idx -= 1

                self.shortcutMoved.emit(from_group, from_idx, self.group_id, to_idx)
            event.acceptProposedAction()
            self._drop_indicator = -1
            self.update()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._drop_indicator = -1
        self.update()
        super().dragLeaveEvent(event)

    def _calc_drop_index(self, pos):
        """根据鼠标位置计算插入索引（基于实际 widget 位置）"""
        if not self.shortcuts:
            return 0

        flow_pos = self.flow_widget.mapFrom(self, pos)

        for i in range(self.flow_layout.count()):
            item = self.flow_layout.itemAt(i)
            if not item:
                continue
            geom = item.geometry()
            if geom.top() <= flow_pos.y() <= geom.bottom():
                if flow_pos.x() < geom.center().x():
                    return i
                else:
                    return i + 1
            if geom.top() <= flow_pos.y() and flow_pos.y() > geom.bottom():
                if i == self.flow_layout.count() - 1:
                    return i + 1
                next_item = self.flow_layout.itemAt(i + 1)
                if next_item and next_item.geometry().top() > geom.bottom():
                    return i + 1

        return len(self.shortcuts)

    def paintEvent(self, event):
        """绘制拖拽插入指示线"""
        super().paintEvent(event)
        if self._drop_indicator >= 0 and self.shortcuts:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            color = PRESET_COLORS[self.color_index % len(PRESET_COLORS)]
            pen_color = QColor(color["primary"])
            pen_color.setAlpha(200)
            painter.setPen(pen_color)
            brush_color = QColor(color["primary"])
            brush_color.setAlpha(40)
            painter.setBrush(brush_color)

            idx = min(self._drop_indicator, len(self.shortcuts))
            item_count = self.flow_layout.count()
            if item_count == 0:
                painter.end()
                return

            flow_offset = self.flow_widget.mapTo(self, QPoint(0, 0))

            if idx < item_count:
                item = self.flow_layout.itemAt(idx)
                if item:
                    geom = item.geometry()
                    x = flow_offset.x() + geom.left() - 2
                    y = flow_offset.y() + geom.top()
                    h = geom.height()
                    painter.drawLine(int(x), int(y), int(x), int(y + h))
            else:
                last_item = self.flow_layout.itemAt(item_count - 1)
                if last_item:
                    geom = last_item.geometry()
                    x = flow_offset.x() + geom.right() + 4
                    y = flow_offset.y() + geom.top()
                    h = geom.height()
                    if x > flow_offset.x() + self.flow_widget.width() - 10:
                        x = flow_offset.x() + 10
                        y = flow_offset.y() + geom.bottom() + 6
                    painter.drawLine(int(x), int(y), int(x), int(y + h))

            painter.end()

    # ---- 右键菜单 ----
    def contextMenuEvent(self, event):
        if self._is_ungrouped:
            return

        menu = QMenu(self)

        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(self._on_rename)
        menu.addAction(rename_action)

        color_menu = menu.addMenu("更换配色")
        for i, color in enumerate(PRESET_COLORS):
            action = QAction(color["name"], self)
            action.triggered.connect(lambda checked, idx=i: self._on_color_change(idx))
            color_menu.addAction(action)

        delete_action = QAction("删除分组", self)
        delete_action.triggered.connect(self._on_delete)
        menu.addAction(delete_action)

        menu.exec_(event.globalPos())

    def _on_rename(self):
        new_name, ok = QInputDialog.getText(
            self, "重命名分组", "请输入新的分组名称:",
            text=self.group_name
        )
        if ok and new_name.strip():
            self.groupRenamed.emit(self.group_id, new_name.strip())

    def _on_color_change(self, color_index):
        self.groupColorChanged.emit(self.group_id, color_index)

    def _on_delete(self):
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "删除分组",
            f"确定要删除分组「{self.group_name}」吗？\n组内快捷方式将移至未添加分组。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.groupDeleted.emit(self.group_id)
