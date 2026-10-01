import json
import os
import uuid

# "全部快捷方式" 区域的虚拟 ID（仅用于拖拽数据标识，不写入配置）
ALL_SHORTCUTS_ID = "__all__"

# 预设配色方案（主色、浅色、深色）
PRESET_COLORS = [
    {"name": "天空蓝", "primary": "#4A90D9", "light": "#E8F2FC", "dark": "#2E6BAE"},
    {"name": "薄荷绿", "primary": "#48BB78", "light": "#E6F7EC", "dark": "#2F855A"},
    {"name": "珊瑚橙", "primary": "#ED8936", "light": "#FDF0E3", "dark": "#C05621"},
    {"name": "玫瑰粉", "primary": "#ED64A6", "light": "#FCE8F3", "dark": "#B83280"},
    {"name": "薰衣紫", "primary": "#9F7AEA", "light": "#F0EBFA", "dark": "#6B46C1"},
    {"name": "琥珀黄", "primary": "#ECC94B", "light": "#FEF7E0", "dark": "#B7791F"},
    {"name": "青碧色", "primary": "#38B2AC", "light": "#E2F7F6", "dark": "#285E61"},
    {"name": "岩石灰", "primary": "#718096", "light": "#EDF0F4", "dark": "#4A5568"},
]

# 图标固定大小（Windows 中等图标尺寸）
ICON_SIZE = 48
SMALL_ICON_SIZE = 32

# 分组默认宽度（约能放 3 个图标）
DEFAULT_GROUP_WIDTH = 240

# 分组最小宽度（约能放 1 个图标）
MIN_GROUP_WIDTH = 100

# 停靠模式
DOCK_MODE_FLOAT = ""       # 自由浮动（按上次位置大小）
DOCK_MODE_FULLSCREEN = "fullscreen"  # 全屏
DOCK_MODE_CENTER = "center"  # 居中
DOCK_MODE_LEFT = "left"     # 靠左
DOCK_MODE_RIGHT = "right"   # 靠右
DOCK_MODE_TOP = "top"       # 靠上
DOCK_MODE_BOTTOM = "bottom"  # 靠下
DOCK_MODE_BOTTOM_LEFT = "bottom_left"  # 左下
DOCK_MODE_BOTTOM_RIGHT = "bottom_right"  # 右下

DEFAULT_CONFIG = {
    "shortcut_dir": "",
    "shortcuts": [],
    "groups": [],
    "dock_mode": "",       # "" 表示自由浮动
    "window_geometry": None,  # [x, y, w, h] 自由浮动时的位置大小
    "close_to_tray": False  # 关闭窗口时是否隐藏到系统托盘
}


class ConfigManager:
    """配置管理器，负责读写 config.json"""

    def __init__(self, config_path):
        self.config_path = config_path
        self.config = {}
        self.load()

    def load(self):
        """加载配置文件，不存在则创建默认配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.config = DEFAULT_CONFIG.copy()
            self.save()

        # 确保关键字段存在
        for key, value in DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = value

        # 确保每个分组都有完整的字段（兼容旧配置）
        for g in self.config.get("groups", []):
            if "icon_size" not in g:
                g["icon_size"] = ICON_SIZE
            if "show_name" not in g:
                g["show_name"] = True

        # 兼容旧版本：旧配置中有 ungrouped 分组，迁移到顶层 shortcuts
        self._migrate_from_old_format()

    def _migrate_from_old_format(self):
        """从旧格式迁移：未分组快捷方式 → 顶层 shortcuts"""
        groups = self.config.get("groups", [])
        ungrouped = None
        for i, g in enumerate(groups):
            if g.get("id") == "ungrouped":
                ungrouped = g
                break
        if ungrouped is not None:
            # 把未分组的快捷方式移到顶层
            top_shortcuts = self.config.get("shortcuts", [])
            ungrouped_shortcuts = ungrouped.get("shortcuts", [])
            # 去重（按 path）
            existing_paths = {s["path"] for s in top_shortcuts}
            for sc in ungrouped_shortcuts:
                if sc["path"] not in existing_paths:
                    top_shortcuts.append(sc)
            self.config["shortcuts"] = top_shortcuts
            # 从未分组列表中移除
            self.config["groups"] = [g for g in groups if g.get("id") != "ungrouped"]
            # 移除旧字段
            self.config.pop("icon_size", None)
            self.config.pop("columns", None)
            self.save()

    def save(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"保存配置失败: {e}")

    # ---- 快捷方式目录 ----
    @property
    def shortcut_dir(self):
        return self.config.get("shortcut_dir", "")

    @shortcut_dir.setter
    def shortcut_dir(self, value):
        self.config["shortcut_dir"] = value
        self.save()

    # ---- 全部快捷方式（顶层） ----
    @property
    def shortcuts(self):
        """获取顶层（未分组）快捷方式列表"""
        return self.config.get("shortcuts", [])

    # ---- 分组管理 ----
    @property
    def groups(self):
        return self.config.get("groups", [])

    def add_group(self, name, color_index=0, width=None):
        """添加新分组，返回分组ID"""
        group_id = str(uuid.uuid4())[:8]
        new_group = {
            "id": group_id,
            "name": name,
            "color_index": color_index % len(PRESET_COLORS),
            "width": width if width else DEFAULT_GROUP_WIDTH,
            "icon_size": ICON_SIZE,
            "show_name": True,
            "shortcuts": []
        }
        self.config["groups"].append(new_group)
        self.save()
        return group_id

    def remove_group(self, group_id):
        """删除分组，将组内快捷方式移回顶层全部快捷方式"""
        group = self.get_group(group_id)
        if not group:
            return
        shortcuts = group.get("shortcuts", [])
        self.config["groups"] = [g for g in self.config["groups"] if g["id"] != group_id]
        # 移回顶层
        if shortcuts:
            self.config["shortcuts"].extend(shortcuts)
        self.save()

    def rename_group(self, group_id, new_name):
        """重命名分组"""
        group = self.get_group(group_id)
        if group:
            group["name"] = new_name
            self.save()

    def set_group_color(self, group_id, color_index):
        """设置分组配色"""
        group = self.get_group(group_id)
        if group:
            group["color_index"] = color_index % len(PRESET_COLORS)
            self.save()

    def set_group_icon_size(self, group_id, icon_size):
        """设置分组图标大小"""
        group = self.get_group(group_id)
        if group:
            group["icon_size"] = int(icon_size)
            self.save()

    def set_group_show_name(self, group_id, show_name):
        """设置分组是否显示图标名称"""
        group = self.get_group(group_id)
        if group:
            group["show_name"] = bool(show_name)
            self.save()

    # ---- 停靠模式 ----
    @property
    def dock_mode(self):
        return self.config.get("dock_mode", DOCK_MODE_FLOAT)

    @dock_mode.setter
    def dock_mode(self, value):
        self.config["dock_mode"] = value
        self.save()

    # ---- 关闭时隐藏到托盘 ----
    @property
    def close_to_tray(self):
        return bool(self.config.get("close_to_tray", False))

    @close_to_tray.setter
    def close_to_tray(self, value):
        self.config["close_to_tray"] = bool(value)
        self.save()

    # ---- 窗口几何（自由浮动时保存/恢复） ----
    @property
    def window_geometry(self):
        return self.config.get("window_geometry")

    @window_geometry.setter
    def window_geometry(self, value):
        self.config["window_geometry"] = value
        self.save()

    # ---- 分组宽度 ----
    def set_group_width(self, group_id, width):
        """设置分组宽度"""
        group = self.get_group(group_id)
        if group:
            group["width"] = max(MIN_GROUP_WIDTH, int(width))
            self.save()

    def get_group(self, group_id):
        """根据ID获取分组"""
        for g in self.config["groups"]:
            if g["id"] == group_id:
                return g
        return None

    def move_group(self, from_index, to_index):
        """移动分组顺序"""
        groups = self.config["groups"]
        if 0 <= from_index < len(groups) and 0 <= to_index < len(groups):
            item = groups.pop(from_index)
            groups.insert(to_index, item)
            self.save()

    # ---- 快捷方式移动 ----
    def move_shortcut(self, from_group_id, from_index, to_group_id, to_index):
        """移动快捷方式（可跨分组，支持顶层 ALL_SHORTCUTS_ID）"""
        from_list = self._get_shortcut_list(from_group_id)
        to_list = self._get_shortcut_list(to_group_id)
        if from_list is None or to_list is None:
            return
        if from_index < 0 or from_index >= len(from_list):
            return
        item = from_list.pop(from_index)
        if to_index < 0 or to_index > len(to_list):
            to_index = len(to_list)
        # 同列表移动时，源在目标前需减一
        if from_list is to_list and from_index < to_index:
            to_index -= 1
        to_list.insert(to_index, item)
        self.save()

    def _get_shortcut_list(self, group_id):
        """根据 group_id 获取对应的快捷方式列表引用"""
        if group_id == ALL_SHORTCUTS_ID:
            return self.config["shortcuts"]
        group = self.get_group(group_id)
        if group:
            return group.get("shortcuts", [])
        return None

    # ---- 同步文件系统快捷方式 ----
    def sync_shortcuts(self, shortcut_paths_with_names):
        """
        同步文件夹中的快捷方式
        shortcut_paths_with_names: [(path, display_name), ...]
        返回新增和删除的数量
        """
        existing_paths = set()

        # 收集所有已有的快捷方式路径（顶层 + 各分组）
        for s in self.config.get("shortcuts", []):
            existing_paths.add(s["path"])
        for g in self.config["groups"]:
            for s in g.get("shortcuts", []):
                existing_paths.add(s["path"])

        current_paths = {path for path, _ in shortcut_paths_with_names}

        # 新增的放到顶层全部快捷方式
        added = 0
        for path, name in shortcut_paths_with_names:
            if path not in existing_paths:
                self.config["shortcuts"].append({"path": path, "name": name})
                added += 1

        # 删除已不存在的
        removed = 0
        # 顶层
        before = len(self.config["shortcuts"])
        self.config["shortcuts"] = [
            s for s in self.config["shortcuts"] if s["path"] in current_paths
        ]
        removed += before - len(self.config["shortcuts"])
        # 各分组
        for g in self.config["groups"]:
            before = len(g["shortcuts"])
            g["shortcuts"] = [s for s in g["shortcuts"] if s["path"] in current_paths]
            removed += before - len(g["shortcuts"])

        self.save()
        return added, removed
