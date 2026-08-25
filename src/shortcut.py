import os
from functools import lru_cache
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QFileIconProvider

# 全局图标缓存，避免重复提取
_icon_cache = {}

# 全局复用 QFileIconProvider，避免重复创建
_icon_provider = None


def _get_icon_provider():
    global _icon_provider
    if _icon_provider is None:
        _icon_provider = QFileIconProvider()
    return _icon_provider


def scan_shortcuts(directory):
    """扫描目录下所有 .lnk 快捷方式文件（不含子目录）"""
    if not directory or not os.path.isdir(directory):
        return []

    shortcuts = []
    try:
        for filename in os.listdir(directory):
            if filename.lower().endswith(".lnk"):
                full_path = os.path.join(directory, filename)
                display_name = os.path.splitext(filename)[0]
                shortcuts.append((full_path, display_name))
    except OSError as e:
        print(f"扫描目录失败: {e}")

    return shortcuts


def get_shortcut_icon(path, size=64):
    """获取快捷方式的目标文件图标（不带箭头），使用缓存"""
    cache_key = (path, size)
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    pixmap = _extract_icon(path, size)
    _icon_cache[cache_key] = pixmap
    return pixmap


def clear_icon_cache():
    """清空图标缓存"""
    global _icon_cache
    _icon_cache = {}


def _extract_icon(path, size):
    """提取快捷方式目标文件的图标（不带箭头）"""
    target_path = _resolve_lnk_target(path)
    provider = _get_icon_provider()
    from PyQt5.QtCore import QFileInfo

    # 优先提取目标文件图标（不带箭头）
    if target_path and os.path.exists(target_path):
        try:
            icon = provider.icon(QFileInfo(target_path))
            if not icon.isNull():
                return _icon_to_pixmap(icon, size)
        except Exception:
            pass

    # 兜底：.lnk 本身图标（可能带箭头）
    try:
        icon = provider.icon(QFileInfo(path))
        if not icon.isNull():
            return _icon_to_pixmap(icon, size)
    except Exception:
        pass

    return _get_default_icon(size)


def _icon_to_pixmap(icon, size):
    """QIcon 转 QPixmap，裁剪透明边缘后拉伸填满"""
    pixmap = icon.pixmap(QSize(size * 2, size * 2))
    if pixmap.isNull():
        pixmap = icon.pixmap(QSize(size, size))
    if pixmap.isNull():
        return _get_default_icon(size)

    return _crop_and_fill(pixmap, size)


def _crop_and_fill(pixmap, size):
    """把 pixmap 按比例缩放后居中放到 size x size 的画布上"""
    if pixmap.isNull():
        return _get_default_icon(size)

    # 保持比例缩放
    scaled = pixmap.scaled(
        size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )

    # 居中绘制到透明画布
    result = QPixmap(size, size)
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()
    return result


@lru_cache(maxsize=512)
def _resolve_lnk_target(lnk_path):
    """解析 .lnk 快捷方式的目标路径（带缓存）"""
    # 方法1：pylnk3（轻量级，优先使用）
    try:
        import pylnk3
        target = pylnk3.parse(lnk_path).path
        if target and os.path.exists(target):
            return target
    except (ImportError, Exception):
        pass

    # 方法2：pywin32（更可靠，但更重）
    try:
        import pythoncom
        from win32com.shell import shell

        pythoncom.CoInitialize()
        try:
            link = pythoncom.CoCreateInstance(
                shell.CLSID_ShellLink, None,
                pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
            )
            link.QueryInterface(pythoncom.IID_IPersistFile).Load(lnk_path)
            target, _ = link.GetPath(0)
            if target and os.path.exists(target):
                return target
        finally:
            pythoncom.CoUninitialize()
    except (ImportError, Exception):
        pass

    return None


def _get_default_icon(size):
    """生成默认文件图标"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(QColor("#D0D0D0")))
    painter.setPen(Qt.NoPen)
    margin = size * 0.15
    painter.drawRoundedRect(
        margin, margin, size - 2 * margin, size - 2 * margin,
        size * 0.1, size * 0.1
    )
    painter.end()
    return pixmap


def launch_shortcut(path):
    """启动快捷方式（等同于资源管理器双击）"""
    try:
        if os.name == "nt":
            os.startfile(path)
            return True
        else:
            from PyQt5.QtGui import QDesktopServices
            from PyQt5.QtCore import QUrl
            return QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    except Exception as e:
        print(f"启动快捷方式失败: {e}")
        return False
