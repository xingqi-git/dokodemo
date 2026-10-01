"""开机自动启动（Windows）

通过 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run 注册，
无需管理员权限。启动命令固定带 --autostart 参数，供 main.py 区分
开机自启与手动启动。

勾选状态以注册表真实内容为唯一权威来源，不写入 config.json，避免
“配置显示已开但注册表被外部删掉”的状态漂移。
"""
import os
import sys

# 自启启动参数：注册表命令中固定携带
AUTOSTART_ARG = "--autostart"

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "dokodemo"


def is_supported():
    """当前平台是否支持开机自启"""
    return os.name == "nt"


def _build_command():
    """构造开机自启命令行（打包后 / 脚本运行两种形态）"""
    if getattr(sys, "frozen", False):
        # PyInstaller 等打包形态：直接启动 exe
        exe = f'"{sys.executable}"'
    else:
        # 脚本形态：优先 pythonw.exe，避免开机时弹出黑色控制台
        py_dir = os.path.dirname(sys.executable)
        pythonw = os.path.join(py_dir, "pythonw.exe")
        launcher = pythonw if os.path.exists(pythonw) else sys.executable
        main_py = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py")
        exe = f'"{launcher}" "{main_py}"'
    return f"{exe} {AUTOSTART_ARG}"


def is_enabled():
    """注册表中是否已启用开机自启"""
    if not is_supported():
        return False
    import winreg
    try:
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, _VALUE_NAME)
            return bool(value)
    except OSError:
        return False


def enable():
    """启用开机自启，成功返回 True"""
    if not is_supported():
        return False
    import winreg
    try:
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(
                key, _VALUE_NAME, 0, winreg.REG_SZ, _build_command())
        return True
    except OSError:
        return False


def disable():
    """关闭开机自启，成功（或本就不存在）返回 True"""
    if not is_supported():
        return False
    import winreg
    try:
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _VALUE_NAME)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def was_autostarted(argv=None):
    """本次进程是否由开机自启拉起（命令带 --autostart）"""
    if argv is None:
        argv = sys.argv
    return AUTOSTART_ARG in argv
