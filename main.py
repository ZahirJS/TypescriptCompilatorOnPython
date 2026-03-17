# =============================================================================
# main.py
# The IDE — visual interface for the TypeScript compiler.
# This file only handles what the user sees and does.
# All compiler logic lives in the compiler/ package.
# =============================================================================

import tkinter as tk
from tkinter import filedialog, Menu, Frame, Text

from compiler.lexer     import Lexer
from compiler.parser    import Parser
from compiler.semantic  import SemanticAnalyzer


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
# Compiler actions
# =============================================================================

def run_compile():
    """
    Runs all three phases in order and shows only errors and warnings.
    This is what a real compiler shows the user — silence means success.
    """
    source = editor.get("1.0", "end-1c")

    # phase 1 — parser checks structure
    structure_errors = [
        (r.line, "error", r.message)
        for r in Parser().parse(source)
        if not r.is_valid
    ]

    # phase 2 — semantic checks meaning
    semantic_results = [
        (r.line, r.severity, r.message)
        for r in SemanticAnalyzer().analyze(source)
    ]

    # combine and sort by line number
    all_results = sorted(structure_errors + semantic_results, key=lambda r: r[0])

    if not all_results:
        _show_output(["Compilation successful. No errors found."])
        return

    lines = []
    for line_number, severity, message in all_results:
        lines.append(f"main.ts:{line_number} - {severity}:  {message}")

    errors   = [r for r in all_results if r[1] == "error"]
    warnings = [r for r in all_results if r[1] == "warning"]
    lines.append("")
    lines.append(f"Found {len(errors)} error(s), {len(warnings)} warning(s).")
    _show_output(lines)


def run_lexer():
    """
    Shows every token the Lexer produces from the source code.
    Useful for inspecting what the compiler sees before any validation.
    """
    source = editor.get("1.0", "end-1c")
    tokens = Lexer(source).tokenize_all()

    lines = ["── Lexer output ──────────────────────────────────────", ""]
    for token in tokens:
        if token.type.name == "END":
            continue
        label  = token.type.label
        prefix = f"< {token.type.name} > < {label} >"
        lines.append(f"{prefix:50}  {token.value!r}   (line {token.line})")

    _show_output(lines)


def run_parser():
    """
    Shows the structural analysis of every line — valid and invalid.
    Useful for seeing whether each line matches a known pattern.
    """
    source  = editor.get("1.0", "end-1c")
    results = Parser().parse(source)

    lines = ["── Parser output ─────────────────────────────────────", ""]
    for r in results:
        status = "ok   " if r.is_valid else "error"
        lines.append(f"line {r.line:<4}  [{status}]  {r.pattern:<24}  {r.message}")

    _show_output(lines)


def run_semantic():
    """
    Shows only semantic errors and warnings — undeclared variables,
    ambiguous declarations, and invalid types.
    """
    source  = editor.get("1.0", "end-1c")
    results = SemanticAnalyzer().analyze(source)

    if not results:
        _show_output(["── Semantic output ───────────────────────────────────", "", "No semantic issues found."])
        return

    lines = ["── Semantic output ───────────────────────────────────", ""]
    for r in results:
        lines.append(f"main.ts:{r.line} - {r.severity}:  {r.message}")

    errors   = [r for r in results if r.is_error()]
    warnings = [r for r in results if r.is_warning()]
    lines.append("")
    lines.append(f"Found {len(errors)} error(s), {len(warnings)} warning(s).")
    _show_output(lines)


def run_symbol_table():
    """
    Runs the semantic analyzer and shows only the symbol table —
    every variable that was successfully declared and its type.
    """
    source   = editor.get("1.0", "end-1c")
    analyzer = SemanticAnalyzer()
    analyzer.analyze(source)  # populate the symbol table

    entries = analyzer.symbol_table.all_entries()
    lines   = ["── Symbol Table ──────────────────────────────────────", ""]

    if not entries:
        lines.append("  (no variables declared)")
    else:
        lines.append(f"  {'Name':<20} {'Type':<12} {'Line'}")
        lines.append(f"  {'─'*20} {'─'*12} {'─'*4}")
        for name, info in entries.items():
            lines.append(f"  {name:<20} {info['type']:<12} {info['line']}")

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
run_menu.add_command(label="Compile          Ctrl+B", command=run_compile)
run_menu.add_separator()
run_menu.add_command(label="Lexer            Ctrl+L", command=run_lexer)
run_menu.add_command(label="Parser           Ctrl+P", command=run_parser)
run_menu.add_command(label="Semantic         Ctrl+S", command=run_semantic)
run_menu.add_command(label="Symbol Table     Ctrl+T", command=run_symbol_table)
run_menu.add_separator()
run_menu.add_command(label="Clear output",             command=clear_output)

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
    toolbar, text="▶  Compile",
    command=run_compile,
    bg="#0e639c", fg="white", font=("Consolas", 10, "bold"),
    relief="flat", padx=12, pady=4, cursor="hand2"
).pack(side="left")

tk.Button(
    toolbar, text="Lexer",
    command=run_lexer,
    bg="#3c3c3c", fg="#cccccc", font=("Consolas", 10),
    relief="flat", padx=12, pady=4, cursor="hand2"
).pack(side="left", padx=(6, 0))

tk.Button(
    toolbar, text="Parser",
    command=run_parser,
    bg="#3c3c3c", fg="#cccccc", font=("Consolas", 10),
    relief="flat", padx=12, pady=4, cursor="hand2"
).pack(side="left", padx=(6, 0))

tk.Button(
    toolbar, text="Semantic",
    command=run_semantic,
    bg="#3c3c3c", fg="#cccccc", font=("Consolas", 10),
    relief="flat", padx=12, pady=4, cursor="hand2"
).pack(side="left", padx=(6, 0))

tk.Button(
    toolbar, text="Symbol Table",
    command=run_symbol_table,
    bg="#3c3c3c", fg="#cccccc", font=("Consolas", 10),
    relief="flat", padx=12, pady=4, cursor="hand2"
).pack(side="left", padx=(6, 0))

tk.Button(
    toolbar, text="✕  Clear",
    command=clear_output,
    bg="#3c3c3c", fg="#cccccc", font=("Consolas", 10),
    relief="flat", padx=12, pady=4, cursor="hand2"
).pack(side="left", padx=(6, 0))

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
root.bind("<Control-b>", lambda e: run_compile())
root.bind("<Control-l>", lambda e: run_lexer())
root.bind("<Control-p>", lambda e: run_parser())
root.bind("<Control-s>", lambda e: run_semantic())
root.bind("<Control-t>", lambda e: run_symbol_table())

# ── Init ──────────────────────────────────────────────────────────────────────
_update_line_numbers()
root.mainloop()