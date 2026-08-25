# -*- coding: utf-8 -*-
"""
自定义 PyQt5 钩子，绕过 PyInstaller 官方钩子的中文路径 bug
手动指定 Qt 插件路径
"""
import os
import PyQt5

# 正确的 Qt 根目录（用 PyQt5.__file__ 计算，避免路径编码问题）
_qt_dir = os.path.join(os.path.dirname(PyQt5.__file__), "Qt5")
_bin_dir = os.path.join(_qt_dir, "bin")
_plugin_dir = os.path.join(_qt_dir, "plugins")

# 告诉 PyInstaller Qt 的位置
os.environ["QT_PLUGIN_PATH"] = _plugin_dir
os.environ["PATH"] = _bin_dir + os.pathsep + os.environ.get("PATH", "")

# 需要的 Qt 插件
plugins = {
    "platforms": ["qwindows.dll"],
    "styles": ["qwindowsvistastyle.dll"],
}

binaries = []
datas = []

for plugin_type, files in plugins.items():
    src_dir = os.path.join(_plugin_dir, plugin_type)
    if os.path.isdir(src_dir):
        for f in files:
            src = os.path.join(src_dir, f)
            if os.path.isfile(src):
                binaries.append((src, os.path.join("PyQt5", "Qt5", "plugins", plugin_type)))

# Qt 运行时 DLL
for dll in ["Qt5Core.dll", "Qt5Gui.dll", "Qt5Widgets.dll"]:
    src = os.path.join(_bin_dir, dll)
    if os.path.isfile(src):
        binaries.append((src, "."))

hiddenimports = ["PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets"]
