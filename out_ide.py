import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import json
import urllib.request
import urllib.error
import tkinter as tk
import queue
import traceback
from tkinter import font as tkfont, filedialog, messagebox, ttk
import json


def get_base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


OUT_EXE = os.path.join(get_base_path(), "out.exe")
APP_NAME = "OUT IDE"
APP_VERSION = "0.6.4"

DEFAULT_THEME = "dark"
_current_theme = DEFAULT_THEME

THEMES = {
    "dark": {
        "bg": "#1e1e1e",
        "sidebar": "#252526",
        "panel": "#1e1e1e",
        "tab": "#2d2d2d",
        "tab_active": "#1e1e1e",
        "title": "#3c3c3c",
        "status": "#007acc",
        "status_error": "#c24038",
        "toolbar": "#333333",
        "input": "#3c3c3c",
        "seal": "#3c3c3c",
        "sep": "#555555",
        "fg": "#cccccc",
        "dim": "#858585",
        "bright": "#ffffff",
        "accent": "#569cd6",
        "green": "#4ec9b0",
        "string": "#ce9178",
        "number": "#b5cea8",
        "keyword": "#c586c0",
        "comment": "#6a9955",
        "function": "#dcdcaa",
        "module": "#4ec9b0",
        "error": "#f44747",
        "warn": "#cca700",
        "bracket": "#ffd700",
        "error_line_bg": "#5a1d1d",
        "current_line_bg": "#2a2d2e",
        "selection": "#264f78",
        "caret": "#ffffff",
        "hover": "#4a4a4a",
        "find_highlight_bg": "#613214",
        "minimap_plain": "#555555",
        "splash_bg": "#0e1525",
        "splash_accent": "#007acc",
        "viewport": "#ffffff",
    },
    "light": {
        "bg": "#ffffff",
        "sidebar": "#f3f3f3",
        "panel": "#ffffff",
        "tab": "#ececec",
        "tab_active": "#ffffff",
        "title": "#f3f3f3",
        "status": "#007acc",
        "status_error": "#c24038",
        "toolbar": "#f3f3f3",
        "input": "#ffffff",
        "seal": "#c8c8c8",
        "sep": "#c8c8c8",
        "fg": "#333333",
        "dim": "#717171",
        "bright": "#000000",
        "accent": "#007acc",
        "green": "#12801c",
        "string": "#a31515",
        "number": "#098658",
        "keyword": "#0000ff",
        "comment": "#008000",
        "function": "#795e26",
        "module": "#12801c",
        "error": "#e51400",
        "warn": "#bf8803",
        "bracket": "#7f3fbf",
        "error_line_bg": "#fce4e4",
        "current_line_bg": "#f5f5f5",
        "selection": "#add6ff",
        "caret": "#000000",
        "hover": "#e6e6e6",
        "find_highlight_bg": "#ffe58f",
        "minimap_plain": "#e0e0e0",
        "splash_bg": "#f3f3f3",
        "splash_accent": "#007acc",
        "viewport": "#d0d0d0",
    },
}


def th(name):
    return THEMES[_current_theme][name]


def make_keyword_colors():
    return {
        "def": th("keyword"), "fn": th("keyword"), "return": th("keyword"),
        "if": th("keyword"), "else": th("keyword"), "for": th("keyword"),
        "in": th("keyword"), "while": th("keyword"), "break": th("keyword"),
        "continue": th("keyword"), "import": th("keyword"), "from": th("keyword"),
        "true": th("accent"), "false": th("accent"), "null": th("accent"),
        "and": th("accent"), "or": th("accent"), "not": th("accent"),
        "try": th("keyword"), "catch": th("keyword"), "throw": th("keyword"),
        "class": th("green"), "new": th("green"), "this": th("green"), "super": th("green"),
    }


KEYWORD_COLORS = make_keyword_colors()


def get_config_path():
    home = os.path.expanduser("~")
    cfg_dir = os.path.join(home, ".out")
    os.makedirs(cfg_dir, exist_ok=True)
    return os.path.join(cfg_dir, "ide_config.json")


def load_theme_config():
    global _current_theme
    try:
        with open(get_config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("theme") in THEMES:
            _current_theme = data["theme"]
    except Exception:
        pass


def save_theme_config(name):
    try:
        data = {}
        try:
            with open(get_config_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
        data["theme"] = name
        with open(get_config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def _normalize_hex(color):
    if color is None:
        return ""
    color = str(color).lower().strip()
    m = re.match(r"^#([0-9a-f])\1([0-9a-f])\2([0-9a-f])\3$", color)
    if m:
        return f"#{m.group(1)}{m.group(2)}{m.group(3)}"
    return color


def _recolor_children(widget, old_theme, new_theme):
    bg_map = {}
    fg_map = {}
    for k, v in old_theme.items():
        nv = new_theme[k]
        bg_map.setdefault(_normalize_hex(v), nv)
        fg_map.setdefault(_normalize_hex(v), nv)

    def rec(w):
        try:
            bg = w.cget("bg")
            nb = bg_map.get(_normalize_hex(bg))
            if nb:
                w.configure(bg=nb)
        except tk.TclError:
            pass
        try:
            fg = w.cget("fg")
            nf = fg_map.get(_normalize_hex(fg))
            if nf:
                w.configure(fg=nf)
        except tk.TclError:
            pass
        try:
            if isinstance(w, tk.Entry) or isinstance(w, tk.Text):
                ibg = w.cget("insertbackground")
                nb = bg_map.get(_normalize_hex(ibg))
                if nb:
                    w.configure(insertbackground=nb)
            if isinstance(w, tk.Entry):
                hb = w.cget("highlightbackground")
                nb = bg_map.get(_normalize_hex(hb))
                if nb:
                    w.configure(highlightbackground=nb)
            if isinstance(w, tk.Button):
                abg = w.cget("activebackground")
                nb = bg_map.get(_normalize_hex(abg))
                if nb:
                    w.configure(activebackground=nb)
        except tk.TclError:
            pass
        for c in w.winfo_children():
            try:
                rec(c)
            except tk.TclError:
                pass
    rec(widget)


TAB_HEIGHT = 35
STATUS_HEIGHT = 24
TOOLBAR_HEIGHT = 40
SIDEBAR_WIDTH = 260
MINIMAP_WIDTH = 100


def open_text(path):
    with open(path, "rb") as f:
        raw = f.read(4)
    if raw[:2] == b"\xff\xfe":
        encoding = "utf-16"
    elif raw[:2] == b"\xfe\xff":
        encoding = "utf-16-be"
    elif raw[:3] == b"\xef\xbb\xbf":
        encoding = "utf-8-sig"
    else:
        encoding = "utf-8"
    with open(path, "r", encoding=encoding, errors="replace") as f:
        return encoding, f.read()


def save_text(path, text, encoding):
    if encoding == "utf-16":
        with open(path, "wb") as f:
            f.write(b"\xff\xfe")
            f.write(text.encode("utf-16-le"))
    elif encoding == "utf-16-be":
        with open(path, "wb") as f:
            f.write(b"\xfe\xff")
            f.write(text.encode("utf-16-be"))
    else:
        with open(path, "w", encoding=encoding) as f:
            f.write(text)


def find_out_exe():
    if os.path.exists(OUT_EXE):
        return OUT_EXE
    for p in ("..", "out-lang", "."):
        cand = os.path.join(os.path.dirname(os.path.abspath(__file__)), p, "out.exe")
        if os.path.exists(cand):
            return cand
    return "out.exe"


KEYWORDS = (
    "def", "fn", "return", "if", "else", "for", "in", "while", "break", "continue",
    "import", "from", "as", "true", "false", "null", "and", "or", "not",
    "class", "new", "this", "super", "try", "catch", "throw",
)
BUILTINS = (
    "print", "len", "str", "int", "float", "type", "range", "error",
    "input", "append", "vibe", "yeet", "sus", "flex", "bruh", "howl", "echo",
)
MODULES = (
    "os", "json", "http", "math", "random", "crypto", "files", "strings",
    "strconv", "list", "env", "time", "dev", "console", "logging",
    "array", "dict", "shell",
)


class SplashScreen:
    def __init__(self, on_done):
        self.on_done = on_done
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=th("splash_bg"))
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 480, 300
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.attributes("-topmost", True)

        c = tk.Canvas(self.root, width=w, height=h, bg=th("splash_bg"), highlightthickness=0)
        c.pack(fill=tk.BOTH, expand=True)

        c.create_rectangle(0, 0, w, 3, fill=th("splash_accent"), outline="")

        c.create_text(w // 2, 70, text="OUT", font=("Segoe UI Light", 48),
                       fill=th("splash_accent"), anchor="center")
        c.create_text(w // 2, 120, text="Language IDE", font=("Segoe UI", 14),
                       fill=th("dim"), anchor="center")
        c.create_text(w // 2, 155, text=f"v{APP_VERSION}", font=("Segoe UI", 10),
                       fill=th("dim"), anchor="center")

        c.create_text(w // 2, 200, text="Загрузка компонентов...",
                       font=("Segoe UI", 9), fill=th("dim"), anchor="center", tags="loading")

        bar_w = 300
        bar_h = 4
        bx = (w - bar_w) // 2
        by = 230
        c.create_rectangle(bx, by, bx + bar_w, by + bar_h, fill=th("title"), outline="")
        self.bar = c.create_rectangle(bx, by, bx, by + bar_h, fill=th("splash_accent"), outline="")
        self.bar_w = bar_w
        self.bx = bx
        self.by = by
        self.canvas = c
        self.progress = 0

        self._animate()

    def _animate(self):
        self.progress += 2
        if self.progress > 100:
            self.progress = 100
        w = int(self.bar_w * self.progress / 100)
        self.canvas.coords(self.bar, self.bx, self.by, self.bx + w, self.by + 4)

        msgs = [
            (20, "Загрузка лексера..."),
            (40, "Загрузка парсера..."),
            (60, "Загрузка модулей..."),
            (80, "Загрузка IDE..."),
            (95, "Готово!"),
        ]
        for threshold, msg in msgs:
            if self.progress >= threshold:
                self.canvas.itemconfig("loading", text=msg)

        if self.progress < 100:
            self.root.after(25, self._animate)
        else:
            self.root.after(400, self._close)

    def _close(self):
        self.root.destroy()
        self.on_done()

    def run(self):
        self.root.mainloop()


class FileExplorer:
    def __init__(self, parent, on_open):
        self.on_open = on_open
        self.frame = tk.Frame(parent, bg=th("sidebar"), width=SIDEBAR_WIDTH)
        self.frame.pack_propagate(False)
        self.current_dir = ""
        self._build()

    def _build(self):
        hdr = tk.Frame(self.frame, bg=th("sidebar"))
        hdr.pack(fill=tk.X, padx=8, pady=(8, 4))
        tk.Label(hdr, text="ПРОВОДНИК", font=("Segoe UI", 10, "bold"),
                 fg=th("dim"), bg=th("sidebar")).pack(side=tk.LEFT)
        tk.Label(hdr, text="⟳", font=("Segoe UI", 11), fg=th("dim"), bg=th("sidebar"),
                 cursor="hand2").pack(side=tk.RIGHT)
        hdr.winfo_children()[-1].bind("<Button-1>", lambda e: self.refresh())

        sep = tk.Frame(self.frame, bg=th("title"), height=1)
        sep.pack(fill=tk.X)

        container = tk.Frame(self.frame, bg=th("sidebar"))
        container.pack(fill=tk.BOTH, expand=True)

        self.tree = tk.Canvas(container, bg=th("sidebar"), highlightthickness=0)
        sb = tk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def set_directory(self, path):
        if not path or not os.path.isdir(path):
            return
        self.current_dir = path
        self.refresh()

    def refresh(self):
        if not self.current_dir:
            return
        self.tree.delete("all")
        y = 8
        try:
            entries = sorted(os.listdir(self.current_dir))
        except PermissionError:
            return
        dirs = [e for e in entries if os.path.isdir(os.path.join(self.current_dir, e))]
        files = [e for e in entries if os.path.isfile(os.path.join(self.current_dir, e))]

        self.tree.create_text(8, y, text=os.path.basename(self.current_dir) or self.current_dir,
                              font=("Segoe UI", 10, "bold"), fill=th("bright"), anchor="w")
        y += 22

        for d in dirs:
            if d.startswith(".") or d.startswith("__"):
                continue
            self.tree.create_text(16, y, text=f"📁 {d}", font=("Segoe UI", 9),
                                  fill=th("dim"), anchor="w", cursor="hand2", tags=("dir",))
            fp_d = os.path.join(self.current_dir, d)
            self.tree.tag_bind("dir", "<Button-1>", lambda e, p=fp_d: self._open_sketch(p))
            y += 22

        for f in files:
            if f.startswith("."):
                continue
            ext = os.path.splitext(f)[1]
            icon = "📄"
            if ext == ".out":
                icon = "🟣"
            elif ext == ".exe":
                icon = "⚙"
            self.tree.create_text(16, y, text=f"{icon} {f}", font=("Segoe UI", 9),
                                  fill=th("dim"), anchor="w", cursor="hand2", tags=("file",))
            fp = os.path.join(self.current_dir, f)
            self.tree.tag_bind("file", "<Button-1>", lambda e, p=fp: self._open_file(p))
            y += 22

        self.tree.configure(scrollregion=self.tree.bbox("all"))

    def _open_file(self, path):
        self.on_open(path)

    def _open_sketch(self, path):
        """Arduino-style: click on a folder -> open every .out inside as tabs."""
        outs = []
        if os.path.isdir(path):
            for root, _, filenames in os.walk(path):
                for fn in filenames:
                    if fn.endswith(".out") and not fn.startswith("."):
                        outs.append(os.path.join(root, fn))
        elif path.endswith(".out"):
            outs.append(path)
        outs.sort(key=lambda p: (os.path.dirname(p), os.path.basename(p)))
        if outs:
            self.on_open(outs if len(outs) > 1 else outs[0])


class TabBar:
    def __init__(self, parent, on_select, on_close):
        self.on_select = on_select
        self.on_close = on_close
        self.tabs = []
        self.active = None
        self.frame = tk.Frame(parent, bg=th("tab"), height=TAB_HEIGHT)
        self.frame.pack_propagate(False)
        self.container = tk.Frame(self.frame, bg=th("tab"))
        self.container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def add_tab(self, title, filepath):
        for t in self.tabs:
            if t["path"] == filepath:
                self.select(t)
                return
        tab = {"title": title, "path": filepath, "frame": None, "label": None, "close": None}
        f = tk.Frame(self.container, bg=th("tab"), height=TAB_HEIGHT)
        f.pack_propagate(False)
        f.pack(side=tk.LEFT, padx=(1, 0))

        inner = tk.Frame(f, bg=th("tab"))
        inner.pack(fill=tk.BOTH, expand=True, padx=4)
        inner.pack_propagate(False)

        lbl = tk.Label(inner, text=f" {title} ", font=("Segoe UI", 9),
                        fg=th("dim"), bg=th("tab"), cursor="hand2")
        lbl.pack(side=tk.LEFT, fill=tk.Y)
        lbl.bind("<Button-1>", lambda e, t=tab: self.select(t))

        cls = tk.Label(inner, text="✕", font=("Segoe UI", 8), fg=th("dim"),
                        bg=th("tab"), cursor="hand2", padx=4)
        cls.pack(side=tk.RIGHT)
        cls.bind("<Button-1>", lambda e, t=tab: self.close_tab(t))

        tab["frame"] = f
        tab["label"] = lbl
        tab["close"] = cls
        self.tabs.append(tab)
        self.select(tab)

    def select(self, tab):
        for t in self.tabs:
            if t["frame"]:
                t["frame"].configure(bg=th("tab"))
                t["label"].configure(bg=th("tab"), fg=th("dim"))
        if tab and tab["frame"]:
            tab["frame"].configure(bg=th("tab_active"))
            tab["label"].configure(bg=th("tab_active"), fg=th("bright"))
        self.active = tab
        if tab:
            self.on_select(tab)

    def close_tab(self, tab):
        if tab in self.tabs:
            self.tabs.remove(tab)
            tab["frame"].destroy()
            if self.active == tab:
                if self.tabs:
                    self.select(self.tabs[-1])
                else:
                    self.active = None
                    self.on_close()

    def get_active_path(self):
        if self.active:
            return self.active["path"]
        return None


class FindReplaceDialog:
    def __init__(self, parent, editor_text):
        self.editor = editor_text
        self.visible = False
        self.frame = None
        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.match_var = tk.StringVar(value="0 совпадений")
        self._create()

    def _create(self):
        self.frame = tk.Frame(self.editor.master, bg=th("title"), bd=0)
        row1 = tk.Frame(self.frame, bg=th("title"))
        row1.pack(fill=tk.X, padx=8, pady=(6, 2))

        tk.Label(row1, text="Найти:", font=("Segoe UI", 9), fg=th("dim"),
                 bg=th("title")).pack(side=tk.LEFT, padx=(0, 6))
        e1 = tk.Entry(row1, textvariable=self.find_var, font=("Consolas", 10),
                       bg=th("input"), fg=th("fg"), insertbackground=th("caret"), bd=0,
                       highlightthickness=1, highlightbackground=th("title"))
        e1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        e1.bind("<KeyRelease>", lambda e: self._on_change())
        e1.bind("<Return>", lambda e: self.find_next())

        tk.Label(row1, textvariable=self.match_var, font=("Segoe UI", 9),
                 fg=th("dim"), bg=th("title"), width=14).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(row1, text="▼", font=("Segoe UI", 9), bg=th("input"), fg=th("fg"),
                  bd=0, command=self.find_next, width=3).pack(side=tk.LEFT, padx=1)
        tk.Button(row1, text="▲", font=("Segoe UI", 9), bg=th("input"), fg=th("fg"),
                  bd=0, command=self.find_prev, width=3).pack(side=tk.LEFT, padx=1)
        tk.Button(row1, text="✕", font=("Segoe UI", 9), bg=th("input"), fg=th("fg"),
                  bd=0, command=self.hide, width=3).pack(side=tk.LEFT, padx=1)

        row2 = tk.Frame(self.frame, bg=th("title"))
        row2.pack(fill=tk.X, padx=8, pady=(2, 6))

        tk.Label(row2, text="Заменить:", font=("Segoe UI", 9), fg=th("dim"),
                 bg=th("title")).pack(side=tk.LEFT, padx=(0, 2))
        tk.Entry(row2, textvariable=self.replace_var, font=("Consolas", 10),
                 bg=th("input"), fg=th("fg"), insertbackground=th("caret"), bd=0,
                 highlightthickness=1, highlightbackground=th("title")).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(row2, text="Заменить", font=("Segoe UI", 9), bg=th("input"), fg=th("fg"),
                  bd=0, command=self.replace_one).pack(side=tk.LEFT, padx=1)
        tk.Button(row2, text="Все", font=("Segoe UI", 9), bg=th("input"), fg=th("fg"),
                  bd=0, command=self.replace_all).pack(side=tk.LEFT, padx=1)

    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()

    def show(self):
        if not self.visible:
            self.frame.pack(side=tk.TOP, fill=tk.X, before=self.editor.master.winfo_children()[0])
            self.visible = True
        self.frame.winfo_children()[0].winfo_children()[1].focus_set()

    def hide(self):
        if self.visible:
            self.frame.pack_forget()
            self.visible = False

    def _on_change(self):
        self.editor.tag_remove("find_highlight", "1.0", tk.END)
        query = self.find_var.get()
        if not query:
            self.match_var.set("0 совпадений")
            return
        count = 0
        start = "1.0"
        while True:
            pos = self.editor.search(query, start, tk.END, nocase=True, count=tk.NONE)
            if not pos:
                break
            end = f"{pos}+{len(query)}c"
            self.editor.tag_add("find_highlight", pos, end)
            count += 1
            start = end
        self.editor.tag_configure("find_highlight", background=th("find_highlight_bg"), foreground=th("bright"))
        self.match_var.set(f"{count} совпадений")

    def find_next(self):
        query = self.find_var.get()
        if not query:
            return
        current = self.editor.index(tk.INSERT)
        pos = self.editor.search(query, current, tk.END, nocase=True)
        if not pos:
            pos = self.editor.search(query, "1.0", current, nocase=True)
        if pos:
            self.editor.mark_set(tk.INSERT, pos)
            end = f"{pos}+{len(query)}c"
            self.editor.tag_remove("sel", "1.0", tk.END)
            self.editor.tag_add("sel", pos, end)
            self.editor.see(pos)

    def find_prev(self):
        query = self.find_var.get()
        if not query:
            return
        current = self.editor.index(tk.INSERT)
        pos = self.editor.search(query, "1.0", current, nocase=True, stopindex=tk.END)
        matches = []
        start = "1.0"
        while True:
            p = self.editor.search(query, start, current, nocase=True)
            if not p:
                break
            matches.append(p)
            start = f"{p}+{len(query)}c"
        if matches:
            pos = matches[-1]
            self.editor.mark_set(tk.INSERT, pos)
            end = f"{pos}+{len(query)}c"
            self.editor.tag_remove("sel", "1.0", tk.END)
            self.editor.tag_add("sel", pos, end)
            self.editor.see(pos)

    def replace_one(self):
        sel = self.editor.tag_ranges("sel")
        if sel:
            self.editor.delete(sel[0], sel[1])
            self.editor.insert(tk.INSERT, self.replace_var.get())
        self.find_next()

    def replace_all(self):
        query = self.find_var.get()
        replacement = self.replace_var.get()
        if not query:
            return
        content = self.editor.get("1.0", tk.END)
        new_content = content.replace(query, replacement)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", new_content)
        self._on_change()


GITHUB_RAW = "https://raw.githubusercontent.com"
GITHUB_REPO = "mark-https-gif/out-lang-libs/main"
UPDATE_REPO = "mark-https-gif/out-updates"


def get_libs_dir():
    base = get_base_path()
    local = os.path.join(base, "libs")
    if os.path.isdir(local):
        return local
    home = os.path.expanduser("~")
    p = os.path.join(home, ".out", "libs")
    os.makedirs(p, exist_ok=True)
    return p


def get_catalog():
    catalog_path = os.path.join(get_base_path(), "libs_catalog.json")
    if os.path.exists(catalog_path):
        with open(catalog_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_installed_libs():
    libs_dir = get_libs_dir()
    installed = []
    if os.path.isdir(libs_dir):
        for f in os.listdir(libs_dir):
            if f.endswith(".out"):
                path = os.path.join(libs_dir, f)
                size = os.path.getsize(path)
                installed.append({"name": f, "path": path, "size": size})
    return installed


def download_lib(url, name):
    libs_dir = get_libs_dir()
    os.makedirs(libs_dir, exist_ok=True)
    full_url = f"{GITHUB_RAW}/{GITHUB_REPO}/{url}.out"
    try:
        req = urllib.request.Request(full_url, headers={"User-Agent": "OUT-IDE"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = resp.read()
        dst = os.path.join(libs_dir, f"{name}.out")
        with open(dst, "wb") as f:
            f.write(data)
        return True, len(data)
    except Exception as e:
        return False, str(e)


def delete_lib(name):
    libs_dir = get_libs_dir()
    path = os.path.join(libs_dir, name)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def parse_version(v):
    try:
        digits = re.findall(r"\d+", v)
        return tuple(int(d) for d in digits[:3])
    except Exception:
        return (0, 0, 0)


def check_update():
    full_url = f"{GITHUB_RAW}/{UPDATE_REPO}/main/update.json"
    req = urllib.request.Request(full_url, headers={"User-Agent": "OUT-IDE"})
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read().decode("utf-8"))


def download_installer(asset_url, dest):
    req = urllib.request.Request(asset_url, headers={"User-Agent": "OUT-IDE"})
    resp = urllib.request.urlopen(req, timeout=300)
    with open(dest, "wb") as f:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
    return dest


class LibManagerDialog:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Менеджер библиотек")
        self.top.geometry("700x550")
        self.top.configure(bg=th("bg"))
        self.top.transient(parent)
        self.top.grab_set()

        self.catalog = get_catalog()
        self.installed = {lib["name"] for lib in get_installed_libs()}

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        hdr = tk.Frame(self.top, bg=th("title"), height=50)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  Библиотеки OUT", font=("Segoe UI", 14, "bold"),
                 fg=th("bright"), bg=th("title")).pack(side=tk.LEFT, padx=10)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_list())
        e = tk.Entry(hdr, textvariable=self.search_var, font=("Segoe UI", 10),
                      bg=th("input"), fg=th("fg"), insertbackground=th("caret"), bd=0,
                      highlightthickness=1, highlightbackground=th("title"), width=30)
        e.pack(side=tk.RIGHT, padx=10, pady=8)
        tk.Label(hdr, text="🔍", font=("Segoe UI", 10), fg=th("dim"), bg=th("title")).pack(side=tk.RIGHT)

        bar = tk.Frame(self.top, bg=th("toolbar"), height=36)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Button(bar, text="⟳ Обновить", command=self._refresh_list,
                  font=("Segoe UI", 9), bg=th("input"), fg=th("fg"), bd=0,
                  activebackground=th("hover"), cursor="hand2").pack(side=tk.LEFT, padx=6, pady=4)
        tk.Button(bar, text="📂 Папка libs", command=self._open_libs_dir,
                  font=("Segoe UI", 9), bg=th("input"), fg=th("fg"), bd=0,
                  activebackground=th("hover"), cursor="hand2").pack(side=tk.LEFT, padx=6, pady=4)

        self.status_var = tk.StringVar(value="Готово")
        tk.Label(bar, textvariable=self.status_var, font=("Segoe UI", 9),
                 fg=th("dim"), bg=th("toolbar")).pack(side=tk.RIGHT, padx=10)

        container = tk.Frame(self.top, bg=th("bg"))
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        cols = ("name", "status", "description")
        self.tree = ttk.Treeview(container, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Название")
        self.tree.heading("status", text="Статус")
        self.tree.heading("description", text="Описание")
        self.tree.column("name", width=130, minwidth=100)
        self.tree.column("status", width=100, minwidth=80)
        self.tree.column("description", width=430, minwidth=200)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=th("bg"), foreground=th("fg"),
                         fieldbackground=th("bg"), font=("Segoe UI", 9), rowheight=28)
        style.configure("Treeview.Heading", background=th("toolbar"), foreground=th("fg"),
                         font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", th("selection"))],
                  foreground=[("selected", th("bright"))])

        sb = tk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(self.top, bg=th("bg"))
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.install_btn = tk.Button(btn_frame, text="⬇ Установить", command=self._install_selected,
                                      font=("Segoe UI", 10, "bold"), bg="#2e7d32", fg=th("bright"),
                                      bd=0, padx=16, pady=6, activebackground="#388e3c",
                                      cursor="hand2")
        self.install_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.uninstall_btn = tk.Button(btn_frame, text="✕ Удалить", command=self._uninstall_selected,
                                        font=("Segoe UI", 10), bg="#c62828", fg=th("bright"),
                                        bd=0, padx=16, pady=6, activebackground="#d32f2f",
                                        cursor="hand2")
        self.uninstall_btn.pack(side=tk.LEFT)

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        search = self.search_var.get().lower()
        self.catalog = get_catalog()
        self.installed = {lib["name"] for lib in get_installed_libs()}

        for lib in self.catalog:
            if search and search not in lib["name"].lower() and search not in lib.get("description", "").lower():
                continue
            status = "✅ Установлена" if lib["name"] in self.installed else "⬜ Доступна"
            tags = ("installed",) if lib["name"] in self.installed else ()
            self.tree.insert("", tk.END, values=(lib["name"], status, lib.get("description", "")),
                             tags=tags, iid=lib["name"])

        self.tree.tag_configure("installed", foreground=th("green"))
        self.status_var.set(f"Каталог: {len(self.catalog)} | Установлено: {len(self.installed)}")

    def _get_selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        name = sel[0]
        for lib in self.catalog:
            if lib["name"] == name:
                return lib
        return None

    def _install_selected(self):
        lib = self._get_selected()
        if not lib:
            return
        if lib["name"] in self.installed:
            self.status_var.set(f"{lib['name']} уже установлена")
            return
        self.status_var.set(f"Загрузка {lib['name']}...")
        self.install_btn.config(state=tk.DISABLED)

        def worker():
            ok, result = download_lib(lib.get("url", lib["name"]), lib["name"])
            self.top.after(0, self._on_install_done, lib["name"], ok, result)

        threading.Thread(target=worker, daemon=True).start()

    def _on_install_done(self, name, ok, result):
        self.install_btn.config(state=tk.NORMAL)
        if ok:
            self.status_var.set(f"✅ {name} установлена ({result} байт)")
            self._refresh_list()
        else:
            self.status_var.set(f"❌ Ошибка: {result}")

    def _uninstall_selected(self):
        lib = self._get_selected()
        if not lib:
            return
        if lib["name"] not in self.installed:
            self.status_var.set(f"{lib['name']} не установлена")
            return
        if not messagebox.askyesno("Удаление", f"Удалить библиотеку {lib['name']}?"):
            return
        if delete_lib(lib["name"] + ".out"):
            self.status_var.set(f"🗑 {lib['name']} удалена")
            self._refresh_list()
        else:
            self.status_var.set(f"❌ Не удалось удалить {lib['name']}")

    def _open_libs_dir(self):
        libs_dir = get_libs_dir()
        os.makedirs(libs_dir, exist_ok=True)
        os.startfile(libs_dir)


class UpdateDialog:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Обновления")
        self.top.geometry("520x340")
        self.top.configure(bg=th("bg"))
        self.top.transient(parent)
        self.top.grab_set()
        self.result = None
        self._build_ui()
        self._check()

    def _build_ui(self):
        hdr = tk.Frame(self.top, bg=th("title"), height=50)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  Обновления OUT IDE", font=("Segoe UI", 14, "bold"),
                 fg=th("bright"), bg=th("title")).pack(side=tk.LEFT, padx=10)

        body = tk.Frame(self.top, bg=th("bg"))
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        self.info_var = tk.StringVar(value="Проверка обновлений...")
        self.info = tk.Label(body, textvariable=self.info_var, font=("Segoe UI", 10),
                             fg=th("fg"), bg=th("bg"), justify=tk.LEFT, anchor="w", wraplength=470)
        self.info.pack(fill=tk.X, pady=(4, 8))

        link_row = tk.Frame(body, bg=th("bg"))
        link_row.pack(fill=tk.X, pady=(8, 4))
        tk.Label(link_row, text="Сервер обновлений:", font=("Segoe UI", 9),
                 fg=th("dim"), bg=th("bg")).pack(side=tk.LEFT, padx=(0, 6))
        self.link_var = tk.StringVar(value=f"{GITHUB_RAW}/{UPDATE_REPO}/main/update.json")
        tk.Entry(link_row, textvariable=self.link_var, font=("Consolas", 8),
                 bg=th("input"), fg=th("fg"), bd=0,
                 highlightthickness=1, highlightbackground=th("title")).pack(side=tk.LEFT, fill=tk.X, expand=True)

        bar = tk.Frame(self.top, bg=th("bg"))
        bar.pack(fill=tk.X, padx=14, pady=(0, 12))
        self.check_btn = tk.Button(bar, text="Проверить снова", command=self._check,
                                   font=("Segoe UI", 10), bg=th("input"), fg=th("fg"),
                                   bd=0, padx=16, pady=6, activebackground=th("hover"),
                                   cursor="hand2")
        self.check_btn.pack(side=tk.LEFT)
        self.download_btn = tk.Button(bar, text="⬇ Скачать и установить", command=self._download,
                                      font=("Segoe UI", 10, "bold"), bg="#2e7d32", fg=th("bright"),
                                      bd=0, padx=16, pady=6, activebackground="#388e3c",
                                      cursor="hand2", state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.close_btn = tk.Button(bar, text="Закрыть", command=self.top.destroy,
                                   font=("Segoe UI", 10), bg=th("input"), fg=th("fg"),
                                   bd=0, padx=16, pady=6, activebackground=th("hover"),
                                   cursor="hand2")
        self.close_btn.pack(side=tk.LEFT, padx=(8, 0))

    def _check(self):
        self.info_var.set("Проверка обновлений...")
        self.download_btn.config(state=tk.DISABLED)
        self.check_btn.config(state=tk.DISABLED)
        self.result = None

        def worker():
            try:
                data = check_update()
                self.top.after(0, self._on_check_done, True, data)
            except Exception as e:
                self.top.after(0, self._on_check_done, False, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_check_done(self, ok, result):
        self.check_btn.config(state=tk.NORMAL)
        if not ok:
            self.info_var.set(f"Ошибка проверки обновлений:\n{result}")
            return
        self.result = result
        try:
            remote = parse_version(result.get("version", ""))
            current = parse_version(APP_VERSION)
        except Exception:
            remote = (0, 0, 0)
            current = (0, 0, 0)
        latest = result.get("latest", {})
        asset_url = latest.get("url", "")
        if remote > current:
            if asset_url:
                self.download_btn.config(state=tk.NORMAL)
            notes = result.get("notes", "")
            self.info_var.set(f"Доступна новая версия: {result.get('version')}\n"
                              f"Текущая версия: {APP_VERSION}\n\n"
                              f"{notes}" if notes else f"Доступна новая версия: {result.get('version')}\n"
                              f"Текущая версия: {APP_VERSION}")
        else:
            self.info_var.set(f"У вас актуальная версия ({APP_VERSION}).\n\nВерсия на сервере: {result.get('version')}")

    def _download(self):
        if not self.result:
            return
        latest = self.result.get("latest", {})
        asset_url = latest.get("url", "")
        if not asset_url:
            self.info_var.set("Ссылка на установщик не найдена")
            return
        self.download_btn.config(state=tk.DISABLED)
        self.check_btn.config(state=tk.DISABLED)
        self.info_var.set("Скачивание установщика...")

        def worker():
            try:
                dest = os.path.join(tempfile.gettempdir(), "OUT-IDE-Setup.exe")
                download_installer(asset_url, dest)
                self.top.after(0, self._on_download_done, True, dest)
            except Exception as e:
                self.top.after(0, self._on_download_done, False, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_download_done(self, ok, result):
        self.check_btn.config(state=tk.NORMAL)
        if not ok:
            self.download_btn.config(state=tk.NORMAL)
            self.info_var.set(f"Ошибка скачивания:\n{result}")
            return
        self.info_var.set(f"Скачано: {result}\nЗапускаю установщик...")
        try:
            os.startfile(result)
            self.top.after(1500, self.top.destroy)
        except Exception as e:
            self.info_var.set(f"Не удалось запустить установщик: {e}")


class OutIde:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} — {APP_VERSION}")
        self.root.geometry("1400x850")
        self.root.minsize(900, 600)
        self.root.configure(bg=th("bg"))

        self.current_file = ""
        self.last_error = ""
        self.error_lines = []
        self._highlight_id = None
        self._save_id = None
        self._sidebar_visible = True
        self._panel_visible = True
        self._panel_height = 200
        self._encoding = "utf-8"
        self.theme_var = tk.StringVar(value=_current_theme)
        self._cmd_queue = queue.Queue()

        self._build_menu()
        self._build_toolbar()
        self._build_tab_bar()
        self._build_main_area()
        self._build_status_bar()
        self._bind_keys()
        self._update_cursor_pos()
        self._apply_widget_defaults()
        self.root.after(2000, self._auto_check_update)
        self.root.after(100, self._poll_queue)

    def _apply_widget_defaults(self):
        self.root.option_add("*Menu.background", th("title"))
        self.root.option_add("*Menu.foreground", th("fg"))
        self.root.option_add("*Menu.activeBackground", th("splash_accent"))
        self.root.option_add("*Menu.activeForeground", th("bright"))
        self.root.option_add("*Menu.selectColor", th("accent"))
        self.root.option_add("*Menu.borderWidth", 0)
        self.root.option_add("*Button.background", th("input"))
        self.root.option_add("*Button.foreground", th("fg"))
        self.root.option_add("*Button.activeBackground", th("hover"))
        self.root.option_add("*Button.activeForeground", th("fg"))
        self.root.option_add("*Button.highlightBackground", th("title"))
        self.root.option_add("*Button.highlightColor", th("title"))
        self.root.option_add("*Button.borderWidth", 0)
        self.root.option_add("*Label.background", th("bg"))
        self.root.option_add("*Label.foreground", th("fg"))
        self.root.option_add("*Frame.background", th("bg"))

        def fix(w):
            try:
                if isinstance(w, tk.Button):
                    w.configure(bg=th("input"), fg=th("fg"),
                                activebackground=th("hover"), activeforeground=th("fg"),
                                highlightbackground=th("title"))
            except tk.TclError:
                pass
            for c in w.winfo_children():
                try:
                    fix(c)
                except tk.TclError:
                    pass
        fix(self.root)

    def _auto_check_update(self):
        def worker():
            try:
                data = check_update()
                remote = parse_version(data.get("version", ""))
                current = parse_version(APP_VERSION)
                if remote > current:
                    self.root.after(0, lambda: self.status_left.config(
                        text=f"Доступно обновление {data.get('version')} — Ctrl+U"))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _build_menu(self):
        mb = tk.Menu(self.root, bg=th("title"), fg=th("fg"), activebackground=th("splash_accent"),
                     activeforeground=th("bright"), bd=0, font=("Segoe UI", 9))

        file_menu = tk.Menu(mb, tearoff=0, bg=th("title"), fg=th("fg"),
                            activebackground=th("splash_accent"), activeforeground=th("bright"),
                            font=("Segoe UI", 9))
        file_menu.add_command(label="Новый файл        Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Открыть...        Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Сохранить         Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Сохранить как...  Ctrl+Shift+S", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        mb.add_cascade(label="Файл", menu=file_menu)

        edit_menu = tk.Menu(mb, tearoff=0, bg=th("title"), fg=th("fg"),
                            activebackground=th("splash_accent"), activeforeground=th("bright"),
                            font=("Segoe UI", 9))
        edit_menu.add_command(label="Отменить       Ctrl+Z", command=lambda: self.editor.edit_undo())
        edit_menu.add_command(label="Повторить       Ctrl+Y", command=lambda: self.editor.edit_redo())
        edit_menu.add_separator()
        edit_menu.add_command(label="Найти и заменить  Ctrl+H", command=self._toggle_find)
        edit_menu.add_command(label="Выделить всё     Ctrl+A",
                              command=lambda: self.editor.tag_add("sel", "1.0", tk.END))
        mb.add_cascade(label="Правка", menu=edit_menu)

        run_menu = tk.Menu(mb, tearoff=0, bg=th("title"), fg=th("fg"),
                           activebackground=th("splash_accent"), activeforeground=th("bright"),
                           font=("Segoe UI", 9))
        run_menu.add_command(label="Проверить      Ctrl+T", command=self.verify_script)
        run_menu.add_command(label="Запустить      Ctrl+R", command=self.run_script)
        run_menu.add_command(label="Компилировать  Ctrl+B", command=self.compile_script)
        mb.add_cascade(label="Запуск", menu=run_menu)

        view_menu = tk.Menu(mb, tearoff=0, bg=th("title"), fg=th("fg"),
                            activebackground=th("splash_accent"), activeforeground=th("bright"),
                            font=("Segoe UI", 9))
        view_menu.add_command(label="Проводник       Ctrl+Shift+E", command=self._toggle_sidebar)
        view_menu.add_command(label="Панель вывода   Ctrl+`", command=self._toggle_panel)
        view_menu.add_command(label="Миникарта", command=self._toggle_minimap)
        view_menu.add_separator()
        view_menu.add_command(label="Библиотеки      Ctrl+Shift+L", command=self._open_lib_manager)
        view_menu.add_separator()
        view_menu.add_radiobutton(label="Тёмная тема", value="dark",
                                  variable=self.theme_var,
                                  command=lambda: self.apply_theme("dark"))
        view_menu.add_radiobutton(label="Светлая тема", value="light",
                                  variable=self.theme_var,
                                  command=lambda: self.apply_theme("light"))
        mb.add_cascade(label="Вид", menu=view_menu)

        help_menu = tk.Menu(mb, tearoff=0, bg=th("title"), fg=th("fg"),
                            activebackground=th("splash_accent"), activeforeground=th("bright"),
                            font=("Segoe UI", 9))
        help_menu.add_command(label="О программе", command=lambda: messagebox.showinfo(
            APP_NAME, f"{APP_NAME} v{APP_VERSION}\nЯзык программирования OUT\nКомпилятор + IDE"))
        help_menu.add_separator()
        help_menu.add_command(label="Проверить обновления   Ctrl+U", command=self._open_update_dialog)
        mb.add_cascade(label="Справка", menu=help_menu)

        self.root.config(menu=mb)

    def _build_toolbar(self):
        if not hasattr(self, "toolbar") or not self.toolbar.winfo_exists():
            self.toolbar = tk.Frame(self.root, bg=th("toolbar"), height=TOOLBAR_HEIGHT)
            self.toolbar.pack(side=tk.TOP, fill=tk.X)
            self.toolbar.pack_propagate(False)
        else:
            self.toolbar.configure(bg=th("toolbar"))
            for w in self.toolbar.winfo_children():
                w.destroy()

        bs = {"font": ("Segoe UI", 9), "bd": 0, "padx": 10, "pady": 5, "cursor": "hand2",
              "activebackground": "#4a4a4a", "activeforeground": th("bright")}

        tools = [
            ("📂 Открыть", self.open_file, th("toolbar"), th("dim")),
            ("💾 Сохранить", self.save_file, th("toolbar"), th("dim")),
            (None, None, None, None),
            ("✓ Проверить", self.verify_script, "#6b2fa0", th("bright")),
            ("▶ Запустить", self.run_script, "#2e7d32", th("bright")),
            ("⚙ Компиляция", self.compile_script, "#1565c0", th("bright")),
            (None, None, None, None),
            ("📋 Копировать ошибку", self.copy_error, "#e65100", th("bright")),
        ]

        for item in tools:
            if item[0] is None:
                tk.Frame(self.toolbar, width=1, bg=th("title")).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
            else:
                tk.Button(self.toolbar, text=item[0], command=item[1],
                          bg=item[2], fg=item[3], **bs).pack(side=tk.LEFT, padx=2, pady=4)

        right = tk.Frame(self.toolbar, bg=th("toolbar"))
        right.pack(side=tk.RIGHT, padx=8)
        tk.Label(right, text="OUT Language", font=("Segoe UI", 9, "italic"),
                 fg=th("dim"), bg=th("toolbar")).pack(side=tk.RIGHT)

    def _build_tab_bar(self):
        self.tab_bar = TabBar(self.root, on_select=self._on_tab_select, on_close=self._on_tab_close)

    def _build_main_area(self):
        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=th("bg"),
                                         sashwidth=3, sashrelief=tk.FLAT, borderwidth=0)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        self.sidebar = FileExplorer(self.main_pane, on_open=self.open_file)
        self.main_pane.add(self.sidebar.frame, width=SIDEBAR_WIDTH, stretch="never")

        right_pane = tk.PanedWindow(self.main_pane, orient=tk.VERTICAL, bg=th("bg"),
                                     sashwidth=3, sashrelief=tk.FLAT, borderwidth=0)
        self.main_pane.add(right_pane, stretch="always")

        editor_frame = tk.Frame(right_pane, bg=th("bg"))

        self.editor_area = tk.Frame(editor_frame, bg=th("bg"))
        self.editor_area.pack(fill=tk.BOTH, expand=True)

        self.line_numbers = tk.Text(self.editor_area, wrap=tk.NONE, state=tk.DISABLED,
                                     font=("Consolas", 11), bg=th("sidebar"), fg=th("dim"),
                                     width=5, padx=6, takefocus=0, border=0,
                                     highlightthickness=0, cursor="arrow")
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        self.editor = tk.Text(self.editor_area, wrap=tk.NONE, undo=True,
                               font=("Consolas", 11), bg=th("bg"), fg=th("fg"),
                               insertbackground=th("caret"), border=0, highlightthickness=0,
                               selectbackground=th("selection"), padx=8)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.minimap = tk.Canvas(self.editor_area, width=MINIMAP_WIDTH, bg=th("bg"),
                                  highlightthickness=0, cursor="arrow")
        self.minimap.pack(side=tk.RIGHT, fill=tk.Y)
        self.minimap.bind("<Button-1>", self._minimap_click)

        self._setup_tags()

        self.find_dialog = FindReplaceDialog(self.editor, self.editor)

        self.output_frame = tk.Frame(right_pane, bg=th("bg"))

        panel_tabs = tk.Frame(self.output_frame, bg=th("tab"), height=28)
        panel_tabs.pack(fill=tk.X)
        panel_tabs.pack_propagate(False)

        self._panel_tab_btns = []
        for name in ["Вывод", "Проблемы"]:
            btn = tk.Label(panel_tabs, text=f"  {name}  ", font=("Segoe UI", 9),
                           fg=th("dim"), bg=th("tab"), cursor="hand2", padx=8)
            btn.pack(side=tk.LEFT)
            self._panel_tab_btns.append((name, btn))

        self.output = tk.Text(self.output_frame, wrap=tk.NONE, state=tk.DISABLED,
                               font=("Consolas", 10), bg=th("panel"), fg=th("green"), border=0,
                               highlightthickness=0, padx=8, pady=4)
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.tag_configure("error", foreground=th("error"))
        self.output.tag_configure("ok", foreground=th("green"))
        self.output.tag_configure("info", foreground=th("accent"))
        self.output.tag_configure("warn", foreground=th("warn"))

        right_pane.add(editor_frame, stretch="always")
        right_pane.add(self.output_frame, height=self._panel_height, stretch="never")

    def _build_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg=th("status"), height=STATUS_HEIGHT)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)

        self.status_left = tk.Label(self.status_bar, text="Готово", anchor="w",
                                     bg=th("status"), fg=th("bright"), font=("Segoe UI", 9), padx=10)
        self.status_left.pack(side=tk.LEFT, fill=tk.Y)

        right = tk.Frame(self.status_bar, bg=th("status"))
        right.pack(side=tk.RIGHT)

        self.cursor_pos = tk.Label(right, text="Стр 1, Стлб 1", anchor="e",
                                    bg=th("status"), fg=th("bright"), font=("Segoe UI", 9), padx=8)
        self.cursor_pos.pack(side=tk.RIGHT)

        self.lang_label = tk.Label(right, text="OUT", anchor="e",
                                    bg=th("status"), fg=th("bright"), font=("Segoe UI", 9), padx=8)
        self.lang_label.pack(side=tk.RIGHT)

        self.enc_label = tk.Label(right, text="UTF-8", anchor="e",
                                   bg=th("status"), fg=th("bright"), font=("Segoe UI", 9), padx=8)
        self.enc_label.pack(side=tk.RIGHT)

    def _setup_tags(self):
        tags = {
            "keyword": th("keyword"), "builtin": th("function"), "string": th("string"),
            "number": th("number"), "comment": th("comment"), "module": th("module"),
            "func": th("function"), "bracket": th("bracket"), "operator": th("fg"),
            "error_line": None, "current_line": th("current_line_bg"),
            "find_highlight": None,
        }
        for name, color in tags.items():
            if color and name not in ("error_line", "current_line", "find_highlight"):
                self.editor.tag_configure(name, foreground=color)
        self.editor.tag_configure("error_line", background=th("error_line_bg"))
        self.editor.tag_configure("current_line", background=th("current_line_bg"))
        self.editor.tag_configure("find_highlight", background=th("find_highlight_bg"), foreground=th("bright"))

        self.line_numbers.tag_configure("current", foreground=th("bright"), font=("Consolas", 11, "bold"))

    def _bind_keys(self):
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_as())
        self.root.bind("<Control-r>", lambda e: self.run_script())
        self.root.bind("<Control-b>", lambda e: self.compile_script())
        self.root.bind("<Control-t>", lambda e: self.verify_script())
        self.root.bind("<Control-e>", lambda e: self.copy_error())
        self.root.bind("<Control-h>", lambda e: self._toggle_find())
        self.root.bind("<Control-f>", lambda e: self._toggle_find())
        self.root.bind("<Control-grave>", lambda e: self._toggle_panel())
        self.root.bind("<Control-Shift-E>", lambda e: self._toggle_sidebar())
        self.root.bind("<Control-Shift-L>", lambda e: self._open_lib_manager())
        self.root.bind("<Control-u>", lambda e: self._open_update_dialog())
        self.root.bind("<F5>", lambda e: self.run_script())

        self.editor.bind("<KeyRelease>", self._on_key)
        self.editor.bind("<ButtonRelease-1>", lambda e: self._on_key())
        self.editor.bind("<MouseWheel>", lambda e: self._update_line_numbers())
        self.editor.bind("<Button-4>", lambda e: self._update_line_numbers())
        self.editor.bind("<Button-5>", lambda e: self._update_line_numbers())
        self.editor.bind("<Button-3>", self._show_context_menu)

        self.context_menu = tk.Menu(self.root, tearoff=0, bg=th("title"), fg=th("fg"),
                                    activebackground=th("splash_accent"), activeforeground=th("bright"),
                                    font=("Segoe UI", 9), bd=0)
        self.context_menu.add_command(label="Вырезать        Ctrl+X", command=self._cut)
        self.context_menu.add_command(label="Копировать      Ctrl+C", command=self._copy)
        self.context_menu.add_command(label="Вставить        Ctrl+V", command=self._paste)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выделить всё    Ctrl+A", command=self._select_all)
        self.context_menu.add_command(label="Отменить        Ctrl+Z", command=lambda: self.editor.edit_undo())
        self.context_menu.add_command(label="Повторить       Ctrl+Y", command=lambda: self.editor.edit_redo())
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Найти           Ctrl+F", command=self._toggle_find)
        self.context_menu.add_command(label="Комментировать  Ctrl+/", command=self._toggle_comment)

        self.editor.bind("<Control-x>", lambda e: self._cut() or "break")
        self.editor.bind("<Control-c>", lambda e: self._copy() or "break")
        self.editor.bind("<Control-v>", lambda e: self._paste() or "break")
        self.root.bind("<Control-a>", lambda e: self._select_all())
        self.root.bind("<Control-z>", lambda e: self._safe_undo())
        self.root.bind("<Control-y>", lambda e: self._safe_redo())
        self.root.bind("<Control-slash>", lambda e: self._toggle_comment())
        self.root.bind("<Tab>", lambda e: self._indent())
        self.root.bind("<Shift-Tab>", lambda e: self._dedent())
        self.root.bind("<Control-d>", lambda e: self._duplicate_line())
        self.root.bind("<Delete>", lambda e: self._delete_line())

    def _show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _cut(self):
        try:
            sel = self.editor.tag_ranges("sel")
            if sel:
                text = self.editor.get(sel[0], sel[1])
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.root.update()
                self.editor.delete(sel[0], sel[1])
        except Exception:
            pass

    def _copy(self):
        try:
            sel = self.editor.tag_ranges("sel")
            if sel:
                text = self.editor.get(sel[0], sel[1])
                if not text:
                    return
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.root.update()
                self.status_left.config(text=f"Скопировано ({len(text)} симв.)")
            else:
                line = self.editor.index(tk.INSERT).split(".")[0]
                text = self.editor.get(f"{line}.0", f"{line}.0+1line")
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.root.update()
                self.status_left.config(text=f"Скопировано: строка {line}")
        except Exception:
            pass

    def _paste(self):
        try:
            text = self.root.clipboard_get()
            sel = self.editor.tag_ranges("sel")
            if sel:
                self.editor.delete(sel[0], sel[1])
            self.editor.insert(tk.INSERT, text)
            self._on_key()
        except Exception:
            pass

    def _select_all(self):
        self.editor.tag_add("sel", "1.0", tk.END)

    def _toggle_comment(self):
        try:
            sel = self.editor.tag_ranges("sel")
            if sel:
                start_line = int(str(sel[0]).split(".")[0])
                end_line = int(str(sel[1]).split(".")[0])
            else:
                line = int(self.editor.index(tk.INSERT).split(".")[0])
                start_line = line
                end_line = line

            all_commented = True
            for ln in range(start_line, end_line + 1):
                line_text = self.editor.get(f"{ln}.0", f"{ln}.0+1line")
                stripped = line_text.lstrip()
                if not stripped.startswith("#"):
                    all_commented = False
                    break

            for ln in range(start_line, end_line + 1):
                line_text = self.editor.get(f"{ln}.0", f"{ln}.end")
                stripped = line_text.lstrip()
                indent = len(line_text) - len(stripped)
                if all_commented:
                    if stripped.startswith("# "):
                        self.editor.delete(f"{ln}.{indent}", f"{ln}.{indent + 2}")
                    elif stripped.startswith("#"):
                        self.editor.delete(f"{ln}.{indent}", f"{ln}.{indent + 1}")
                else:
                    self.editor.insert(f"{ln}.{indent}", "# ")
            self._on_key()
        except Exception:
            pass

    def _safe_undo(self):
        try:
            self.editor.edit_undo()
        except Exception:
            pass
        self._on_key()

    def _safe_redo(self):
        try:
            self.editor.edit_redo()
        except Exception:
            pass
        self._on_key()

    def _indent(self):
        sel = self.editor.tag_ranges("sel")
        if sel:
            start_line = int(str(sel[0]).split(".")[0])
            end_line = int(str(sel[1]).split(".")[0])
            for ln in range(start_line, end_line + 1):
                self.editor.insert(f"{ln}.0", "    ")
        else:
            self.editor.insert(tk.INSERT, "    ")
        return "break"

    def _dedent(self):
        sel = self.editor.tag_ranges("sel")
        if sel:
            start_line = int(str(sel[0]).split(".")[0])
            end_line = int(str(sel[1]).split(".")[0])
            for ln in range(start_line, end_line + 1):
                line_text = self.editor.get(f"{ln}.0", f"{ln}.end")
                removed = 0
                for ci, ch in enumerate(line_text):
                    if ch == " " and removed < 4:
                        self.editor.delete(f"{ln}.{ci}", f"{ln}.{ci + 1}")
                        removed += 1
                    elif ch == "\t" and removed < 4:
                        self.editor.delete(f"{ln}.{ci}", f"{ln}.{ci + 1}")
                        removed += 4
                        break
                    else:
                        break
        else:
            line_text = self.editor.get(tk.INSERT + " display linestart", tk.INSERT)
            removed = 0
            pos = self.editor.index(tk.INSERT)
            col = int(pos.split(".")[1])
            for ci in range(col - 1, -1, -1):
                ch = self.editor.get(f"{pos.split('.')[0]}.{ci}")
                if ch == " " and removed < 4:
                    self.editor.delete(f"{pos.split('.')[0]}.{ci}", f"{pos.split('.')[0]}.{ci + 1}")
                    removed += 1
                elif ch == "\t" and removed < 4:
                    self.editor.delete(f"{pos.split('.')[0]}.{ci}", f"{pos.split('.')[0]}.{ci + 1}")
                    removed += 4
                    break
                else:
                    break
        self._on_key()
        return "break"

    def _duplicate_line(self):
        line = self.editor.index(tk.INSERT).split(".")[0]
        text = self.editor.get(f"{line}.0", f"{line}.0+1line")
        self.editor.insert(f"{line}.0+1line", text)
        self._on_key()
        return "break"

    def _delete_line(self):
        sel = self.editor.tag_ranges("sel")
        if sel:
            self.editor.delete(sel[0], sel[1])
            self._on_key()
            return "break"
        line = self.editor.index(tk.INSERT).split(".")[0]
        count = int(self.editor.index("end-1c").split(".")[0])
        if count <= 1:
            self.editor.delete("1.0", "1.0+1line")
        elif int(line) >= count:
            self.editor.delete(f"{line}.0-1line", f"{line}.0")
        else:
            self.editor.delete(f"{line}.0", f"{line}.0+1line")
        self._on_key()
        return "break"

    def _on_key(self, event=None):
        self._update_line_numbers()
        self._update_cursor_pos()
        self._update_minimap()
        self._schedule_highlight()
        self._schedule_auto_save()
        self._highlight_current_line()

    def _highlight_current_line(self):
        self.editor.tag_remove("current_line", "1.0", tk.END)
        line = self.editor.index(tk.INSERT).split(".")[0]
        self.editor.tag_add("current_line", f"{line}.0", f"{line}.0+1line")
        self.editor.tag_lower("current_line")

    def _schedule_highlight(self):
        if self._highlight_id:
            self.root.after_cancel(self._highlight_id)
        self._highlight_id = self.root.after(200, self._highlight_syntax)

    def _schedule_auto_save(self):
        if self._save_id:
            self.root.after_cancel(self._save_id)
        self._save_id = self.root.after(2000, self._auto_save)

    def _auto_save(self):
        if self.current_file:
            try:
                save_text(self.current_file, self.editor.get("1.0", tk.END), self._encoding)
                self.status_left.config(text=f"Автосохранено: {os.path.basename(self.current_file)}")
            except Exception:
                pass

    def _update_line_numbers(self, event=None):
        self.line_numbers.configure(state=tk.NORMAL)
        self.line_numbers.delete("1.0", tk.END)
        count = int(self.editor.index("end-1c").split(".")[0])
        current_line = self.editor.index(tk.INSERT).split(".")[0]
        lines = []
        for i in range(1, count + 1):
            lines.append(str(i))
        self.line_numbers.insert("1.0", "\n".join(lines))
        self.line_numbers.configure(state=tk.DISABLED)
        self.line_numbers.yview_moveto(self.editor.yview()[0])

        try:
            self.line_numbers.tag_remove("current", "1.0", tk.END)
            self.line_numbers.tag_add("current", f"{current_line}.0", f"{current_line}.0+1line")
        except Exception:
            pass

    def _update_cursor_pos(self):
        try:
            pos = self.editor.index(tk.INSERT)
            line, col = pos.split(".")
            self.cursor_pos.config(text=f"Стр {line}, Стлб {int(col) + 1}")
        except Exception:
            pass

    def _update_minimap(self):
        self.minimap.delete("all")
        code = self.editor.get("1.0", tk.END)
        lines = code.split("\n")
        total = len(lines)
        if total < 1:
            return
        h = max(1, self.minimap.winfo_height())
        line_h = max(1, h / max(total, 50))

        view_start = self.editor.yview()[0]
        view_end = self.editor.yview()[1]

        for i, line in enumerate(lines):
            y = int(i * line_h)
            if y > h:
                break
            stripped = line.strip()
            if not stripped:
                continue
            indent = len(line) - len(line.lstrip())
            width = min(len(stripped) * 0.6, 80)
            x = 8 + indent * 0.8

            if stripped.startswith("#"):
                color = th("comment")
            elif stripped.startswith(("def ", "class ")):
                color = th("keyword")
            elif stripped.startswith(("if ", "for ", "while ", "try", "catch")):
                color = th("keyword")
            elif stripped.startswith(("import ", "from ")):
                color = th("module")
            elif stripped.startswith(("return ", "throw ")):
                color = th("keyword")
            elif '"' in stripped or "'" in stripped:
                color = th("string")
            else:
                color = th("minimap_plain")

            self.minimap.create_rectangle(x, y, x + width, y + max(line_h - 1, 1),
                                           fill=color, outline="")

        vp_top = int(view_start * h)
        vp_bottom = int(view_end * h)
        self.minimap.create_rectangle(0, vp_top, MINIMAP_WIDTH, vp_bottom,
                                       fill=th("viewport"), outline="", stipple="gray25")

    def _minimap_click(self, event):
        h = self.minimap.winfo_height()
        if h <= 0:
            return
        ratio = event.y / h
        code = self.editor.get("1.0", tk.END)
        total = len(code.split("\n"))
        target_line = int(ratio * total) + 1
        self.editor.see(f"{target_line}.0")
        self.editor.mark_set(tk.INSERT, f"{target_line}.0")

    def _highlight_syntax(self):
        for tag in ("keyword", "builtin", "string", "number", "comment", "module", "func", "bracket", "operator"):
            self.editor.tag_remove(tag, "1.0", tk.END)

        code = self.editor.get("1.0", tk.END)
        lines = code.split("\n")
        for i, line in enumerate(lines):
            ln = str(i + 1)
            j = 0
            in_string = False
            quote_char = ""

            while j < len(line):
                ch = line[j]

                if in_string:
                    if ch == "\\" and j + 1 < len(line):
                        j += 2
                        continue
                    if ch == quote_char:
                        in_string = False
                        self.editor.tag_add("string", f"{ln}.{j}", f"{ln}.{j + 1}")
                    j += 1
                    continue

                if ch in ('"', "'"):
                    start = j
                    in_string = True
                    quote_char = ch
                    j += 1
                    continue

                if ch == "#":
                    self.editor.tag_add("comment", f"{ln}.{j}", f"{ln}.end")
                    break

                if ch.isdigit() or (ch == "." and j + 1 < len(line) and line[j + 1].isdigit()):
                    start = j
                    while j < len(line) and (line[j].isdigit() or line[j] == "."):
                        j += 1
                    self.editor.tag_add("number", f"{ln}.{start}", f"{ln}.{j}")
                    continue

                if ch.isalpha() or ch == "_":
                    start = j
                    while j < len(line) and (line[j].isalnum() or line[j] == "_"):
                        j += 1
                    word = line[start:j]
                    if word in KEYWORDS:
                        color = KEYWORD_COLORS.get(word, th("keyword"))
                        self.editor.tag_add("keyword", f"{ln}.{start}", f"{ln}.{j}")
                    elif word in BUILTINS:
                        self.editor.tag_add("builtin", f"{ln}.{start}", f"{ln}.{j}")
                    elif word in MODULES:
                        self.editor.tag_add("module", f"{ln}.{start}", f"{ln}.{j}")
                    elif j < len(line) and line[j] == "(":
                        self.editor.tag_add("func", f"{ln}.{start}", f"{ln}.{j}")
                    continue

                if ch in ("(", ")", "{", "}", "[", "]"):
                    self.editor.tag_add("bracket", f"{ln}.{j}", f"{ln}.{j + 1}")

                if ch in ("+", "-", "*", "/", "=", "<", ">", "!", "&", "|", "?", ":", "."):
                    self.editor.tag_add("operator", f"{ln}.{j}", f"{ln}.{j + 1}")

                j += 1

        self._highlight_errors(self.editor)

    def _highlight_errors(self, text_widget):
        text_widget.tag_remove("error_line", "1.0", tk.END)
        self.error_lines = []
        content = text_widget.get("1.0", tk.END)
        for line in content.split("\n"):
            m = re.search(r"line (\d+):(\d+)", line)
            if m:
                ln = int(m.group(1))
                self.error_lines.append((ln, line.strip()))
                text_widget.tag_add("error_line", f"{ln}.0", f"{ln}.0+1line")
        if self.error_lines:
            text_widget.see(f"{self.error_lines[0][0]}.0")

    def _set_output(self, text, tag=None):
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.insert("1.0", text, tag or ())
        self.output.configure(state=tk.DISABLED)

    def _append_output(self, text, tag=None):
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text, tag or ())
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def _toggle_sidebar(self):
        if self._sidebar_visible:
            self.main_pane.forget(self.sidebar.frame)
            self._sidebar_visible = False
        else:
            self.main_pane.insert(0, self.sidebar.frame, before=self.main_pane.panes()[0])
            self._sidebar_visible = True

    def _toggle_panel(self):
        if self._panel_visible:
            self.main_pane.forget(self.output_frame)
            self._panel_visible = False
        else:
            self.main_pane.add(self.output_frame, stretch="never")
            self._panel_visible = True

    def _toggle_minimap(self):
        if self.minimap.winfo_viewable():
            self.minimap.pack_forget()
        else:
            self.minimap.pack(side=tk.RIGHT, fill=tk.Y)

    def _toggle_find(self):
        self.find_dialog.toggle()

    def _open_lib_manager(self):
        LibManagerDialog(self.root)

    def _open_update_dialog(self):
        UpdateDialog(self.root)

    def apply_theme(self, name):
        global _current_theme, KEYWORD_COLORS
        if name not in THEMES or name == _current_theme:
            return
        old = _current_theme
        _current_theme = name
        self.theme_var.set(name)
        save_theme_config(name)
        KEYWORD_COLORS = make_keyword_colors()
        self.root.configure(bg=th("bg"))
        self._apply_widget_defaults()
        self._build_menu()
        self._build_toolbar()
        _recolor_children(self.root, THEMES[old], THEMES[name])
        self.editor.configure(bg=th("bg"), fg=th("fg"),
                              insertbackground=th("caret"),
                              selectbackground=th("selection"))
        self.line_numbers.configure(bg=th("sidebar"), fg=th("dim"))
        self.minimap.configure(bg=th("bg"))
        self.output.configure(bg=th("panel"), fg=th("green"))
        self.output.tag_configure("error", foreground=th("error"))
        self.output.tag_configure("ok", foreground=th("green"))
        self.output.tag_configure("info", foreground=th("accent"))
        self.output.tag_configure("warn", foreground=th("warn"))
        self.status_bar.configure(bg=th("status"))
        if hasattr(self, 'context_menu'):
            self.context_menu.configure(bg=th("title"), fg=th("fg"),
                                        activebackground=th("splash_accent"),
                                        activeforeground=th("bright"))
        if hasattr(self, 'sidebar'):
            self.sidebar.frame.configure(bg=th("sidebar"))
            self.sidebar.tree.configure(bg=th("sidebar"))
            self.sidebar.refresh()
        self._setup_tags()
        self._highlight_syntax()
        self._update_line_numbers()
        self._update_minimap()
        if hasattr(self, 'tab_bar') and self.tab_bar.active:
            self.tab_bar.select(self.tab_bar.active)
        suffix = f" — {os.path.basename(self.current_file)}" if self.current_file else ""
        self.root.title(f"{APP_NAME}{suffix}")

    def _on_tab_select(self, tab):
        if tab and tab["path"] and os.path.exists(tab["path"]):
            self._load_file(tab["path"])

    def _on_tab_close(self):
        self.editor.delete("1.0", tk.END)
        self.current_file = ""
        self.root.title(f"{APP_NAME}")

    def new_file(self):
        self.editor.delete("1.0", tk.END)
        self.current_file = ""
        self._encoding = "utf-8"
        self.enc_label.config(text="UTF-8")
        self.root.title(f"{APP_NAME} — Новый")
        self.tab_bar.add_tab("Новый", "")
        self._update_line_numbers()

    def open_file(self, paths=None):
        if not paths:
            paths = filedialog.askopenfilenames(title="Открыть файлы (Ctrl+клик — несколько)",
                                                filetypes=[("OUT", "*.out"), ("Все файлы", "*.*")])
        if not paths:
            return
        if isinstance(paths, tuple):
            paths = list(paths)
        if not isinstance(paths, list):
            paths = [paths]
        first = True
        for path in paths:
            self._open_one(path)
            if first:
                self.first_open_dir = os.path.dirname(path)
                first = False
        if self.first_open_dir:
            self.sidebar.set_directory(self.first_open_dir)

    def _open_one(self, path):
        self._load_file(path)
        self.tab_bar.add_tab(os.path.basename(path), path)

    def _load_file(self, path):
        try:
            encoding, content = open_text(path)
        except Exception:
            return
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", content)
        self.current_file = path
        self._encoding = encoding
        self.enc_label.config(text=encoding.upper())
        self.root.title(f"{APP_NAME} — {os.path.basename(path)}")
        self._update_line_numbers()
        self._highlight_syntax()
        self._update_minimap()

    def save_file(self):
        if not self.current_file:
            return self.save_as()
        try:
            save_text(self.current_file, self.editor.get("1.0", tk.END), self._encoding)
            self.status_left.config(text=f"Сохранено: {os.path.basename(self.current_file)}")
            for t in self.tab_bar.tabs:
                if t["path"] == self.current_file:
                    t["label"].config(text=f" {os.path.basename(self.current_file)} ")
        except Exception as e:
            self.status_left.config(text=f"Ошибка: {e}")

    def save_as(self):
        path = filedialog.asksaveasfilename(title="Сохранить как",
                                             defaultextension=".out",
                                             initialfile="main.out",
                                             filetypes=[("OUT", "*.out")])
        if not path:
            return
        self.current_file = path
        self.save_file()
        self.tab_bar.add_tab(os.path.basename(path), path)

    def _save_temp(self):
        tmpdir = tempfile.mkdtemp(prefix="outide_")
        tmpfile = os.path.join(tmpdir, "main.out")
        with open(tmpfile, "w", encoding="utf-8") as f:
            f.write(self.editor.get("1.0", tk.END))
        return tmpfile

    def _run_cmd(self, args, timeout, callback):
        exe = find_out_exe()

        def worker():
            try:
                r = subprocess.run([exe] + args, capture_output=True, text=True,
                                   timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
                self._cmd_queue.put((callback, r.returncode, r.stdout + r.stderr))
            except subprocess.TimeoutExpired:
                self._cmd_queue.put((callback, 1, f"Таймаут ({timeout}с)"))
            except Exception as e:
                self._cmd_queue.put((callback, 1, str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                callback, code, out = self._cmd_queue.get_nowait()
                try:
                    callback(code, out)
                except Exception as e:
                    self._append_output(f"Ошибка обработчика: {e}\n", "error")
                    self.status_left.config(text="Ошибка обработчика")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def verify_script(self):
        self.status_left.config(text="Проверка...")
        self.status_bar.configure(bg="#6b2fa0")
        self.status_left.configure(bg="#6b2fa0")
        tmpfile = self._save_temp()
        self._set_output("$ out verify\n")

        def on_done(code, out):
            self.status_bar.configure(bg=th("status"))
            self.status_left.configure(bg=th("status"))
            if code == 0:
                self._append_output("Ошибок нет\n", "ok")
                self.status_left.config(text="Ошибок нет")
                self.editor.tag_remove("error_line", "1.0", tk.END)
            else:
                self._append_output(out, "error")
                self.last_error = out.strip()
                self.status_left.config(text="Ошибки найдены")
                self._highlight_errors(self.editor)

        self._run_cmd(["errors", tmpfile], 30, on_done)

    def run_script(self):
        self.status_left.config(text="Запуск...")
        self.status_bar.configure(bg="#2e7d32")
        self.status_left.configure(bg="#2e7d32")
        tmpfile = self._save_temp()
        self._set_output("$ out run\n")

        def on_done(code, out):
            self.status_bar.configure(bg=th("status"))
            self.status_left.configure(bg=th("status"))
            if code == 0:
                self._append_output(out, "ok")
                self.status_left.config(text="Завершено")
                self.editor.tag_remove("error_line", "1.0", tk.END)
            else:
                self._append_output(out, "error")
                self.last_error = out.strip()
                self.status_left.config(text="Ошибка выполнения")
                self._highlight_errors(self.editor)

        self._run_cmd(["run", tmpfile], 60, on_done)

    def compile_script(self):
        self.status_left.config(text="Компиляция...")
        self.status_bar.configure(bg="#1565c0")
        self.status_left.configure(bg="#1565c0")
        tmpfile = self._save_temp()
        outpath = os.path.splitext(self.current_file or tmpfile)[0] + ".exe"
        self._set_output("$ out compile\n")

        def on_done(code, out):
            self.status_bar.configure(bg=th("status"))
            self.status_left.configure(bg=th("status"))
            if code == 0 and os.path.exists(outpath):
                size = os.path.getsize(outpath) // 1024
                self._append_output(f"Готово: {outpath}\nРазмер: {size} КБ\n", "ok")
                self.status_left.config(text=f"Компилировано ({size} КБ)")
                self.editor.tag_remove("error_line", "1.0", tk.END)
            else:
                self._append_output(out, "error")
                self.last_error = out.strip()
                self.status_left.config(text="Ошибка компиляции")
                self._highlight_errors(self.editor)

        self._run_cmd(["compile", tmpfile, outpath], 60, on_done)

    def copy_error(self):
        if self.last_error:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.last_error)
            self.status_left.config(text="Ошибка скопирована")

    def copy_code(self):
        try:
            sel = self.editor.tag_ranges("sel")
            if sel:
                text = self.editor.get(sel[0], sel[1])
            else:
                text = self.editor.get("1.0", tk.END).rstrip("\n")
            if not text:
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.status_left.config(text=f"Скопировано ({len(text)} симв.)")
        except Exception:
            pass


def main():
    load_theme_config()

    def start_ide():
        root = tk.Tk()
        root.withdraw()
        OutIde(root)
        root.deiconify()

    splash = SplashScreen(lambda: start_ide())
    splash.run()


if __name__ == "__main__":
    main()
