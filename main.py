import sys
import os

# 屏蔽 Windows TSF 输入法的调试日志
if os.name == "nt":
    _devnull = open(os.devnull, "w")
    sys.stderr = _devnull

# 确保 src 目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 修复虚拟环境中 Qt 平台插件路径问题
def _fix_qt_plugin_path():
    try:
        import PyQt5
        pyqt_dir = os.path.dirname(PyQt5.__file__)
        plugin_path = os.path.join(pyqt_dir, "Qt5", "plugins")
        if os.path.isdir(plugin_path):
            os.environ["QT_PLUGIN_PATH"] = plugin_path
            platforms_path = os.path.join(plugin_path, "platforms")
            if os.path.isdir(platforms_path):
                if hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(platforms_path)
    except Exception:
        pass

_fix_qt_plugin_path()

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

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from src.main_window import MainWindow
from src.app_icon import get_app_icon


def _get_resource_path(relative_path):
    """获取资源文件路径（兼容打包后和开发环境）"""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)


def main():
    app = QApplication(sys.argv)

    # 设置默认字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 设置应用程序图标（任务栏显示用）——使用内嵌图标，不依赖文件路径
    app.setWindowIcon(get_app_icon())

    # 配置文件路径（与程序同目录）
    config_path = _get_resource_path("config.json")

    window = MainWindow(config_path)
    window.setWindowTitle("快捷方式管理")
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
