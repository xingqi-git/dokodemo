import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QInputDialog, QMessageBox, QSlider, QApplication
)
from PyQt5.QtCore import Qt, QPoint, QTimer

from .config import ConfigManager, UNGROUPED_ID
from .shortcut import scan_shortcuts, clear_icon_cache
from .groups_container import GroupsContainer
from .styles import GLOBAL_QSS


class MainWindow(QWidget):
    """主窗口：无边框、自定义标题栏、工具栏、分组区域"""

    def __init__(self, config_path):
        super().__init__()
        self.config = ConfigManager(config_path)

        # 无边框，同时保留最小化/最大化系统菜单（让任务栏图标能正常最小化）
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Window
            | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # 窗口拖动
        self._drag_pos = None
        self._is_maximized = False

        self._init_ui()
        self._connect_signals()
        self.setStyleSheet(GLOBAL_QSS)

        # 启动时最大化
        self.showMaximized()
        self._is_maximized = True

        # 启动时立即加载分组内容
        if self.config.shortcut_dir:
            self.groups_container.refresh()

    def _init_ui(self):
        # 主布局（带圆角的外层容器）
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 主widget
        self.main_widget = QWidget(self)
        self.main_widget.setObjectName("mainWidget")
        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 标题栏
        self.title_bar = QWidget(self.main_widget)
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(36)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        self.title_label = QLabel("dokodemo", self.title_bar)
        self.title_label.setObjectName("titleLabel")
        title_layout.addWidget(self.title_label)

        title_layout.addStretch()

        # 最小化按钮
        self.min_btn = QPushButton("—", self.title_bar)
        self.min_btn.setObjectName("titleBtn")
        self.min_btn.setCursor(Qt.PointingHandCursor)
        title_layout.addWidget(self.min_btn)

        # 最大化/还原按钮
        self.max_btn = QPushButton("□", self.title_bar)
        self.max_btn.setObjectName("titleBtn")
        self.max_btn.setCursor(Qt.PointingHandCursor)
        title_layout.addWidget(self.max_btn)

        # 关闭按钮
        self.close_btn = QPushButton("✕", self.title_bar)
        self.close_btn.setObjectName("titleBtn")
        self.close_btn.setProperty("class", "close")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        # 单独设置关闭按钮hover样式
        self.close_btn.setStyleSheet("""
            QPushButton#titleBtn {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 14px;
                width: 40px;
                height: 36px;
            }
            QPushButton#titleBtn:hover {
                background-color: #E74C3C;
            }
        """)
        title_layout.addWidget(self.close_btn)

        main_layout.addWidget(self.title_bar)

        # 工具栏
        self.tool_bar = QWidget(self.main_widget)
        self.tool_bar.setObjectName("toolBar")
        self.tool_bar.setFixedHeight(40)
        tool_layout = QHBoxLayout(self.tool_bar)
        tool_layout.setContentsMargins(16, 4, 16, 4)
        tool_layout.setSpacing(8)

        # 选择目录按钮
        self.dir_btn = QPushButton("选择目录", self.tool_bar)
        self.dir_btn.setObjectName("toolBtnSecondary")
        self.dir_btn.setCursor(Qt.PointingHandCursor)
        tool_layout.addWidget(self.dir_btn)

        # 当前目录显示
        self.dir_label = QLabel("未设置快捷方式目录", self.tool_bar)
        self.dir_label.setStyleSheet("color: #666; font-size: 12px;")
        self.dir_label.setMinimumWidth(180)
        tool_layout.addWidget(self.dir_label)

        tool_layout.addSpacing(12)

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新", self.tool_bar)
        self.refresh_btn.setObjectName("toolBtn")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        tool_layout.addWidget(self.refresh_btn)

        # 添加分组按钮
        self.add_group_btn = QPushButton("添加分组", self.tool_bar)
        self.add_group_btn.setObjectName("toolBtn")
        self.add_group_btn.setCursor(Qt.PointingHandCursor)
        tool_layout.addWidget(self.add_group_btn)

        tool_layout.addStretch()

        # 图标大小调节
        size_label = QLabel("图标大小:", self.tool_bar)
        size_label.setObjectName("sliderLabel")
        tool_layout.addWidget(size_label)

        self.size_slider = QSlider(Qt.Horizontal, self.tool_bar)
        self.size_slider.setMinimum(32)
        self.size_slider.setMaximum(128)
        self.size_slider.setValue(self.config.icon_size)
        self.size_slider.setFixedWidth(120)
        self.size_slider.setCursor(Qt.PointingHandCursor)
        tool_layout.addWidget(self.size_slider)

        self.size_value_label = QLabel(f"{self.config.icon_size}px", self.tool_bar)
        self.size_value_label.setObjectName("sliderLabel")
        self.size_value_label.setFixedWidth(36)
        tool_layout.addWidget(self.size_value_label)

        tool_layout.addSpacing(12)

        # 列数调节
        col_label = QLabel("列数:", self.tool_bar)
        col_label.setObjectName("sliderLabel")
        tool_layout.addWidget(col_label)

        self.col_slider = QSlider(Qt.Horizontal, self.tool_bar)
        self.col_slider.setMinimum(1)
        self.col_slider.setMaximum(5)
        self.col_slider.setValue(self.config.columns)
        self.col_slider.setFixedWidth(80)
        self.col_slider.setCursor(Qt.PointingHandCursor)
        self.col_slider.setPageStep(1)  # 点击轨道时 +1 / -1，而不是跳一大段
        tool_layout.addWidget(self.col_slider)

        self.col_value_label = QLabel(f"{self.config.columns}", self.tool_bar)
        self.col_value_label.setObjectName("sliderLabel")
        self.col_value_label.setFixedWidth(20)
        tool_layout.addWidget(self.col_value_label)

        main_layout.addWidget(self.tool_bar)

        # 分组容器
        self.groups_container = GroupsContainer(self.config, self.main_widget)
        main_layout.addWidget(self.groups_container)

        outer_layout.addWidget(self.main_widget)

        # 更新目录显示
        self._update_dir_label()

    def _connect_signals(self):
        # 标题栏按钮
        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self._toggle_maximize)
        self.close_btn.clicked.connect(self.close)

        # 工具栏按钮
        self.dir_btn.clicked.connect(self._choose_directory)
        self.refresh_btn.clicked.connect(self._refresh_shortcuts)
        self.add_group_btn.clicked.connect(self._add_group)

        # 图标大小滑块
        self.size_slider.valueChanged.connect(self._on_icon_size_changed)
        self.size_slider.sliderReleased.connect(self._on_icon_size_released)

        # 列数滑块
        self.col_slider.valueChanged.connect(self._on_columns_changed)
        self.col_slider.sliderReleased.connect(self._on_columns_released)

        # 分组容器信号
        self.groups_container.shortcutMoved.connect(self._on_shortcut_moved)
        self.groups_container.groupMoved.connect(self._on_group_moved)
        self.groups_container.groupRenamed.connect(self._on_group_renamed)
        self.groups_container.groupColorChanged.connect(self._on_group_color_changed)
        self.groups_container.groupDeleted.connect(self._on_group_deleted)

    # ---- 标题栏拖动 ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 检查是否在标题栏区域
            if self.title_bar.geometry().contains(event.pos()):
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_pos:
            if self._is_maximized:
                # 拖动时还原窗口
                self._toggle_maximize()
                # 调整拖动位置
                self._drag_pos = QPoint(int(event.globalPos().x() - self.width() / 2),
                                        int(event.globalPos().y() - 10))
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.title_bar.geometry().contains(event.pos()):
            self._toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _toggle_maximize(self):
        if self._is_maximized:
            self.showNormal()
            # 计算还原尺寸：宽度 1/2 屏幕，高度 2/3 屏幕，居中显示
            screen = QApplication.primaryScreen().availableGeometry()
            width = screen.width() // 2
            height = screen.height() * 2 // 3
            x = screen.x() + (screen.width() - width) // 2
            y = screen.y() + (screen.height() - height) // 2
            self.setGeometry(x, y, width, height)
            self.max_btn.setText("□")
            self._is_maximized = False
        else:
            self.showMaximized()
            self.max_btn.setText("❐")
            self._is_maximized = True

    # ---- 目录管理 ----
    def _choose_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "选择快捷方式目录",
            self.config.shortcut_dir or ""
        )
        if directory:
            self.config.shortcut_dir = directory
            self._update_dir_label()
            self._refresh_shortcuts()

    def _update_dir_label(self):
        if self.config.shortcut_dir:
            self.dir_label.setText(f"当前目录: {self.config.shortcut_dir}")
            self.dir_label.setToolTip(self.config.shortcut_dir)
        else:
            self.dir_label.setText("未设置快捷方式目录")
            self.dir_label.setToolTip("")

    def _refresh_shortcuts(self):
        """刷新快捷方式列表"""
        if not self.config.shortcut_dir:
            QMessageBox.information(self, "提示", "请先选择快捷方式目录")
            return

        shortcuts = scan_shortcuts(self.config.shortcut_dir)
        added, removed = self.config.sync_shortcuts(shortcuts)

        # 清空图标缓存
        clear_icon_cache()

        # 刷新界面
        self.groups_container.refresh()

        if added > 0 or removed > 0:
            QMessageBox.information(
                self, "刷新完成",
                f"新增 {added} 个快捷方式，移除 {removed} 个快捷方式"
            )

    # ---- 分组管理 ----
    def _add_group(self):
        name, ok = QInputDialog.getText(
            self, "添加分组", "请输入分组名称:"
        )
        if ok and name.strip():
            self.config.add_group(name.strip())
            self.groups_container.refresh()

    def _on_shortcut_moved(self, from_group, from_idx, to_group, to_idx):
        # 更新数据
        self.config.move_shortcut(from_group, from_idx, to_group, to_idx)
        # 延迟刷新，确保拖拽完全结束后再重建 widget，避免崩溃
        QTimer.singleShot(50, self.groups_container.refresh)

    def _on_group_moved(self, from_idx, to_idx):
        self.config.move_group(from_idx, to_idx)
        QTimer.singleShot(200, self.groups_container.refresh)

    def _on_group_renamed(self, group_id, new_name):
        self.config.rename_group(group_id, new_name)
        self.groups_container.refresh()

    def _on_group_color_changed(self, group_id, color_index):
        self.config.set_group_color(group_id, color_index)
        self.groups_container.refresh()

    def _on_group_deleted(self, group_id):
        self.config.remove_group(group_id)
        self.groups_container.refresh()

    # ---- 图标大小 ----
    def _on_icon_size_changed(self, value):
        self.size_value_label.setText(f"{value}px")
        self.groups_container.update_icon_size(value)

    def _on_icon_size_released(self):
        value = self.size_slider.value()
        self.config.icon_size = value
        clear_icon_cache()
        self.groups_container.refresh()

    def _on_columns_changed(self, value):
        self.col_value_label.setText(str(value))
        # 鼠标拖动时不刷新（松开再刷），键盘/点击操作立即刷新
        if not self.col_slider.isSliderDown():
            self.config.columns = value
            self.groups_container.set_columns(value)

    def _on_columns_released(self):
        value = self.col_slider.value()
        self.config.columns = value
        self.groups_container.set_columns(value)
