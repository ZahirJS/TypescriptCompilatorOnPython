# =============================================================================
# main.py  —  TypeScript Compiler IDE
# Phases shown:  Lexer | Parser (lines) | AST | Semantic | Code Gen | Run VM
# =============================================================================

import tkinter as tk
from tkinter import filedialog, Menu, Frame, Text

from compiler.lexer            import Lexer
from compiler.parser           import Parser
from compiler.parser_program   import parse_program_source, ProgramParseResult
from compiler.semantic_ast     import SemanticAnalyzerAST
from compiler.code_generator   import CodeGenerator
from compiler.virtual_machine  import VirtualMachine


# =============================================================================
# File helpers
# =============================================================================

def open_file():
    path = filedialog.askopenfilename(
        filetypes=[("TypeScript", "*.ts"), ("Text", "*.txt"), ("All", "*.*")])
    if path:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        editor.delete("1.0", "end")
        editor.insert("1.0", content)
        _update_line_numbers()

def save_file():
    path = filedialog.asksaveasfilename(
        defaultextension=".ts",
        filetypes=[("TypeScript", "*.ts"), ("Text", "*.txt"), ("All", "*.*")])
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(editor.get("1.0", "end-1c"))


# =============================================================================
# Shared parse helper
# =============================================================================

def _get_source() -> str:
    return editor.get("1.0", "end-1c")

def _parse_errors_to_tuples(errors):
    out = []
    for err in errors:
        if err.startswith("line "):
            rest = err[len("line "):]
            num, _, msg = rest.partition(": ")
            try:   line_num = int(num)
            except ValueError: line_num = 0
            out.append((line_num, "error", msg.strip()))
        else:
            out.append((0, "error", err))
    return out


# =============================================================================
# Phase 1 — Lexer
# =============================================================================

def run_lexer():
    tokens = Lexer(_get_source()).tokenize_all()
    lines  = ["── Lexer ────────────────────────────────────────────", ""]
    for t in tokens:
        if t.type.name == "END":
            continue
        lines.append(
            f"  line {t.line:<4}  {t.type.name:<18}  {t.type.label:<18}  {t.value!r}")
    _show(lines)


# =============================================================================
# Phase 2 — Parser (line-by-line legacy)
# =============================================================================

def run_parser_lines():
    results = Parser().parse(_get_source())
    lines   = ["── Parser (línea por línea) ─────────────────────────", ""]
    for r in results:
        status = "ok   " if r.is_valid else "error"
        lines.append(f"  line {r.line:<4}  [{status}]  {r.pattern:<26}  {r.message}")
    _show(lines)


# =============================================================================
# Phase 3 — AST (whole-program parser)
# =============================================================================

def run_ast():
    src    = _get_source().strip()
    result = parse_program_source(src)
    lines  = ["── AST (programa completo) ──────────────────────────", ""]
    if result.errors:
        for e in result.errors:
            lines.append(f"  {e}")
        lines.append(""); lines.append("  Parse fallido — AST no construido.")
    else:
        lines.append(result.program.tree().rstrip())
        lines.append(""); lines.append("  Parse exitoso.")
    _show(lines)


# =============================================================================
# Phase 4 — Semantic analysis
# =============================================================================

def run_semantic():
    pr = parse_program_source(_get_source())
    lines = ["── Análisis Semántico ───────────────────────────────", ""]
    if pr.errors:
        lines.append("  Corrige errores de sintaxis primero:")
        for e in pr.errors:
            lines.append(f"  {e}")
        _show(lines); return

    results = SemanticAnalyzerAST().analyze(pr.program)
    if not results:
        lines.append("  Sin errores semánticos.")
    else:
        for r in results:
            lines.append(f"  main.ts:{r.line} - {r.severity}:  {r.message}")
        errs  = [r for r in results if r.severity == "error"]
        warns = [r for r in results if r.severity == "warning"]
        lines.append("")
        lines.append(f"  {len(errs)} error(es), {len(warns)} advertencia(s).")
    _show(lines)


# =============================================================================
# Phase 4b — Symbol Table
# =============================================================================

def run_symbol_table():
    pr = parse_program_source(_get_source())
    lines = ["── Tabla de Símbolos ────────────────────────────────", ""]
    if pr.errors:
        lines.append("  (errores de parse — ejecuta AST primero)")
        _show(lines); return
    analyzer = SemanticAnalyzerAST()
    analyzer.analyze(pr.program)
    flat = analyzer.symbols.all_flat()
    flat.sort(key=lambda r: (r[3], r[2], r[0]))
    if not flat:
        lines.append("  (ninguna variable declarada)")
    else:
        lines.append(f"  {'Nombre':<20} {'Tipo':<16} {'Línea':<8} Scope")
        lines.append(f"  {'─'*20} {'─'*16} {'─'*8} {'─'*6}")
        for name, typ, ln, depth in flat:
            scope = "global" if depth == 0 else f"local-{depth}"
            lines.append(f"  {name:<20} {typ:<16} {ln:<8} {scope}")
    _show(lines)


# =============================================================================
# Phase 5 — Code generation
# =============================================================================

def run_codegen():
    pr = parse_program_source(_get_source())
    lines = ["── Código Intermedio ────────────────────────────────", ""]
    if pr.errors:
        lines += ["  Corrige errores de sintaxis primero:"] + [f"  {e}" for e in pr.errors]
        _show(lines); return

    sem_results = SemanticAnalyzerAST().analyze(pr.program)
    sem_errors  = [r for r in sem_results if r.severity == "error"]
    if sem_errors:
        lines += ["  Corrige errores semánticos primero:"]
        for r in sem_errors:
            lines.append(f"  main.ts:{r.line} - error:  {r.message}")
        _show(lines); return

    try:
        asm = CodeGenerator().generate(pr.program)
        lines.append(asm)
    except Exception as exc:
        lines.append(f"  [!] Error en generación: {exc}")
    _show(lines)


# =============================================================================
# Phase 6 — Execute in VM
# =============================================================================

def run_vm():
    pr = parse_program_source(_get_source())
    lines = ["── Ejecución — Máquina Virtual ──────────────────────", ""]
    if pr.errors:
        lines += ["  Corrige errores de sintaxis primero:"] + [f"  {e}" for e in pr.errors]
        _show(lines); return

    sem_results = SemanticAnalyzerAST().analyze(pr.program)
    sem_errors  = [r for r in sem_results if r.severity == "error"]
    if sem_errors:
        lines += ["  Corrige errores semánticos primero:"]
        for r in sem_errors:
            lines.append(f"  main.ts:{r.line} - error:  {r.message}")
        _show(lines); return

    try:
        asm    = CodeGenerator().generate(pr.program)
        result = VirtualMachine(asm).run()
        lines.append(result)
    except Exception as exc:
        lines.append(f"  [!] Error en VM: {exc}")
    _show(lines)


# =============================================================================
# Compile — parse, analyze, run, show output or errors
# =============================================================================

def run_compile():
    pr = parse_program_source(_get_source())

    if pr.errors:
        errs = _parse_errors_to_tuples(pr.errors)
        lines = []
        for ln, sev, msg in errs:
            lines.append(f"  main.ts:{ln} - {sev}:  {msg}")
        lines += ["", f"  {len(errs)} error(es) de sintaxis — compilación detenida."]
        _show(lines)
        return

    sem_results = SemanticAnalyzerAST().analyze(pr.program)
    sem_errors  = [r for r in sem_results if r.severity == "error"]
    sem_warns   = [r for r in sem_results if r.severity == "warning"]

    if sem_errors:
        lines = []
        for r in sorted(sem_errors + sem_warns, key=lambda r: r.line):
            lines.append(f"  main.ts:{r.line} - {r.severity}:  {r.message}")
        lines += ["", f"  {len(sem_errors)} error(es), {len(sem_warns)} advertencia(s) — compilación detenida."]
        _show(lines)
        return

    # Warnings only (no blocking errors) — prepend them, then run
    prefix = []
    if sem_warns:
        for r in sem_warns:
            prefix.append(f"  main.ts:{r.line} - warning:  {r.message}")
        prefix.append("")

    try:
        asm    = CodeGenerator().generate(pr.program)
        result = VirtualMachine(asm).run()
        out    = [l for l in result.split("\n") if not l.startswith(">>>") and l.strip()]
        _show(prefix + (out if out else ["  (sin salida)"]))
    except Exception as exc:
        _show(prefix + [f"  Error: {exc}"])


def clear_output():
    _show([])


# =============================================================================
# UI helpers
# =============================================================================

def _show(lines):
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
root.geometry("1100x780")
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
run_menu.add_command(label="▶ Compilar            Ctrl+B", command=run_compile)
run_menu.add_separator()
run_menu.add_command(label="Análisis Léxico       Ctrl+1", command=run_lexer)
run_menu.add_command(label="Análisis Sintáctico   Ctrl+2", command=run_parser_lines)
run_menu.add_command(label="Árbol Sintáctico (AST) Ctrl+3", command=run_ast)
run_menu.add_command(label="Análisis Semántico    Ctrl+4", command=run_semantic)
run_menu.add_command(label="Tabla de Símbolos     Ctrl+T", command=run_symbol_table)
run_menu.add_command(label="Código Intermedio     Ctrl+5", command=run_codegen)
run_menu.add_separator()
run_menu.add_command(label="Limpiar salida",               command=clear_output)

# ── Editor area ───────────────────────────────────────────────────────────────
editor_frame = Frame(root, bg="#1e1e1e")
editor_frame.pack(fill="both", expand=True, padx=6, pady=(6, 0))

line_numbers = Text(
    editor_frame, width=4, bg="#1e1e1e", fg="#858585",
    font=("Consolas", 12), state="disabled",
    takefocus=0, borderwidth=0, highlightthickness=0)
line_numbers.pack(side="left", fill="y")

editor = Text(
    editor_frame, bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
    font=("Consolas", 12), borderwidth=0, highlightthickness=0, undo=True)
editor.pack(side="left", fill="both", expand=True)
editor.bind("<KeyRelease>", _update_line_numbers)

# ── Toolbar ───────────────────────────────────────────────────────────────────
toolbar = Frame(root, bg="#2b2b2b")
toolbar.pack(fill="x", padx=6, pady=(4, 0))

BTN_NORMAL = "#3c3c3c"
BTN_RUN    = "#1e6b1e"

def _btn(parent, label, cmd, color=BTN_NORMAL):
    return tk.Button(parent, text=label, command=cmd,
                     bg=color, fg="white", font=("Consolas", 10, "bold"),
                     relief="flat", padx=10, pady=4, cursor="hand2")

# LEFT: main compile action
_btn(toolbar, "▶  Compilar", run_compile, BTN_RUN).pack(side="left", padx=(0, 14))

# RIGHT: phase inspection buttons (packed right-to-left to render left-to-right)
_btn(toolbar, "✕ Limpiar",        clear_output).pack(side="right", padx=(2, 0))
_btn(toolbar, "Cód. Intermedio",  run_codegen).pack(side="right", padx=2)
_btn(toolbar, "Símbolos",         run_symbol_table).pack(side="right", padx=2)
_btn(toolbar, "Semántico",        run_semantic).pack(side="right", padx=2)
_btn(toolbar, "AST",              run_ast).pack(side="right", padx=2)
_btn(toolbar, "Parser",           run_parser_lines).pack(side="right", padx=2)
_btn(toolbar, "Léxico",           run_lexer).pack(side="right", padx=2)

# ── Output panel ──────────────────────────────────────────────────────────────
output_frame = Frame(root, bg="#1e1e1e", height=260)
output_frame.pack(fill="both", padx=6, pady=6)
output_frame.pack_propagate(False)

tk.Label(output_frame, text="Output", bg="#1e1e1e", fg="#9cdcfe",
         font=("Consolas", 10, "bold"), anchor="w").pack(fill="x", padx=8, pady=(6, 0))

output = Text(output_frame, bg="#1e1e1e", fg="#ce9178",
              font=("Consolas", 11), state="disabled",
              borderwidth=0, highlightthickness=0)
output.pack(fill="both", expand=True, padx=8, pady=(2, 8))

# ── Keyboard shortcuts ────────────────────────────────────────────────────────
root.bind("<Control-b>", lambda e: run_compile())
root.bind("<Control-1>", lambda e: run_lexer())
root.bind("<Control-2>", lambda e: run_parser_lines())
root.bind("<Control-3>", lambda e: run_ast())
root.bind("<Control-4>", lambda e: run_semantic())
root.bind("<Control-t>", lambda e: run_symbol_table())
root.bind("<Control-5>", lambda e: run_codegen())

# ── Seed the editor with the bubble-sort demo ─────────────────────────────────
BUBBLE_SORT_DEMO = """\
function bubbleSort(arr: number[], n: number): void {
    let i: number = 0;
    let j: number = 0;
    let temp: number = 0;
    for (i = 0; i < n; i = i + 1) {
        for (j = 0; j < n - i - 1; j = j + 1) {
            if (arr[j] > arr[j + 1]) {
                temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}

let datos: number[] = [64, 34, 25, 12, 22, 11, 90];
let n: number = 7;
bubbleSort(datos, n);
let k: number = 0;
for (k = 0; k < n; k = k + 1) {
    console.log(datos[k]);
}
"""

editor.insert("1.0", BUBBLE_SORT_DEMO)
_update_line_numbers()
root.mainloop()
