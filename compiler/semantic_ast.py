# =============================================================================
# compiler/semantic_ast.py
# Semantic analysis over the whole-program AST (scopes, types, console.log).
# Reuses AnalysisResult / Severity from compiler.semantic for uniform IDE output.
# =============================================================================

from __future__ import annotations

from compiler import ast
from compiler.semantic import AnalysisResult, Severity

_VALID_TYPES = frozenset({"number", "string", "boolean", "void"})


class _ScopedSymbols:
    """Stack of scopes: innermost is last. Lookup walks inner → outer."""

    def __init__(self):
        self._scopes: list[dict[str, dict]] = [{}]

    def enter_scope(self) -> None:
        self._scopes.append({})

    def exit_scope(self) -> None:
        if len(self._scopes) > 1:
            self._scopes.pop()

    def define(self, name: str, type_name: str, line: int) -> bool:
        """False if name already exists in the current (innermost) scope."""
        cur = self._scopes[-1]
        if name in cur:
            return False
        cur[name] = {"type": type_name, "line": line}
        return True

    def lookup(self, name: str) -> dict | None:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def exists(self, name: str) -> bool:
        return self.lookup(name) is not None

    def all_flat(self) -> list[tuple[str, str, int, int]]:
        """(name, type, line, scope_depth) for display — globals first, then deeper."""
        rows: list[tuple[str, str, int, int]] = []
        for depth, scope in enumerate(self._scopes):
            for name, info in scope.items():
                rows.append((name, info["type"], info["line"], depth))
        return rows


class SemanticAnalyzerAST:
    """
    Walks a Program AST produced by parser_program. Collects errors/warnings.
    """

    def __init__(self):
        self.symbols = _ScopedSymbols()
        self._results: list[AnalysisResult] = []

    def analyze(self, program: ast.Program) -> list[AnalysisResult]:
        self.symbols = _ScopedSymbols()
        self._results = []
        for stmt in program.statements:
            self._visit_stmt(stmt)
        return list(self._results)

    def _add(self, r: AnalysisResult) -> None:
        self._results.append(r)

    # ------------------------------------------------------------------ statements

    def _visit_stmt(self, node: ast.Stmt) -> None:
        if isinstance(node, ast.BlockStmt):
            self.symbols.enter_scope()
            for s in node.statements:
                self._visit_stmt(s)
            self.symbols.exit_scope()
        elif isinstance(node, ast.LetStmt):
            self._visit_let(node)
        elif isinstance(node, ast.AssignStmt):
            self._visit_assign(node)
        elif isinstance(node, ast.ExprStmt):
            self._visit_expr(node.expr, use_value=False)
        else:
            self._add(
                AnalysisResult(
                    f"Internal: unsupported statement {type(node).__name__}",
                    getattr(node, "line", 0),
                    Severity.ERROR,
                )
            )

    def _visit_let(self, node: ast.LetStmt) -> None:
        if node.type_name not in _VALID_TYPES:
            self._add(
                AnalysisResult(
                    f'"{node.type_name}" is not a valid type for a variable.',
                    node.line,
                    Severity.ERROR,
                )
            )
            return

        init_type: str | None = None
        if node.initializer is not None:
            init_type = self._expr_type(node.initializer)
            if init_type != "unknown" and node.type_name != "void":
                if init_type != node.type_name:
                    self._add(
                        AnalysisResult(
                            f'Cannot assign type "{init_type}" to "{node.name}" '
                            f'annotated as {node.type_name}.',
                            node.line,
                            Severity.ERROR,
                        )
                    )
                    return

        if not self.symbols.define(node.name, node.type_name, node.line):
            existing = self.symbols.lookup(node.name)
            assert existing is not None
            self._add(
                AnalysisResult(
                    f'"{node.name}" is already declared in this scope (line {existing["line"]}).',
                    node.line,
                    Severity.ERROR,
                )
            )

    def _visit_assign(self, node: ast.AssignStmt) -> None:
        sym = self.symbols.lookup(node.name)
        if sym is None:
            self._add(
                AnalysisResult(
                    f'"{node.name}" is assigned but was never declared.',
                    node.line,
                    Severity.WARNING,
                )
            )
            return
        vt = self._expr_type(node.value)
        if vt != "unknown" and sym["type"] != vt:
            self._add(
                AnalysisResult(
                    f'Cannot assign "{vt}" to "{node.name}" of type {sym["type"]}.',
                    node.line,
                    Severity.ERROR,
                )
            )

    # ------------------------------------------------------------------ expressions

    def _visit_expr(self, e: ast.Expr, *, use_value: bool) -> None:
        """use_value reserved for future side-effect-only distinction."""
        if isinstance(e, ast.CallExpr) and e.callee == "console.log":
            for arg in e.arguments:
                self._check_console_arg(arg, e.line)
        elif isinstance(e, ast.BinaryExpr):
            self._visit_expr(e.left, use_value=True)
            self._visit_expr(e.right, use_value=True)
        elif isinstance(e, ast.GroupingExpr):
            self._visit_expr(e.inner, use_value=True)
        elif isinstance(e, ast.CallExpr):
            self._add(
                AnalysisResult(
                    f'Unsupported call "{e.callee}" in this semantic pass.',
                    e.line,
                    Severity.WARNING,
                )
            )
        elif isinstance(e, ast.IdentifierExpr):
            if not self.symbols.exists(e.name):
                self._add(
                    AnalysisResult(
                        f'"{e.name}" is used but was never declared.',
                        e.line,
                        Severity.WARNING,
                    )
                )

    def _check_console_arg(self, arg: ast.Expr, call_line: int) -> None:
        if isinstance(arg, ast.IdentifierExpr):
            if not self.symbols.exists(arg.name):
                self._add(
                    AnalysisResult(
                        f'"{arg.name}" passed to console.log was never declared.',
                        call_line,
                        Severity.WARNING,
                    )
                )
        elif isinstance(arg, ast.BinaryExpr):
            self._visit_expr(arg, use_value=True)
        elif isinstance(arg, ast.GroupingExpr):
            self._visit_expr(arg.inner, use_value=True)
        elif isinstance(arg, ast.CallExpr):
            self._visit_expr(arg, use_value=True)

    def _expr_type(self, e: ast.Expr) -> str:
        if isinstance(e, ast.NumberLiteral):
            return "number"
        if isinstance(e, ast.StringLiteral):
            return "string"
        if isinstance(e, ast.BoolLiteral):
            return "boolean"
        if isinstance(e, ast.IdentifierExpr):
            sym = self.symbols.lookup(e.name)
            if sym is None:
                self._add(
                    AnalysisResult(
                        f'"{e.name}" is used but was never declared.',
                        e.line,
                        Severity.WARNING,
                    )
                )
                return "unknown"
            return sym["type"]
        if isinstance(e, ast.GroupingExpr):
            return self._expr_type(e.inner)
        if isinstance(e, ast.CallExpr):
            self._visit_expr(e, use_value=True)
            return "void"
        if isinstance(e, ast.BinaryExpr):
            return self._binary_type(e)
        return "unknown"

    def _binary_type(self, e: ast.BinaryExpr) -> str:
        left_t = self._expr_type(e.left)
        right_t = self._expr_type(e.right)
        op = e.op

        if op == "+":
            if left_t == "string" and right_t == "string":
                return "string"
            if left_t == "number" and right_t == "number":
                return "number"
            self._add(
                AnalysisResult(
                    f'Operator "+" expects two numbers or two strings, got {left_t} and {right_t}.',
                    e.line,
                    Severity.ERROR,
                )
            )
            return "unknown"

        if op in ("-", "*", "/", "%"):
            if left_t == "number" and right_t == "number":
                return "number"
            self._add(
                AnalysisResult(
                    f'Operator "{op}" expects two numbers, got {left_t} and {right_t}.',
                    e.line,
                    Severity.ERROR,
                )
            )
            return "unknown"

        self._add(
            AnalysisResult(f'Unsupported operator "{op}" in semantic pass.', e.line, Severity.ERROR)
        )
        return "unknown"
