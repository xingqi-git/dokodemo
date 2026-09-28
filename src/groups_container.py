from PyQt5.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint

from .group_widget import GroupWidget
from .shortcut_item import ShortcutItem
from .flow_layout import FlowLayout
from .config import ALL_SHORTCUTS_ID


class GroupsContainer(QScrollArea):
    """
    磁贴式容器：
    顶部：全部快捷方式（流式布局，占满宽度）
    下方：分组列表（流式布局，每组独立宽度，可拖拽排序）
    """

    shortcutMoved = pyqtSignal(str, int, str, int)  # from_group, from_idx, to_group, to_idx
    shortcutLaunched = pyqtSignal()
    shortcutRenamed = pyqtSignal(str, str, str, str)  # group_id, old_path, new_path, new_name
    groupMoved = pyqtSignal(int, int)  # from_idx, to_idx
    groupRenamed = pyqtSignal(str, str)  # group_id, new_name
    groupColorChanged = pyqtSignal(str, int)  # group_id, color_index
    groupDeleted = pyqtSignal(str)  # group_id
    groupWidthChanged = pyqtSignal(str, int)  # group_id, width
    blankClicked = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._group_widgets = []
        self._drag_drop_indicator = -1  # 分组拖拽插入位置索引

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WA_StyledBackground, True)

        # 主内容 widget
        self._content = QWidget(self)
        self._content.setObjectName("groupsContent")
        self._main_layout = QVBoxLayout(self._content)
        self._main_layout.setContentsMargins(16, 16, 16, 16)
        self._main_layout.setSpacing(16)

        # ---- 顶部：全部快捷方式区域 ----
        self._all_section = QWidget(self._content)
        self._all_section.setObjectName("allShortcutsSection")
        all_layout = QVBoxLayout(self._all_section)
        all_layout.setContentsMargins(0, 0, 0, 0)
        all_layout.setSpacing(0)

        # 快捷方式流
        self._all_flow_widget = QWidget(self._all_section)
        self._all_flow_widget.setObjectName("allShortcutsFlow")
        self._all_flow_widget.setAcceptDrops(True)
        self._all_flow_layout = FlowLayout(self._all_flow_widget, margin=0, spacing=6)
        self._all_flow_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        all_layout.addWidget(self._all_flow_widget)

        self._main_layout.addWidget(self._all_section)

        # ---- 下方：分组区域 ----
        self._groups_flow_widget = QWidget(self._content)
        self._groups_flow_widget.setObjectName("groupsFlow")
        self._groups_flow_widget.setAcceptDrops(True)
        self._groups_flow_layout = FlowLayout(self._groups_flow_widget, margin=0, spacing=12)
        self._groups_flow_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self._main_layout.addWidget(self._groups_flow_widget)
        self._main_layout.addStretch()

        self.setWidget(self._content)

        # 安装事件过滤器，检测空白处点击
        self._content.installEventFilter(self)
        self.viewport().installEventFilter(self)

    # ---- 刷新 ----
    def refresh(self):
        """全量刷新界面"""
        # 生成所有分组列表 [(id, name), ...]
        group_list = [(g["id"], g["name"]) for g in self.config.groups]

        # 清空全部快捷方式
        while self._all_flow_layout.count():
            item = self._all_flow_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 清空分组
        for gw in self._group_widgets:
            gw.setParent(None)
            gw.deleteLater()
        self._group_widgets.clear()

        # 填充全部快捷方式
        for i, sc in enumerate(self.config.shortcuts):
            item = ShortcutItem(
                sc["path"], sc["name"],
                ALL_SHORTCUTS_ID, i,
                group_list,
                self._all_flow_widget
            )
            item.shortcutLaunched.connect(self.shortcutLaunched.emit)
            item.shortcutRenamed.connect(self._on_shortcut_renamed_all)
            item.shortcutMoveToGroup.connect(self._on_shortcut_move_to_group)
            self._all_flow_layout.addWidget(item)

        # 填充分组
        for g in self.config.groups:
            gw = GroupWidget(
                g["id"], g["name"], g.get("color_index", 0),
                g.get("shortcuts", []),
                g.get("width", 240),
                group_list,
                self._groups_flow_widget
            )
            self._connect_group_signals(gw)
            self._groups_flow_layout.addWidget(gw)
            self._group_widgets.append(gw)

        # 没有分组时隐藏分组流
        has_groups = len(self.config.groups) > 0
        self._groups_flow_widget.setVisible(has_groups)

        # 没有未分组快捷方式时隐藏顶部全部快捷方式区域
        has_all_shortcuts = len(self.config.shortcuts) > 0
        self._all_section.setVisible(has_all_shortcuts)

        # 如果没有未分组快捷方式，顶部边距设为 0（分组直接顶到最上面）
        if has_all_shortcuts:
            self._main_layout.setContentsMargins(16, 16, 16, 16)
        else:
            self._main_layout.setContentsMargins(16, 12, 16, 16)

    def _connect_group_signals(self, gw):
        """连接分组组件的信号"""
        gw.shortcutMoved.connect(self.shortcutMoved.emit)
        gw.shortcutLaunched.connect(self.shortcutLaunched.emit)
        gw.shortcutRenamed.connect(self.shortcutRenamed.emit)
        gw.groupDragStarted.connect(self._on_group_drag_started)
        gw.groupRenamed.connect(self.groupRenamed.emit)
        gw.groupColorChanged.connect(self.groupColorChanged.emit)
        gw.groupDeleted.connect(self.groupDeleted.emit)
        gw.groupWidthChanged.connect(self.groupWidthChanged.emit)

    def _on_shortcut_renamed_all(self, old_path, new_path, new_name):
        """顶层快捷方式重命名"""
        self.shortcutRenamed.emit(ALL_SHORTCUTS_ID, old_path, new_path, new_name)

    def _on_shortcut_move_to_group(self, from_group, from_idx, to_group):
        """右键移动快捷方式到指定分组"""
        self.shortcutMoved.emit(from_group, from_idx, to_group, -1)

    def _on_group_drag_started(self, group_id):
        """分组拖拽开始（预留扩展）"""
        pass

    # ---- 事件过滤器：点击空白处 ----
    def eventFilter(self, obj, event):
        if event.type() == event.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                # 判断是否点在内容区空白处
                if obj is self._content or obj is self.viewport():
                    child = self._content.childAt(event.pos())
                    if child is None or child.objectName() in ("groupsContent", "allShortcutsSection",
                                                               "groupsFlow",
                                                               "allShortcutsFlow"):
                        self.blankClicked.emit()
                        return True
        return super().eventFilter(obj, event)

    # ---- 拖拽：接收快捷方式到"全部快捷方式"区域 ----
    # 由 _all_flow_widget 处理
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-shortcut-item"):
            event.acceptProposedAction()
        elif event.mimeData().hasFormat("application/x-group-item"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-group-item"):
            # 计算分组插入位置
            pos = self._groups_flow_widget.mapFrom(self, event.pos())
            self._drag_drop_indicator = self._calc_group_drop_index(pos)
            event.acceptProposedAction()
            self._groups_flow_widget.update()
        elif event.mimeData().hasFormat("application/x-shortcut-item"):
            # 判断是否在全部快捷方式区域内
            all_pos = self._all_flow_widget.mapFrom(self, event.pos())
            if self._all_flow_widget.rect().contains(all_pos):
                event.acceptProposedAction()
            else:
                event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-group-item"):
            data = bytes(event.mimeData().data("application/x-group-item")).decode("utf-8")
            group_id = data
            # 找到源分组索引
            from_idx = -1
            for i, gw in enumerate(self._group_widgets):
                if gw.group_id == group_id:
                    from_idx = i
                    break
            if from_idx >= 0:
                pos = self._groups_flow_widget.mapFrom(self, event.pos())
                to_idx = self._calc_group_drop_index(pos)
                # 源在目标前则减一
                if from_idx < to_idx:
                    to_idx -= 1
                if from_idx != to_idx:
                    self.groupMoved.emit(from_idx, to_idx)
            self._drag_drop_indicator = -1
            self._groups_flow_widget.update()
            event.acceptProposedAction()
        elif event.mimeData().hasFormat("application/x-shortcut-item"):
            data = bytes(event.mimeData().data("application/x-shortcut-item")).decode("utf-8")
            parts = data.split("|")
            if len(parts) != 2:
                event.ignore()
                return
            from_group = parts[0]
            from_idx = int(parts[1])

            # 先判断是否落在某个分组上（分组自己处理）
            # 如果落在空白区域或全部快捷方式区域，则移入"全部快捷方式"
            child = self._content.childAt(event.pos())
            drop_on_group = False
            gw_item = child
            while gw_item is not None:
                if isinstance(gw_item, GroupWidget):
                    drop_on_group = True
                    break
                gw_item = gw_item.parent()

            if drop_on_group:
                # 交给分组自己处理（event 会被分组的 dropEvent 接收）
                event.ignore()
            else:
                # 落在空白/全部快捷方式区域 → 移出到全部快捷方式
                all_pos = self._all_flow_widget.mapFrom(self, event.pos())
                if self._all_flow_widget.rect().contains(all_pos):
                    to_idx = self._calc_all_drop_index(all_pos)
                    if from_group == ALL_SHORTCUTS_ID and from_idx < to_idx:
                        to_idx -= 1
                else:
                    # 空白区域：追加到末尾
                    to_idx = len(self.config.shortcuts)
                    if from_group == ALL_SHORTCUTS_ID:
                        # 自身移出，索引需减一（追加到末尾的话源索引<末尾，无需调整）
                        pass
                self.shortcutMoved.emit(from_group, from_idx, ALL_SHORTCUTS_ID, to_idx)
                event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._drag_drop_indicator = -1
        self._groups_flow_widget.update()
        super().dragLeaveEvent(event)

    def _calc_group_drop_index(self, pos):
        """根据位置计算分组插入索引（流式布局）"""
        count = len(self._group_widgets)
        if count == 0:
            return 0

        # 获取所有分组的几何信息
        geoms = []
        for gw in self._group_widgets:
            geoms.append(gw.geometry())

        # 按行分组
        rows = []  # [(start_idx, end_idx, top, bottom)]
        current_row_top = None
        current_row_bottom = None
        row_start = 0

        for i in range(count):
            g = geoms[i]
            if current_row_top is None:
                current_row_top = g.top()
                current_row_bottom = g.bottom()
                row_start = i
            elif g.top() > current_row_bottom + 6:
                # 新行
                rows.append((row_start, i - 1, current_row_top, current_row_bottom))
                current_row_top = g.top()
                current_row_bottom = g.bottom()
                row_start = i
            else:
                current_row_bottom = max(current_row_bottom, g.bottom())
        rows.append((row_start, count - 1, current_row_top, current_row_bottom))

        # 找到所在行
        target_row_idx = 0
        for i, (_, _, top, bottom) in enumerate(rows):
            if pos.y() <= (top + bottom) // 2:
                target_row_idx = i
                break
            target_row_idx = i

        row_start, row_end, row_top, row_bottom = rows[target_row_idx]

        # 在行内找插入点
        if pos.y() < row_top:
            return row_start
        for i in range(row_start, row_end + 1):
            g = geoms[i]
            if pos.x() < g.center().x():
                return i
        return row_end + 1

    def _calc_all_drop_index(self, pos):
        """计算在全部快捷方式流中的插入位置"""
        count = self._all_flow_layout.count()
        if count == 0:
            return 0

        rows = []
        current_row_top = None
        current_row_bottom = None
        row_start = 0

        for i in range(count):
            item = self._all_flow_layout.itemAt(i)
            if not item:
                continue
            geom = item.geometry()
            if current_row_top is None:
                current_row_top = geom.top()
                current_row_bottom = geom.bottom()
                row_start = i
            elif geom.top() > current_row_bottom + 2:
                rows.append((row_start, i - 1, current_row_top, current_row_bottom))
                current_row_top = geom.top()
                current_row_bottom = geom.bottom()
                row_start = i
            else:
                current_row_bottom = max(current_row_bottom, geom.bottom())
        rows.append((row_start, count - 1, current_row_top, current_row_bottom))

        target_row_idx = 0
        for i, (_, _, top, bottom) in enumerate(rows):
            if pos.y() <= bottom:
                target_row_idx = i
                break
            target_row_idx = i

        row_start, row_end, row_top, row_bottom = rows[target_row_idx]

        if pos.y() < row_top:
            return row_start
        if pos.y() <= row_bottom:
            for i in range(row_start, row_end + 1):
                item = self._all_flow_layout.itemAt(i)
                if not item:
                    continue
                geom = item.geometry()
                if pos.x() < geom.center().x():
                    return i
            return row_end + 1
        return row_end + 1
