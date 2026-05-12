# =============================================================================
# compiler/semantic_ast.py
# Semantic analysis over the full AST — scopes, types, undeclared variables.
# =============================================================================

from __future__ import annotations
from compiler import ast
from compiler.semantic import AnalysisResult, Severity

_VALID_BASE_TYPES = frozenset({"number", "string", "boolean", "void"})


def _is_valid_type(t: str) -> bool:
    return t in _VALID_BASE_TYPES or t.endswith("[]")


def _base_type(t: str) -> str:
    """'number[]' → 'number', 'number' → 'number'"""
    return t[:-2] if t.endswith("[]") else t


# ---------------------------------------------------------------------------
# Scoped symbol table
# ---------------------------------------------------------------------------

class _ScopedSymbols:
    def __init__(self):
        self._scopes: list = [{}]

    def enter_scope(self):
        self._scopes.append({})

    def exit_scope(self):
        if len(self._scopes) > 1:
            self._scopes.pop()

    def define(self, name: str, type_name: str, line: int) -> bool:
        cur = self._scopes[-1]
        if name in cur:
            return False
        cur[name] = {"type": type_name, "line": line}
        return True

    def lookup(self, name: str):
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def exists(self, name: str) -> bool:
        return self.lookup(name) is not None

    def all_flat(self) -> list:
        rows = []
        for depth, scope in enumerate(self._scopes):
            for name, info in scope.items():
                rows.append((name, info["type"], info["line"], depth))
        return rows


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class SemanticAnalyzerAST:
    def __init__(self):
        self.symbols  = _ScopedSymbols()
        self._results: list = []
        self._func_ret_type: str | None = None
        self._in_loop: int = 0   # depth counter

    def analyze(self, program: ast.Program) -> list:
        self.symbols        = _ScopedSymbols()
        self._results       = []
        self._func_ret_type = None
        self._in_loop       = 0
        for stmt in program.statements:
            self._visit_stmt(stmt)
        return list(self._results)

    def _err(self, msg: str, line: int):
        self._results.append(AnalysisResult(msg, line, Severity.ERROR))

    def _warn(self, msg: str, line: int):
        self._results.append(AnalysisResult(msg, line, Severity.WARNING))

    # ── statements ──────────────────────────────────────────────────────────

    def _visit_stmt(self, node):
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
            self._expr_type(node.expr)

        elif isinstance(node, ast.IfStmt):
            ct = self._expr_type(node.condition)
            # Allow number as truthy condition (common pattern)
            self._visit_stmt(node.then_block)
            if node.else_block:
                self._visit_stmt(node.else_block)

        elif isinstance(node, ast.WhileStmt):
            self._expr_type(node.condition)
            self._in_loop += 1
            self._visit_stmt(node.body)
            self._in_loop -= 1

        elif isinstance(node, ast.ForStmt):
            self.symbols.enter_scope()
            self._in_loop += 1
            if node.init:
                self._visit_stmt(node.init)
            if node.condition:
                self._expr_type(node.condition)
            if node.step:
                self._visit_stmt(node.step)
            self._visit_stmt(node.body)
            self._in_loop -= 1
            self.symbols.exit_scope()

        elif isinstance(node, ast.SwitchStmt):
            self._expr_type(node.expr)
            self._in_loop += 1
            for c in node.cases:
                self._visit_stmt(c)
            self._in_loop -= 1

        elif isinstance(node, ast.CaseClause):
            self._expr_type(node.value)
            for s in node.body:
                self._visit_stmt(s)

        elif isinstance(node, ast.DefaultClause):
            for s in node.body:
                self._visit_stmt(s)

        elif isinstance(node, ast.BreakStmt):
            if self._in_loop == 0:
                self._err("'break' used outside of a loop or switch", node.line)

        elif isinstance(node, ast.ContinueStmt):
            if self._in_loop == 0:
                self._err("'continue' used outside of a loop", node.line)

        elif isinstance(node, ast.ReturnStmt):
            if self._func_ret_type is None:
                self._err("'return' used outside of a function", node.line)
            else:
                rt = self._expr_type(node.value) if node.value else "void"
                if (self._func_ret_type != "void" and rt != "unknown"
                        and rt != self._func_ret_type):
                    self._err(
                        f'Function expects return type "{self._func_ret_type}", got "{rt}"',
                        node.line)

        elif isinstance(node, ast.FunctionDecl):
            self._visit_function(node)

    def _visit_let(self, node: ast.LetStmt):
        if not _is_valid_type(node.type_name):
            self._err(f'"{node.type_name}" is not a valid type', node.line)
            return

        if node.initializer is not None:
            it = self._expr_type(node.initializer)
            if it not in ("unknown", "any") and not self._types_compatible(node.type_name, it):
                self._err(
                    f'Cannot assign "{it}" to "{node.name}" declared as "{node.type_name}"',
                    node.line)

        if not self.symbols.define(node.name, node.type_name, node.line):
            existing = self.symbols.lookup(node.name)
            self._err(
                f'"{node.name}" already declared in this scope (line {existing["line"]})',
                node.line)

    def _visit_assign(self, node: ast.AssignStmt):
        sym = self.symbols.lookup(node.name)
        if sym is None:
            self._err(f'"{node.name}" assigned but never declared', node.line)
            self._expr_type(node.value)
            return

        vt = self._expr_type(node.value)

        if node.index is not None:
            # array element assignment: arr[idx] = val
            it = self._expr_type(node.index)
            if it not in ("unknown", "any", "number"):
                self._err(f'Array index must be "number", got "{it}"', node.line)
            elem_type = _base_type(sym["type"])
            if vt not in ("unknown", "any") and not self._types_compatible(elem_type, vt):
                self._err(
                    f'Cannot assign "{vt}" to element of "{node.name}" (type {elem_type})',
                    node.line)
        else:
            if vt not in ("unknown", "any") and not self._types_compatible(sym["type"], vt):
                self._err(
                    f'Cannot assign "{vt}" to "{node.name}" of type "{sym["type"]}"',
                    node.line)

    def _visit_function(self, node: ast.FunctionDecl):
        if not self.symbols.define(
            node.name, f"function->{node.return_type}", node.line
        ):
            self._err(f'Function "{node.name}" already declared', node.line)

        self.symbols.enter_scope()
        saved_ret = self._func_ret_type
        self._func_ret_type = node.return_type

        for p in node.params:
            self.symbols.define(p.name, p.type_name, p.line)

        for s in node.body.statements:
            self._visit_stmt(s)

        self._func_ret_type = saved_ret
        self.symbols.exit_scope()

    # ── expressions → infer type ────────────────────────────────────────────

    def _expr_type(self, node) -> str:
        if node is None:
            return "void"

        if isinstance(node, ast.NumberLiteral):
            return "number"
        if isinstance(node, ast.StringLiteral):
            return "string"
        if isinstance(node, ast.BoolLiteral):
            return "boolean"

        if isinstance(node, ast.IdentifierExpr):
            sym = self.symbols.lookup(node.name)
            if sym is None:
                self._err(f'"{node.name}" used but never declared', node.line)
                return "unknown"
            return sym["type"]

        if isinstance(node, ast.ArrayLiteralExpr):
            if not node.elements:
                return "any[]"
            first_t = self._expr_type(node.elements[0])
            for e in node.elements[1:]:
                et = self._expr_type(e)
                if et != first_t:
                    return "any[]"
            return first_t + "[]"

        if isinstance(node, ast.ArrayAccessExpr):
            sym = self.symbols.lookup(node.name)
            if sym is None:
                self._err(f'"{node.name}" used but never declared', node.line)
                return "unknown"
            it = self._expr_type(node.index)
            if it not in ("unknown", "any", "number"):
                self._err(f'Array index must be "number", got "{it}"', node.line)
            return _base_type(sym["type"])

        if isinstance(node, ast.GroupingExpr):
            return self._expr_type(node.inner)

        if isinstance(node, ast.BinaryExpr):
            return self._binary_type(node)

        if isinstance(node, ast.UnaryExpr):
            t = self._expr_type(node.operand)
            if node.op == "!" and t not in ("unknown", "boolean"):
                self._err(f'"!" requires boolean operand, got "{t}"', node.line)
            return t

        if isinstance(node, ast.PostfixExpr):
            t = self._expr_type(node.operand)
            if t not in ("unknown", "any", "number"):
                self._err(f'"{node.op}" requires number operand, got "{t}"', node.line)
            return "number"

        if isinstance(node, ast.CallExpr):
            return self._call_type(node)

        return "unknown"

    def _binary_type(self, node: ast.BinaryExpr) -> str:
        lt = self._expr_type(node.left)
        rt = self._expr_type(node.right)
        op = node.op

        # Logical operators
        if op in ("&&", "||"):
            return "boolean"

        # Comparison operators → always boolean
        if op in ("==", "!=", "<", ">", "<=", ">="):
            return "boolean"

        # Arithmetic
        if op == "+":
            if lt in ("unknown", "any") or rt in ("unknown", "any"):
                return "unknown"
            if lt == "string" and rt == "string":
                return "string"
            if lt == "number" and rt == "number":
                return "number"
            self._err(
                f'Operator "+" between "{lt}" and "{rt}" is not valid', node.line)
            return "unknown"

        if op in ("-", "*", "/", "%"):
            if lt in ("unknown", "any") or rt in ("unknown", "any"):
                return "number"
            if lt == "number" and rt == "number":
                return "number"
            self._err(
                f'Operator "{op}" requires numbers, got "{lt}" and "{rt}"', node.line)
            return "unknown"

        return "unknown"

    def _call_type(self, node: ast.CallExpr) -> str:
        if node.callee == "console.log":
            for a in node.arguments:
                self._expr_type(a)
            return "void"

        sym = self.symbols.lookup(node.callee)
        if sym is None:
            self._err(f'Function "{node.callee}" not declared', node.line)
            return "unknown"

        # Validate argument count (loose check — allow mismatch for flexibility)
        for a in node.arguments:
            self._expr_type(a)

        ret = sym["type"]
        if ret.startswith("function->"):
            return ret[len("function->"):]
        return ret

    # ── helpers ─────────────────────────────────────────────────────────────

    def _types_compatible(self, declared: str, actual: str) -> bool:
        if declared == actual:
            return True
        if actual in ("unknown", "any") or declared in ("any", "unknown"):
            return True
        # allow number[] ↔ any[]
        if declared.endswith("[]") and actual == "any[]":
            return True
        if actual.endswith("[]") and declared == "any[]":
            return True
        return False
