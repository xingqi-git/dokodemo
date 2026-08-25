import json
import os
import uuid

# 未分组的固定ID
UNGROUPED_ID = "ungrouped"
UNGROUPED_NAME = "未添加分组"

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

DEFAULT_CONFIG = {
    "shortcut_dir": "",
    "icon_size": 64,
    "columns": 2,
    "groups": []
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

    # ---- 图标大小 ----
    @property
    def icon_size(self):
        return self.config.get("icon_size", 64)

    @icon_size.setter
    def icon_size(self, value):
        self.config["icon_size"] = max(32, min(128, int(value)))
        self.save()

    # ---- 列数 ----
    @property
    def columns(self):
        return self.config.get("columns", 2)

    @columns.setter
    def columns(self, value):
        self.config["columns"] = max(1, min(5, int(value)))
        self.save()

    # ---- 分组管理 ----
    @property
    def groups(self):
        return self.config.get("groups", [])

    def add_group(self, name, color_index=0):
        """添加新分组，返回分组ID"""
        group_id = str(uuid.uuid4())[:8]
        color = PRESET_COLORS[color_index % len(PRESET_COLORS)]
        new_group = {
            "id": group_id,
            "name": name,
            "color_index": color_index,
            "shortcuts": []
        }
        self.config["groups"].append(new_group)
        self.save()
        return group_id

    def remove_group(self, group_id):
        """删除分组，将组内快捷方式移到未分组"""
        if group_id == UNGROUPED_ID:
            return  # 未分组不可删除
        group = self.get_group(group_id)
        if not group:
            return
        shortcuts = group.get("shortcuts", [])
        self.config["groups"] = [g for g in self.config["groups"] if g["id"] != group_id]
        # 移到未分组
        if shortcuts:
            ungrouped = self._get_or_create_ungrouped()
            ungrouped["shortcuts"].extend(shortcuts)
        self.save()

    def rename_group(self, group_id, new_name):
        """重命名分组"""
        if group_id == UNGROUPED_ID:
            return  # 未分组不可改名
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

    def get_group(self, group_id):
        """根据ID获取分组"""
        for g in self.config["groups"]:
            if g["id"] == group_id:
                return g
        return None

    def get_group_color(self, group_id):
        """获取分组的配色字典"""
        group = self.get_group(group_id)
        if group:
            idx = group.get("color_index", 0)
            return PRESET_COLORS[idx % len(PRESET_COLORS)]
        return PRESET_COLORS[0]

    def move_group(self, from_index, to_index):
        """移动分组顺序（未分组固定在第一位，不参与移动）"""
        groups = self.config["groups"]
        if 0 <= from_index < len(groups) and 0 <= to_index < len(groups):
            # 未分组不允许移动
            if groups[from_index]["id"] == UNGROUPED_ID:
                return
            # 不允许移到未分组前面（如果未分组存在且在第0位）
            if len(groups) > 0 and groups[0]["id"] == UNGROUPED_ID and to_index == 0:
                to_index = 1
            item = groups.pop(from_index)
            groups.insert(to_index, item)
            # 确保未分组始终在第一位
            self._ensure_ungrouped_first()
            self.save()

    def _ensure_ungrouped_first(self):
        """确保未分组始终在列表第一位"""
        groups = self.config["groups"]
        ungrouped_idx = -1
        for i, g in enumerate(groups):
            if g["id"] == UNGROUPED_ID:
                ungrouped_idx = i
                break
        if ungrouped_idx > 0:
            item = groups.pop(ungrouped_idx)
            groups.insert(0, item)

    # ---- 未分组管理 ----
    def _get_or_create_ungrouped(self):
        """获取或创建未分组（仅内部数据用，不显示在groups列表头部）"""
        for g in self.config["groups"]:
            if g["id"] == UNGROUPED_ID:
                return g
        ungrouped = {
            "id": UNGROUPED_ID,
            "name": UNGROUPED_NAME,
            "color_index": 7,  # 岩石灰
            "shortcuts": []
        }
        self.config["groups"].insert(0, ungrouped)
        return ungrouped

    def get_ungrouped(self):
        """获取未分组，不存在返回None"""
        for g in self.config["groups"]:
            if g["id"] == UNGROUPED_ID:
                return g
        return None

    # ---- dokodemo ----
    def add_shortcut_to_ungrouped(self, shortcut_path, display_name):
        """添加快捷方式到未分组"""
        ungrouped = self._get_or_create_ungrouped()
        # 避免重复
        for s in ungrouped["shortcuts"]:
            if s["path"] == shortcut_path:
                return
        ungrouped["shortcuts"].append({
            "path": shortcut_path,
            "name": display_name
        })
        self.save()

    def remove_shortcut(self, group_id, shortcut_path):
        """从分组中移除快捷方式"""
        group = self.get_group(group_id)
        if group:
            group["shortcuts"] = [s for s in group["shortcuts"] if s["path"] != shortcut_path]
            self.save()

    def move_shortcut(self, from_group_id, from_index, to_group_id, to_index):
        """移动快捷方式（可跨分组）"""
        from_group = self.get_group(from_group_id)
        to_group = self.get_group(to_group_id)
        if not from_group or not to_group:
            return
        shortcuts = from_group.get("shortcuts", [])
        if from_index < 0 or from_index >= len(shortcuts):
            return
        item = shortcuts.pop(from_index)
        to_shortcuts = to_group.get("shortcuts", [])
        if to_index < 0 or to_index > len(to_shortcuts):
            to_index = len(to_shortcuts)
        to_shortcuts.insert(to_index, item)
        self.save()

    def reorder_shortcuts_in_group(self, group_id, shortcut_paths):
        """按给定路径列表重排分组内的快捷方式"""
        group = self.get_group(group_id)
        if not group:
            return
        existing = {s["path"]: s for s in group["shortcuts"]}
        new_list = []
        for path in shortcut_paths:
            if path in existing:
                new_list.append(existing[path])
        # 把没在列表里的补到后面
        for s in group["shortcuts"]:
            if s["path"] not in set(shortcut_paths):
                new_list.append(s)
        group["shortcuts"] = new_list
        self.save()

    def sync_shortcuts(self, shortcut_paths_with_names):
        """
        同步文件夹中的快捷方式
        shortcut_paths_with_names: [(path, display_name), ...]
        返回新增和删除的数量
        """
        ungrouped = self._get_or_create_ungrouped()
        existing_paths = set()

        # 收集所有分组中已有的快捷方式路径
        for g in self.config["groups"]:
            for s in g.get("shortcuts", []):
                existing_paths.add(s["path"])

        current_paths = {path for path, _ in shortcut_paths_with_names}

        # 新增的放到未分组
        added = 0
        for path, name in shortcut_paths_with_names:
            if path not in existing_paths:
                ungrouped["shortcuts"].append({"path": path, "name": name})
                added += 1

        # 删除已不存在的
        removed = 0
        for g in self.config["groups"]:
            before = len(g["shortcuts"])
            g["shortcuts"] = [s for s in g["shortcuts"] if s["path"] in current_paths]
            removed += before - len(g["shortcuts"])

        self.save()
        return added, removed
