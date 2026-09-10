from PyQt5.QtWidgets import QWidget, QGridLayout, QScrollArea
from PyQt5.QtCore import Qt, pyqtSignal

from .group_widget import GroupWidget
from .config import UNGROUPED_ID


class GroupsContainer(QScrollArea):
    """
    分组容器：多列Z型排列所有分组，支持分组间拖拽排序
    未添加分组固定在第一位，不参与排序
    """

    shortcutMoved = pyqtSignal(str, int, str, int)
    shortcutLaunched = pyqtSignal()
    shortcutRenamed = pyqtSignal(str, str, str, str)  # group_id, old_path, new_path, new_name
    groupMoved = pyqtSignal(int, int)  # from_index, to_index（仅自定义分组之间）
    groupRenamed = pyqtSignal(str, str)
    groupColorChanged = pyqtSignal(str, int)
    groupDeleted = pyqtSignal(str)
    blankClicked = pyqtSignal()  # 空白区域点击

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.group_widgets = []
        self._columns = self.config.columns

        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._container = None

        self.setAcceptDrops(True)
        self._drag_group_id = None

    @property
    def columns(self):
        return self._columns

    def set_columns(self, n):
        """设置列数并重排分组"""
        n = max(1, int(n))
        if n == self._columns:
            return
        self._columns = n
        self.refresh()

    def refresh(self):
        """根据配置刷新所有分组（全量重建 container）"""
        # 旧 container 整体删除（连带里面所有 widget 和 layout）
        old = self._container
        self.group_widgets = []

        # 新建 container 和 layout
        self._container = QWidget()
        self._container.installEventFilter(self)
        layout = QGridLayout(self._container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignTop)
        for c in range(self._columns):
            layout.setColumnStretch(c, 1)

        groups = self._visible_groups()

        for i, g in enumerate(groups):
            row = i // self._columns
            col = i % self._columns
            gw = GroupWidget(
                g["id"], g["name"],
                g.get("color_index", 0),
                g.get("shortcuts", []),
                self.config.icon_size,
                self._container
            )
            gw.shortcutMoved.connect(self.shortcutMoved.emit)
            gw.shortcutLaunched.connect(self.shortcutLaunched.emit)
            gw.shortcutRenamed.connect(self.shortcutRenamed.emit)
            gw.groupDragStarted.connect(self._on_group_drag_started)
            gw.groupRenamed.connect(self.groupRenamed.emit)
            gw.groupColorChanged.connect(self.groupColorChanged.emit)
            gw.groupDeleted.connect(self.groupDeleted.emit)
            layout.addWidget(gw, row, col)
            self.group_widgets.append(gw)

        self.setWidget(self._container)
        # 注意：setWidget 会自动删除旧的 widget，不需要再手动 deleteLater

    def eventFilter(self, obj, event):
        if obj is self._container and event.type() == event.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                # 判断点击位置是否在子控件上，不在则视为空白区域
                child = self._container.childAt(event.pos())
                if child is None:
                    self.blankClicked.emit()
        return super().eventFilter(obj, event)

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
