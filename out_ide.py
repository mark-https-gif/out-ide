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
from tkinter import font as tkfont, filedialog, messagebox, ttk
import json


def get_base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


OUT_EXE = os.path.join(get_base_path(), "out.exe")
APP_NAME = "OUT IDE"
APP_VERSION = "0.5.1"

BG_DARK = "#1e1e1e"
BG_SIDEBAR = "#252526"
BG_PANEL = "#1e1e1e"
BG_TAB = "#2d2d2d"
BG_TAB_ACTIVE = "#1e1e1e"
BG_TITLE = "#3c3c3c"
BG_STATUS = "#007acc"
BG_STATUS_ERROR = "#c24038"
BG_TOOLBAR = "#333333"
BG_INPUT = "#3c3c3c"
FG_DARK = "#cccccc"
FG_DIM = "#858585"
FG_BRIGHT = "#ffffff"
FG_ACCENT = "#569cd6"
FG_GREEN = "#4ec9b0"
FG_STRING = "#ce9178"
FG_NUMBER = "#b5cea8"
FG_KEYWORD = "#c586c0"
FG_COMMENT = "#6a9955"
FG_FUNCTION = "#dcdcaa"
FG_MODULE = "#4ec9b0"
FG_ERROR = "#f44747"
FG_WARN = "#cca700"
FG_BRACKET = "#ffd700"
BG_ERROR_LINE = "#5a1d1d"
BG_CURRENT_LINE = "#2a2d2e"
BG_SPLASH = "#0e1525"
SPLASH_ACCENT = "#007acc"
TAB_HEIGHT = 35
STATUS_HEIGHT = 24
TOOLBAR_HEIGHT = 40
SIDEBAR_WIDTH = 260
MINIMAP_WIDTH = 100


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

KEYWORD_COLORS = {
    "def": "#c586c0", "fn": "#c586c0", "return": "#c586c0", "if": "#c586c0", "else": "#c586c0",
    "for": "#c586c0", "in": "#c586c0", "while": "#c586c0", "break": "#c586c0",
    "continue": "#c586c0", "import": "#c586c0", "from": "#c586c0",
    "true": "#569cd6", "false": "#569cd6", "null": "#569cd6",
    "and": "#569cd6", "or": "#569cd6", "not": "#569cd6",
    "try": "#c586c0", "catch": "#c586c0", "throw": "#c586c0",
    "class": "#4ec9b0", "new": "#4ec9b0", "this": "#4ec9b0", "super": "#4ec9b0",
}


class SplashScreen:
    def __init__(self, on_done):
        self.on_done = on_done
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=BG_SPLASH)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 480, 300
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.attributes("-topmost", True)

        c = tk.Canvas(self.root, width=w, height=h, bg=BG_SPLASH, highlightthickness=0)
        c.pack(fill=tk.BOTH, expand=True)

        c.create_rectangle(0, 0, w, 3, fill=SPLASH_ACCENT, outline="")

        c.create_text(w // 2, 70, text="OUT", font=("Segoe UI Light", 48),
                       fill=SPLASH_ACCENT, anchor="center")
        c.create_text(w // 2, 120, text="Language IDE", font=("Segoe UI", 14),
                       fill=FG_DIM, anchor="center")
        c.create_text(w // 2, 155, text=f"v{APP_VERSION}", font=("Segoe UI", 10),
                       fill=FG_DIM, anchor="center")

        c.create_text(w // 2, 200, text="Загрузка компонентов...",
                       font=("Segoe UI", 9), fill=FG_DIM, anchor="center", tags="loading")

        bar_w = 300
        bar_h = 4
        bx = (w - bar_w) // 2
        by = 230
        c.create_rectangle(bx, by, bx + bar_w, by + bar_h, fill="#1a1a2e", outline="")
        self.bar = c.create_rectangle(bx, by, bx, by + bar_h, fill=SPLASH_ACCENT, outline="")
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
        self.frame = tk.Frame(parent, bg=BG_SIDEBAR, width=SIDEBAR_WIDTH)
        self.frame.pack_propagate(False)
        self.current_dir = ""
        self._build()

    def _build(self):
        hdr = tk.Frame(self.frame, bg=BG_SIDEBAR)
        hdr.pack(fill=tk.X, padx=8, pady=(8, 4))
        tk.Label(hdr, text="ПРОВОДНИК", font=("Segoe UI", 10, "bold"),
                 fg=FG_DIM, bg=BG_SIDEBAR).pack(side=tk.LEFT)
        tk.Label(hdr, text="⟳", font=("Segoe UI", 11), fg=FG_DIM, bg=BG_SIDEBAR,
                 cursor="hand2").pack(side=tk.RIGHT)
        hdr.winfo_children()[-1].bind("<Button-1>", lambda e: self.refresh())

        sep = tk.Frame(self.frame, bg="#3c3c3c", height=1)
        sep.pack(fill=tk.X)

        container = tk.Frame(self.frame, bg=BG_SIDEBAR)
        container.pack(fill=tk.BOTH, expand=True)

        self.tree = tk.Canvas(container, bg=BG_SIDEBAR, highlightthickness=0)
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
                              font=("Segoe UI", 10, "bold"), fill=FG_BRIGHT, anchor="w")
        y += 22

        for d in dirs:
            if d.startswith(".") or d.startswith("__"):
                continue
            self.tree.create_text(16, y, text=f"📁 {d}", font=("Segoe UI", 9),
                                  fill=FG_DIM, anchor="w", tags=("item",))
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
                                  fill=FG_DIM, anchor="w", cursor="hand2", tags=("file",))
            fp = os.path.join(self.current_dir, f)
            self.tree.tag_bind("file", "<Button-1>", lambda e, p=fp: self._open_file(p))
            y += 22

        self.tree.configure(scrollregion=self.tree.bbox("all"))

    def _open_file(self, path):
        self.on_open(path)


class TabBar:
    def __init__(self, parent, on_select, on_close):
        self.on_select = on_select
        self.on_close = on_close
        self.tabs = []
        self.active = None
        self.frame = tk.Frame(parent, bg=BG_TAB, height=TAB_HEIGHT)
        self.frame.pack_propagate(False)
        self.container = tk.Frame(self.frame, bg=BG_TAB)
        self.container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def add_tab(self, title, filepath):
        for t in self.tabs:
            if t["path"] == filepath:
                self.select(t)
                return
        tab = {"title": title, "path": filepath, "frame": None, "label": None, "close": None}
        f = tk.Frame(self.container, bg=BG_TAB, height=TAB_HEIGHT)
        f.pack_propagate(False)
        f.pack(side=tk.LEFT, padx=(1, 0))

        inner = tk.Frame(f, bg=BG_TAB)
        inner.pack(fill=tk.BOTH, expand=True, padx=4)
        inner.pack_propagate(False)

        lbl = tk.Label(inner, text=f" {title} ", font=("Segoe UI", 9),
                        fg=FG_DIM, bg=BG_TAB, cursor="hand2")
        lbl.pack(side=tk.LEFT, fill=tk.Y)
        lbl.bind("<Button-1>", lambda e, t=tab: self.select(t))

        cls = tk.Label(inner, text="✕", font=("Segoe UI", 8), fg=FG_DIM,
                        bg=BG_TAB, cursor="hand2", padx=4)
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
                t["frame"].configure(bg=BG_TAB)
                t["label"].configure(bg=BG_TAB, fg=FG_DIM)
        if tab and tab["frame"]:
            tab["frame"].configure(bg=BG_TAB_ACTIVE)
            tab["label"].configure(bg=BG_TAB_ACTIVE, fg=FG_BRIGHT)
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
        self.frame = tk.Frame(self.editor.master, bg=BG_TITLE, bd=0)
        row1 = tk.Frame(self.frame, bg=BG_TITLE)
        row1.pack(fill=tk.X, padx=8, pady=(6, 2))

        tk.Label(row1, text="Найти:", font=("Segoe UI", 9), fg=FG_DIM,
                 bg=BG_TITLE).pack(side=tk.LEFT, padx=(0, 6))
        e1 = tk.Entry(row1, textvariable=self.find_var, font=("Consolas", 10),
                       bg=BG_INPUT, fg=FG_DARK, insertbackground="white", bd=0,
                       highlightthickness=1, highlightbackground="#555")
        e1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        e1.bind("<KeyRelease>", lambda e: self._on_change())
        e1.bind("<Return>", lambda e: self.find_next())

        tk.Label(row1, textvariable=self.match_var, font=("Segoe UI", 9),
                 fg=FG_DIM, bg=BG_TITLE, width=14).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(row1, text="▼", font=("Segoe UI", 9), bg=BG_INPUT, fg=FG_DARK,
                  bd=0, command=self.find_next, width=3).pack(side=tk.LEFT, padx=1)
        tk.Button(row1, text="▲", font=("Segoe UI", 9), bg=BG_INPUT, fg=FG_DARK,
                  bd=0, command=self.find_prev, width=3).pack(side=tk.LEFT, padx=1)
        tk.Button(row1, text="✕", font=("Segoe UI", 9), bg=BG_INPUT, fg=FG_DARK,
                  bd=0, command=self.hide, width=3).pack(side=tk.LEFT, padx=1)

        row2 = tk.Frame(self.frame, bg=BG_TITLE)
        row2.pack(fill=tk.X, padx=8, pady=(2, 6))

        tk.Label(row2, text="Заменить:", font=("Segoe UI", 9), fg=FG_DIM,
                 bg=BG_TITLE).pack(side=tk.LEFT, padx=(0, 2))
        tk.Entry(row2, textvariable=self.replace_var, font=("Consolas", 10),
                 bg=BG_INPUT, fg=FG_DARK, insertbackground="white", bd=0,
                 highlightthickness=1, highlightbackground="#555").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(row2, text="Заменить", font=("Segoe UI", 9), bg=BG_INPUT, fg=FG_DARK,
                  bd=0, command=self.replace_one).pack(side=tk.LEFT, padx=1)
        tk.Button(row2, text="Все", font=("Segoe UI", 9), bg=BG_INPUT, fg=FG_DARK,
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
        self.editor.tag_configure("find_highlight", background="#613214", foreground=FG_BRIGHT)
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


class LibManagerDialog:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Менеджер библиотек")
        self.top.geometry("700x550")
        self.top.configure(bg=BG_DARK)
        self.top.transient(parent)
        self.top.grab_set()

        self.catalog = get_catalog()
        self.installed = {lib["name"] for lib in get_installed_libs()}

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        hdr = tk.Frame(self.top, bg=BG_TITLE, height=50)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  Библиотеки OUT", font=("Segoe UI", 14, "bold"),
                 fg=FG_BRIGHT, bg=BG_TITLE).pack(side=tk.LEFT, padx=10)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_list())
        e = tk.Entry(hdr, textvariable=self.search_var, font=("Segoe UI", 10),
                      bg=BG_INPUT, fg=FG_DARK, insertbackground="white", bd=0,
                      highlightthickness=1, highlightbackground="#555", width=30)
        e.pack(side=tk.RIGHT, padx=10, pady=8)
        tk.Label(hdr, text="🔍", font=("Segoe UI", 10), fg=FG_DIM, bg=BG_TITLE).pack(side=tk.RIGHT)

        bar = tk.Frame(self.top, bg=BG_TOOLBAR, height=36)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Button(bar, text="⟳ Обновить", command=self._refresh_list,
                  font=("Segoe UI", 9), bg=BG_INPUT, fg=FG_DARK, bd=0,
                  activebackground="#4a4a4a", cursor="hand2").pack(side=tk.LEFT, padx=6, pady=4)
        tk.Button(bar, text="📂 Папка libs", command=self._open_libs_dir,
                  font=("Segoe UI", 9), bg=BG_INPUT, fg=FG_DARK, bd=0,
                  activebackground="#4a4a4a", cursor="hand2").pack(side=tk.LEFT, padx=6, pady=4)

        self.status_var = tk.StringVar(value="Готово")
        tk.Label(bar, textvariable=self.status_var, font=("Segoe UI", 9),
                 fg=FG_DIM, bg=BG_TOOLBAR).pack(side=tk.RIGHT, padx=10)

        container = tk.Frame(self.top, bg=BG_DARK)
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
        style.configure("Treeview", background=BG_DARK, foreground=FG_DARK,
                         fieldbackground=BG_DARK, font=("Segoe UI", 9), rowheight=28)
        style.configure("Treeview.Heading", background=BG_TOOLBAR, foreground=FG_DARK,
                         font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#264f78")],
                  foreground=[("selected", FG_BRIGHT)])

        sb = tk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(self.top, bg=BG_DARK)
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.install_btn = tk.Button(btn_frame, text="⬇ Установить", command=self._install_selected,
                                      font=("Segoe UI", 10, "bold"), bg="#2e7d32", fg=FG_BRIGHT,
                                      bd=0, padx=16, pady=6, activebackground="#388e3c",
                                      cursor="hand2")
        self.install_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.uninstall_btn = tk.Button(btn_frame, text="✕ Удалить", command=self._uninstall_selected,
                                        font=("Segoe UI", 10), bg="#c62828", fg=FG_BRIGHT,
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

        self.tree.tag_configure("installed", foreground=FG_GREEN)
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


class OutIde:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} — {APP_VERSION}")
        self.root.geometry("1400x850")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG_DARK)

        self.current_file = ""
        self.last_error = ""
        self.error_lines = []
        self._highlight_id = None
        self._save_id = None
        self._sidebar_visible = True
        self._panel_visible = True
        self._panel_height = 200

        self._build_menu()
        self._build_toolbar()
        self._build_tab_bar()
        self._build_main_area()
        self._build_status_bar()
        self._bind_keys()
        self._update_cursor_pos()

    def _build_menu(self):
        mb = tk.Menu(self.root, bg=BG_TITLE, fg=FG_DARK, activebackground=SPLASH_ACCENT,
                     activeforeground=FG_BRIGHT, bd=0, font=("Segoe UI", 9))

        file_menu = tk.Menu(mb, tearoff=0, bg=BG_TITLE, fg=FG_DARK,
                            activebackground=SPLASH_ACCENT, activeforeground=FG_BRIGHT,
                            font=("Segoe UI", 9))
        file_menu.add_command(label="Новый файл        Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Открыть...        Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Сохранить         Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Сохранить как...  Ctrl+Shift+S", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        mb.add_cascade(label="Файл", menu=file_menu)

        edit_menu = tk.Menu(mb, tearoff=0, bg=BG_TITLE, fg=FG_DARK,
                            activebackground=SPLASH_ACCENT, activeforeground=FG_BRIGHT,
                            font=("Segoe UI", 9))
        edit_menu.add_command(label="Отменить       Ctrl+Z", command=lambda: self.editor.edit_undo())
        edit_menu.add_command(label="Повторить       Ctrl+Y", command=lambda: self.editor.edit_redo())
        edit_menu.add_separator()
        edit_menu.add_command(label="Найти и заменить  Ctrl+H", command=self._toggle_find)
        edit_menu.add_command(label="Выделить всё     Ctrl+A",
                              command=lambda: self.editor.tag_add("sel", "1.0", tk.END))
        mb.add_cascade(label="Правка", menu=edit_menu)

        run_menu = tk.Menu(mb, tearoff=0, bg=BG_TITLE, fg=FG_DARK,
                           activebackground=SPLASH_ACCENT, activeforeground=FG_BRIGHT,
                           font=("Segoe UI", 9))
        run_menu.add_command(label="Проверить      Ctrl+T", command=self.verify_script)
        run_menu.add_command(label="Запустить      Ctrl+R", command=self.run_script)
        run_menu.add_command(label="Компилировать  Ctrl+B", command=self.compile_script)
        mb.add_cascade(label="Запуск", menu=run_menu)

        view_menu = tk.Menu(mb, tearoff=0, bg=BG_TITLE, fg=FG_DARK,
                            activebackground=SPLASH_ACCENT, activeforeground=FG_BRIGHT,
                            font=("Segoe UI", 9))
        view_menu.add_command(label="Проводник       Ctrl+Shift+E", command=self._toggle_sidebar)
        view_menu.add_command(label="Панель вывода   Ctrl+`", command=self._toggle_panel)
        view_menu.add_command(label="Миникарта", command=self._toggle_minimap)
        view_menu.add_separator()
        view_menu.add_command(label="Библиотеки      Ctrl+Shift+L", command=self._open_lib_manager)
        mb.add_cascade(label="Вид", menu=view_menu)

        help_menu = tk.Menu(mb, tearoff=0, bg=BG_TITLE, fg=FG_DARK,
                            activebackground=SPLASH_ACCENT, activeforeground=FG_BRIGHT,
                            font=("Segoe UI", 9))
        help_menu.add_command(label="О программе", command=lambda: messagebox.showinfo(
            APP_NAME, f"{APP_NAME} v{APP_VERSION}\nЯзык программирования OUT\nКомпилятор + IDE"))
        mb.add_cascade(label="Справка", menu=help_menu)

        self.root.config(menu=mb)

    def _build_toolbar(self):
        self.toolbar = tk.Frame(self.root, bg=BG_TOOLBAR, height=TOOLBAR_HEIGHT)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        self.toolbar.pack_propagate(False)

        bs = {"font": ("Segoe UI", 9), "bd": 0, "padx": 10, "pady": 5, "cursor": "hand2",
              "activebackground": "#4a4a4a", "activeforeground": FG_BRIGHT}

        tools = [
            ("📂 Открыть", self.open_file, BG_TOOLBAR, FG_DIM),
            ("💾 Сохранить", self.save_file, BG_TOOLBAR, FG_DIM),
            (None, None, None, None),
            ("✓ Проверить", self.verify_script, "#6b2fa0", FG_BRIGHT),
            ("▶ Запустить", self.run_script, "#2e7d32", FG_BRIGHT),
            ("⚙ Компиляция", self.compile_script, "#1565c0", FG_BRIGHT),
            (None, None, None, None),
            ("📋 Копировать ошибку", self.copy_error, "#e65100", FG_BRIGHT),
        ]

        for item in tools:
            if item[0] is None:
                tk.Frame(self.toolbar, width=1, bg="#555").pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
            else:
                tk.Button(self.toolbar, text=item[0], command=item[1],
                          bg=item[2], fg=item[3], **bs).pack(side=tk.LEFT, padx=2, pady=4)

        right = tk.Frame(self.toolbar, bg=BG_TOOLBAR)
        right.pack(side=tk.RIGHT, padx=8)
        tk.Label(right, text="OUT Language", font=("Segoe UI", 9, "italic"),
                 fg=FG_DIM, bg=BG_TOOLBAR).pack(side=tk.RIGHT)

    def _build_tab_bar(self):
        self.tab_bar = TabBar(self.root, on_select=self._on_tab_select, on_close=self._on_tab_close)

    def _build_main_area(self):
        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=BG_DARK,
                                         sashwidth=3, sashrelief=tk.FLAT, borderwidth=0)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        self.sidebar = FileExplorer(self.main_pane, on_open=self.open_file)
        self.main_pane.add(self.sidebar.frame, width=SIDEBAR_WIDTH, stretch="never")

        right_pane = tk.PanedWindow(self.main_pane, orient=tk.VERTICAL, bg=BG_DARK,
                                     sashwidth=3, sashrelief=tk.FLAT, borderwidth=0)
        self.main_pane.add(right_pane, stretch="always")

        editor_frame = tk.Frame(right_pane, bg=BG_DARK)

        self.editor_area = tk.Frame(editor_frame, bg=BG_DARK)
        self.editor_area.pack(fill=tk.BOTH, expand=True)

        self.line_numbers = tk.Text(self.editor_area, wrap=tk.NONE, state=tk.DISABLED,
                                     font=("Consolas", 11), bg=BG_SIDEBAR, fg=FG_DIM,
                                     width=5, padx=6, takefocus=0, border=0,
                                     highlightthickness=0, cursor="arrow")
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        self.editor = tk.Text(self.editor_area, wrap=tk.NONE, undo=True,
                               font=("Consolas", 11), bg=BG_DARK, fg=FG_DARK,
                               insertbackground="white", border=0, highlightthickness=0,
                               selectbackground="#264f78", padx=8)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.minimap = tk.Canvas(self.editor_area, width=MINIMAP_WIDTH, bg=BG_DARK,
                                  highlightthickness=0, cursor="arrow")
        self.minimap.pack(side=tk.RIGHT, fill=tk.Y)
        self.minimap.bind("<Button-1>", self._minimap_click)

        self._setup_tags()

        self.find_dialog = FindReplaceDialog(self.editor, self.editor)

        self.output_frame = tk.Frame(right_pane, bg=BG_DARK)

        panel_tabs = tk.Frame(self.output_frame, bg=BG_TAB, height=28)
        panel_tabs.pack(fill=tk.X)
        panel_tabs.pack_propagate(False)

        self._panel_tab_btns = []
        for name in ["Вывод", "Проблемы"]:
            btn = tk.Label(panel_tabs, text=f"  {name}  ", font=("Segoe UI", 9),
                           fg=FG_DIM, bg=BG_TAB, cursor="hand2", padx=8)
            btn.pack(side=tk.LEFT)
            self._panel_tab_btns.append((name, btn))

        self.output = tk.Text(self.output_frame, wrap=tk.NONE, state=tk.DISABLED,
                               font=("Consolas", 10), bg=BG_PANEL, fg=FG_GREEN, border=0,
                               highlightthickness=0, padx=8, pady=4)
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.tag_configure("error", foreground=FG_ERROR)
        self.output.tag_configure("ok", foreground=FG_GREEN)
        self.output.tag_configure("info", foreground=FG_ACCENT)
        self.output.tag_configure("warn", foreground=FG_WARN)

        right_pane.add(editor_frame, stretch="always")
        right_pane.add(self.output_frame, height=self._panel_height, stretch="never")

    def _build_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg=BG_STATUS, height=STATUS_HEIGHT)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)

        self.status_left = tk.Label(self.status_bar, text="Готово", anchor="w",
                                     bg=BG_STATUS, fg=FG_BRIGHT, font=("Segoe UI", 9), padx=10)
        self.status_left.pack(side=tk.LEFT, fill=tk.Y)

        right = tk.Frame(self.status_bar, bg=BG_STATUS)
        right.pack(side=tk.RIGHT)

        self.cursor_pos = tk.Label(right, text="Стр 1, Стлб 1", anchor="e",
                                    bg=BG_STATUS, fg=FG_BRIGHT, font=("Segoe UI", 9), padx=8)
        self.cursor_pos.pack(side=tk.RIGHT)

        self.lang_label = tk.Label(right, text="OUT", anchor="e",
                                    bg=BG_STATUS, fg=FG_BRIGHT, font=("Segoe UI", 9), padx=8)
        self.lang_label.pack(side=tk.RIGHT)

        self.enc_label = tk.Label(right, text="UTF-8", anchor="e",
                                   bg=BG_STATUS, fg=FG_BRIGHT, font=("Segoe UI", 9), padx=8)
        self.enc_label.pack(side=tk.RIGHT)

    def _setup_tags(self):
        tags = {
            "keyword": FG_KEYWORD, "builtin": FG_FUNCTION, "string": FG_STRING,
            "number": FG_NUMBER, "comment": FG_COMMENT, "module": FG_MODULE,
            "func": FG_FUNCTION, "bracket": FG_BRACKET, "operator": FG_DARK,
            "error_line": None, "current_line": BG_CURRENT_LINE,
            "find_highlight": None,
        }
        for name, color in tags.items():
            if color and name not in ("error_line", "current_line", "find_highlight"):
                self.editor.tag_configure(name, foreground=color)
        self.editor.tag_configure("error_line", background=BG_ERROR_LINE)
        self.editor.tag_configure("current_line", background=BG_CURRENT_LINE)
        self.editor.tag_configure("find_highlight", background="#613214", foreground=FG_BRIGHT)

        self.line_numbers.tag_configure("current", foreground=FG_BRIGHT, font=("Consolas", 11, "bold"))

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
        self.root.bind("<F5>", lambda e: self.run_script())

        self.editor.bind("<KeyRelease>", self._on_key)
        self.editor.bind("<ButtonRelease-1>", lambda e: self._on_key())
        self.editor.bind("<MouseWheel>", lambda e: self._update_line_numbers())
        self.editor.bind("<Button-4>", lambda e: self._update_line_numbers())
        self.editor.bind("<Button-5>", lambda e: self._update_line_numbers())
        self.editor.bind("<Button-3>", self._show_context_menu)

        self.context_menu = tk.Menu(self.root, tearoff=0, bg=BG_TITLE, fg=FG_DARK,
                                    activebackground=SPLASH_ACCENT, activeforeground=FG_BRIGHT,
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

        self.root.bind("<Control-x>", lambda e: self._cut())
        self.root.bind("<Control-c>", lambda e: self._copy())
        self.root.bind("<Control-v>", lambda e: self._paste())
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
                self.editor.delete(sel[0], sel[1])
        except Exception:
            pass

    def _copy(self):
        try:
            sel = self.editor.tag_ranges("sel")
            if sel:
                text = self.editor.get(sel[0], sel[1])
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
            else:
                line = self.editor.index(tk.INSERT).split(".")[0]
                text = self.editor.get(f"{line}.0", f"{line}.0+1line")
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
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
                with open(self.current_file, "w", encoding="utf-8") as f:
                    f.write(self.editor.get("1.0", tk.END))
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
                color = FG_COMMENT
            elif stripped.startswith(("def ", "class ")):
                color = FG_KEYWORD
            elif stripped.startswith(("if ", "for ", "while ", "try", "catch")):
                color = "#c586c0"
            elif stripped.startswith(("import ", "from ")):
                color = FG_MODULE
            elif stripped.startswith(("return ", "throw ")):
                color = FG_KEYWORD
            elif '"' in stripped or "'" in stripped:
                color = FG_STRING
            else:
                color = "#555555"

            self.minimap.create_rectangle(x, y, x + width, y + max(line_h - 1, 1),
                                           fill=color, outline="")

        vp_top = int(view_start * h)
        vp_bottom = int(view_end * h)
        self.minimap.create_rectangle(0, vp_top, MINIMAP_WIDTH, vp_bottom,
                                       fill="#ffffff", outline="", stipple="gray25")

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
                        color = KEYWORD_COLORS.get(word, FG_KEYWORD)
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
        self.root.title(f"{APP_NAME} — Новый")
        self.tab_bar.add_tab("Новый", "")
        self._update_line_numbers()

    def open_file(self, path=None):
        if not path:
            path = filedialog.askopenfilename(title="Открыть файл",
                                               filetypes=[("OUT", "*.out"), ("Все файлы", "*.*")])
        if not path:
            return
        self._load_file(path)
        self.tab_bar.add_tab(os.path.basename(path), path)
        self.sidebar.set_directory(os.path.dirname(path))

    def _load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                content = f.read()
        except Exception:
            return
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", content)
        self.current_file = path
        self.root.title(f"{APP_NAME} — {os.path.basename(path)}")
        self._update_line_numbers()
        self._highlight_syntax()
        self._update_minimap()

    def save_file(self):
        if not self.current_file:
            return self.save_as()
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.editor.get("1.0", tk.END))
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
                self.root.after(0, callback, r.returncode, r.stdout + r.stderr)
            except subprocess.TimeoutExpired:
                self.root.after(0, callback, 1, f"Таймаут ({timeout}с)")
            except Exception as e:
                self.root.after(0, callback, 1, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def verify_script(self):
        self.status_left.config(text="Проверка...")
        self.status_bar.configure(bg="#6b2fa0")
        self.status_left.configure(bg="#6b2fa0")
        tmpfile = self._save_temp()
        self._set_output("$ out verify\n")

        def on_done(code, out):
            self.status_bar.configure(bg=BG_STATUS)
            self.status_left.configure(bg=BG_STATUS)
            if code == 0:
                self._append_output("Ошибок нет\n", "ok")
                self.status_left.config(text="Ошибок нет")
                self.editor.tag_remove("error_line", "1.0", tk.END)
            else:
                self._append_output(out, "error")
                self.last_error = out.strip()
                self.status_left.config(text="Ошибки найдены")
                self._highlight_errors(self.editor)

        self._run_cmd(["run", tmpfile], 30, on_done)

    def run_script(self):
        self.status_left.config(text="Запуск...")
        self.status_bar.configure(bg="#2e7d32")
        self.status_left.configure(bg="#2e7d32")
        tmpfile = self._save_temp()
        self._set_output("$ out run\n")

        def on_done(code, out):
            self.status_bar.configure(bg=BG_STATUS)
            self.status_left.configure(bg=BG_STATUS)
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
            self.status_bar.configure(bg=BG_STATUS)
            self.status_left.configure(bg=BG_STATUS)
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


def main():
    def start_ide():
        root = tk.Tk()
        root.withdraw()
        OutIde(root)
        root.deiconify()

    splash = SplashScreen(lambda: start_ide())
    splash.run()


if __name__ == "__main__":
    main()
