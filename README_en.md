# Astrbot-Launcher-WSL

[English](./README_en.md) | [中文](./README_zh.md)

---

## Project Overview

Astrbot-Launcher-WSL is a Windows GUI application designed to launch and manage the AstrBot QQ bot service running under WSL (Windows Subsystem for Linux).

## Features

| Feature | Description |
|---------|-------------|
| One-Click Launch | Start both NapCat QQ bot and AstrBot services simultaneously |
| Process Monitor | Real-time monitoring of service status |
| WSL Management | Support for shutting down/restarting WSL instances |
| Auto-Detection | Automatically detect service installation paths in WSL |
| Log Viewer | One-click access to real-time log terminal |
| Data Management | Quick access to data directories |

## Requirements

- Windows 10/11 with WSL installed
- WSL2 recommended
- Python 3.8+ (if running from source)
- AstrBot & NapCat installed in WSL

## Quick Start

### Download & Run

Download the latest `Astrbot-Launcher-WSL.exe` from [Releases](https://github.com/your-repo/Astrbot-Launcher-WSL/releases) and run it directly.

### Run from Source

```bash
# Clone the repository
git clone https://github.com/your-repo/Astrbot-Launcher-WSL.git
cd Astrbot-Launcher-WSL

# Run
python Astrbot-Launcher-WSL.py
```

## Usage

### First Setup

1. Open the app, click "Settings"
2. Enter your WSL distro name (e.g., `arch`)
3. Click "Fetch User Directory" to select or input username
4. Click "Auto-Detect Paths" to automatically fill NapCat, AstrBot, and Data paths
5. (Optional) Enter QQ number for NapCat login
6. Click "Save Settings"

### Starting Services

1. Click "Start AstrBot" on the main interface
2. Wait for services to start (status indicator turns green)
3. Click "Open WebUI" to access AstrBot control panel

## Project Structure

```
Astrbot-Launcher-WSL/
├── Astrbot-Launcher-WSL.py    # Main source code
├── astrbot.ico                 # Application icon
├── LICENSE                    # MIT License
├── README.md                  # Main file (bilingual)
├── README_en.md               # English version
├── README_zh.md               # Chinese version
└── .github/
    └── workflows/
        └── build.yml          # CI/CD workflow
```

## Development Build

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --windowed --icon=astrbot.ico --name Astrbot-Launcher-WSL Astrbot-Launcher-WSL.py
```

## License

This project is open source under the [MIT License](./LICENSE).

## Credits

- [AstrBot](https://github.com/SillyGods/AstrBot) - QQ Bot Framework
- [NapCat](https://github.com/NapNeko/NapCat-QQBot) - QQ Protocol Client

---

[English](./README_en.md) | [中文](./README_zh.md)
