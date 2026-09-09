import os
from functools import lru_cache
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QFileIconProvider

# 全局图标缓存，避免重复提取
_icon_cache = {}

# 全局复用 QFileIconProvider，避免重复创建
_icon_provider = None

# 预检测可用的 lnk 解析方式，避免每次调用都重复 try/except
_pylnk3_available = None
_pywin32_available = None


def _check_pylnk3():
    global _pylnk3_available
    if _pylnk3_available is None:
        try:
            import pylnk3  # noqa: F401
            _pylnk3_available = True
        except ImportError:
            _pylnk3_available = False
    return _pylnk3_available


def _check_pywin32():
    global _pywin32_available
    if _pywin32_available is None:
        try:
            import pythoncom  # noqa: F401
            from win32com.shell import shell  # noqa: F401
            _pywin32_available = True
        except ImportError:
            _pywin32_available = False
    return _pywin32_available


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
    """解析 .lnk 快捷方式的目标路径（带缓存）"""
    # 方法1：pylnk3（轻量级，优先使用）
    if _check_pylnk3():
        try:
            import pylnk3
            target = pylnk3.parse(lnk_path).path
            if target and os.path.exists(target):
                return target
        except Exception:
            pass

    # 方法2：pywin32（更可靠）
    if _check_pywin32():
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
        except Exception:
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


def open_shortcut_location(lnk_path):
    """
    打开快捷方式指向的目标文件所在位置（在资源管理器中选中）
    如果无法解析目标，则打开 .lnk 文件所在目录并选中 .lnk
    使用 SHOpenFolderAndSelectItems API，比启动 explorer 进程更快
    """
    try:
        target = _resolve_lnk_target(lnk_path)
        open_path = target if target else lnk_path
        if os.name == "nt":
            return _open_and_select_in_explorer(open_path)
        else:
            # 非 Windows：打开所在目录
            dir_path = os.path.dirname(open_path)
            from PyQt5.QtGui import QDesktopServices
            from PyQt5.QtCore import QUrl
            return QDesktopServices.openUrl(QUrl.fromLocalFile(dir_path))
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
        ole32 = ctypes.windll.ole32

        # 关键：正确声明 PIDL 相关函数的返回类型为指针
        # （64 位系统上 ctypes 默认返回 c_int，指针会被截断导致失效）
        shell32.ILCreateFromPathW.restype = wintypes.LPCVOID
        shell32.ILClone.restype = wintypes.LPCVOID
        shell32.ILFindLastID.restype = wintypes.LPCVOID
        shell32.SHOpenFolderAndSelectItems.restype = ctypes.c_long
        shell32.ILFree.argtypes = [wintypes.LPCVOID]
        shell32.ILRemoveLastID.argtypes = [wintypes.LPCVOID]
        shell32.ILRemoveLastID.restype = wintypes.BOOL

        # 初始化 COM
        ole32.CoInitializeEx(None, 0)  # COINIT_APARTMENTTHREADED

        # 1. 获取完整路径的绝对 PIDL
        pidl_full = shell32.ILCreateFromPathW(file_path)
        if not pidl_full:
            ole32.CoUninitialize()
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
            ole32.CoUninitialize()

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
        subprocess.Popen(f'explorer /select,"{file_path}"', shell=True)
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
