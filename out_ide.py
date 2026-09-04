import os
import re
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import scrolledtext


def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


OUT_EXE = os.path.join(get_base_path(), "out.exe")


def find_out_exe():
    if os.path.exists(OUT_EXE):
        return OUT_EXE
    for p in ("..", "out-lang", "."):
        cand = os.path.join(os.path.dirname(os.path.abspath(__file__)), p, "out.exe")
        if os.path.exists(cand):
            return cand
    return "out.exe"


LIBS = {
    "ФАЙЛЫ": [("fs", "read(), write()"), ("path", "join(), dir()"), ("os", "env()")],
    "ДАННЫЕ": [("json", "parse(), stringify()"), ("csv", "read(), write()")],
    "СЕТЬ": [("http", "get(), post()"), ("socket", "tcp(), udp()")],
    "МАТЕМ": [("math", "abs(), sqrt(), sin()"), ("random", "int(), float()")],
    "ГРАФИКА": [("graphics", "line(), rect()"), ("gui", "window(), button()")],
    "УТИЛИТЫ": [("strings", "trim(), split()"), ("array", "filter(), map()"), ("logging", "info(), error()")],
    "ЖЕЛЕЗО": [("dev", "board(), pinMode()"), ("serial", "open(), read()")],
}

KEYWORDS = (
    "def", "return", "if", "else", "for", "in", "while", "break", "continue",
    "import", "from", "as", "true", "false", "null", "and", "or", "not",
    "class", "new", "this", "super", "try", "catch", "throw",
)
BUILTINS = (
    "print", "len", "str", "int", "float", "type", "range", "error",
)
MODULES = (
    "os", "json", "http", "math", "random", "crypto", "files", "strings",
    "strconv", "list", "env", "time", "dev", "serial", "console", "logging",
    "array", "dict", "shell", "graphics", "gui", "plot", "socket",
)

COLORS = {
    "keyword": "#c586c0", "builtin": "#dcdcaa", "string": "#ce9178",
    "number": "#b5cea8", "comment": "#6a9955", "module": "#4ec9b0",
    "operator": "#d4d4d4", "bracket": "#ffd700", "func": "#dcdcaa",
    "bg": "#1e1e1e", "fg": "#d4d4d4", "line_bg": "#252526",
    "error_line": "#3a1d1d", "toolbar": "#2d2d2d", "output_bg": "#0c0c0c",
    "output_fg": "#00ff00", "error_fg": "#f44747", "ok_fg": "#4ec9b0",
}


class OutIde:
    def __init__(self, root):
        self.root = root
        self.current_file = ""
        self.last_error = ""
        self.error_lines = []
        self._auto_save_id = None
        root.title("OUT IDE")
        root.geometry("1200x750")
        root.minsize(800, 500)
        root.configure(bg=COLORS["bg"])

        self._build_toolbar()
        self._build_main()
        self._build_status()
        self._bind_keys()
        self._update_lines()

    def _build_toolbar(self):
        tb = tk.Frame(self.root, bg=COLORS["toolbar"], height=36)
        tb.pack(side=tk.TOP, fill=tk.X)
        tb.pack_propagate(False)
        bs = {"font": ("Consolas", 9), "bd": 0, "padx": 8, "pady": 3, "cursor": "hand2"}

        tk.Button(tb, text="📂 Открыть", command=self.open_file, bg="#3c3c3c", fg="white", **bs).pack(side=tk.LEFT, padx=2, pady=4)
        tk.Button(tb, text="💾 Сохранить", command=self.save_file, bg="#3c3c3c", fg="white", **bs).pack(side=tk.LEFT, padx=2, pady=4)
        tk.Frame(tb, width=2, bg="#555").pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=4)
        tk.Button(tb, text="✓ Проверить", command=self.verify_script, bg="#9C27B0", fg="white", **bs).pack(side=tk.LEFT, padx=2, pady=4)
        tk.Button(tb, text="▶ Запустить", command=self.run_script, bg="#4CAF50", fg="white", **bs).pack(side=tk.LEFT, padx=2, pady=4)
        tk.Button(tb, text="⚙ Компилировать", command=self.compile_script, bg="#2196F3", fg="white", **bs).pack(side=tk.LEFT, padx=2, pady=4)
        tk.Frame(tb, width=2, bg="#555").pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=4)
        tk.Button(tb, text="📋 Ошибка", command=self.copy_error, bg="#FF9800", fg="white", **bs).pack(side=tk.LEFT, padx=2, pady=4)

    def _build_main(self):
        pw = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=COLORS["bg"], sashwidth=4, sashrelief=tk.FLAT)
        pw.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        epw = tk.PanedWindow(pw, orient=tk.VERTICAL, bg=COLORS["bg"], sashwidth=4, sashrelief=tk.FLAT)

        ef = tk.Frame(epw, bg=COLORS["bg"])
        self.line_numbers = tk.Text(ef, wrap=tk.NONE, state=tk.DISABLED, font=("Consolas", 11),
                                     bg=COLORS["line_bg"], fg="#858585", width=4, padx=4,
                                     takefocus=0, border=0, highlightthickness=0)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        self.editor = tk.Text(ef, wrap=tk.NONE, undo=True, font=("Consolas", 11),
                               bg=COLORS["bg"], fg=COLORS["fg"], insertbackground="white",
                               border=0, highlightthickness=0)
        self.editor.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        ef.pack(fill=tk.BOTH, expand=True)
        epw.add(ef, stretch="always")

        self.editor.tag_configure("keyword", foreground=COLORS["keyword"])
        self.editor.tag_configure("builtin", foreground=COLORS["builtin"])
        self.editor.tag_configure("string", foreground=COLORS["string"])
        self.editor.tag_configure("number", foreground=COLORS["number"])
        self.editor.tag_configure("comment", foreground=COLORS["comment"])
        self.editor.tag_configure("module", foreground=COLORS["module"])
        self.editor.tag_configure("func", foreground=COLORS["func"])
        self.editor.tag_configure("bracket", foreground=COLORS["bracket"])
        self.editor.tag_configure("error_line", background=COLORS["error_line"])

        self.output = tk.Text(epw, wrap=tk.NONE, state=tk.DISABLED, font=("Consolas", 11),
                               bg=COLORS["output_bg"], fg=COLORS["output_fg"], border=0)
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.tag_configure("error", foreground=COLORS["error_fg"])
        self.output.tag_configure("ok", foreground=COLORS["ok_fg"])
        self.output.tag_configure("info", foreground="#569cd6")
        epw.add(self.output, stretch="always")
        epw.paneconfigure(ef, height=400)

        pw.add(epw, stretch="always")

        lf = tk.Frame(pw, bg="#252526", width=250)
        lc = tk.Canvas(lf, bg="#252526", highlightthickness=0)
        ls = tk.Scrollbar(lf, orient=tk.VERTICAL, command=lc.yview)
        li = tk.Frame(lc, bg="#252526")
        li.bind("<Configure>", lambda e: lc.configure(scrollregion=lc.bbox("all")))
        lc.create_window((0, 0), window=li, anchor="nw")
        lc.configure(yscrollcommand=ls.set)
        for cat, items in LIBS.items():
            tk.Label(li, text=cat, font=("Consolas", 9, "bold"), fg="#569cd6", bg="#252526", anchor="w").pack(fill=tk.X, padx=5, pady=(8, 2))
            for name, desc in items:
                row = tk.Frame(li, bg="#252526")
                row.pack(fill=tk.X, padx=5)
                lbl = tk.Label(row, text=f"  {name}", font=("Consolas", 9), fg="#4ec9b0", bg="#252526", anchor="w", cursor="hand2")
                lbl.pack(side=tk.LEFT)
                lbl.bind("<Double-Button-1>", lambda e, n=name: self._insert_lib(n))
                tk.Label(row, text=f" {desc}", font=("Consolas", 7), fg="#808080", bg="#252526", anchor="w", wraplength=160).pack(side=tk.LEFT, fill=tk.X)
        ls.pack(side=tk.RIGHT, fill=tk.Y)
        lc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lf.pack(fill=tk.BOTH, expand=False)
        pw.add(lf, stretch="never")

    def _build_status(self):
        s = tk.Frame(self.root, bg=COLORS["toolbar"], height=30)
        s.pack(side=tk.BOTTOM, fill=tk.X)
        s.pack_propagate(False)
        self.status = tk.Label(s, text="Готово", anchor="w", bg="#007acc", fg="white",
                               font=("Consolas", 9), padx=8)
        self.status.pack(fill=tk.BOTH, expand=True)

    def _bind_keys(self):
        self.root.bind("<Control-r>", lambda e: self.run_script())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-b>", lambda e: self.compile_script())
        self.root.bind("<Control-t>", lambda e: self.verify_script())
        self.root.bind("<Control-e>", lambda e: self.copy_error())
        self.editor.bind("<KeyRelease>", self._on_key)
        self.editor.bind("<MouseWheel>", lambda e: self._update_lines())
        self.editor.bind("<ButtonRelease-1>", lambda e: self._update_lines())

    def _on_key(self, event=None):
        self._update_lines()
        self._schedule_highlight()
        self._schedule_auto_save()

    def _schedule_highlight(self):
        if self._auto_save_id:
            self.root.after_cancel(self._auto_save_id)
        self._auto_save_id = self.root.after(300, self._highlight_syntax)

    def _schedule_auto_save(self):
        if hasattr(self, '_save_id') and self._save_id:
            self.root.after_cancel(self._save_id)
        self._save_id = self.root.after(2000, self._auto_save)

    def _auto_save(self):
        if self.current_file:
            try:
                with open(self.current_file, "w", encoding="utf-8") as f:
                    f.write(self.editor.get("1.0", tk.END))
                self.status.config(text=f"Автосохранено: {os.path.basename(self.current_file)}")
            except Exception:
                pass

    def _update_lines(self, event=None):
        self.line_numbers.configure(state=tk.NORMAL)
        self.line_numbers.delete("1.0", tk.END)
        count = int(self.editor.index("end-1c").split(".")[0])
        self.line_numbers.insert("1.0", "\n".join(str(i) for i in range(1, count + 1)))
        self.line_numbers.configure(state=tk.DISABLED)
        self.line_numbers.yview_moveto(self.editor.yview()[0])

    def _highlight_syntax(self):
        for tag in ("keyword", "builtin", "string", "number", "comment", "module", "func", "bracket"):
            self.editor.tag_remove(tag, "1.0", tk.END)

        code = self.editor.get("1.0", tk.END)
        lines = code.split("\n")
        for i, line in enumerate(lines):
            ln = f"{i + 1}"
            in_string = False
            quote_char = ""
            j = 0
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

                if ch.isdigit() or (ch == '.' and j + 1 < len(line) and line[j + 1].isdigit()):
                    start = j
                    while j < len(line) and (line[j].isdigit() or line[j] == '.'):
                        j += 1
                    self.editor.tag_add("number", f"{ln}.{start}", f"{ln}.{j}")
                    continue

                if ch.isalpha() or ch == '_':
                    start = j
                    while j < len(line) and (line[j].isalnum() or line[j] == '_'):
                        j += 1
                    word = line[start:j]
                    if word in KEYWORDS:
                        self.editor.tag_add("keyword", f"{ln}.{start}", f"{ln}.{j}")
                    elif word in BUILTINS:
                        self.editor.tag_add("builtin", f"{ln}.{start}", f"{ln}.{j}")
                    elif word in MODULES:
                        self.editor.tag_add("module", f"{ln}.{start}", f"{ln}.{j}")
                    elif j < len(line) and line[j] == '(':
                        self.editor.tag_add("func", f"{ln}.{start}", f"{ln}.{j}")
                    continue

                if ch in ("(", ")", "{", "}", "[", "]"):
                    self.editor.tag_add("bracket", f"{ln}.{j}", f"{ln}.{j + 1}")

                j += 1

    def _highlight_errors(self, text):
        self.editor.tag_remove("error_line", "1.0", tk.END)
        self.error_lines = []
        for line in text.split("\n"):
            m = re.search(r"line (\d+):(\d+)", line)
            if m:
                ln = int(m.group(1))
                self.error_lines.append((ln, line.strip()))
                self.editor.tag_add("error_line", f"{ln}.0", f"{ln}.0+1line")
        if self.error_lines:
            self.editor.see(f"{self.error_lines[0][0]}.0")

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

    def _insert_lib(self, name):
        self.editor.insert(tk.INSERT, name + "::")
        self.editor.focus_set()

    def copy_error(self):
        if self.last_error:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.last_error)
            self.status.config(text="Скопировано")

    def open_file(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(title="Открыть", filetypes=[("OUT", "*.out"), ("Все", "*.*")])
        if not path:
            return
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            self.editor.delete("1.0", tk.END)
            self.editor.insert("1.0", f.read())
        self.current_file = path
        self.root.title(f"OUT IDE — {os.path.basename(path)}")
        self._update_lines()
        self._highlight_syntax()

    def save_file(self):
        from tkinter import filedialog
        if not self.current_file:
            path = filedialog.asksaveasfilename(title="Сохранить", defaultextension=".out",
                                                 initialfile="main.out", filetypes=[("OUT", "*.out")])
            if not path:
                return
            self.current_file = path
        with open(self.current_file, "w", encoding="utf-8") as f:
            f.write(self.editor.get("1.0", tk.END))
        self.root.title(f"OUT IDE — {os.path.basename(self.current_file)}")
        self.status.config(text=f"Сохранено: {os.path.basename(self.current_file)}")

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
        self.status.config(text="Проверка...")
        tmpfile = self._save_temp()
        self._set_output("$ out verify\n")
        self.last_error = ""

        def on_done(code, out):
            if code == 0:
                self._append_output("✓ Ошибок нет\n", "ok")
                self.status.config(text="✓ Ошибок нет")
                self.editor.tag_remove("error_line", "1.0", tk.END)
            else:
                for l in out.strip().split("\n"):
                    self._append_output(f"  ✗ {l}\n", "error")
                self.last_error = out.strip()
                self.status.config(text=f"✗ Ошибки найдены")
                self._highlight_errors(out)

        self._run_cmd(["run", tmpfile], 30, on_done)

    def run_script(self):
        self.status.config(text="Запуск...")
        tmpfile = self._save_temp()
        self._set_output("$ out run\n")
        self.last_error = ""

        def on_done(code, out):
            if code == 0:
                self._append_output(out, "ok")
                self.status.config(text="✓ Завершено")
                self.editor.tag_remove("error_line", "1.0", tk.END)
            else:
                self._append_output(out, "error")
                self.last_error = out.strip()
                self.status.config(text=f"✗ Ошибка")
                self._highlight_errors(out)

        self._run_cmd(["run", tmpfile], 60, on_done)

    def compile_script(self):
        self.status.config(text="Компиляция...")
        tmpfile = self._save_temp()
        outpath = os.path.splitext(self.current_file or tmpfile)[0] + ".exe"
        self._set_output("$ out compile\n")
        self.last_error = ""

        def on_done(code, out):
            if code == 0 and os.path.exists(outpath):
                size = os.path.getsize(outpath) // 1024
                self._append_output(f"✓ Готово: {outpath}\n  Размер: {size} КБ\n", "ok")
                self.status.config(text=f"✓ {size} КБ")
                self.editor.tag_remove("error_line", "1.0", tk.END)
            else:
                for l in out.strip().split("\n"):
                    self._append_output(f"  ✗ {l}\n", "error")
                self.last_error = out.strip()
                self.status.config(text="✗ Ошибка компиляции")
                self._highlight_errors(out)

        self._run_cmd(["compile", tmpfile, outpath], 60, on_done)


def main():
    root = tk.Tk()
    OutIde(root)
    root.mainloop()


if __name__ == "__main__":
    main()
