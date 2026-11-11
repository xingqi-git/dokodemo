import os
from functools import lru_cache
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush
from PyQt5.QtCore import QSize, Qt, QFileInfo
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
    """先裁掉透明边缘，再按比例缩放居中填充"""
    if pixmap.isNull():
        return _get_default_icon(size)

    image = pixmap.toImage()
    w, h = image.width(), image.height()

    # 从上往下扫描，找到第一个有内容的行
    top = 0
    while top < h:
        found = False
        for x in range(w):
            if image.pixelColor(x, top).alpha() > 10:
                found = True
                break
        if found:
            break
        top += 1

    # 从下往上扫描
    bottom = h - 1
    while bottom > top:
        found = False
        for x in range(w):
            if image.pixelColor(x, bottom).alpha() > 10:
                found = True
                break
        if found:
            break
        bottom -= 1

    # 从左往右扫描
    left = 0
    while left < w:
        found = False
        for y in range(top, bottom + 1):
            if image.pixelColor(left, y).alpha() > 10:
                found = True
                break
        if found:
            break
        left += 1

    # 从右往左扫描
    right = w - 1
    while right > left:
        found = False
        for y in range(top, bottom + 1):
            if image.pixelColor(right, y).alpha() > 10:
                found = True
                break
        if found:
            break
        right -= 1

    if top >= bottom or left >= right:
        # 全透明，返回默认
        result = QPixmap(size, size)
        result.fill(Qt.transparent)
        return result

    content = image.copy(left, top, right - left + 1, bottom - top + 1)
    content_pm = QPixmap.fromImage(content)

    # 按比例缩放
    scaled = content_pm.scaled(
        size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )

    # 居中绘制
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
    """解析 .lnk 快捷方式的目标路径（带缓存）

    pylnk3 对部分 lnk（特殊结构/相对路径/文件夹目标等）解析会失败，
    失败后返回 None，由上层用 _resolve_lnk_target_shell 兜底。"""
    try:
        import pylnk3
        target = pylnk3.parse(lnk_path).path
        if target:
            # 规范化：去掉文件夹 lnk 常见的尾随反斜杠、统一分隔符
            target = os.path.normpath(target)
            if os.path.exists(target):
                return target
    except Exception:
        pass
    return None


def _resolve_lnk_target_shell(lnk_path):
    """用 WScript.Shell COM（经 PowerShell）兜底解析 lnk 目标。

    仅在 pylnk3 解析失败时调用（有约 1 秒的子进程开销）。
    WScript.Shell 对文件夹目标的 lnk 支持良好，可补 pylnk3 的短板。
    特殊外壳文件夹（此电脑/网络连接等）没有文件系统路径，会失败返回 None。"""
    try:
        import subprocess
        # 单引号内的单引号用两个单引号转义
        safe = lnk_path.replace("'", "''")
        script = (
            "$s = New-Object -ComObject WScript.Shell;"
            f"$lnk = $s.CreateShortcut('{safe}');"
            "$lnk.TargetPath"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=5,
            # 打包版无控制台，不隐藏的话会弹出 PowerShell 黑框
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        target = out.stdout.strip()
        return target or None
    except Exception:
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
        os.startfile(path)
        return True
    except Exception as e:
        print(f"启动快捷方式失败: {e}")
        return False


def open_shortcut_location(lnk_path):
    """
    打开快捷方式指向的目标文件所在位置（在资源管理器中选中）
    如果无法解析目标，则打开 .lnk 文件所在目录并选中 .lnk
    使用 SHOpenFolderAndSelectItems API，比启动 explorer 进程更快
    """
    try:
        # 条目本身是文件夹（不是 .lnk）：直接打开其父目录并选中它
        if os.path.isdir(lnk_path):
            return _open_and_select_in_explorer(lnk_path)

        target = _resolve_lnk_target(lnk_path)
        if not target:
            # pylnk3 失败（部分文件夹 lnk / 特殊结构 lnk），换 WScript.Shell 兜底
            target = _resolve_lnk_target_shell(lnk_path)
            if target:
                target = os.path.normpath(target)
        if target and os.path.exists(target):
            return _open_and_select_in_explorer(target)
        # 都解析失败：打开 .lnk 所在目录
        return _open_and_select_in_explorer(lnk_path)
    except Exception as e:
        print(f"打开所在位置失败: {e}")
        return False


def _open_and_select_in_explorer(file_path):
    """
    在资源管理器中打开并选中文件。
    使用 Windows API SHOpenFolderAndSelectItems（通过 ctypes 调用，正确声明 64 位指针），
    复用已有 explorer 窗口，比启动新的 explorer 进程快很多。
    """
    try:
        import ctypes
        from ctypes import wintypes

        shell32 = ctypes.windll.shell32

        # 关键：正确声明 PIDL 相关函数的返回类型为指针
        # （64 位系统上 ctypes 默认返回 c_int，指针会被截断导致失效）
        shell32.ILCreateFromPathW.restype = wintypes.LPCVOID
        shell32.ILClone.restype = wintypes.LPCVOID
        shell32.ILFindLastID.restype = wintypes.LPCVOID
        shell32.SHOpenFolderAndSelectItems.restype = ctypes.c_long
        shell32.ILFree.argtypes = [wintypes.LPCVOID]
        shell32.ILRemoveLastID.argtypes = [wintypes.LPCVOID]
        shell32.ILRemoveLastID.restype = wintypes.BOOL

        # 1. 获取完整路径的绝对 PIDL
        pidl_full = shell32.ILCreateFromPathW(file_path)
        if not pidl_full:
            raise RuntimeError("ILCreateFromPathW failed")

        try:
            # 2. 获取父文件夹 PIDL：克隆完整 PIDL 后移除最后一项
            parent_pidl = shell32.ILClone(pidl_full)
            if not parent_pidl or not shell32.ILRemoveLastID(parent_pidl):
                if parent_pidl:
                    shell32.ILFree(parent_pidl)
                raise RuntimeError("failed to get parent pidl")

            # 3. 获取最后一项（相对父文件夹的 PIDL）
            child_pidl = shell32.ILFindLastID(pidl_full)
            if not child_pidl:
                shell32.ILFree(parent_pidl)
                raise RuntimeError("ILFindLastID failed")

            # 4. 构造子项 PIDL 数组
            pidl_array = (wintypes.LPCVOID * 1)()
            pidl_array[0] = child_pidl

            # 5. 调用 SHOpenFolderAndSelectItems
            hr = shell32.SHOpenFolderAndSelectItems(
                parent_pidl,  # pidlFolder
                1,            # cidl
                pidl_array,   # apidl
                0             # dwFlags
            )

            shell32.ILFree(parent_pidl)

            if hr == 0:  # S_OK
                return True
            else:
                raise RuntimeError(
                    f"SHOpenFolderAndSelectItems returned 0x{hr & 0xFFFFFFFF:08X}"
                )

        finally:
            try:
                shell32.ILFree(pidl_full)
            except Exception:
                pass

    except Exception as e:
        print(f"_open_and_select_in_explorer 异常: {e}")

    # 兜底：subprocess 启动 explorer
    try:
        import subprocess
        # 尾随反斜杠会吃掉 cmd 的闭合引号（explorer 只开默认窗口），先规范化
        safe_path = os.path.normpath(file_path)
        subprocess.Popen(f'explorer /select,"{safe_path}"', shell=True)
        return True
    except Exception as e:
        print(f"打开所在位置失败: {e}")
        return False


def rename_shortcut(lnk_path, new_name):
    """
    重命名快捷方式文件（不修改目标，仅修改 .lnk 文件名）
    new_name 不需要带 .lnk 后缀
    成功返回新的完整路径，失败返回 None
    """
    try:
        if not os.path.isfile(lnk_path):
            return None
        dir_path = os.path.dirname(lnk_path)
        old_name = os.path.basename(lnk_path)
        # 确保新名不带 .lnk
        base_new = os.path.splitext(new_name)[0]
        if not base_new.strip():
            return None
        new_filename = base_new + ".lnk"
        new_path = os.path.join(dir_path, new_filename)
        if old_name.lower() == new_filename.lower():
            return lnk_path  # 大小写相同不改名
        if os.path.exists(new_path):
            return None  # 已存在，不覆盖
        os.rename(lnk_path, new_path)
        clear_icon_cache()
        return new_path
    except Exception as e:
        print(f"重命名快捷方式失败: {e}")
        return None
