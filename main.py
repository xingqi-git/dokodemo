import sys
import os


# 设置 Windows AppUserModelID（必须在 QApplication 创建之前）
# 这样任务栏才能正确显示程序图标
def _set_app_id():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "dokodemo.app"
            )
        except Exception:
            pass

_set_app_id()

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

from src.main_window import MainWindow
from src.app_icon import get_app_icon
from src import autostart

# 单实例本地服务名
_SINGLE_INSTANCE_SERVER = "dokodemo_SingleInstance"

# 开机自启（非托盘模式）下，界面正常展示后延迟多久再最小化。
# 开机时桌面/任务栏尚在初始化，直接以最小化状态创建窗口在真实开机
# 环境不可靠；先正常显示、等环境稳定后走与“最小化按钮”相同的路径。
_AUTOSTART_MINIMIZE_DELAY_MS = 800


def _get_resource_path(relative_path):
    """获取资源文件路径（兼容打包后和开发环境）"""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)


def _show_window(window):
    """唤醒主窗口，保持之前的最大化状态"""
    window.showNormal()  # 先 showNormal，再根据状态决定是否最大化
    if window._is_maximized:
        window.showMaximized()
    window.raise_()
    window.activateWindow()


def main():
    app = QApplication(sys.argv)

    # ---- 单实例检测 ----
    # 先尝试连接已有实例
    socket = QLocalSocket()
    socket.connectToServer(_SINGLE_INSTANCE_SERVER)
    if socket.waitForConnected(500):
        # 连接成功 → 已有实例在运行，发唤醒消息后退出
        socket.write(b"show")
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        sys.exit(0)
    socket.close()

    # 连接失败 → 自己是第一个实例，启动服务端监听
    server = QLocalServer()
    server.removeServer(_SINGLE_INSTANCE_SERVER)  # 清理上次残留
    server.listen(_SINGLE_INSTANCE_SERVER)

    # 设置默认字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    app_icon = get_app_icon()

    # 设置应用程序图标（任务栏显示用）——使用内嵌图标，不依赖文件路径
    app.setWindowIcon(app_icon)

    # 配置文件路径（与程序同目录）
    config_path = _get_resource_path("config.json")

    window = MainWindow(config_path)
    window.setWindowTitle("dokodemo")

    # ---- 首次显示策略 ----
    # 手动启动：正常显示界面。
    # 开机自启（注册表命令带 --autostart）：
    #   托盘模式 → 不显示主窗口，只留托盘图标；
    #   非托盘   → 先正常显示，等桌面环境稳定后再最小化。
    autostarted = autostart.was_autostarted()
    hide_to_tray = (
        window.config.close_to_tray and window._tray_icon is not None)

    if autostarted and hide_to_tray:
        pass  # 托盘图标已在窗口构造时显示，主窗口保持隐藏
    else:
        window.show()
        if autostarted:
            # 与点击标题栏最小化按钮走同一条 showMinimized() 路径
            QTimer.singleShot(
                _AUTOSTART_MINIMIZE_DELAY_MS,
                lambda: window.showMinimized() if window.isVisible() else None
            )

    # ---- 点击快捷方式后收起窗口（托盘模式隐藏到托盘，否则最小化） ----
    def _on_shortcut_launched():
        window.dock_away()

    window.groups_container.shortcutLaunched.connect(_on_shortcut_launched)

    # ---- 点击空白区域收起窗口 ----
    def _on_blank_clicked():
        window.dock_away()

    window.groups_container.blankClicked.connect(_on_blank_clicked)

    # ---- 服务端收到第二个实例的唤醒消息 ----
    def _on_new_connection():
        client = server.nextPendingConnection()
        if not client:
            return
        client.readyRead.connect(
            lambda c=client: _on_client_message(c)
        )

    def _on_client_message(client):
        data = bytes(client.readAll())
        if data == b"show":
            _show_window(window)
        client.disconnectFromServer()

    server.newConnection.connect(_on_new_connection)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
