# -*- mode: python ; coding: utf-8 -*-
"""
dokodemo 打包配置文件（PyInstaller 6.x，体积深度优化版）

使用方法：
    pyinstaller dokodemo.spec --clean

所有打包参数都集中在此文件中，无需再在命令行传 --noconsole / --icon /
--name / --additional-hooks-dir 等参数。

体积优化（按收益排序）：
1. 排除不用的 Qt 模块 DLL（QtQml / QtQuick / QtWebEngine / QtSql 等）
2. 排除不用的 PyQt5 Python 绑定模块
3. 清理 Qt 翻译文件（只留中文）
4. 过滤冗余 Qt 插件（imageformats / generic / platformthemes 等）
5. 排除 tkinter、unittest 等无关标准库
6. 字节码优化 optimize=2
7. UPX 压缩
"""
import os

# ── 排除确定不用的 Python 模块 ──────────────────────

# PyQt5 未使用的子模块
_pyqt5_excludes = [
    # QML / Quick 系列（纯 QtWidgets，不用 QML）
    'PyQt5.QtQml',
    'PyQt5.QtQuick',
    'PyQt5.QtQuickWidgets',
    'PyQt5.QtQuick3D',
    'PyQt5.QtQuickControls2',
    'PyQt5.QtQuickTemplates2',
    'PyQt5.QtQuickShapes',
    'PyQt5.QtQuickParticles',
    'PyQt5.QtQuickLocalStorage',
    'PyQt5.QtQuickWindow',
    # Location / Positioning
    'PyQt5.QtLocation',
    'PyQt5.QtPositioning',
    # Multimedia
    'PyQt5.QtMultimedia',
    'PyQt5.QtMultimediaWidgets',
    # WebEngine（大块头）
    'PyQt5.QtWebEngine',
    'PyQt5.QtWebEngineCore',
    'PyQt5.QtWebEngineWidgets',
    'PyQt5.QtWebChannel',
    'PyQt5.QtWebSockets',
    # 其他未用 Qt 模块
    'PyQt5.QtSql',
    'PyQt5.QtXml',
    'PyQt5.QtXmlPatterns',
    'PyQt5.QtSensors',
    'PyQt5.QtSerialPort',
    'PyQt5.QtBluetooth',
    'PyQt5.QtNfc',
    'PyQt5.QtTextToSpeech',
    'PyQt5.QtRemoteObjects',
    'PyQt5.QtHelp',
    'PyQt5.QtDesigner',
    'PyQt5.QtTest',
    'PyQt5.QtWinExtras',
    'PyQt5.QtSvg',
    'PyQt5.QtOpenGL',
    'PyQt5.QtDBus',
    'PyQt5.QtPrintSupport',
    # Charts / DataVisualization / 3D
    'PyQt5.QtCharts',
    'PyQt5.QtDataVisualization',
    'PyQt5.Qt3DCore',
    'PyQt5.Qt3DRender',
    'PyQt5.Qt3DInput',
    'PyQt5.Qt3DLogic',
    'PyQt5.Qt3DAnimation',
    'PyQt5.Qt3DExtras',
    # uic / pylupdate 等开发工具
    'PyQt5.uic',
    'PyQt5.pylupdate',
]

# 标准库中确定不用的大块头
# 注意：只排除"顶层大块、不会被运行时/标准库内部间接引用"的模块。
# urllib / email / xml / csv / ssl / hashlib / locale / gettext 等都可能被
# pathlib / zipfile / json / PyInstaller 运行时间接引用，不可随意排除。
_stdlib_excludes = [
    # GUI 框架（项目用 PyQt5，不用 Tk）
    'tkinter',
    'turtle',
    'turtledemo',
    'idlelib',
    # 测试相关（体积大，确定不用）
    'unittest',
    'doctest',
    'test',
    'pydoc',
    'pydoc_data',
    # 数据库（项目用 json 存配置，且不会被标准库间接引用）
    'sqlite3',
    'bdb',
    'dbm',
    'dumbdbm',
    # 打包 / 构建工具
    'distutils',
    'setuptools',
    'pkg_resources',
    'ensurepip',
    'lib2to3',
    # 多进程（项目单线程 GUI）
    'multiprocessing',
    # 纯网络协议顶层包（注意：urllib 会被 pathlib 间接引用，不可排除）
    'ftplib',
    'poplib',
    'imaplib',
    'smtplib',
    'telnetlib',
    'nntplib',
    # 音频模块
    'aifc',
    'sunau',
    'wave',
    'audioop',
    'chunk',
    # Unix 特定（Windows 平台，这些模块在 Windows 上本就不存在/不可加载）
    'ossaudiodev',
    'nis',
    'syslog',
    'posix',
    'pwd',
    'grp',
    'resource',
    'fcntl',
    'termios',
    'tty',
    'pty',
    # 纯开发工具 / 交互式模块
    'readline',
    'rlcompleter',
    'cmd',
    'code',
    'codeop',
    'py_compile',
    'compileall',
    'modulefinder',
    'pyclbr',
    'tabnanny',
    'wsgiref',
    'cgi',
    'cgitb',
    'uu',
    'quopri',
    'binhex',
    'shelve',
    'netrc',
    'xdrlib',
    'plistlib',
    'graphlib',
    'zoneinfo',
    'colorsys',
    'imghdr',
    'sndhdr',
    'pyexpat',
    # decimal/_decimal：项目不用高精度十进制，110KB
    'decimal',
    '_decimal',
    # lzma/_lzma：项目不用 LZMA 压缩，88KB
    'lzma',
    '_lzma',
    # bz2/_bz2：项目不用 BZ2 压缩，50KB
    'bz2',
    '_bz2',
    # _wmi：WMI 扩展模块，项目不用，30KB
    '_wmi',
]

excludes = _pyqt5_excludes + _stdlib_excludes


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)

# ══════════════════════════════════════════════════════
# 体积优化：手动过滤冗余二进制和数据文件
# ══════════════════════════════════════════════════════

# ── 过滤冗余 DLL（hook 误带进来的） ──
_DLL_BLACKLIST = {
    # OpenGL / D3D 相关（纯 QtWidgets 不需要）
    'opengl32sw.dll',
    'libglesv2.dll',
    'libegl.dll',
    'd3dcompiler_47.dll',
    'qt5opengl.dll',
    # Qml / Quick
    'qt5qml.dll',
    'qt5qmlmodels.dll',
    'qt5qmlworkerscript.dll',
    'qt5qmllocalstorage.dll',
    'qt5quick.dll',
    'qt5quickwidgets.dll',
    'qt5quickcontrols2.dll',
    'qt5quicktemplates2.dll',
    'qt5quickshapes.dll',
    'qt5quickparticles.dll',
    'qt5quick3d.dll',
    # WebEngine（大块头）
    'qt5webenginecore.dll',
    'qt5webenginewidgets.dll',
    'qt5webchannel.dll',
    'qt5websockets.dll',
    # Location / Positioning
    'qt5location.dll',
    'qt5positioning.dll',
    # Multimedia
    'qt5multimedia.dll',
    'qt5multimediawidgets.dll',
    # 其他未用 Qt 模块
    'qt5sql.dll',
    'qt5xml.dll',
    'qt5xmlpatterns.dll',
    'qt5sensors.dll',
    'qt5serialport.dll',
    'qt5bluetooth.dll',
    'qt5nfc.dll',
    'qt5texttospeech.dll',
    'qt5remoteobjects.dll',
    'qt5help.dll',
    'qt5designer.dll',
    'qt5designercomponents.dll',
    'qt5test.dll',
    'qt5winextras.dll',
    'qt5svg.dll',
    'qt5dbus.dll',
    'qt5printsupport.dll',
    # Charts / DataVisualization / 3D
    'qt5charts.dll',
    'qt5datavisualization.dll',
    'qt53dcore.dll',
    'qt53drender.dll',
    'qt53dinput.dll',
    'qt53dlogic.dll',
    'qt53danimation.dll',
    'qt53dextras.dll',
}


def _is_dll_blacklisted(dest_path):
    """判断 DLL 是否在黑名单中（只比较文件名，不区分大小写）"""
    name = os.path.basename(dest_path).lower()
    return name in _DLL_BLACKLIST


a.binaries = [b for b in a.binaries if not _is_dll_blacklisted(b[0])]

# ── 过滤 Qt 翻译文件（只留中文） ──
_KEEP_QM_PREFIXES = ('qt_zh', 'qtbase_zh')


def _is_keep_qm(dest_path):
    """判断 .qm 翻译文件是否保留（只留中文相关）"""
    if not dest_path.endswith('.qm'):
        return True
    if 'translations' not in dest_path.replace('\\', '/'):
        return True
    fname = os.path.basename(dest_path).lower()
    return any(fname.startswith(p) for p in _KEEP_QM_PREFIXES)


a.datas = [d for d in a.datas if _is_keep_qm(d[0])]

# ── 过滤 Qt 插件中冗余的图片格式、平台插件 ──
_KEEP_IMAGE_FORMATS = ('qico', 'qpng')
_KEEP_PLATFORMS = ('qwindows',)
_KEEP_STYLES = ()


def _is_keep_plugin(dest_path):
    """判断 Qt 插件是否保留"""
    p = dest_path.replace('\\', '/')
    if 'plugins/imageformats/' in p:
        fname = os.path.basename(p).lower()
        return any(fname.startswith(k) for k in _KEEP_IMAGE_FORMATS)
    if 'plugins/platforms/' in p:
        fname = os.path.basename(p).lower()
        return any(fname.startswith(k) for k in _KEEP_PLATFORMS)
    if 'plugins/styles/' in p:
        fname = os.path.basename(p).lower()
        return any(fname.startswith(k) for k in _KEEP_STYLES)
    if 'plugins/bearer/' in p:
        # 网络承载插件（如 3G/Wi-Fi 自动切换），桌面应用不用
        return False
    if 'plugins/generic/' in p:
        # 触摸等通用插件，Windows 桌面不用
        return False
    if 'plugins/platformthemes/' in p:
        # Linux 的桌面主题插件，Windows 不用
        return False
    if 'plugins/printsupport/' in p:
        # 打印支持插件，不用
        return False
    if 'plugins/iconengines/' in p:
        # 图标引擎插件，不用
        return False
    return True


a.datas = [d for d in a.datas if _is_keep_plugin(d[0])]
a.binaries = [b for b in a.binaries if _is_keep_plugin(b[0])]

# ── 去重：移除 PyQt5\Qt5\bin\ 下重复的 MSVC 运行时 DLL ──
# 根目录（_internal\）已经有一份 MSVC 运行时，Qt DLL 在搜索路径上能找到它们
_DUP_MSVC = [
    'msvcp140.dll',
    'msvcp140_1.dll',
    'msvcp140_2.dll',
    'msvcp140_atomic_wait.dll',
    'msvcp140_codecvt_ids.dll',
    'vcruntime140.dll',
    'vcruntime140_1.dll',
    'vcruntime140_threads.dll',
]


def _is_dup_msvc(dest_path):
    p = dest_path.replace('\\', '/').lower()
    if 'pyqt5/qt5/bin/' not in p:
        return False
    return os.path.basename(p).lower() in _DUP_MSVC


a.binaries = [b for b in a.binaries if not _is_dup_msvc(b[0])]

# ── 过滤 OpenSSL DLL（项目无 HTTPS 请求，不需要） ──
_SSL_DLLS = (
    'libcrypto-1_1-x64.dll',
    'libssl-1_1-x64.dll',
    'libcrypto-3-x64.dll',
    'libssl-3-x64.dll',
)


def _is_ssl_dll(dest_path):
    return os.path.basename(dest_path).lower() in _SSL_DLLS


a.binaries = [b for b in a.binaries if not _is_ssl_dll(b[0])]


pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='dokodemo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='dokodemo',
)
