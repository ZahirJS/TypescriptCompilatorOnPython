# =============================================================================
# main.py
# The IDE — visual interface for the TypeScript compiler.
# This file only handles what the user sees and does.
# All compiler logic lives in the compiler/ package.
# =============================================================================

import tkinter as tk
from tkinter import filedialog, Menu, Frame, Text

from compiler.lexer          import Lexer
from compiler.parser        import Parser
from compiler.parser_program import parse_program_source, ProgramParseResult
from compiler.semantic_ast   import SemanticAnalyzerAST


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

def _parse_errors_to_tuples(errors: list[str]) -> list[tuple[int, str, str]]:
    """Turn 'line N: msg' strings into (line, 'error', message) tuples."""
    out: list[tuple[int, str, str]] = []
    for err in errors:
        if err.startswith("line "):
            rest = err[len("line ") :]
            num, _, msg = rest.partition(": ")
            try:
                line_num = int(num)
            except ValueError:
                line_num = 0
            out.append((line_num, "error", msg.strip()))
        else:
            out.append((0, "error", err))
    return out


def _program_parse_diagnostics(source: str) -> list[tuple[int, str, str]]:
    """
    Whole-program (AST) parse. Returns (line, severity, message) tuples
    for structural failures — same shape as the rest of compile output.
    """
    return _parse_errors_to_tuples(parse_program_source(source).errors)


def _compile_structure_and_semantic(source: str) -> tuple[list[tuple[int, str, str]], list[tuple[int, str, str]]]:
    """
    Single parse of source; if syntax OK, run AST semantic analyzer.
    Returns (structure_tuples, semantic_tuples).
    """
    pr: ProgramParseResult = parse_program_source(source)
    structure = _parse_errors_to_tuples(pr.errors)
    if pr.errors:
        return structure, []
    sem_results = SemanticAnalyzerAST().analyze(pr.program)
    semantic = [(r.line, r.severity, r.message) for r in sem_results]
    return structure, semantic


def run_compile():
    """
    Runs all phases in order and shows only errors and warnings.
    Phase 1: whole-program parse (AST). Phase 2: semantic analysis on that AST
    (scopes, types, console.log).
    """
    source = editor.get("1.0", "end-1c")

    structure_errors, semantic_results = _compile_structure_and_semantic(source)

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
    Line-by-line structural patterns (legacy). For full-program syntax,
    use AST (Ctrl+U) — Compile already uses the whole-program parser for phase 1.
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
    Semantic analysis on the program AST (scopes + types). If syntax fails,
    only parse diagnostics are shown.
    """
    source = editor.get("1.0", "end-1c")
    pr = parse_program_source(source)

    if pr.errors:
        lines = ["── Semantic (AST) ────────────────────────────────────", "", "Fix syntax first:"]
        for err in pr.errors:
            if err.startswith("line "):
                rest = err[len("line ") :]
                num, _, msg = rest.partition(": ")
                lines.append(f"main.ts:{num} - error:  {msg}")
            else:
                lines.append(f"main.ts: error:  {err}")
        _show_output(lines)
        return

    results = SemanticAnalyzerAST().analyze(pr.program)

    if not results:
        _show_output(["── Semantic (AST) ───────────────────────────────────", "", "No semantic issues found."])
        return

    lines = ["── Semantic (AST) ───────────────────────────────────", ""]
    for r in results:
        lines.append(f"main.ts:{r.line} - {r.severity}:  {r.message}")

    errors   = [r for r in results if r.is_error()]
    warnings = [r for r in results if r.is_warning()]
    lines.append("")
    lines.append(f"Found {len(errors)} error(s), {len(warnings)} warning(s).")
    _show_output(lines)


def run_ast_program():
    """
    Whole-program parse: builds an AST from the full source (not line-by-line).
    This is the foundation for semantic analysis, codegen, and execution.
    """
    source = editor.get("1.0", "end-1c").strip()
    if not source:
        _show_output(["── AST (program) ─────────────────────────────────────", "", "(empty editor)"])
        return

    result = parse_program_source(source)
    lines = ["── AST (program) ─────────────────────────────────────", ""]

    if result.errors:
        for err in result.errors:
            if err.startswith("line "):
                rest = err[len("line ") :]
                num, _, msg = rest.partition(": ")
                lines.append(f"main.ts:{num} - error:  {msg}")
            else:
                lines.append(f"main.ts: error:  {err}")
        lines.append("")
        lines.append("Parse failed; AST not built.")
        _show_output(lines)
        return

    lines.append(result.program.tree().rstrip())
    lines.append("")
    lines.append("Parse successful.")
    _show_output(lines)


def run_symbol_table():
    """
    Shows symbols discovered by the AST semantic pass (name, type, line, scope depth).
    """
    source = editor.get("1.0", "end-1c")
    pr = parse_program_source(source)

    lines = ["── Symbol Table (AST) ─────────────────────────────────", ""]

    if pr.errors:
        lines.append("  (parse errors — run AST or Compile first)")
        _show_output(lines)
        return

    analyzer = SemanticAnalyzerAST()
    analyzer.analyze(pr.program)
    flat = analyzer.symbols.all_flat()
    flat.sort(key=lambda row: (row[3], row[2], row[0]))

    if not flat:
        lines.append("  (no variables declared)")
    else:
        lines.append(f"  {'Name':<16} {'Type':<10} {'Line':<6} Scope")
        lines.append(f"  {'─'*16} {'─'*10} {'─'*6} {'─'*6}")
        for name, typ, line, depth in flat:
            lines.append(f"  {name:<16} {typ:<10} {line:<6} {depth}")

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
run_menu.add_command(label="Parser (lines)    Ctrl+P", command=run_parser)
run_menu.add_command(label="Semantic         Ctrl+S", command=run_semantic)
run_menu.add_command(label="AST (program)    Ctrl+U", command=run_ast_program)
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
    toolbar, text="Parser (lines)",
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
    toolbar, text="AST",
    command=run_ast_program,
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
root.bind("<Control-u>", lambda e: run_ast_program())

# ── Init ──────────────────────────────────────────────────────────────────────
_update_line_numbers()
root.mainloop()