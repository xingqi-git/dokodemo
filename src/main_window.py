import os
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QAction,
    QFileDialog, QInputDialog, QMessageBox, QApplication, QSizePolicy
)
from PyQt5.QtCore import Qt, QPoint, QTimer, QRect, QRectF, QSize
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QBrush, QPen, QFontMetrics, QIcon

from .config import (
    ConfigManager, DOCK_MODE_FLOAT, DOCK_MODE_FULLSCREEN, DOCK_MODE_CENTER,
    DOCK_MODE_LEFT, DOCK_MODE_RIGHT, DOCK_MODE_BOTTOM_LEFT
)
from .shortcut import scan_shortcuts, clear_icon_cache
from .groups_container import GroupsContainer
from .styles import GLOBAL_QSS


def _make_icon_pixmap(draw_fn, size=16, color="#333", pen_width=1.2):
    """用 QPainter 绘制图标，确保大小和线条粗细统一"""
    from PyQt5.QtGui import QPixmap
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(pen_width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    draw_fn(painter, size)
    painter.end()
    return pixmap


def _refresh_icon(size=16, color="#333", pen_width=1.2):
    """绘制刷新图标（缺口朝右，上端箭头沿顺时针方向）"""
    def draw(painter, s):
        import math
        from PyQt5.QtGui import QPolygonF
        from PyQt5.QtCore import QPointF

        cx, cy = s / 2, s / 2
        r = s / 2 - 2  # 半径

        # 圆弧：缺口朝右，60° 缺口
        # 起点在右下（-30°），顺时针扫过 300°，终点在右上（30°）
        # 经过下方、左方、上方
        start_angle = -30   # 起始角度（Qt 坐标：0°=右，90°=顶）
        span_angle = -300   # 负 = 顺时针

        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        painter.drawArc(rect, int(start_angle * 16), int(span_angle * 16))

        # 上端箭头：在圆弧终点（30°，右上）
        # 三角形底边沿径向，尖端沿顺时针切线方向
        # 圆弧端点 = 底边中点，径向线平分三角形
        arrow_angle = 30  # 上端点角度
        arrow_angle_rad = math.radians(arrow_angle)

        # 底边中点 = 圆弧端点
        base_mid_x = cx + r * math.cos(arrow_angle_rad)
        base_mid_y = cy - r * math.sin(arrow_angle_rad)

        arrow_len = 4.2         # 箭头长度（从底边中点到尖端的距离）
        arrow_half_width = 2.6  # 底边半宽

        # 尖端：从底边中点沿顺时针切线方向前进 arrow_len
        forward_angle = math.radians(arrow_angle - 90)
        tip_x = base_mid_x + arrow_len * math.cos(forward_angle)
        tip_y = base_mid_y - arrow_len * math.sin(forward_angle)

        # 底边两端：从底边中点沿径向方向 ± half_width
        radial_angle = math.radians(arrow_angle)
        base_outer_x = base_mid_x + arrow_half_width * math.cos(radial_angle)
        base_outer_y = base_mid_y - arrow_half_width * math.sin(radial_angle)
        base_inner_x = base_mid_x - arrow_half_width * math.cos(radial_angle)
        base_inner_y = base_mid_y + arrow_half_width * math.sin(radial_angle)

        arrow = QPolygonF()
        arrow.append(QPointF(tip_x, tip_y))
        arrow.append(QPointF(base_outer_x, base_outer_y))
        arrow.append(QPointF(base_inner_x, base_inner_y))
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(arrow)
        # 恢复画笔
        pen = painter.pen()
        pen.setWidthF(pen_width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

    return _make_icon_pixmap(draw, size, color, pen_width)


def _settings_icon(size=16, color="#333", pen_width=1.2):
    """绘制齿轮设置图标（线条风格）"""
    def draw(painter, s):
        import math
        cx, cy = s / 2, s / 2
        outer_r = s / 2 - 1.5
        inner_r = outer_r * 0.65
        hole_r = outer_r * 0.3
        teeth = 8

        # 齿轮外轮廓（8 齿）—— 线条风格
        from PyQt5.QtGui import QPolygonF
        from PyQt5.QtCore import QPointF
        points = QPolygonF()
        for i in range(teeth * 2):
            angle = i * math.pi / teeth - math.pi / 2
            r = outer_r if i % 2 == 0 else inner_r
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append(QPointF(x, y))

        pen = painter.pen()
        pen.setJoinStyle(Qt.MiterJoin)
        painter.setPen(pen)
        painter.drawPolygon(points)

        # 中心圆孔
        painter.drawEllipse(QPointF(cx, cy), hole_r, hole_r)
    return _make_icon_pixmap(draw, size, color, pen_width)


# Windows 消息/命中测试常量
_WM_NCHITTEST = 0x0084
_HTCLIENT = 1
_HTCAPTION = 2
_HTLEFT = 10
_HTRIGHT = 11
_HTTOP = 12
_HTTOPLEFT = 13
_HTTOPRIGHT = 14
_HTBOTTOM = 15
_HTBOTTOMLEFT = 16
_HTBOTTOMRIGHT = 17

_IS_WINDOWS = os.name == "nt"


class MainWindow(QWidget):
    """主窗口：无边框、自定义标题栏、工具栏、磁贴式分组"""

    def __init__(self, config_path):
        super().__init__()
        self.config = ConfigManager(config_path)

        # 无边框，保留最小化系统菜单（让任务栏图标能正常最小化）
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Window
            | Qt.WindowMinimizeButtonHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 窗口拖动
        self._drag_pos = None
        self._is_maximized = False

        # 窗口缩放
        self._resize_margin = 8  # 边缘可缩放区域宽度
        self._resize_edge = None  # 当前正在缩放的边
        self._resize_start_geom = None
        self._resize_start_pos = None

        # 窗口圆角半径
        self._corner_radius = 12

        # 标记：是否正在由程序主动设置窗口几何（避免 resizeEvent/moveEvent 误判为用户手动调整）
        self._setting_geometry = False

        # 目录完整路径（用于省略文本计算）
        self._dir_full_path = ""

        # 各边/角枚举
        self._EDGE_NONE = 0
        self._EDGE_LEFT = 1
        self._EDGE_RIGHT = 2
        self._EDGE_TOP = 4
        self._EDGE_BOTTOM = 8
        self._EDGE_TOPLEFT = self._EDGE_TOP | self._EDGE_LEFT
        self._EDGE_TOPRIGHT = self._EDGE_TOP | self._EDGE_RIGHT
        self._EDGE_BOTTOMLEFT = self._EDGE_BOTTOM | self._EDGE_LEFT
        self._EDGE_BOTTOMRIGHT = self._EDGE_BOTTOM | self._EDGE_RIGHT

        self._init_ui()
        self._connect_signals()
        self.setStyleSheet(GLOBAL_QSS)

        # 启动时立即加载分组内容
        if self.config.shortcut_dir:
            self.groups_container.refresh()

    def _init_ui(self):
        # 主布局
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 主widget
        self.main_widget = QWidget(self)
        self.main_widget.setObjectName("mainWidget")
        main_layout = QVBoxLayout(self.main_widget)
        # 底部留出圆角半径的空间，让底部圆角露出来
        main_layout.setContentsMargins(0, 0, 0, self._corner_radius)
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

        # 目录显示（占满标题和按钮之间的所有空间）
        self.dir_label = QLabel("未设置目录", self.title_bar)
        self.dir_label.setObjectName("dirLabel")
        self.dir_label.setStyleSheet("color: #666; font-size: 12px; padding-left: 8px;")
        self.dir_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        title_layout.addWidget(self.dir_label, 1)

        # 刷新按钮
        self.refresh_btn = QPushButton("", self.title_bar)
        self.refresh_btn.setObjectName("titleIconBtn")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setToolTip("刷新")
        self.refresh_btn.setIcon(QIcon(_refresh_icon()))
        self.refresh_btn.setIconSize(QSize(16, 16))
        title_layout.addWidget(self.refresh_btn)

        # 设置按钮（齿轮图标 + 下拉菜单）
        self.settings_btn = QPushButton("", self.title_bar)
        self.settings_btn.setObjectName("titleIconBtn")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setToolTip("设置")
        self.settings_btn.setIcon(QIcon(_settings_icon()))
        self.settings_btn.setIconSize(QSize(16, 16))
        title_layout.addWidget(self.settings_btn)

        # 最小化按钮
        self.min_btn = QPushButton("—", self.title_bar)
        self.min_btn.setObjectName("titleBtn")
        self.min_btn.setCursor(Qt.PointingHandCursor)
        title_layout.addWidget(self.min_btn)

        # 关闭按钮
        self.close_btn = QPushButton("✕", self.title_bar)
        self.close_btn.setObjectName("titleBtn")
        self.close_btn.setProperty("class", "close")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        # 关闭按钮 hover 颜色由全局 QSS 的 [class="close"] 控制
        title_layout.addWidget(self.close_btn)

        main_layout.addWidget(self.title_bar)

        # 分组容器
        self.groups_container = GroupsContainer(self.config, self.main_widget)
        main_layout.addWidget(self.groups_container)

        # 设置下拉菜单
        self.settings_menu = QMenu(self)
        self.settings_menu.addAction("设置目录…", self._choose_directory)
        self.settings_menu.addAction("添加分组", self._add_group)
        self.settings_menu.addSeparator()

        # 停靠方式子菜单
        self.dock_menu = QMenu("停靠方式", self)
        self._dock_action_group = None  # 后面在 _init_dock_menu 中创建
        self._build_dock_menu()
        self.settings_menu.addMenu(self.dock_menu)
        self.settings_menu.addSeparator()
        self.settings_menu.addAction("使用说明", self._show_help)
        self.settings_btn.clicked.connect(self._show_settings_menu)

        outer_layout.addWidget(self.main_widget)

        # 更新目录显示
        self._update_dir_label()

    def _connect_signals(self):
        # 标题栏按钮
        self.min_btn.clicked.connect(self.showMinimized)
        self.close_btn.clicked.connect(self.close)

        # 标题栏功能按钮
        self.refresh_btn.clicked.connect(self._refresh_shortcuts)

        # 分组容器信号
        self.groups_container.shortcutMoved.connect(self._on_shortcut_moved)
        self.groups_container.groupMoved.connect(self._on_group_moved)
        self.groups_container.groupRenamed.connect(self._on_group_renamed)
        self.groups_container.groupColorChanged.connect(self._on_group_color_changed)
        self.groups_container.groupDeleted.connect(self._on_group_deleted)
        self.groups_container.groupWidthChanged.connect(self._on_group_width_changed)
        self.groups_container.groupIconSizeChanged.connect(self._on_group_icon_size_changed)
        self.groups_container.groupShowNameChanged.connect(self._on_group_show_name_changed)
        self.groups_container.shortcutRenamed.connect(self._on_shortcut_renamed)

    # ---- 标题栏拖动 & 边缘缩放 ----
    def _hit_test_edge(self, pos):
        """判断鼠标位置落在窗口的哪条边/角上，返回边标志位组合"""
        if self._is_maximized:
            return self._EDGE_NONE
        w, h = self.width(), self.height()
        m = self._resize_margin
        x, y = pos.x(), pos.y()
        edge = self._EDGE_NONE
        if x <= m:
            edge |= self._EDGE_LEFT
        elif x >= w - m:
            edge |= self._EDGE_RIGHT
        if y <= m:
            edge |= self._EDGE_TOP
        elif y >= h - m:
            edge |= self._EDGE_BOTTOM
        return edge

    def _cursor_for_edge(self, edge):
        """根据边标志返回对应鼠标光标"""
        if edge == self._EDGE_NONE:
            return Qt.ArrowCursor
        if edge in (self._EDGE_LEFT, self._EDGE_RIGHT):
            return Qt.SizeHorCursor
        if edge in (self._EDGE_TOP, self._EDGE_BOTTOM):
            return Qt.SizeVerCursor
        if edge in (self._EDGE_TOPLEFT, self._EDGE_BOTTOMRIGHT):
            return Qt.SizeFDiagCursor
        if edge in (self._EDGE_TOPRIGHT, self._EDGE_BOTTOMLEFT):
            return Qt.SizeBDiagCursor
        return Qt.ArrowCursor

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 先检查是否在边缘缩放区
            edge = self._hit_test_edge(event.pos())
            if edge != self._EDGE_NONE:
                self._resize_edge = edge
                self._resize_start_geom = self.geometry()
                self._resize_start_pos = event.globalPos()
                event.accept()
                return
            # 检查是否在标题栏区域
            if self.title_bar.geometry().contains(event.pos()):
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 正在缩放
        if event.buttons() & Qt.LeftButton and self._resize_edge is not None:
            edge = self._resize_edge
            g = QRect(self._resize_start_geom)
            delta = event.globalPos() - self._resize_start_pos
            dx, dy = delta.x(), delta.y()
            min_w, min_h = 400, 300

            if edge & self._EDGE_LEFT:
                new_x = g.x() + dx
                new_w = g.width() - dx
                if new_w >= min_w:
                    g.setX(new_x)
                    g.setWidth(new_w)
                else:
                    g.setWidth(min_w)
            elif edge & self._EDGE_RIGHT:
                g.setWidth(max(min_w, g.width() + dx))

            if edge & self._EDGE_TOP:
                new_y = g.y() + dy
                new_h = g.height() - dy
                if new_h >= min_h:
                    g.setY(new_y)
                    g.setHeight(new_h)
                else:
                    g.setHeight(min_h)
            elif edge & self._EDGE_BOTTOM:
                g.setHeight(max(min_h, g.height() + dy))

            self.setGeometry(g)
            event.accept()
            return

        # 正在拖动（全屏/最大化状态下不允许拖动）
        if event.buttons() & Qt.LeftButton and self._drag_pos and not self._is_maximized:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return

        # 未按下时，根据鼠标位置更新光标形状
        if not (event.buttons() & Qt.LeftButton):
            edge = self._hit_test_edge(event.pos())
            self.setCursor(self._cursor_for_edge(edge))

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_resizing = self._resize_edge is not None
        was_dragging = self._drag_pos is not None
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start_geom = None
        self._resize_start_pos = None
        self.setCursor(Qt.ArrowCursor)
        # 手动调整大小或位置后，切回浮动模式
        if was_resizing or was_dragging:
            if self.config.dock_mode != DOCK_MODE_FLOAT:
                self.config.dock_mode = DOCK_MODE_FLOAT
                # 更新菜单选中状态
                if self._dock_action_group:
                    for act in self._dock_action_group.actions():
                        if act.data() == DOCK_MODE_FLOAT:
                            act.setChecked(True)
                            break
            self._save_float_geometry()
        super().mouseReleaseEvent(event)

    # ---- Windows 原生消息处理：边缘缩放 + 标题栏拖动 ----
    def _is_in_title_bar_drag_area(self, pos):
        """判断点是否在标题栏可拖动区域（排除右侧按钮区）"""
        if not self.title_bar.geometry().contains(pos):
            return False
        # 标题栏右侧按钮区：刷新 + 设置 + 最小化 + 关闭（每个 46px）
        title_bar_rect = self.title_bar.geometry()
        btn_area_left = title_bar_rect.right() - 184
        return pos.x() < btn_area_left

    def nativeEvent(self, eventType, message):
        if not _IS_WINDOWS or self._is_maximized:
            return super().nativeEvent(eventType, message)

        msg = wintypes.MSG.from_address(int(message))
        if msg.message != _WM_NCHITTEST:
            return super().nativeEvent(eventType, message)

        # 把屏幕坐标转换为窗口客户区坐标
        x = ctypes.c_short(msg.lParam & 0xFFFF).value
        y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
        pos = self.mapFromGlobal(QPoint(x, y))

        w, h = self.width(), self.height()
        m = self._resize_margin
        px, py = pos.x(), pos.y()

        # 命中测试：先判断四个角，再判断四条边
        result = _HTCLIENT
        left = px <= m
        right = px >= w - m
        top = py <= m
        bottom = py >= h - m

        if top and left:
            result = _HTTOPLEFT
        elif top and right:
            result = _HTTOPRIGHT
        elif bottom and left:
            result = _HTBOTTOMLEFT
        elif bottom and right:
            result = _HTBOTTOMRIGHT
        elif top:
            result = _HTTOP
        elif bottom:
            result = _HTBOTTOM
        elif left:
            result = _HTLEFT
        elif right:
            result = _HTRIGHT

        if result != _HTCLIENT:
            return True, result

        return super().nativeEvent(eventType, message)

    def showEvent(self, event):
        super().showEvent(event)
        # 首次显示后重新计算目录省略文本（此时布局已完成）
        self._update_dir_elided_text()
        # 首次显示时应用停靠模式
        if not event.spontaneous():
            self._apply_dock_mode()

    def closeEvent(self, event):
        """关闭时保存自由浮动时的窗口几何"""
        self._save_float_geometry()
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 窗口大小变化时重新计算目录文本的省略
        self._update_dir_elided_text()
        # 用户手动调整大小/位置 → 切回浮动模式
        self._check_user_manual_adjust()

    def moveEvent(self, event):
        super().moveEvent(event)
        # 用户手动调整大小/位置 → 切回浮动模式
        self._check_user_manual_adjust()

    def _check_user_manual_adjust(self):
        """检测是否为用户手动调整，是则切回浮动模式"""
        if self._setting_geometry:
            return
        if self._is_maximized:
            return
        if self.config.dock_mode == DOCK_MODE_FLOAT:
            return
        # 切回浮动模式
        self.config.dock_mode = DOCK_MODE_FLOAT
        self._save_float_geometry()
        # 更新菜单选中状态
        if self._dock_action_group:
            for act in self._dock_action_group.actions():
                if act.data() == DOCK_MODE_FLOAT:
                    act.setChecked(True)
                    break

    def paintEvent(self, event):
        """绘制圆角背景（最大化时无圆角，填满整个窗口）"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        if self._is_maximized:
            # 最大化：填满窗口，无圆角
            painter.fillRect(self.rect(), QColor("#F3F3F3"))
            return

        # 普通状态：圆角矩形背景
        radius = self._corner_radius
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.fillPath(path, QColor("#F3F3F3"))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    # ---- 停靠模式 ----
    def _build_dock_menu(self):
        """构建停靠方式子菜单"""
        from PyQt5.QtWidgets import QActionGroup

        self._dock_action_group = QActionGroup(self.dock_menu)
        self._dock_action_group.setExclusive(True)

        modes = [
            ("自由", DOCK_MODE_FLOAT),
            ("全屏", DOCK_MODE_FULLSCREEN),
            ("居中", DOCK_MODE_CENTER),
            ("靠左", DOCK_MODE_LEFT),
            ("靠右", DOCK_MODE_RIGHT),
            ("左下", DOCK_MODE_BOTTOM_LEFT),
        ]
        current = self.config.dock_mode
        for text, mode in modes:
            act = QAction(text, self.dock_menu, checkable=True)
            act.setData(mode)
            act.triggered.connect(lambda checked, m=mode: self._set_dock_mode(m))
            if mode == current:
                act.setChecked(True)
            self._dock_action_group.addAction(act)
            self.dock_menu.addAction(act)

    def _set_dock_mode(self, mode):
        """设置停靠模式并应用"""
        self.config.dock_mode = mode
        # 选择"自由"时，初始化为居中大小（2/3 屏宽、2/3 屏高、居中）
        if mode == DOCK_MODE_FLOAT:
            screen = QApplication.primaryScreen().availableGeometry()
            w = screen.width() * 2 // 3
            h = screen.height() * 2 // 3
            x = screen.x() + (screen.width() - w) // 2
            y = screen.y() + (screen.height() - h) // 2
            self.config.window_geometry = [x, y, w, h]
        self._apply_dock_mode()

    def _apply_dock_mode(self):
        """根据当前 dock_mode 应用窗口位置和大小"""
        self._setting_geometry = True
        try:
            self._do_apply_dock_mode()
        finally:
            self._setting_geometry = False

    def _do_apply_dock_mode(self):
        mode = self.config.dock_mode
        screen = QApplication.primaryScreen().availableGeometry()

        if mode == DOCK_MODE_FULLSCREEN:
            self._is_maximized = True
            self._update_maximized_state()
            self.showMaximized()

        elif mode == DOCK_MODE_CENTER:
            self._is_maximized = False
            self._update_maximized_state()
            w = screen.width() * 2 // 3
            h = screen.height() * 2 // 3
            x = screen.x() + (screen.width() - w) // 2
            y = screen.y() + (screen.height() - h) // 2
            self.showNormal()
            self.setGeometry(x, y, w, h)

        elif mode == DOCK_MODE_LEFT:
            self._is_maximized = False
            self._update_maximized_state()
            w = screen.width() // 3
            h = screen.height()
            x = screen.x()
            y = screen.y()
            self.showNormal()
            self.setGeometry(x, y, w, h)

        elif mode == DOCK_MODE_RIGHT:
            self._is_maximized = False
            self._update_maximized_state()
            w = screen.width() // 3
            h = screen.height()
            x = screen.x() + screen.width() - w
            y = screen.y()
            self.showNormal()
            self.setGeometry(x, y, w, h)

        elif mode == DOCK_MODE_BOTTOM_LEFT:
            self._is_maximized = False
            self._update_maximized_state()
            w = screen.width() // 3
            h = screen.height() * 2 // 3
            x = screen.x()
            y = screen.y() + screen.height() - h
            self.showNormal()
            self.setGeometry(x, y, w, h)

        else:  # DOCK_MODE_FLOAT
            # 按上次保存的几何信息显示
            self._is_maximized = False
            self._update_maximized_state()
            self.showNormal()
            geom = self.config.window_geometry
            if geom and len(geom) == 4:
                x, y, w, h = geom
                # 确保不超屏幕
                screen = QApplication.primaryScreen().availableGeometry()
                w = max(400, min(w, screen.width()))
                h = max(300, min(h, screen.height()))
                x = max(screen.x(), min(x, screen.x() + screen.width() - w))
                y = max(screen.y(), min(y, screen.y() + screen.height() - h))
                self.setGeometry(x, y, w, h)
            else:
                # 默认：宽度 1/2 屏幕，高度 2/3 屏幕，居中
                w = screen.width() // 2
                h = screen.height() * 2 // 3
                x = screen.x() + (screen.width() - w) // 2
                y = screen.y() + (screen.height() - h) // 2
                self.setGeometry(x, y, w, h)

    def _save_float_geometry(self):
        """保存自由浮动时的窗口几何位置"""
        if self.config.dock_mode == DOCK_MODE_FLOAT and not self._is_maximized:
            g = self.geometry()
            self.config.window_geometry = [g.x(), g.y(), g.width(), g.height()]

    def _show_settings_menu(self):
        """显示设置下拉菜单"""
        # 菜单显示在设置按钮的下方
        pos = self.settings_btn.mapToGlobal(self.settings_btn.rect().bottomLeft())
        self.settings_menu.exec_(pos)

    def _update_maximized_state(self):
        """根据最大化状态更新标题栏圆角、内容边距等"""
        if self._is_maximized:
            self.title_bar.setStyleSheet(
                "QWidget#titleBar { background-color: #F3F3F3; border-top-left-radius: 0px; border-top-right-radius: 0px; }"
            )
            # 最大化时底部不留圆角边距
            self.main_widget.layout().setContentsMargins(0, 0, 0, 0)
        else:
            self.title_bar.setStyleSheet(
                "QWidget#titleBar { background-color: #F3F3F3; border-top-left-radius: 12px; border-top-right-radius: 12px; }"
            )
            # 普通状态底部留圆角半径的空间
            self.main_widget.layout().setContentsMargins(0, 0, 0, self._corner_radius)
        self.update()

    # ---- 使用说明 ----
    def _show_help(self):
        text = (
            "使用说明\n\n"
            "1. 在电脑上创建一个文件夹，把常用的快捷方式放进去\n"
            "2. 点右上角 ⚙ →「设置目录」，选择这个文件夹\n"
            "3. 图标会显示在顶部，拖拽可以调整顺序\n"
            "4. 可创建分组，把图标拖进分组分类管理\n"
            "5. 点击图标启动程序，窗口自动最小化"
        )
        QMessageBox.information(self, "使用说明", text)

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
            self._dir_full_path = self.config.shortcut_dir
            self.dir_label.setToolTip(self.config.shortcut_dir)
            self._update_dir_elided_text()
        else:
            self._dir_full_path = ""
            self.dir_label.setText("")
            self.dir_label.setToolTip("")

    def _update_dir_elided_text(self):
        """根据当前可用宽度计算省略后的目录文本"""
        if not self._dir_full_path:
            return
        available_width = self.dir_label.width()
        if available_width <= 0:
            return
        font = self.dir_label.font()
        fm = QFontMetrics(font)
        elided = fm.elidedText(self._dir_full_path, Qt.ElideMiddle, available_width)
        self.dir_label.setText(elided)

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

    def _on_shortcut_renamed(self, group_id, old_path, new_path, new_name):
        """快捷方式文件重命名后，更新配置中的 path 和 name"""
        renamed = False
        # 顶层快捷方式
        for sc in self.config.shortcuts:
            if sc["path"] == old_path:
                sc["path"] = new_path
                sc["name"] = new_name
                renamed = True
        # 分组内快捷方式
        if not renamed:
            for g in self.config.groups:
                for sc in g.get("shortcuts", []):
                    if sc["path"] == old_path:
                        sc["path"] = new_path
                        sc["name"] = new_name
                        renamed = True
        if renamed:
            self.config.save()

    def _on_group_moved(self, from_idx, to_idx):
        self.config.move_group(from_idx, to_idx)
        QTimer.singleShot(200, self.groups_container.refresh)

    def _on_group_renamed(self, group_id, new_name):
        self.config.rename_group(group_id, new_name)
        self.groups_container.refresh()

    def _on_group_color_changed(self, group_id, color_index):
        self.config.set_group_color(group_id, color_index)
        self.groups_container.refresh()

    def _on_group_width_changed(self, group_id, width):
        self.config.set_group_width(group_id, width)

    def _on_group_icon_size_changed(self, group_id, icon_size):
        self.config.set_group_icon_size(group_id, icon_size)

    def _on_group_show_name_changed(self, group_id, show_name):
        self.config.set_group_show_name(group_id, show_name)

    def _on_group_deleted(self, group_id):
        self.config.remove_group(group_id)
        self.groups_container.refresh()
