import tkinter as tk
import tkinter.ttk as ttk
import subprocess
import threading
import webbrowser
import os
import json
import sys
import ctypes
from ctypes import windll, byref, sizeof, c_int


class SettingsManager:
    def __init__(self):
        self.settings_file = os.path.join(
            os.environ.get("APPDATA", "."), "AstrBotManager", "settings.json"
        )
        self.settings = {
            "startup": False,
            "minimize_to_tray": False,
            "process_monitor": False,
            "monitor_interval": 5,
            "wsl_distro": "arch",
            "wsl_user": "dujunxi",
            "data_folder": "",
            "napcat_path": "",
            "astrbot_path": "",
            "qq_number": "",
        }
        self.load()

    def load(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
        except (json.JSONDecodeError, OSError, PermissionError):
            pass

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except (OSError, PermissionError):
            pass

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def get(self, key, default=None):
        return self.settings.get(key, default)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def lerp_color(a, b, t):
    return "#{:02x}{:02x}{:02x}".format(
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def is_valid_wsl_name(name):
    import re

    return bool(re.match(r"^[a-zA-Z0-9_-]+$", name))


class FluentButton(tk.Frame):
    def __init__(self, parent, text, command, primary=False, height=None, **kw):
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

        for w in (self, self._btn):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<ButtonPress-1>", self._on_press)
            w.bind("<ButtonRelease-1>", self._on_release)

    def configure_text(self, text=None, fg=None, bg=None, bd_col=None, **kw):
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

    def _animate(self, target_hex, steps=4, interval=12):
        start = self._current_bg
        target = hex_to_rgb(target_hex)
        self._animating = True

        def step(i):
            if not self._animating:
                return
            t = i / steps
            color = lerp_color(start, target, t)
            try:
                self._btn.configure(bg=color)
            except Exception:
                return
            if i < steps:
                self._btn.after(interval, lambda: step(i + 1))
            else:
                self._current_bg = target
                self._animating = False

        step(1)

    def _on_enter(self, e):
        self._animating = False
        self._animate(self._hover)

    def _on_leave(self, e):
        self._animating = False
        self._animate(self._bg)

    def _on_press(self, e):
        if getattr(self, "_command_enabled", True):
            self._animating = False
            self._btn.configure(bg=self._press)
            self._current_bg = hex_to_rgb(self._press)

    def _on_release(self, e):
        if getattr(self, "_command_enabled", True):
            self._animate(self._hover)
            if self._command:
                self._command()

    def set_state(self, state):
        cursor = "hand2" if state == "normal" else "arrow"
        self._btn.configure(cursor=cursor)
        if state == "disabled":
            self._btn.configure(bg="#e8e8e8", fg="#a0a0a0")
        else:
            self._btn.configure(bg=self._bg, fg=self._fg)
            self._current_bg = hex_to_rgb(self._bg)
        self._command_enabled = state == "normal"


class AstrBotManager:
    BG = "#f3f3f3"
    CARD = "#ffffff"
    BORDER = "#e5e5e5"
    TEXT = "#1c1c1c"
    TEXT2 = "#767676"
    ACCENT = "#0078d4"
    GREEN = "#107c10"
    ORANGE = "#ff8c00"
    RED = "#c42b1c"
    GRAY = "#8a8a8a"

    def __init__(self, root):
        self.root = root
        self.settings = SettingsManager()

        self.root.title("Astrbot WSL Launcher")
        self.root.geometry("340x400")
        self.root.resizable(True, True)
        self.root.minsize(320, 340)
        self.root.configure(bg=self.BG)

        self.is_running = False
        self.monitor_thread = None
        self.stop_monitor = False
        self.settings_window = None

        self._apply_win11_style()
        self.setup_ui()

        if self.settings.get("startup"):
            self.enable_startup()

        if self.settings.get("process_monitor"):
            self.start_process_monitor()

    def _apply_win11_style(self):
        try:
            self.root.update_idletasks()
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                byref(c_int(DWMWCP_ROUND)),
                sizeof(c_int),
            )
        except Exception:
            pass

    def _card(self, parent, **pack_kw):
        f = tk.Frame(
            parent,
            bg=self.CARD,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )
        f.pack(**pack_kw)
        inner = tk.Frame(f, bg=self.CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        return inner

    def setup_ui(self):
        status_inner = self._card(self.root, fill=tk.X, padx=12, pady=(12, 6))

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

        self.status_text = tk.Label(
            status_inner,
            text="就绪",
            font=("Segoe UI Variable", 10),
            fg=self.TEXT2,
            bg=self.CARD,
            anchor="w",
        )
        self.status_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_area = tk.Frame(self.root, bg=self.BG)
        btn_area.pack(fill=tk.X, padx=12, pady=6)

        col0 = tk.Frame(btn_area, bg=self.BG)
        col0.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        col1 = tk.Frame(btn_area, bg=self.BG)
        col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        col2 = tk.Frame(btn_area, bg=self.BG)
        col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.btn_start = FluentButton(
            col0, "启动 AstrBot", self.toggle_astrbot, primary=True
        )
        self.btn_start.pack(fill=tk.BOTH, expand=True)
        self.btn_start._btn.configure(pady=14)

        self.btn_log = FluentButton(col1, "查看日志", self.open_log_terminal)
        self.btn_log.pack(fill=tk.X, pady=(0, 4))
        self.btn_log._btn.configure(pady=8)

        self.btn_shutdown = FluentButton(col1, "关闭 WSL", self.shutdown_wsl)
        self.btn_shutdown.pack(fill=tk.X)
        self.btn_shutdown._btn.configure(pady=8)

        self.btn_webui = FluentButton(col2, "打开 WebUI", self.open_webui)
        self.btn_webui.pack(fill=tk.X, pady=(0, 4))
        self.btn_webui._btn.configure(pady=8)

        self.btn_settings_btn = FluentButton(col2, "设置", self.open_settings)
        self.btn_settings_btn.pack(fill=tk.X)
        self.btn_settings_btn._btn.configure(pady=8)

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

    def _make_labeled_entry(self, parent, label, var, width=25):
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

    def _make_dropdown_row(self, parent, label, var, values):
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

    def _make_button_in_row(self, parent, text, command):
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

    def open_settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return

        win = tk.Toplevel(self.root)
        self.settings_window = win
        win.title("设置")
        win.geometry("460x500")
        win.resizable(False, False)
        win.configure(bg=self.BG)

        try:
            win.update_idletasks()
            hwnd = windll.user32.GetParent(win.winfo_id())
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, byref(c_int(2)), sizeof(c_int)
            )
        except Exception:
            pass

        main_frame = tk.Frame(win, bg=self.BG)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        tk.Label(
            main_frame,
            text="设置",
            font=("Segoe UI Variable", 12, "bold"),
            fg=self.TEXT,
            bg=self.BG,
        ).pack(anchor="w", pady=(0, 6))

        wsl_card = self._make_card_in(main_frame, fill=tk.X, pady=(0, 8))
        tk.Label(
            wsl_card,
            text="WSL 配置",
            font=("Segoe UI Variable", 10, "bold"),
            fg=self.TEXT,
            bg=self.CARD,
        ).pack(anchor="w", pady=(0, 4))

        self.var_wsl_distro = tk.StringVar(
            value=self.settings.get("wsl_distro", "arch")
        )
        self.var_wsl_user = tk.StringVar(value=self.settings.get("wsl_user", ""))

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

        get_users_btn = FluentButton(
            user_container,
            "获取用户目录",
            self._fetch_wsl_users,
            primary=False,
        )
        get_users_btn.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        get_users_btn._btn.configure(pady=8)

        path_card = self._make_card_in(main_frame, fill=tk.X, pady=(0, 8))
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

        detect_btn = FluentButton(
            path_card,
            "自动检测路径",
            self._auto_detect_paths,
            primary=False,
        )
        detect_btn.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        detect_btn._btn.configure(pady=8)

        opt_card = self._make_card_in(main_frame, fill=tk.X, pady=(0, 8))
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
        tk.Checkbutton(
            opt_card,
            text="开机自启",
            variable=self.var_startup,
            command=self.on_startup_changed,
            **chk_style,
        ).pack(anchor="w", pady=1)

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
        self.interval_spin.insert(0, str(self.settings.get("monitor_interval", 5)))
        self.interval_spin.bind("<<Spinbox>>", self.on_interval_changed)
        tk.Label(
            mon_row,
            text="秒",
            font=("Segoe UI Variable", 9),
            fg=self.TEXT2,
            bg=self.CARD,
        ).pack(side=tk.LEFT, padx=(3, 0))

        act_card = self._make_card_in(main_frame, fill=tk.X, pady=(0, 6))
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

        win.protocol("WM_DELETE_WINDOW", win.destroy)

    def _make_card_in(self, parent, height=None, **pack_kw):
        card = tk.Frame(
            parent,
            bg=self.CARD,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )
        card.pack(**pack_kw)
        if height:
            card.pack_propagate(False)
            card.configure(height=height)
        inner = tk.Frame(card, bg=self.CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        return inner

    def _get_wsl_distros(self):
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
        except Exception:
            pass
        return ["arch"]

    def _get_wsl_users(self, distro):
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
        except Exception:
            pass
        return []

    def _detect_napcat_path(self, distro, user):
        try:
            result = subprocess.run(
                [
                    "wsl",
                    "-d",
                    distro,
                    "bash",
                    "-c",
                    f"ls /home/{user}/napcat/*.AppImage 2>/dev/null | head -1",
                ],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.decode("utf-8").strip()
        except Exception:
            pass
        try:
            result = subprocess.run(
                [
                    "wsl",
                    "-d",
                    distro,
                    "bash",
                    "-c",
                    f"find /home/{user}/napcat -name '*.AppImage' -type f 2>/dev/null | head -1",
                ],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.decode("utf-8").strip()
        except Exception:
            pass
        return ""

    def _detect_astrbot_path(self, distro, user):
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
        except Exception:
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
        except Exception:
            pass
        return fallback

    def _detect_data_folder(self, distro, user):
        return f"/home/{user}/data"

    def _fetch_wsl_users(self):
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

    def _auto_detect_paths(self):
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

    def _save_settings(self):
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

    def on_startup_changed(self):
        v = self.var_startup.get()
        self.settings.set("startup", v)
        if v:
            self.enable_startup()
        else:
            self.disable_startup()

    def on_monitor_changed(self):
        v = self.var_monitor.get()
        self.settings.set("process_monitor", v)
        if v:
            self.start_process_monitor()
        else:
            self.stop_process_monitor()

    def on_interval_changed(self, event=None):
        try:
            self.settings.set("monitor_interval", int(self.interval_spin.get()))
        except Exception:
            pass

    def enable_startup(self):
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

    def disable_startup(self):
        try:
            import winreg

            key = r"Software\Microsoft\Windows\CurrentVersion\Run"
            rk = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(rk, "AstrBotManager")
            except Exception:
                pass
            winreg.CloseKey(rk)
        except Exception as e:
            self.append_info(f"取消开机自启失败: {e}\n")

    def start_process_monitor(self):
        self.stop_monitor = False
        interval = self.settings.get("monitor_interval", 5)

        def monitor():
            import time

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
                for _ in range(interval * 10):
                    if self.stop_monitor:
                        break
                    time.sleep(0.1)

        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()

    def stop_process_monitor(self):
        self.stop_monitor = True

    def check_process(self, name):
        try:
            distro = self.settings.get("wsl_distro", "arch")
            r = subprocess.run(
                f"wsl -d {distro} pgrep -f {name}",
                shell=True,
                capture_output=True,
                text=True,
            )
            return r.returncode == 0
        except:
            return False

    def _build_start_command(self):
        distro = self.settings.get("wsl_distro", "arch").strip()
        user = self.settings.get("wsl_user", "dujunxi").strip()
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

    def open_data_directory(self):
        distro = self.settings.get("wsl_distro", "arch").strip()
        user = self.settings.get("wsl_user", "dujunxi").strip()
        data_folder = self.settings.get("data_folder", "")

        if not data_folder:
            self.append_info("请先配置 Data 目录\n")
            return

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
            subprocess.Popen(
                f'explorer "{wsl_path}"',
                shell=True,
            )
            self.append_info("已打开数据目录\n")
        except Exception as e:
            self.append_info(f"打开失败: {e}\n")

    def restart_services(self):
        self.append_info("正在重启服务...\n")
        self.update_status("重启中...", self.ACCENT)
        self.btn_start.set_state("disabled")
        self.btn_start.configure_text(text="重启中...")

        def _restart():
            self.stop_process_monitor()
            distro = self.settings.get("wsl_distro", "arch")
            self.run_wsl_command(
                f'wsl -d {distro} bash -c "pkill -f napcat; pkill -f astrbot"',
                wait=True,
            )
            import time

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

    def append_info(self, message):
        def _append():
            self.info_area.configure(state="normal")
            self.info_area.insert(tk.END, message)
            self.info_area.see(tk.END)
            self.info_area.configure(state="disabled")

        self.root.after(0, _append)

    def update_status(self, text, color=None):
        if color is None:
            color = self.GRAY

        def _update():
            self.status_text.configure(text=text, fg=color)
            self.status_dot.itemconfig(self.status_dot_id, fill=color)

        self.root.after(0, _update)

    def run_wsl_command(self, command, wait=True):
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

    def toggle_astrbot(self):
        if self.is_running:
            self.stop_astrbot()
        else:
            self.start_astrbot()

    def start_astrbot(self):
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
            import time

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

    def stop_astrbot(self):
        self.append_info("正在关闭 AstrBot...\n")
        self.update_status("关闭中...", self.ACCENT)
        self.btn_start.set_state("disabled")
        self.btn_start.configure_text(text="关闭中...")

        def _stop():
            self.stop_process_monitor()
            distro = self.settings.get("wsl_distro", "arch")
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

    def shutdown_wsl(self):
        self.append_info("正在关闭 WSL...\n")
        self.update_status("关闭中...", self.ACCENT)

        def _shutdown():
            self.stop_process_monitor()
            distro = self.settings.get("wsl_distro", "arch")
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

    def _reset_start_button(self, running=False):
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

    def open_log_terminal(self):
        distro = self.settings.get("wsl_distro", "arch")
        user = self.settings.get("wsl_user", "dujunxi")
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

    def open_webui(self):
        self.append_info("正在打开 WebUI...\n")
        try:
            webbrowser.open("http://localhost:6185/")
            self.append_info("WebUI 已打开\n")
        except Exception as e:
            self.append_info(f"打开失败: {e}\n")

    def on_closing(self):
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AstrBotManager(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
