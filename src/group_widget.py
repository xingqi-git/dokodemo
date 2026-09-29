from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QMenu, QAction, QInputDialog, QFrame, QMessageBox,
    QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QFont, QPainter, QColor

from .shortcut_item import ShortcutItem
from .flow_layout import FlowLayout
from .config import PRESET_COLORS, MIN_GROUP_WIDTH, ICON_SIZE, SMALL_ICON_SIZE


def _darken_color(color_hex, ratio):
    """将颜色按 ratio（0~1）加深（与黑色混合），返回十六进制色值"""
    r = int(color_hex[1:3], 16)
    g = int(color_hex[3:5], 16)
    b = int(color_hex[5:7], 16)
    r = int(r * (1 - ratio))
    g = int(g * (1 - ratio))
    b = int(b * (1 - ratio))
    return f"#{r:02X}{g:02X}{b:02X}"


class GroupWidget(QFrame):
    """
    分组组件：标题栏 + 快捷方式流式布局
    支持右边缘拖拽调整宽度、组内拖拽排序、接收外部拖拽、右键菜单
    高度根据内容自动调整
    """

    shortcutMoved = pyqtSignal(str, int, str, int)  # from_group, from_idx, to_group, to_idx
    shortcutLaunched = pyqtSignal()  # 组内快捷方式被启动
    shortcutRenamed = pyqtSignal(str, str, str, str)  # group_id, old_path, new_path, new_name
    groupDragStarted = pyqtSignal(str)  # group_id
    groupRenamed = pyqtSignal(str, str)  # group_id, new_name
    groupColorChanged = pyqtSignal(str, int)  # group_id, color_index
    groupDeleted = pyqtSignal(str)  # group_id
    groupWidthChanged = pyqtSignal(str, int)  # group_id, width
    groupIconSizeChanged = pyqtSignal(str, int)  # group_id, icon_size
    groupShowNameChanged = pyqtSignal(str, bool)  # group_id, show_name

    def __init__(self, group_id, group_name, color_index, shortcuts, group_width,
                 group_list=None, icon_size=ICON_SIZE, show_name=True, parent=None):
        super().__init__(parent)
        self.group_id = group_id
        self.group_name = group_name
        self.color_index = color_index
        self.group_width = max(MIN_GROUP_WIDTH, int(group_width))
        self.shortcuts = shortcuts  # [{path, name}, ...]
        self.group_list = group_list or []  # [(id, name), ...] 所有分组列表
        self.icon_size = icon_size
        self.show_name = show_name
        self._drag_start_pos = None
        self._drop_indicator = -1  # 插入位置指示

        # 宽度调整
        self._resize_margin = 6
        self._is_resizing = False
        self._resize_start_width = 0
        self._resize_start_x = 0

        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedWidth(self.group_width)
        # 高度由内容决定（heightForWidth）
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        self._init_ui()
        self._apply_style()

        # 给 resize handle 安装事件过滤器，捕获鼠标事件
        self._resize_handle.installEventFilter(self)

    def _init_ui(self):
        # 外层水平布局：内容 + 右侧拖拽手柄
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 内容区
        self._content_widget = QWidget(self)
        main_layout = QVBoxLayout(self._content_widget)
        main_layout.setContentsMargins(0, 0, 0, 12)
        main_layout.setSpacing(2)

        # 标题栏
        self.title_bar = QWidget(self._content_widget)
        self.title_bar.setFixedHeight(26)
        self.title_bar.setCursor(Qt.OpenHandCursor)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(12, 12, 12, 1)
        title_layout.setSpacing(8)

        self.title_label = QLabel(self.group_name, self.title_bar)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        self.title_label.setFont(title_font)
        title_layout.addWidget(self.title_label)

        title_layout.addStretch()

        main_layout.addWidget(self.title_bar)

        # 快捷方式流式布局区域
        self.flow_widget = QWidget(self._content_widget)
        self.flow_layout = FlowLayout(self.flow_widget, margin=6, spacing=4)
        self.flow_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        # flow_widget 高度由 FlowLayout 决定（Minimum 表示最小高度=内容高度）
        self.flow_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        main_layout.addWidget(self.flow_widget)

        outer_layout.addWidget(self._content_widget, 1)

        # 右侧宽度拖拽手柄（悬浮叠加在右边缘）
        self._resize_handle = QWidget(self)
        self._resize_handle.setFixedWidth(self._resize_margin)
        self._resize_handle.setCursor(Qt.SizeHorCursor)
        self._resize_handle.setStyleSheet("background-color: transparent;")
        # 手动定位，由 resizeEvent 控制位置

        self._populate_shortcuts()

    def _apply_style(self):
        """根据配色应用样式（一体感，无边框，分组背景略深）"""
        color = PRESET_COLORS[self.color_index % len(PRESET_COLORS)]
        # 分组背景色：在浅色基础上略加深，与界面底色区分更明显
        bg_color = _darken_color(color["light"], 0.08)
        self.setStyleSheet(f"""
            GroupWidget {{
                background-color: {bg_color};
                border: none;
                border-radius: 10px;
            }}
        """)
        self.title_label.setStyleSheet(f"color: {color['dark']};")
        self.title_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
        """)

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
                self.group_id, i,
                self.group_list,
                icon_size=self.icon_size,
                show_name=self.show_name,
                parent=self.flow_widget
            )
            item.shortcutLaunched.connect(self.shortcutLaunched.emit)
            item.shortcutRenamed.connect(self._on_shortcut_renamed)
            item.shortcutMoveToGroup.connect(self._on_shortcut_move_to_group)
            self.flow_layout.addWidget(item)

        # 触发高度重算
        self.updateGeometry()

    def _on_shortcut_renamed(self, old_path, new_path, new_name):
        """快捷方式重命名后，更新本地数据并向上传递"""
        for sc in self.shortcuts:
            if sc["path"] == old_path:
                sc["path"] = new_path
                sc["name"] = new_name
                break
        self.shortcutRenamed.emit(self.group_id, old_path, new_path, new_name)

    def _on_shortcut_move_to_group(self, from_group, from_idx, to_group):
        """快捷方式右键移动到分组"""
        # 目标是本组的话忽略
        if from_group == to_group:
            return
        if to_group == self.group_id:
            return
        # 向上转发，最终由 GroupsContainer/MainWindow 处理
        self.shortcutMoved.emit(from_group, from_idx, to_group, -1)

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

    def set_group_width(self, width):
        """设置分组宽度"""
        width = max(MIN_GROUP_WIDTH, int(width))
        self.group_width = width
        self.setFixedWidth(width)
        self.updateGeometry()

    def hasHeightForWidth(self):
        """告诉布局系统高度随宽度变化"""
        return True

    def heightForWidth(self, width):
        """根据宽度计算需要的高度（标题栏 + flow内容 + 边距 + 间距）"""
        # 标题栏固定高度 26 + 间距 2 + bottom margin 12 + flow高度
        flow_width = width
        flow_height = self.flow_layout.heightForWidth(flow_width)
        return 26 + 2 + 12 + flow_height

    def resizeEvent(self, event):
        """调整大小时同步更新右侧手柄位置"""
        super().resizeEvent(event)
        handle_width = self._resize_margin
        self._resize_handle.setGeometry(
            self.width() - handle_width,
            0,
            handle_width,
            self.height()
        )
        self._resize_handle.raise_()

    # ---- 宽度调整（右侧拖拽手柄） ----
    def eventFilter(self, obj, event):
        if obj is self._resize_handle:
            if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                self._is_resizing = True
                self._resize_start_width = self.group_width
                self._resize_start_x = event.globalX()
                return True
            elif event.type() == event.MouseMove and event.buttons() & Qt.LeftButton and self._is_resizing:
                dx = event.globalX() - self._resize_start_x
                new_width = max(MIN_GROUP_WIDTH, self._resize_start_width + dx)
                self.set_group_width(new_width)
                return True
            elif event.type() == event.MouseButtonRelease and event.button() == Qt.LeftButton and self._is_resizing:
                self._is_resizing = False
                self.groupWidthChanged.emit(self.group_id, self.group_width)
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 检测标题栏分组整体拖拽
            if self.title_bar.geometry().contains(event.pos()):
                self._drag_start_pos = event.pos()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 分组整体拖拽
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
        pixmap = pixmap.scaledToWidth(180, Qt.SmoothTransformation)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(20, 16))

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
        """根据鼠标位置计算插入索引（先找行，再在行内找位置）"""
        count = self.flow_layout.count()
        if count == 0:
            return 0

        flow_pos = self.flow_widget.mapFrom(self, pos)

        # 第一步：按行分组
        rows = []  # [(start_idx, end_idx, top, bottom)]
        current_row_top = None
        current_row_bottom = None
        row_start = 0

        for i in range(count):
            item = self.flow_layout.itemAt(i)
            if not item:
                continue
            geom = item.geometry()
            if current_row_top is None:
                current_row_top = geom.top()
                current_row_bottom = geom.bottom()
                row_start = i
            elif geom.top() > current_row_bottom + 2:
                # 新行
                rows.append((row_start, i - 1, current_row_top, current_row_bottom))
                current_row_top = geom.top()
                current_row_bottom = geom.bottom()
                row_start = i
            else:
                current_row_bottom = max(current_row_bottom, geom.bottom())
        rows.append((row_start, count - 1, current_row_top, current_row_bottom))

        # 第二步：找到鼠标所在的行
        target_row_idx = 0
        for i, (_, _, top, bottom) in enumerate(rows):
            if flow_pos.y() <= bottom:
                target_row_idx = i
                break
            target_row_idx = i

        row_start, row_end, row_top, row_bottom = rows[target_row_idx]

        # 第三步：在目标行内按 x 位置找插入点
        if flow_pos.y() < row_top:
            return row_start
        if flow_pos.y() <= row_bottom:
            for i in range(row_start, row_end + 1):
                item = self.flow_layout.itemAt(i)
                if not item:
                    continue
                geom = item.geometry()
                if flow_pos.x() < geom.center().x():
                    return i
            return row_end + 1
        return row_end + 1

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
        menu = QMenu(self)

        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(self._on_rename)
        menu.addAction(rename_action)

        color_menu = menu.addMenu("更换配色")
        for i, color in enumerate(PRESET_COLORS):
            action = QAction(color["name"], self)
            action.triggered.connect(lambda checked, idx=i: self._on_color_change(idx))
            color_menu.addAction(action)

        menu.addSeparator()

        # 图标大小子菜单
        size_menu = menu.addMenu("图标大小")
        big_action = QAction("大图标", self)
        big_action.setCheckable(True)
        big_action.setChecked(self.icon_size == ICON_SIZE)
        big_action.triggered.connect(lambda: self._on_icon_size_change(ICON_SIZE))
        size_menu.addAction(big_action)
        small_action = QAction("小图标", self)
        small_action.setCheckable(True)
        small_action.setChecked(self.icon_size == SMALL_ICON_SIZE)
        small_action.triggered.connect(lambda: self._on_icon_size_change(SMALL_ICON_SIZE))
        size_menu.addAction(small_action)

        # 显示/隐藏图标名称
        if self.show_name:
            name_action = QAction("隐藏图标名称", self)
        else:
            name_action = QAction("显示图标名称", self)
        name_action.triggered.connect(self._on_show_name_change)
        menu.addAction(name_action)

        menu.addSeparator()

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

    def _on_icon_size_change(self, size):
        """切换图标大小"""
        if self.icon_size == size:
            return
        self.icon_size = size
        self._populate_shortcuts()
        self.groupIconSizeChanged.emit(self.group_id, size)

    def _on_show_name_change(self):
        """切换是否显示图标名称"""
        self.show_name = not self.show_name
        self._populate_shortcuts()
        self.groupShowNameChanged.emit(self.group_id, self.show_name)

    def _on_delete(self):
        reply = QMessageBox.question(
            self, "删除分组",
            f"确定要删除分组「{self.group_name}」吗？\n组内快捷方式将移回全部快捷方式。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.groupDeleted.emit(self.group_id)
