# -*- coding: utf-8 -*-
"""版本号单一来源（Single Source of Truth）。

- dokodemo.spec 动态读取此常量，生成 exe 的 Windows 版本资源
  （右键属性 → 详细信息）
- 程序内"关于"等界面也引用这里，保证全项目版本一致
- 升版只改 APP_VERSION 一行，Windows 四段式：主版本.次版本.修订号.内部版本号
"""
APP_VERSION = "1.0.0.0"
