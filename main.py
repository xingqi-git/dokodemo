import sys
import os


# 设置 Windows AppUserModelID（必须在 QApplication 创建之前）
# 这样任务栏才能正确显示程序图标
def _set_app_id():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "shortcutmanager.app.v1"
            )
        except Exception:
            pass

_set_app_id()

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

from src.main_window import MainWindow
from src.app_icon import get_app_icon

# 单实例本地服务名
_SINGLE_INSTANCE_SERVER = "DokodemoShortcutManager_SingleInstance"


def _get_resource_path(relative_path):
    """获取资源文件路径（兼容打包后和开发环境）"""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)


def _show_window(window):
    """唤醒并最大化显示主窗口"""
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

    # 关闭最后一个窗口不退出（托盘驻留）
    app.setQuitOnLastWindowClosed(False)

    # 设置默认字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    app_icon = get_app_icon()

    # 设置应用程序图标（任务栏显示用）——使用内嵌图标，不依赖文件路径
    app.setWindowIcon(app_icon)

    # 配置文件路径（与程序同目录）
    config_path = _get_resource_path("config.json")

    window = MainWindow(config_path)
    window.setWindowTitle("快捷方式管理")
    window.show()

    # ---- 系统托盘 ----
    tray = QSystemTrayIcon(app_icon)
    tray.setToolTip("快捷方式管理")

    tray_menu = QMenu()

    show_action = QAction("显示主窗口", tray_menu)
    show_action.triggered.connect(lambda: _show_window(window))
    tray_menu.addAction(show_action)

    tray_menu.addSeparator()

    quit_action = QAction("退出", tray_menu)
    quit_action.triggered.connect(app.quit)
    tray_menu.addAction(quit_action)

    tray.setContextMenu(tray_menu)

    def _on_tray_activated(reason):
        # 单击或双击托盘图标 → 切换显示/隐藏
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if window.isVisible():
                window.hide()
            else:
                _show_window(window)

    tray.activated.connect(_on_tray_activated)
    tray.show()

    # ---- 点击快捷方式后自动隐藏到托盘 ----
    def _on_shortcut_launched():
        window.hide()

    window.groups_container.shortcutLaunched.connect(_on_shortcut_launched)

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
