# =============================================================================
# main.py
# The IDE — visual interface for the TypeScript compiler.
# This file only handles what the user sees and does.
# All compiler logic lives in the compiler/ package.
# =============================================================================

import tkinter as tk
from tkinter import filedialog, Menu, Frame, Text

from compiler.lexer    import Lexer
from compiler.semantic import SemanticAnalyzer


# =============================================================================
# File actions
# =============================================================================

def open_file():
    path = filedialog.askopenfilename(
        filetypes=[("TypeScript", "*.ts"), ("Text", "*.txt"), ("All", "*.*")]
    )
    if path:
        with open(path, "r") as f:
            content = f.read()
        editor.delete("1.0", "end")
        editor.insert("1.0", content)
        _update_line_numbers()

def save_file():
    path = filedialog.asksaveasfilename(
        defaultextension=".ts",
        filetypes=[("TypeScript", "*.ts"), ("Text", "*.txt"), ("All", "*.*")]
    )
    if path:
        with open(path, "w") as f:
            f.write(editor.get("1.0", "end-1c"))


# =============================================================================
# Compiler actions — these call into compiler/ and show results
# =============================================================================

def run_lexer():
    """
    Tokenizes the editor content and shows every token in the output panel.
    Useful for seeing exactly what the Lexer is producing.
    """
    source = editor.get("1.0", "end-1c")
    lexer  = Lexer(source)
    tokens = lexer.tokenize_all()

    lines = ["── Lexer output ──────────────────────────", ""]
    for token in tokens:
        if token.type.name == "END":
            continue
        label  = token.type.label or token.type.name
        prefix = f"< {token.type.name} > < {label} >"
        lines.append(f"{prefix:45}  {token.value!r}   (line {token.line})")

    _show_output(lines)

def run_semantic():
    """
    Runs the semantic analyzer on the editor content.
    """
    source   = editor.get("1.0", "end-1c")
    analyzer = SemanticAnalyzer()
    results  = analyzer.analyze(source)

    if not results:
        _show_output(["Compilation successful. No errors found."])
        return

    lines = []
    for r in results:
        lines.append(f"main.ts:{r.line} - error:  {r.message}")

    lines.append("")
    lines.append(f"Found {len(results)} error(s).")
    _show_output(lines)

def clear_output():
    _show_output([])


# =============================================================================
# UI helpers
# =============================================================================

def _show_output(lines: list[str]):
    """Writes a list of strings into the output panel."""
    output.config(state="normal")
    output.delete("1.0", "end")
    for line in lines:
        output.insert("end", line + "\n")
    output.config(state="disabled")

def _update_line_numbers(event=None):
    line_numbers.config(state="normal")
    line_numbers.delete("1.0", "end")
    count = editor.get("1.0", "end-1c").count("\n") + 1
    line_numbers.insert("1.0", "\n".join(str(i) for i in range(1, count + 1)))
    line_numbers.config(state="disabled")


# =============================================================================
# Build the window
# =============================================================================

root = tk.Tk()
root.title("TypeScript Compiler")
root.geometry("1000x720")
root.configure(bg="#2b2b2b")

# ── Menu bar ──────────────────────────────────────────────────────────────────
menu_bar = Menu(root)
root.config(menu=menu_bar)

file_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Open",  command=open_file)
file_menu.add_command(label="Save",  command=save_file)
file_menu.add_separator()
file_menu.add_command(label="Exit",  command=root.quit)

run_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Run", menu=run_menu)
run_menu.add_command(label="Tokenize       Ctrl+L", command=run_lexer)
run_menu.add_command(label="Analyze        Ctrl+R", command=run_semantic)
run_menu.add_separator()
run_menu.add_command(label="Clear output",           command=clear_output)

# ── Editor area ───────────────────────────────────────────────────────────────
editor_frame = Frame(root, bg="#1e1e1e")
editor_frame.pack(fill="both", expand=True, padx=6, pady=(6, 0))

line_numbers = Text(
    editor_frame,
    width=4, bg="#1e1e1e", fg="#858585",
    font=("Consolas", 12), state="disabled",
    takefocus=0, borderwidth=0, highlightthickness=0
)
line_numbers.pack(side="left", fill="y")

editor = Text(
    editor_frame,
    bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
    font=("Consolas", 12), borderwidth=0, highlightthickness=0,
    undo=True
)
editor.pack(side="left", fill="both", expand=True)
editor.bind("<KeyRelease>", _update_line_numbers)

# ── Toolbar ───────────────────────────────────────────────────────────────────
toolbar = Frame(root, bg="#2b2b2b")
toolbar.pack(fill="x", padx=6, pady=(4, 0))

tk.Button(
    toolbar, text="▶  Tokenize",
    command=run_lexer,
    bg="#0e639c", fg="white", font=("Consolas", 10, "bold"),
    relief="flat", padx=12, pady=4, cursor="hand2"
).pack(side="left")

tk.Button(
    toolbar, text="▶  Analyze",
    command=run_semantic,
    bg="#1e8a4a", fg="white", font=("Consolas", 10, "bold"),
    relief="flat", padx=12, pady=4, cursor="hand2"
).pack(side="left", padx=(6, 0))

tk.Button(
    toolbar, text="✕  Clear",
    command=clear_output,
    bg="#3c3c3c", fg="#cccccc", font=("Consolas", 10),
    relief="flat", padx=12, pady=4, cursor="hand2"
).pack(side="left", padx=(6, 0))

tk.Label(
    toolbar,
    text="Write TypeScript code above and click Analyze",
    bg="#2b2b2b", fg="#6a9955", font=("Consolas", 9)
).pack(side="left", padx=(14, 0))

# ── Output panel ──────────────────────────────────────────────────────────────
output_frame = Frame(root, bg="#1e1e1e", height=220)
output_frame.pack(fill="both", padx=6, pady=6)
output_frame.pack_propagate(False)

tk.Label(
    output_frame,
    text="Output", bg="#1e1e1e", fg="#9cdcfe",
    font=("Consolas", 10, "bold"), anchor="w"
).pack(fill="x", padx=8, pady=(6, 0))

output = Text(
    output_frame,
    bg="#1e1e1e", fg="#ce9178",
    font=("Consolas", 11), state="disabled",
    borderwidth=0, highlightthickness=0
)
output.pack(fill="both", expand=True, padx=8, pady=(2, 8))

# ── Keyboard shortcuts ────────────────────────────────────────────────────────
root.bind("<Control-l>", lambda e: run_lexer())
root.bind("<Control-r>", lambda e: run_semantic())

# ── Init ──────────────────────────────────────────────────────────────────────
_update_line_numbers()
root.mainloop()