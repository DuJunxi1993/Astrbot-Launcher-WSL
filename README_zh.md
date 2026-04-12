# Astrbot-Launcher-WSL

[English](./README_en.md) | [中文](./README_zh.md)

---

## 项目简介

Astrbot-Launcher-WSL 是一款运行在 Windows 上的图形化管理工具，用于通过 WSL (Windows Subsystem for Linux) 启动和管理 AstrBot QQ 机器人服务。

## 功能特点

| 功能 | 描述 |
|------|------|
| 一键启动 | 同时启动 NapCat QQ机器人和 AstrBot 服务 |
| 进程监控 | 实时监控服务运行状态 |
| WSL 管理 | 支持关闭/重启 WSL 实例 |
| 路径自动检测 | 自动检测 WSL 中的服务安装路径 |
| 日志查看 | 一键打开实时日志终端 |
| 数据管理 | 快速访问数据目录 |

## 系统要求

- Windows 10/11 已安装 WSL
- 推荐使用 WSL2
- Python 3.8+（如需从源码运行）
- WSL 中已安装 AstrBot 和 NapCat

## 快速开始

### 下载运行

前往 [Releases](https://github.com/your-repo/Astrbot-Launcher-WSL/releases) 下载最新版本的 `Astrbot-Launcher-WSL.exe` 并直接运行。

### 从源码运行

```bash
# 克隆仓库
git clone https://github.com/your-repo/Astrbot-Launcher-WSL.git
cd Astrbot-Launcher-WSL

# 运行
python Astrbot-Launcher-WSL.py
```

## 使用说明

### 首次配置

1. 打开程序，点击「设置」
2. 填写 WSL 发行版名称（如 `arch`）
3. 点击「获取用户目录」选择或输入用户名
4. 点击「自动检测路径」自动填充 NapCat、AstrBot、Data 目录
5. （可选）填写 QQ 号用于 NapCat 登录
6. 点击「保存设置」

### 启动服务

1. 点击主界面「启动 AstrBot」按钮
2. 等待服务启动（状态指示变为绿色）
3. 点击「打开 WebUI」访问 AstrBot 控制面板

## 项目结构

```
Astrbot-Launcher-WSL/
├── Astrbot-Launcher-WSL.py    # 主程序源代码
├── astrbot.ico                 # 程序图标
├── LICENSE                    # MIT 许可证
├── README.md                  # 主文件（双语）
├── README_en.md               # 英文版本
├── README_zh.md               # 中文版本
└── .github/
    └── workflows/
        └── build.yml          # CI/CD 工作流
```

## 开发构建

```bash
# 安装 PyInstaller
pip install pyinstaller

# 构建可执行文件
pyinstaller --onefile --windowed --icon=astrbot.ico --name Astrbot-Launcher-WSL Astrbot-Launcher-WSL.py
```

## 开源协议

本项目基于 [MIT License](./LICENSE) 开源。

## 致谢

- [AstrBot](https://github.com/SillyGods/AstrBot) - QQ 机器人框架
- [NapCat](https://github.com/NapNeko/NapCat-QQBot) - QQ 协议客户端

---

[English](./README_en.md) | [中文](./README_zh.md)
