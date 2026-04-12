# Astrbot-Launcher-WSL

[English](./README_en.md) | [中文](./README_zh.md)

---

## 项目简介 | Project Overview

Astrbot-Launcher-WSL 是一款运行在 Windows 上的图形化管理工具，用于通过 WSL (Windows Subsystem for Linux) 启动和管理 AstrBot QQ 机器人服务。

Astrbot-Launcher-WSL is a Windows GUI application designed to launch and manage the AstrBot QQ bot service running under WSL (Windows Subsystem for Linux).

## 功能特点 | Features

| 功能 / Feature | 描述 / Description |
|---------------|-------------------|
| 一键启动 / One-Click Launch | 同时启动 NapCat QQ机器人 和 AstrBot 服务 |
| 进程监控 / Process Monitor | 实时监控服务运行状态 |
| WSL 管理 / WSL Management | 支持关闭/重启 WSL 实例 |
| 路径自动检测 / Auto-Detection | 自动检测 WSL 中的服务安装路径 |
| 日志查看 / Log Viewer | 一键打开实时日志终端 |
| 数据管理 / Data Management | 快速访问数据目录 |

## 系统要求 | Requirements

- Windows 10/11 with WSL installed
- WSL2 recommended
- Python 3.8+ (if running from source)
- AstrBot & NapCat installed in WSL

## 快速开始 | Quick Start

### 下载运行 / Download & Run

前往 [Releases](https://github.com/your-repo/Astrbot-Launcher-WSL/releases) 下载最新版本的 `Astrbot-Launcher-WSL.exe` 并直接运行。

Download the latest `Astrbot-Launcher-WSL.exe` from [Releases](https://github.com/your-repo/Astrbot-Launcher-WSL/releases) and run it directly.

### 从源码运行 / Run from Source

```bash
# Clone the repository
git clone https://github.com/your-repo/Astrbot-Launcher-WSL.git
cd Astrbot-Launcher-WSL

# Install dependencies (only tkinter required from stdlib)
# No additional dependencies needed

# Run
python Astrbot-Launcher-WSL.py
```

## 使用说明 | Usage

### 首次配置 / First Setup

1. 打开程序，点击「设置」
2. 填写 WSL 发行版名称（如 `arch`）
3. 点击「获取用户目录」选择或输入用户名
4. 点击「自动检测路径」自动填充 NapCat、AstrBot、Data 目录
5. （可选）填写 QQ 号用于 NapCat 登录
6. 点击「保存设置」

Open the app, click "Settings". Enter your WSL distro name, fetch user directories, auto-detect service paths, and save settings.

### 启动服务 / Starting Services

1. 点击主界面「启动 AstrBot」按钮
2. 等待服务启动（状态指示变为绿色）
3. 点击「打开 WebUI」访问 AstrBot 控制面板

Click "Start AstrBot" on the main interface. Wait for services to start, then access the AstrBot control panel via "Open WebUI".

## 项目结构 | Project Structure

```
Astrbot-Launcher-WSL/
├── Astrbot-Launcher-WSL.py    # Main source code
├── LICENSE                    # MIT License
├── README.md                  # This file
├── README_en.md               # English version
├── README_zh.md               # Chinese version
```

## 开发构建 | Development Build

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --windowed --icon=astrbot.ico --name Astrbot-Launcher-WSL Astrbot-Launcher-WSL.py
```

## 开源协议 | License

本项目基于 [MIT License](./LICENSE) 开源。

This project is open source under the [MIT License](./LICENSE).

## 致谢 | Credits

- [AstrBot](https://github.com/SillyGods/AstrBot) - QQ 机器人框架
- [NapCat](https://github.com/NapNeko/NapCat-QQBot) - QQ 协议客户端

---

[English](./README_en.md) | [中文](./README_zh.md)
