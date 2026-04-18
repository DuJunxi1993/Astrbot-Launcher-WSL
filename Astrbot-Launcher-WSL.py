"""
Astrbot WSL Launcher - AstrBot QQ机器人的WSL图形化管理工具

功能：
- 一键启动/关闭 NapCat 和 AstrBot 服务
- 进程监控，自动检测服务运行状态
- WSL 实例管理（关机、重启）
- 自动检测服务路径
- 查看日志终端
- 打开 WebUI 管理界面
- 开机自启设置
"""

import tkinter as tk
import tkinter.ttk as ttk
import subprocess
import threading
import webbrowser
import os
import json
import sys
import re
import time
from ctypes import windll, byref, sizeof, c_int
from typing import Optional, Callable


# ==================== 全局常量 ====================
# Windows DWM 窗口圆角属性常量
DWMWA_WINDOW_CORNER_PREFERENCE = 33  # DWM窗口圆角偏好属性
DWMWCP_ROUND = 2                      # 圆角大小
DEFAULT_MONITOR_INTERVAL = 5          # 默认进程监控间隔（秒）
DEFAULT_DISTRO = "archlinux"               # 默认 WSL 发行版
DEFAULT_USER = "username"              # 默认 WSL 用户
WEBUI_PORT = 6185                    # WebUI 默认端口


# ==================== 设置管理类 ====================
class SettingsManager:
    """
    设置管理器，负责从 JSON 文件加载和保存用户配置
    使用线程锁确保多线程访问安全
    """

    def __init__(self):
        self._lock = threading.Lock()  # 线程安全锁
        # 设置文件路径：%APPDATA%/AstrBotManager/settings.json
        self.settings_file = os.path.join(
            os.environ.get("APPDATA", "."), "AstrBotManager", "settings.json"
        )
        # 默认配置项
        self.settings: dict = {
            "startup": False,               # 开机自启
            "minimize_to_tray": False,      # 最小化到托盘
            "process_monitor": False,        # 启用进程监控
            "monitor_interval": DEFAULT_MONITOR_INTERVAL,  # 监控间隔
            "wsl_distro": DEFAULT_DISTRO,    # WSL 发行版名称
            "wsl_user": DEFAULT_USER,        # WSL 用户名
            "data_folder": "",              # 数据目录路径
            "napcat_path": "",              # NapCat 可执行文件路径
            "astrbot_path": "",             # AstrBot 路径
            "qq_number": "",                # QQ 号（可选）
        }
        self.load()

    def load(self) -> None:
        """从 JSON 文件加载设置"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
        except (json.JSONDecodeError, OSError, PermissionError):
            pass

    def save(self) -> None:
        """保存设置到 JSON 文件"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except (OSError, PermissionError):
            pass

    def set(self, key: str, value) -> None:
        """设置配置项（带线程安全）"""
        with self._lock:
            self.settings[key] = value
        self.save()

    def get(self, key: str, default=None):
        """获取配置项（带线程安全）"""
        with self._lock:
            return self.settings.get(key, default)


# ==================== 工具函数 ====================
def hex_to_rgb(h: str) -> tuple:
    """将十六进制颜色转换为 RGB 元组"""
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def lerp_color(a: tuple, b: tuple, t: float) -> str:
    """
    颜色线性插值
    a: 起始颜色 RGB
    b: 目标颜色 RGB
    t: 插值系数 [0, 1]
    """
    return "#{:02x}{:02x}{:02x}".format(
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def is_valid_wsl_name(name: str) -> bool:
    """验证 WSL 发行版/用户名是否合法（仅字母数字下划线）"""
    return bool(re.match(r"^[a-zA-Z0-9_-]+$", name))


# ==================== 自定义按钮组件 ====================
class FluentButton(tk.Frame):
    """
    扁平化风格按钮组件，支持鼠标悬停动画效果
    继承自 tk.Frame，可作为容器放置在其他父组件中
    """

    def __init__(
        self,
        parent,
        text: str,
        command: Optional[Callable],
        primary: bool = False,
        height: Optional[int] = None,
        **kw,
    ):
        """
        初始化按钮
        :param parent: 父组件
        :param text: 按钮文本
        :param command: 点击回调函数
        :param primary: 是否为主要按钮（蓝色主题）
        :param height: 固定高度（像素）
        """
        # 根据是否为 primary 设置颜色方案
        if primary:
            self._bg = "#0078d4"
            self._hover = "#106ebe"
            self._press = "#005a9e"
            self._fg = "white"
            self._bd_col = "#005a9e"
        else:
            self._bg = "#f9f9f9"
            self._hover = "#ebebeb"
            self._press = "#e0e0e0"
            self._fg = "#1c1c1c"
            self._bd_col = "#d1d1d1"

        super().__init__(parent, bg=self._bd_col, padx=1, pady=1)
        self._primary = primary
        self._command = command
        self._animating = False
        self._current_bg = hex_to_rgb(self._bg)
        self._custom_height = height

        # 内部 Label 作为按钮显示
        self._btn = tk.Label(
            self,
            text=text,
            font=("Segoe UI Variable", 9),
            fg=self._fg,
            bg=self._bg,
            cursor="hand2",
            anchor="center",
        )
        self._btn.pack(fill=tk.BOTH, expand=True, ipady=2)

        if height is not None:
            self.pack_propagate(False)
            self.configure(height=height)

        # 绑定鼠标事件
        for w in (self, self._btn):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<ButtonPress-1>", self._on_press)
            w.bind("<ButtonRelease-1>", self._on_release)

    def configure_text(
        self, text: Optional[str] = None, fg=None, bg=None, bd_col=None, **kw
    ):
        """动态更新按钮样式"""
        if text is not None:
            self._btn.configure(text=text)
        if fg is not None:
            self._fg = fg
            self._btn.configure(fg=fg)
        if bg is not None:
            self._bg = bg
            self._btn.configure(bg=bg)
            self._current_bg = hex_to_rgb(bg)
        if bd_col is not None:
            self._bd_col = bd_col
            self.configure(bg=bd_col)

    def _animate(self, target_hex: str, steps: int = 4, interval: int = 12) -> None:
        """颜色渐变动画"""
        start = self._current_bg
        target = hex_to_rgb(target_hex)
        self._animating = True

        def step(i: int):
            if not self._animating:
                return
            t = i / steps
            color = lerp_color(start, target, t)
            try:
                self._btn.configure(bg=color)
            except tk.TclError:
                return
            if i < steps:
                self._btn.after(interval, lambda: step(i + 1))
            else:
                self._current_bg = target
                self._animating = False

        step(1)

    def _on_enter(self, e) -> None:
        """鼠标进入事件"""
        self._animating = False
        self._animate(self._hover)

    def _on_leave(self, e) -> None:
        """鼠标离开事件"""
        self._animating = False
        self._animate(self._bg)

    def _on_press(self, e) -> None:
        """鼠标按下事件"""
        if getattr(self, "_command_enabled", True):
            self._animating = False
            self._btn.configure(bg=self._press)
            self._current_bg = hex_to_rgb(self._press)

    def _on_release(self, e) -> None:
        """鼠标释放事件"""
        if getattr(self, "_command_enabled", True):
            self._animate(self._hover)
            if self._command:
                self._command()

    def set_state(self, state: str) -> None:
        """
        设置按钮状态
        :param state: "normal" 或 "disabled"
        """
        cursor = "hand2" if state == "normal" else "arrow"
        self._btn.configure(cursor=cursor)
        if state == "disabled":
            self._btn.configure(bg="#e8e8e8", fg="#a0a0a0")
        else:
            self._btn.configure(bg=self._bg, fg=self._fg)
            self._current_bg = hex_to_rgb(self._bg)
        self._command_enabled = state == "normal"


# ==================== 主应用程序类 ====================
class AstrBotManager:
    """
    AstrBot 管理器主类
    管理所有 UI 组件和业务逻辑
    """

    # UI 颜色主题常量
    BG = "#f3f3f3"       # 背景色
    CARD = "#ffffff"      # 卡片背景色
    BORDER = "#e5e5e5"   # 边框色
    TEXT = "#1c1c1c"     # 主文字色
    TEXT2 = "#767676"    # 次要文字色
    ACCENT = "#0078d4"   # 强调色（蓝色）
    GREEN = "#107c10"    # 绿色（运行中）
    ORANGE = "#ff8c00"   # 橙色（部分运行）
    RED = "#c42b1c"      # 红色（错误/停止）
    GRAY = "#8a8a8a"     # 灰色（未运行）

    def __init__(self, root: tk.Tk):
        """初始化主窗口"""
        self.root = root
        self.settings = SettingsManager()

        # 窗口基本配置
        self.root.title("Astrbot WSL Launcher")
        self.root.geometry("340x400")
        self.root.resizable(True, True)
        self.root.minsize(320, 340)
        self.root.configure(bg=self.BG)

        # 运行状态标志
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitor = False
        self.settings_window: Optional[tk.Toplevel] = None

        self._apply_win11_style()
        self.setup_ui()

        # 根据设置决定是否启用自启和监控
        if self.settings.get("startup"):
            self.enable_startup()

        if self.settings.get("process_monitor"):
            self.start_process_monitor()

    def _apply_win11_style(self) -> None:
        """应用 Windows 11 窗口圆角风格"""
        try:
            self.root.update_idletasks()
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                byref(c_int(DWMWCP_ROUND)),
                sizeof(c_int),
            )
        except Exception:
            pass

    def _create_card(self, parent, height: Optional[int] = None, **pack_kw) -> tk.Frame:
        """
        创建卡片容器（通用组件）
        :param parent: 父组件
        :param height: 固定高度（可选）
        :return: 内层 Frame（可用于放置内容）
        """
        card = tk.Frame(
            parent,
            bg=self.CARD,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )
        card.pack(**pack_kw)
        if height is not None:
            card.pack_propagate(False)
            card.configure(height=height)
        inner = tk.Frame(card, bg=self.CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        return inner

    def _create_settings_card(self, parent, **pack_kw) -> tk.Frame:
        """
        创建设置页面的卡片容器（内边距较小）
        """
        card = tk.Frame(
            parent,
            bg=self.CARD,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )
        card.pack(**pack_kw)
        inner = tk.Frame(card, bg=self.CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        return inner

    def setup_ui(self) -> None:
        """初始化主界面 UI"""
        # 状态栏卡片
        status_inner = self._create_card(self.root, fill=tk.X, padx=12, pady=(12, 6))

        # 状态指示圆点
        self.status_dot = tk.Canvas(
            status_inner,
            width=10,
            height=10,
            bg=self.CARD,
            highlightthickness=0,
        )
        self.status_dot.pack(side=tk.LEFT, padx=(0, 8))
        self.status_dot_id = self.status_dot.create_oval(
            1, 1, 9, 9, fill=self.GRAY, outline=""
        )

        # 状态文字
        self.status_text = tk.Label(
            status_inner,
            text="就绪",
            font=("Segoe UI Variable", 10),
            fg=self.TEXT2,
            bg=self.CARD,
            anchor="w",
        )
        self.status_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 按钮区域（三列布局）
        btn_area = tk.Frame(self.root, bg=self.BG)
        btn_area.pack(fill=tk.X, padx=12, pady=6)

        col0 = tk.Frame(btn_area, bg=self.BG)
        col0.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        col1 = tk.Frame(btn_area, bg=self.BG)
        col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        col2 = tk.Frame(btn_area, bg=self.BG)
        col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 启动/关闭按钮（主要按钮）
        self.btn_start = FluentButton(
            col0, "启动 AstrBot", self.toggle_astrbot, primary=True
        )
        self.btn_start.pack(fill=tk.BOTH, expand=True)
        self.btn_start._btn.configure(pady=14)

        # 查看日志按钮
        self.btn_log = FluentButton(col1, "查看日志", self.open_log_terminal)
        self.btn_log.pack(fill=tk.X, pady=(0, 4))
        self.btn_log._btn.configure(pady=8)

        # 关闭 WSL 按钮
        self.btn_shutdown = FluentButton(col1, "关闭 WSL", self.shutdown_wsl)
        self.btn_shutdown.pack(fill=tk.X)
        self.btn_shutdown._btn.configure(pady=8)

        # 打开 WebUI 按钮
        self.btn_webui = FluentButton(col2, "打开 WebUI", self.open_webui)
        self.btn_webui.pack(fill=tk.X, pady=(0, 4))
        self.btn_webui._btn.configure(pady=8)

        # 设置按钮
        self.btn_settings_btn = FluentButton(col2, "设置", self.open_settings)
        self.btn_settings_btn.pack(fill=tk.X)
        self.btn_settings_btn._btn.configure(pady=8)

        # 日志显示区域
        log_card = tk.Frame(
            self.root,
            bg=self.CARD,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )
        log_card.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))

        log_inner = tk.Frame(log_card, bg=self.CARD)
        log_inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        self.info_area = tk.Text(
            log_inner,
            font=("Cascadia Code", 8),
            fg=self.TEXT2,
            bg=self.CARD,
            relief="flat",
            state="disabled",
            wrap=tk.WORD,
        )
        self.info_area.pack(fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(log_inner, command=self.info_area.yview, width=10)
        self.info_area.configure(yscrollcommand=sb.set)

        self.append_info("Astrbot WSL Launcher 已启动\n")
        self.append_info("提示: 请先在设置中配置 WSL 和路径信息\n")

    def _make_labeled_entry(self, parent, label: str, var, width: int = 25):
        """
        创建带标签的输入框组件
        :param parent: 父组件
        :param label: 标签文字
        :param var: tk.StringVar 变量
        """
        row = tk.Frame(parent, bg=self.CARD)
        row.pack(fill=tk.X, pady=2)
        tk.Label(
            row,
            text=label,
            font=("Segoe UI Variable", 9),
            fg=self.TEXT2,
            bg=self.CARD,
            width=14,
            anchor="w",
        ).pack(side=tk.LEFT)
        entry_frame = tk.Frame(row, bg=self.BORDER, padx=1, pady=1)
        entry_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry = tk.Entry(
            entry_frame,
            textvariable=var,
            font=("Segoe UI Variable", 9),
            bg=self.CARD,
            fg=self.TEXT,
            relief="flat",
            insertbackground=self.TEXT,
        )
        entry.pack(fill=tk.X, ipady=3)
        return entry

    def _make_dropdown_row(self, parent, label: str, var, values):
        """创建带标签的下拉框组件"""
        row = tk.Frame(parent, bg=self.CARD)
        row.pack(fill=tk.X, pady=2)
        tk.Label(
            row,
            text=label,
            font=("Segoe UI Variable", 9),
            fg=self.TEXT2,
            bg=self.CARD,
            width=14,
            anchor="w",
        ).pack(side=tk.LEFT)

        container = tk.Frame(row, bg=self.CARD)
        container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        dropdown = ttk.Combobox(
            container,
            textvariable=var,
            values=list(values) if values else [],
            font=("Segoe UI Variable", 9),
            state="readonly",
        )
        dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        return dropdown

    def _make_button_in_row(self, parent, text: str, command: Callable):
        """创建行内小按钮"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI Variable", 9),
            bg=self.ACCENT,
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=2,
        )
        btn.pack(side=tk.LEFT, padx=(4, 0))
        return btn

    # ==================== 设置页面各区块 ====================
    def _create_wsl_config_section(self, parent) -> None:
        """创建设置页面 - WSL 配置区块"""
        wsl_card = self._create_settings_card(parent, fill=tk.X, pady=(0, 8))
        tk.Label(
            wsl_card,
            text="WSL 配置",
            font=("Segoe UI Variable", 10, "bold"),
            fg=self.TEXT,
            bg=self.CARD,
        ).pack(anchor="w", pady=(0, 4))

        self.var_wsl_distro = tk.StringVar(
            value=self.settings.get("wsl_distro", DEFAULT_DISTRO)
        )
        self.var_wsl_user = tk.StringVar(value=self.settings.get("wsl_user", ""))

        # 发行版输入框
        distro_row = tk.Frame(wsl_card, bg=self.CARD)
        distro_row.pack(fill=tk.X, pady=1)
        tk.Label(
            distro_row,
            text="WSL 发行版:",
            font=("Segoe UI Variable", 9),
            fg=self.TEXT2,
            bg=self.CARD,
            width=14,
            anchor="w",
        ).pack(side=tk.LEFT)
        distro_entry_frame = tk.Frame(distro_row, bg=self.BORDER, padx=1, pady=1)
        distro_entry_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        distro_entry = tk.Entry(
            distro_entry_frame,
            textvariable=self.var_wsl_distro,
            font=("Segoe UI Variable", 9),
            bg=self.CARD,
            fg=self.TEXT,
            relief="flat",
            insertbackground=self.TEXT,
        )
        distro_entry.pack(fill=tk.X, ipady=3)

        # 用户目录下拉框
        user_row = tk.Frame(wsl_card, bg=self.CARD)
        user_row.pack(fill=tk.X, pady=1)
        tk.Label(
            user_row,
            text="用户目录:",
            font=("Segoe UI Variable", 9),
            fg=self.TEXT2,
            bg=self.CARD,
            width=14,
            anchor="w",
        ).pack(side=tk.LEFT)

        user_container = tk.Frame(user_row, bg=self.CARD)
        user_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        dropdown_frame = tk.Frame(user_container, bg=self.BORDER, padx=1, pady=1)
        dropdown_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._user_dropdown = ttk.Combobox(
            dropdown_frame,
            textvariable=self.var_wsl_user,
            font=("Segoe UI Variable", 9),
            state="readonly",
        )
        self._user_dropdown.pack(fill=tk.X, ipady=2)

        # 获取用户目录按钮
        get_users_btn = FluentButton(
            user_container,
            "获取用户目录",
            self._fetch_wsl_users,
            primary=False,
        )
        get_users_btn.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        get_users_btn._btn.configure(pady=8)

    def _create_path_config_section(self, parent) -> None:
        """创建设置页面 - 服务路径配置区块"""
        path_card = self._create_settings_card(parent, fill=tk.X, pady=(0, 8))
        tk.Label(
            path_card,
            text="服务路径",
            font=("Segoe UI Variable", 10, "bold"),
            fg=self.TEXT,
            bg=self.CARD,
        ).pack(anchor="w", pady=(0, 4))

        self.var_data_folder = tk.StringVar(value=self.settings.get("data_folder", ""))
        self.var_napcat_path = tk.StringVar(value=self.settings.get("napcat_path", ""))
        self.var_astrbot_path = tk.StringVar(
            value=self.settings.get("astrbot_path", "")
        )
        self.var_qq_number = tk.StringVar(value=self.settings.get("qq_number", ""))

        self._make_labeled_entry(path_card, "Data 目录:", self.var_data_folder)
        self._make_labeled_entry(path_card, "NapCat 路径:", self.var_napcat_path)
        self._make_labeled_entry(path_card, "AstrBot 路径:", self.var_astrbot_path)
        self._make_labeled_entry(path_card, "QQ 号 (可选):", self.var_qq_number)

        # 自动检测路径按钮
        detect_btn = FluentButton(
            path_card,
            "自动检测路径",
            self._auto_detect_paths,
            primary=False,
        )
        detect_btn.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        detect_btn._btn.configure(pady=8)

    def _create_options_section(self, parent) -> None:
        """创建设置页面 - 选项区块（开机自启、进程监控）"""
        opt_card = self._create_settings_card(parent, fill=tk.X, pady=(0, 8))
        tk.Label(
            opt_card,
            text="选项",
            font=("Segoe UI Variable", 10, "bold"),
            fg=self.TEXT,
            bg=self.CARD,
        ).pack(anchor="w", pady=(0, 4))

        self.var_startup = tk.BooleanVar(value=self.settings.get("startup"))
        self.var_monitor = tk.BooleanVar(value=self.settings.get("process_monitor"))

        chk_style = dict(
            font=("Segoe UI Variable", 10),
            fg=self.TEXT,
            bg=self.CARD,
            activeforeground=self.TEXT,
            activebackground=self.CARD,
            selectcolor=self.CARD,
            cursor="hand2",
        )

        # 开机自启复选框
        tk.Checkbutton(
            opt_card,
            text="开机自启",
            variable=self.var_startup,
            command=self.on_startup_changed,
            **chk_style,
        ).pack(anchor="w", pady=1)

        # 进程监控复选框 + 间隔设置
        mon_row = tk.Frame(opt_card, bg=self.CARD)
        mon_row.pack(anchor="w", pady=1)
        tk.Checkbutton(
            mon_row,
            text="启用进程监控",
            variable=self.var_monitor,
            command=self.on_monitor_changed,
            **chk_style,
        ).pack(side=tk.LEFT)
        spin_frame = tk.Frame(mon_row, bg=self.BORDER, padx=1, pady=1)
        spin_frame.pack(side=tk.LEFT, padx=(6, 0))
        self.interval_spin = tk.Spinbox(
            spin_frame,
            from_=1,
            to=60,
            width=3,
            font=("Segoe UI Variable", 9),
            bg=self.CARD,
            fg=self.TEXT,
            relief="flat",
            buttonbackground=self.CARD,
        )
        self.interval_spin.pack(fill=tk.X, ipady=1)
        self.interval_spin.delete(0, tk.END)
        self.interval_spin.insert(
            0, str(self.settings.get("monitor_interval", DEFAULT_MONITOR_INTERVAL))
        )
        self.interval_spin.bind("<<Spinbox>>", self.on_interval_changed)
        tk.Label(
            mon_row,
            text="秒",
            font=("Segoe UI Variable", 9),
            fg=self.TEXT2,
            bg=self.CARD,
        ).pack(side=tk.LEFT, padx=(3, 0))

    def _create_action_buttons(self, parent) -> None:
        """创建设置页面 - 操作按钮区块"""
        act_card = self._create_settings_card(parent, fill=tk.X, pady=(0, 6))
        btn_row = tk.Frame(act_card, bg=self.CARD)
        btn_row.pack(fill=tk.X)
        for text, cmd in [
            ("保存设置", self._save_settings),
            ("打开数据目录", self.open_data_directory),
            ("一键重启服务", self.restart_services),
        ]:
            b = FluentButton(
                btn_row,
                text,
                cmd,
                primary=False,
            )
            b.pack(side=tk.LEFT, padx=(0, 6))
            b._btn.configure(pady=6)

    def _setup_settings_window_style(self, win: tk.Toplevel) -> None:
        """为设置窗口应用 Windows 11 圆角风格"""
        try:
            win.update_idletasks()
            hwnd = windll.user32.GetParent(win.winfo_id())
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                byref(c_int(DWMWCP_ROUND)),
                sizeof(c_int),
            )
        except Exception:
            pass

    def open_settings(self) -> None:
        """打开设置窗口"""
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return

        win = tk.Toplevel(self.root)
        self.settings_window = win
        win.title("设置")
        win.geometry("460x500")
        win.resizable(False, False)
        win.configure(bg=self.BG)

        self._setup_settings_window_style(win)

        main_frame = tk.Frame(win, bg=self.BG)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        tk.Label(
            main_frame,
            text="设置",
            font=("Segoe UI Variable", 12, "bold"),
            fg=self.TEXT,
            bg=self.BG,
        ).pack(anchor="w", pady=(0, 6))

        # 依次创建各个配置区块
        self._create_wsl_config_section(main_frame)
        self._create_path_config_section(main_frame)
        self._create_options_section(main_frame)
        self._create_action_buttons(main_frame)

        win.protocol("WM_DELETE_WINDOW", win.destroy)

    # ==================== WSL 命令封装 ====================
    def _get_wsl_distros(self) -> list:
        """获取本机已安装的 WSL 发行版列表"""
        try:
            result = subprocess.run(
                ["wsl", "--list", "--quiet"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                output = result.stdout.decode("utf-16-le").strip()
                lines = output.splitlines()
                distros = []
                for line in lines:
                    stripped = line.strip()
                    if stripped and len(stripped) > 1:
                        distros.append(stripped)
                if distros:
                    return list(dict.fromkeys(distros))
        except (subprocess.TimeoutExpired, OSError):
            pass
        return [DEFAULT_DISTRO]

    def _get_wsl_users(self, distro: str) -> list:
        """
        获取指定 WSL 发行版中的用户目录列表
        :param distro: WSL 发行版名称
        :return: 用户名列表
        """
        if not distro or not distro.strip():
            return []
        distro = distro.strip()
        try:
            result = subprocess.run(
                ["wsl", "-d", distro, "bash", "-c", "ls /home/"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                output = result.stdout.decode("utf-8").strip()
                users = []
                for line in output.splitlines():
                    stripped = line.strip()
                    if stripped and stripped != "." and not stripped.startswith("-"):
                        users.append(stripped)
                return users
        except (subprocess.TimeoutExpired, OSError):
            pass
        return []

    def _detect_napcat_path(self, distro: str, user: str) -> str:
        """
        自动检测 NapCat 可执行文件路径
        尝试两种方式：ls glob 匹配和 find 命令
        """
        commands = [
            f"ls /home/{user}/napcat/*.AppImage 2>/dev/null | head -1",
            f"find /home/{user}/napcat -name '*.AppImage' -type f 2>/dev/null | head -1",
        ]
        for cmd in commands:
            try:
                result = subprocess.run(
                    ["wsl", "-d", distro, "bash", "-c", cmd],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0 and result.stdout:
                    return result.stdout.decode("utf-8").strip()
            except (subprocess.TimeoutExpired, OSError):
                continue
        return ""

    def _detect_astrbot_path(self, distro: str, user: str) -> str:
        """
        自动检测 AstrBot 可执行文件路径
        优先使用 which 命令，失败则检查默认位置
        """
        try:
            result = subprocess.run(
                ["wsl", "-d", distro, "bash", "-c", "which astrbot"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout:
                path = result.stdout.decode("utf-8").strip()
                if path and path != "which":
                    return path
        except (subprocess.TimeoutExpired, OSError):
            pass
        fallback = f"/home/{user}/.local/bin/astrbot"
        try:
            result = subprocess.run(
                [
                    "wsl",
                    "-d",
                    distro,
                    "bash",
                    "-c",
                    f"test -f {fallback} && echo {fallback}",
                ],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.decode("utf-8").strip()
        except (subprocess.TimeoutExpired, OSError):
            pass
        return fallback

    def _detect_data_folder(self, distro: str, user: str) -> str:
        """检测 Data 目录路径"""
        return f"/home/{user}/data"

    def _fetch_wsl_users(self) -> None:
        """从设置页面获取 WSL 用户列表"""
        distro = self.var_wsl_distro.get().strip()
        if not distro:
            self.append_info("请先填写 WSL 发行版\n")
            return

        self.append_info(f"正在获取 {distro} 的用户目录...\n")
        users = self._get_wsl_users(distro)

        if users:
            if hasattr(self, "_user_dropdown") and self._user_dropdown:
                self._user_dropdown["values"] = users
                self._user_dropdown.set(users[0])
            else:
                self.var_wsl_user.set(users[0])
            self.append_info(f"已找到用户: {', '.join(users)}\n")
        else:
            self.append_info(f"未找到用户目录，请手动输入\n")

    def _auto_detect_paths(self) -> None:
        """自动检测所有服务路径"""
        distro = self.var_wsl_distro.get().strip()
        user = self.var_wsl_user.get().strip()

        if not distro or not user:
            self.append_info("请先填写发行版和选择用户目录\n")
            return

        self.append_info(f"正在检测 {distro}:/{user} 下的路径...\n")

        data_folder = self._detect_data_folder(distro, user)
        napcat_path = self._detect_napcat_path(distro, user)
        astrbot_path = self._detect_astrbot_path(distro, user)

        self.var_data_folder.set(data_folder)
        self.var_napcat_path.set(napcat_path)
        self.var_astrbot_path.set(astrbot_path)

        self.append_info(f"Data: {data_folder}\n")
        self.append_info(f"NapCat: {napcat_path or '未找到'}\n")
        self.append_info(f"AstrBot: {astrbot_path}\n")

    def _save_settings(self) -> None:
        """保存设置到配置文件"""
        self.settings.set("wsl_distro", self.var_wsl_distro.get())
        self.settings.set("wsl_user", self.var_wsl_user.get())
        self.settings.set("data_folder", self.var_data_folder.get())
        self.settings.set("napcat_path", self.var_napcat_path.get())
        self.settings.set("astrbot_path", self.var_astrbot_path.get())
        self.settings.set("qq_number", self.var_qq_number.get())
        self.append_info("设置已保存\n")
        if self.settings_window:
            self.settings_window.destroy()
            self.settings_window = None

    # ==================== 设置回调函数 ====================
    def on_startup_changed(self) -> None:
        """开机自启复选框回调"""
        v = self.var_startup.get()
        self.settings.set("startup", v)
        if v:
            self.enable_startup()
        else:
            self.disable_startup()

    def on_monitor_changed(self) -> None:
        """进程监控复选框回调"""
        v = self.var_monitor.get()
        self.settings.set("process_monitor", v)
        if v:
            self.start_process_monitor()
        else:
            self.stop_process_monitor()

    def on_interval_changed(self, event=None) -> None:
        """监控间隔变化回调"""
        try:
            self.settings.set("monitor_interval", int(self.interval_spin.get()))
        except ValueError:
            pass

    def enable_startup(self) -> None:
        """启用开机自启（写入注册表）"""
        try:
            import winreg

            key = r"Software\Microsoft\Windows\CurrentVersion\Run"
            rk = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE)
            exe = sys.executable
            script = os.path.abspath(sys.argv[0])
            winreg.SetValueEx(
                rk, "AstrBotManager", 0, winreg.REG_SZ, f'"{exe}" "{script}"'
            )
            winreg.CloseKey(rk)
        except Exception as e:
            self.append_info(f"设置开机自启失败: {e}\n")

    def disable_startup(self) -> None:
        """禁用开机自启（删除注册表项）"""
        try:
            import winreg

            key = r"Software\Microsoft\Windows\CurrentVersion\Run"
            rk = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(rk, "AstrBotManager")
            except OSError:
                pass
            winreg.CloseKey(rk)
        except Exception as e:
            self.append_info(f"取消开机自启失败: {e}\n")

    # ==================== 进程监控 ====================
    def start_process_monitor(self) -> None:
        """
        启动进程监控线程
        定期检查 NapCat 和 AstrBot 是否运行
        """
        self.stop_monitor = False
        interval = self.settings.get("monitor_interval", DEFAULT_MONITOR_INTERVAL)

        def monitor():
            while not self.stop_monitor:
                nc = self.check_process("napcat")
                ab = self.check_process("astrbot")
                if nc and ab:
                    s, c = "运行中 (NapCat + AstrBot)", self.GREEN
                elif nc:
                    s, c = "部分运行 (NapCat)", self.ORANGE
                elif ab:
                    s, c = "部分运行 (AstrBot)", self.ORANGE
                else:
                    s, c = "已停止", self.GRAY
                self.root.after(0, lambda s=s, c=c: self.update_status(s, c))
                time.sleep(interval)

        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()

    def stop_process_monitor(self) -> None:
        """停止进程监控"""
        self.stop_monitor = True

    def check_process(self, name: str) -> bool:
        """
        检查指定进程是否在运行
        :param name: 进程名（napcat 或 astrbot）
        """
        try:
            distro = self.settings.get("wsl_distro", DEFAULT_DISTRO)
            r = subprocess.run(
                f"wsl -d {distro} pgrep -f {name}",
                shell=True,
                capture_output=True,
                text=True,
            )
            return r.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False

    # ==================== 服务启动/停止 ====================
    def _build_start_command(self) -> Optional[str]:
        """
        构建服务启动命令
        :return: 完整的 WSL 启动命令字符串
        """
        distro = self.settings.get("wsl_distro", DEFAULT_DISTRO).strip()
        user = self.settings.get("wsl_user", DEFAULT_USER).strip()
        napcat = self.settings.get("napcat_path", "").strip()
        astrbot = self.settings.get("astrbot_path", "").strip()
        qq = self.settings.get("qq_number", "").strip()

        if not napcat or not astrbot:
            self.append_info("错误: 请先配置 NapCat 和 AstrBot 路径\n")
            return None

        if not is_valid_wsl_name(distro) or not is_valid_wsl_name(user):
            self.append_info("错误: WSL 发行版或用户目录名称无效\n")
            return None

        qq_arg = f" -- -q {qq}" if qq else ""
        cmd = f'wsl -d {distro} fish -c "cd /home/{user} && {napcat}{qq_arg} & {astrbot} run"'
        return cmd

    def open_data_directory(self) -> None:
        """通过文件管理器打开数据目录"""
        distro = self.settings.get("wsl_distro", DEFAULT_DISTRO).strip()
        user = self.settings.get("wsl_user", DEFAULT_USER).strip()
        data_folder = self.settings.get("data_folder", "")

        if not data_folder:
            self.append_info("请先配置 Data 目录\n")
            return

        # 将 Linux 路径转换为 Windows 路径
        if data_folder.startswith("/"):
            linux_path = data_folder.strip("/")
            wsl_path = (
                r"\\wsl.localhost"
                + "\\"
                + distro
                + "\\"
                + linux_path.replace("/", "\\")
            )
        else:
            wsl_path = data_folder

        try:
            subprocess.Popen(f'explorer "{wsl_path}"', shell=True)
            self.append_info("已打开数据目录\n")
        except Exception as e:
            self.append_info(f"打开失败: {e}\n")

    def restart_services(self) -> None:
        """重启所有服务"""
        self.append_info("正在重启服务...\n")
        self.update_status("重启中...", self.ACCENT)
        self.btn_start.set_state("disabled")
        self.btn_start.configure_text(text="重启中...")

        def _restart():
            self.stop_process_monitor()
            distro = self.settings.get("wsl_distro", DEFAULT_DISTRO)
            self.run_wsl_command(
                f'wsl -d {distro} bash -c "pkill -f napcat; pkill -f astrbot"',
                wait=True,
            )
            time.sleep(1)
            start_cmd = self._build_start_command()
            if start_cmd:
                self.run_wsl_command(start_cmd, wait=False)
            time.sleep(3)
            self.is_running = True

            def _done():
                self.update_status("运行中 (NapCat + AstrBot)", self.GREEN)
                self._reset_start_button(True)
                self.append_info("服务已重启\n")
                if self.settings.get("process_monitor"):
                    self.start_process_monitor()

            self.root.after(0, _done)

        threading.Thread(target=_restart, daemon=True).start()

    # ==================== UI 更新辅助 ====================
    def append_info(self, message: str) -> None:
        """向日志区域追加消息（线程安全）"""
        def _append():
            self.info_area.configure(state="normal")
            self.info_area.insert(tk.END, message)
            self.info_area.see(tk.END)
            self.info_area.configure(state="disabled")

        self.root.after(0, _append)

    def update_status(self, text: str, color: Optional[str] = None) -> None:
        """更新状态显示（线程安全）"""
        if color is None:
            color = self.GRAY

        def _update():
            self.status_text.configure(text=text, fg=color)
            self.status_dot.itemconfig(self.status_dot_id, fill=color)

        self.root.after(0, _update)

    def run_wsl_command(self, command: str, wait: bool = True):
        """
        执行 WSL 命令
        :param command: 命令字符串
        :param wait: 是否等待执行完成
        """
        try:
            if wait:
                return subprocess.run(
                    command, shell=True, capture_output=True, text=True
                )
            else:
                subprocess.Popen(command, shell=True)
                return None
        except Exception as e:
            self.append_info(f"执行错误: {e}\n")
            return None

    # ==================== 主按钮操作 ====================
    def toggle_astrbot(self) -> None:
        """切换服务运行状态"""
        if self.is_running:
            self.stop_astrbot()
        else:
            self.start_astrbot()

    def start_astrbot(self) -> None:
        """启动 AstrBot 服务"""
        self.append_info("正在启动 AstrBot...\n")
        self.update_status("启动中...", self.ACCENT)
        self.btn_start.set_state("disabled")
        self.btn_start.configure_text(text="启动中...")

        def _start():
            start_cmd = self._build_start_command()
            if not start_cmd:
                self.root.after(0, lambda: self.update_status("配置错误", self.RED))
                self.root.after(0, lambda: self.btn_start.set_state("normal"))
                return

            self.run_wsl_command(start_cmd, wait=False)
            self.append_info("启动命令已发送\n")
            time.sleep(3)
            self.is_running = True

            def _done():
                self.update_status("运行中 (NapCat + AstrBot)", self.GREEN)
                self._reset_start_button(True)
                self.append_info("AstrBot 已启动\n")

            self.root.after(0, _done)
            if self.settings.get("process_monitor"):
                self.start_process_monitor()

        threading.Thread(target=_start, daemon=True).start()

    def stop_astrbot(self) -> None:
        """停止 AstrBot 服务"""
        self.append_info("正在关闭 AstrBot...\n")
        self.update_status("关闭中...", self.ACCENT)
        self.btn_start.set_state("disabled")
        self.btn_start.configure_text(text="关闭中...")

        def _stop():
            self.stop_process_monitor()
            distro = self.settings.get("wsl_distro", DEFAULT_DISTRO)
            self.run_wsl_command(
                f'wsl -d {distro} bash -c "pkill -f napcat; pkill -f astrbot"',
                wait=True,
            )
            self.append_info("AstrBot 和 NapCat 已终止\n")
            self.is_running = False

            def _done():
                self.update_status("已停止", self.GRAY)
                self._reset_start_button(False)
                self.append_info("AstrBot 已关闭\n")

            self.root.after(0, _done)

        threading.Thread(target=_stop, daemon=True).start()

    def shutdown_wsl(self) -> None:
        """关闭 WSL 实例"""
        self.append_info("正在关闭 WSL...\n")
        self.update_status("关闭中...", self.ACCENT)

        def _shutdown():
            self.stop_process_monitor()
            distro = self.settings.get("wsl_distro", DEFAULT_DISTRO)
            if self.is_running:
                self.run_wsl_command(
                    f'wsl -d {distro} bash -c "pkill -f napcat; pkill -f astrbot"',
                    wait=True,
                )
            self.is_running = False
            result = self.run_wsl_command("wsl --shutdown", wait=True)
            if result and result.returncode == 0:
                self.root.after(0, lambda: self.append_info("WSL 已关闭\n"))
                self.root.after(0, lambda: self.update_status("WSL 已关闭", self.GRAY))
                self.root.after(0, lambda: self._reset_start_button(False))
            else:
                self.root.after(0, lambda: self.append_info("关闭 WSL 失败\n"))
                self.root.after(0, lambda: self.update_status("关闭失败", self.RED))

        threading.Thread(target=_shutdown, daemon=True).start()

    def _reset_start_button(self, running: bool = False) -> None:
        """
        重置启动按钮状态
        :param running: True 表示服务运行中，按钮显示"关闭"；False 表示停止，按钮显示"启动"
        """
        self.btn_start._bg = "#0078d4"
        self.btn_start._hover = "#106ebe"
        self.btn_start._press = "#005a9e"
        self.btn_start._bd_col = "#005a9e"
        self.btn_start.configure(bg="#005a9e")
        self.btn_start.set_state("normal")
        if running:
            self.btn_start.configure_text(
                text="关闭 AstrBot",
                fg="white",
                bg=self.RED,
                bd_col="#8b1a1a",
            )
        else:
            self.btn_start.configure_text(
                text="启动 AstrBot",
                fg="white",
                bg="#0078d4",
                bd_col="#005a9e",
            )

    def open_log_terminal(self) -> None:
        """在新命令行窗口中打开日志实时跟踪"""
        distro = self.settings.get("wsl_distro", DEFAULT_DISTRO)
        user = self.settings.get("wsl_user", DEFAULT_USER)
        data_folder = self.settings.get("data_folder", f"/home/{user}/data")

        if not data_folder:
            self.append_info("请先配置 Data 目录\n")
            return

        self.append_info("正在打开日志终端...\n")
        try:
            subprocess.Popen(
                f'start cmd /k "wsl -d {distro} tail -f {data_folder}/logs/astrbot.log"',
                shell=True,
            )
            self.append_info("日志终端已打开\n")
        except Exception as e:
            self.append_info(f"打开失败: {e}\n")

    def open_webui(self) -> None:
        """在浏览器中打开 AstrBot WebUI"""
        self.append_info("正在打开 WebUI...\n")
        try:
            webbrowser.open(f"http://localhost:{WEBUI_PORT}/")
            self.append_info("WebUI 已打开\n")
        except Exception as e:
            self.append_info(f"打开失败: {e}\n")

    def on_closing(self) -> None:
        """窗口关闭回调"""
        self.root.destroy()


def main():
    """程序入口函数"""
    root = tk.Tk()
    app = AstrBotManager(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
