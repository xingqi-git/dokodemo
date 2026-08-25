import os
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QFileIconProvider

# 全局图标缓存，避免重复提取
_icon_cache = {}


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

    # 优先提取目标文件图标（不带箭头）
    if target_path and os.path.exists(target_path):
        try:
            from PyQt5.QtCore import QFileInfo
            provider = QFileIconProvider()
            icon = provider.icon(QFileInfo(target_path))
            if not icon.isNull():
                return _icon_to_pixmap(icon, size)
        except Exception:
            pass

    # 兜底：.lnk 本身图标（可能带箭头）
    try:
        from PyQt5.QtCore import QFileInfo
        provider = QFileIconProvider()
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
    """裁剪掉透明边缘，然后拉伸填满整个 size x size 区域"""
    if pixmap.isNull():
        return _get_default_icon(size)

    image = pixmap.toImage()
    min_x = image.width()
    min_y = image.height()
    max_x = 0
    max_y = 0
    has_content = False

    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 10:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y
                has_content = True

    if not has_content:
        result = QPixmap(size, size)
        result.fill(Qt.transparent)
        return result

    content = image.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
    return QPixmap.fromImage(content).scaled(
        size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
    )


def _resolve_lnk_target(lnk_path):
    """解析 .lnk 快捷方式的目标路径"""
    # 方法1：pywin32（最可靠）
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

    # 方法2：pylnk3（轻量级）
    try:
        import pylnk3
        target = pylnk3.parse(lnk_path).path
        if target and os.path.exists(target):
            return target
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
