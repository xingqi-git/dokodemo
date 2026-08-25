from PyQt5.QtWidgets import QWidget, QGridLayout, QScrollArea
from PyQt5.QtCore import Qt, pyqtSignal

from .group_widget import GroupWidget
from .config import UNGROUPED_ID


class GroupsContainer(QScrollArea):
    """
    分组容器：两列Z型排列所有分组，支持分组间拖拽排序
    未添加分组固定在第一位，不参与排序
    """

    shortcutMoved = pyqtSignal(str, int, str, int)
    groupMoved = pyqtSignal(int, int)  # from_index, to_index（仅自定义分组之间）
    groupRenamed = pyqtSignal(str, str)
    groupColorChanged = pyqtSignal(str, int)
    groupDeleted = pyqtSignal(str)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.group_widgets = []

        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._container = QWidget()
        self._layout = QGridLayout(self._container)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(16)
        self._layout.setAlignment(Qt.AlignTop)

        self.setWidget(self._container)

        self.setAcceptDrops(True)
        self._drag_group_id = None

        self.refresh()

    def refresh(self):
        """根据配置刷新所有分组（全量重建）"""
        for gw in self.group_widgets:
            gw.deleteLater()
        self.group_widgets = []

        while self._layout.count():
            self._layout.takeAt(0)

        groups = self._visible_groups()

        for i, g in enumerate(groups):
            row = i // 2
            col = i % 2
            gw = self._create_group_widget(g)
            self._layout.addWidget(gw, row, col)
            self.group_widgets.append(gw)

        self._layout.setColumnStretch(0, 1)
        self._layout.setColumnStretch(1, 1)

    def _create_group_widget(self, group_data):
        """创建单个分组 widget"""
        gw = GroupWidget(
            group_data["id"], group_data["name"],
            group_data.get("color_index", 0),
            group_data.get("shortcuts", []),
            self.config.icon_size,
            self._container
        )
        gw.shortcutMoved.connect(self.shortcutMoved.emit)
        gw.groupDragStarted.connect(self._on_group_drag_started)
        gw.groupRenamed.connect(self.groupRenamed.emit)
        gw.groupColorChanged.connect(self.groupColorChanged.emit)
        gw.groupDeleted.connect(self.groupDeleted.emit)
        return gw

    def update_group_name(self, group_id, new_name):
        """更新分组名称"""
        for gw in self.group_widgets:
            if gw.group_id == group_id:
                gw.update_name(new_name)
                return

    def update_group_color(self, group_id, color_index):
        """更新分组配色"""
        for gw in self.group_widgets:
            if gw.group_id == group_id:
                gw.update_color(color_index)
                return

    def update_icon_size(self, size):
        """更新所有分组的图标大小"""
        for gw in self.group_widgets:
            gw.update_icon_size(size)

    def _on_group_drag_started(self, group_id):
        self._drag_group_id = group_id

    # ---- 分组拖拽 ----
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-group-item"):
            dragged_id = bytes(event.mimeData().data("application/x-group-item")).decode("utf-8")
            if dragged_id == UNGROUPED_ID:
                event.ignore()
                return
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-group-item"):
            dragged_id = bytes(event.mimeData().data("application/x-group-item")).decode("utf-8")
            if dragged_id == UNGROUPED_ID:
                event.ignore()
                return
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-group-item"):
            dragged_id = bytes(event.mimeData().data("application/x-group-item")).decode("utf-8")

            if dragged_id == UNGROUPED_ID:
                event.ignore()
                return

            custom_groups = self._custom_groups()

            from_idx = -1
            for i, g in enumerate(custom_groups):
                if g["id"] == dragged_id:
                    from_idx = i
                    break

            if from_idx < 0:
                event.ignore()
                return

            to_idx = self._calc_custom_group_drop_index(event.pos())
            to_idx = max(0, min(len(custom_groups), to_idx))

            if from_idx != to_idx:
                real_from = self._config_index_of(dragged_id)
                if to_idx < len(custom_groups):
                    real_to = self._config_index_of(custom_groups[to_idx]["id"])
                else:
                    real_to = len(self.config.groups)

                if real_from >= 0 and real_to >= 0:
                    if real_from < real_to:
                        real_to -= 1
                    self.groupMoved.emit(real_from, real_to)

            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def _visible_groups(self):
        """获取可见的分组列表（未分组在前，为空则不显示）"""
        ungrouped = None
        custom = []
        for g in self.config.groups:
            if g["id"] == UNGROUPED_ID:
                if g.get("shortcuts", []):
                    ungrouped = g
            else:
                custom.append(g)

        result = []
        if ungrouped:
            result.append(ungrouped)
        result.extend(custom)
        return result

    def _custom_groups(self):
        """获取所有自定义分组（排除未分组）"""
        return [g for g in self.config.groups if g["id"] != UNGROUPED_ID]

    def _config_index_of(self, group_id):
        for i, g in enumerate(self.config.groups):
            if g["id"] == group_id:
                return i
        return -1

    def _calc_custom_group_drop_index(self, pos):
        """
        根据鼠标位置计算自定义分组的插入索引
        （未分组占的位置跳过，不允许插到未分组前面）
        """
        visible = self._visible_groups()
        if not visible:
            return 0

        container_pos = self._container.mapFrom(self, pos)

        for i, gw in enumerate(self.group_widgets):
            geom = gw.geometry()
            if geom.top() <= container_pos.y() <= geom.bottom():
                mid_y = geom.top() + geom.height() / 2
                vis_idx = i if container_pos.y() < mid_y else i + 1

                has_ungrouped = visible and visible[0]["id"] == UNGROUPED_ID
                custom_idx = vis_idx - 1 if has_ungrouped else vis_idx

                return max(0, custom_idx)

        custom_count = len([g for g in visible if g["id"] != UNGROUPED_ID])
        return custom_count
