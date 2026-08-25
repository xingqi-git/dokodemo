# dokodemo

一个基于 PyQt5 的桌面快捷方式管理工具，支持分组管理、拖拽排序、自定义图标大小。

## 功能特性

- 📂 扫描指定目录下的 .lnk 快捷方式
- 🗂️ 分组管理，支持拖拽排序快捷方式和分组
- 🎨 8 种预设配色方案
- 🔍 图标大小可调（32px ~ 128px）
- 🖱️ 单击启动快捷方式
- 🪟 无边框自定义窗口，支持最大化/最小化/拖动

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 使用说明

1. 点击「选择目录」，选择存放 .lnk 快捷方式的文件夹
2. 点击「刷新」加载快捷方式，新扫描到的快捷方式会进入「未添加分组」
3. 点击「添加分组」创建自定义分组
4. 拖拽快捷方式到不同分组中进行分类
5. 拖动分组标题栏可调整分组顺序
6. 右键分组标题可重命名、更换配色、删除分组
7. 拖动「图标大小」滑块调整图标尺寸

## 项目结构

```
dokodemo/
├── main.py              # 程序入口
├── config.json          # 配置文件
├── requirements.txt     # 依赖列表
├── hooks/               # PyInstaller 打包钩子
└── src/
    ├── main_window.py   # 主窗口
    ├── app_icon.py      # 应用图标
    ├── config.py        # 配置管理
    ├── shortcut.py      # 快捷方式扫描与图标提取
    ├── shortcut_item.py # 单个快捷方式组件
    ├── group_widget.py  # 分组组件
    ├── groups_container.py  # 分组容器
    ├── flow_layout.py   # 流式布局
    └── styles.py        # 全局样式
```
