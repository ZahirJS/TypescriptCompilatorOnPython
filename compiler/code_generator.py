# =============================================================================
# compiler/code_generator.py
# Walks the AST and emits stack-machine instructions.
#
# Variable scoping is handled via name-mangling:
#   - Global variables keep their name.
#   - Variables inside function "foo" become "__foo_varname".
# Arrays are Python lists stored in the VM's memory dict; passing an array
# to a function stores a reference to the SAME list → in-place mutation works.
#
# Instruction set:
#   PUSH_CONST value        push literal onto stack
#   PUSH_VAR   name         push memory[name]
#   STORE_VAR  name         pop → memory[name]
#   LOAD_IDX   name         pop index → push memory[name][index]
#   STORE_IDX  name         pop index, pop value → memory[name][index] = value
#   MAKE_ARRAY count        pop count items (reverse order) → push list
#   ADD / SUB / MUL / DIV / MOD / NEG
#   EQ / NEQ / LT / GT / LEQ / GEQ
#   AND / OR / NOT
#   JMP   label             unconditional jump
#   JMPF  label             jump if top-of-stack is falsy (pop)
#   LABEL label             (not executed; used for jump targets)
#   CALL  func_name         push return-IP, jump to func_<func_name>
#   RET                     pop return-IP, jump there
#   PRINT                   pop and print
#   HALT                    stop execution
# =============================================================================

from __future__ import annotations
from compiler import ast


class CodeGenerator:
    def __init__(self):
        self._main_buf: list[str] = []   # global / main code
        self._func_buf: list[str] = []   # all function bodies
        self._label_counter = 0
        self._current_func: str | None = None  # name of function being compiled

    # ── public API ───────────────────────────────────────────────────────────

    def generate(self, program: ast.Program) -> str:
        """Return the complete assembly text."""
        self._main_buf = []
        self._func_buf = []
        self._label_counter = 0
        self._current_func  = None

        for stmt in program.statements:
            self._gen_stmt(stmt)

        self._emit_main("HALT")

        lines = (
            ["; ── main ───────────────────────────────────────────────────"]
            + self._main_buf
            + ["", "; ── functions ──────────────────────────────────────────────"]
            + self._func_buf
        )
        return "\n".join(lines)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _new_label(self) -> str:
        self._label_counter += 1
        return f"L{self._label_counter}"

    def _emit_main(self, instr: str):
        self._main_buf.append(instr)

    def _emit_func(self, instr: str):
        self._func_buf.append(instr)

    def _emit(self, instr: str):
        """Emit to the currently active buffer."""
        if self._current_func is not None:
            self._emit_func(instr)
        else:
            self._emit_main(instr)

    def _var(self, name: str) -> str:
        """Apply name-mangling when inside a function."""
        if self._current_func:
            return f"__{self._current_func}_{name}"
        return name

    # ── statement dispatch ───────────────────────────────────────────────────

    def _gen_stmt(self, node):
        if isinstance(node, ast.FunctionDecl):
            self._gen_function(node)
        elif isinstance(node, ast.LetStmt):
            self._gen_let(node)
        elif isinstance(node, ast.AssignStmt):
            self._gen_assign(node)
        elif isinstance(node, ast.ExprStmt):
            self._gen_expr_stmt(node)
        elif isinstance(node, ast.BlockStmt):
            for s in node.statements:
                self._gen_stmt(s)
        elif isinstance(node, ast.IfStmt):
            self._gen_if(node)
        elif isinstance(node, ast.WhileStmt):
            self._gen_while(node)
        elif isinstance(node, ast.ForStmt):
            self._gen_for(node)
        elif isinstance(node, ast.SwitchStmt):
            self._gen_switch(node)
        elif isinstance(node, ast.ReturnStmt):
            self._gen_return(node)
        elif isinstance(node, ast.BreakStmt):
            self._emit(f"JMP {self._break_label}")
        elif isinstance(node, ast.ContinueStmt):
            self._emit(f"JMP {self._continue_label}")

    # ── function declaration ─────────────────────────────────────────────────

    def _gen_function(self, node: ast.FunctionDecl):
        saved_func    = self._current_func
        self._current_func = node.name

        self._emit_func(f"LABEL func_{node.name}")

        # Pop parameters from stack in reverse order (last param first).
        for p in reversed(node.params):
            self._emit_func(f"STORE_VAR {self._var(p.name)}")

        for s in node.body.statements:
            self._gen_stmt(s)

        # Implicit return for void functions
        self._emit_func("RET")

        self._current_func = saved_func

    # ── let / const ──────────────────────────────────────────────────────────

    def _gen_let(self, node: ast.LetStmt):
        if node.initializer is not None:
            self._gen_expr(node.initializer)
        else:
            # default: 0 for number, "" for string, false for boolean
            if node.type_name.endswith("[]"):
                self._emit(f"MAKE_ARRAY 0")
            else:
                self._emit("PUSH_CONST 0")
        self._emit(f"STORE_VAR {self._var(node.name)}")

    # ── assignment ───────────────────────────────────────────────────────────

    def _gen_assign(self, node: ast.AssignStmt):
        if node.index is not None:
            # arr[idx] = value
            # Stack protocol for STORE_IDX: push value first, then index
            self._gen_expr(node.value)
            self._gen_expr(node.index)
            self._emit(f"STORE_IDX {self._var(node.name)}")
        else:
            self._gen_expr(node.value)
            self._emit(f"STORE_VAR {self._var(node.name)}")

    # ── expression statement ─────────────────────────────────────────────────

    def _gen_expr_stmt(self, node: ast.ExprStmt):
        if isinstance(node.expr, ast.CallExpr):
            self._gen_call(node.expr)
        elif isinstance(node.expr, ast.PostfixExpr):
            self._gen_postfix_stmt(node.expr)
        else:
            self._gen_expr(node.expr)

    def _gen_postfix_stmt(self, node: ast.PostfixExpr):
        if isinstance(node.operand, ast.IdentifierExpr):
            vname = self._var(node.operand.name)
            self._emit(f"PUSH_VAR {vname}")
            self._emit("PUSH_CONST 1")
            self._emit("ADD" if node.op == "++" else "SUB")
            self._emit(f"STORE_VAR {vname}")

    # ── if ───────────────────────────────────────────────────────────────────

    def _gen_if(self, node: ast.IfStmt):
        l_false = self._new_label()
        l_end   = self._new_label()

        self._gen_expr(node.condition)
        self._emit(f"JMPF {l_false}")
        self._gen_stmt(node.then_block)
        self._emit(f"JMP {l_end}")
        self._emit(f"LABEL {l_false}")
        if node.else_block:
            self._gen_stmt(node.else_block)
        self._emit(f"LABEL {l_end}")

    # ── while ────────────────────────────────────────────────────────────────

    def _gen_while(self, node: ast.WhileStmt):
        l_start = self._new_label()
        l_end   = self._new_label()
        saved_break    = getattr(self, "_break_label", None)
        saved_continue = getattr(self, "_continue_label", None)
        self._break_label    = l_end
        self._continue_label = l_start

        self._emit(f"LABEL {l_start}")
        self._gen_expr(node.condition)
        self._emit(f"JMPF {l_end}")
        self._gen_stmt(node.body)
        self._emit(f"JMP {l_start}")
        self._emit(f"LABEL {l_end}")

        self._break_label    = saved_break
        self._continue_label = saved_continue

    # ── for ──────────────────────────────────────────────────────────────────

    def _gen_for(self, node: ast.ForStmt):
        l_cond     = self._new_label()
        l_step     = self._new_label()
        l_end      = self._new_label()
        saved_break    = getattr(self, "_break_label", None)
        saved_continue = getattr(self, "_continue_label", None)
        self._break_label    = l_end
        self._continue_label = l_step

        # Init
        if node.init:
            self._gen_stmt(node.init)

        # Condition check
        self._emit(f"LABEL {l_cond}")
        if node.condition:
            self._gen_expr(node.condition)
            self._emit(f"JMPF {l_end}")

        # Body
        self._gen_stmt(node.body)

        # Step
        self._emit(f"LABEL {l_step}")
        if node.step:
            self._gen_stmt(node.step)
        self._emit(f"JMP {l_cond}")
        self._emit(f"LABEL {l_end}")

        self._break_label    = saved_break
        self._continue_label = saved_continue

    # ── switch ───────────────────────────────────────────────────────────────

    def _gen_switch(self, node: ast.SwitchStmt):
        l_end = self._new_label()
        saved_break = getattr(self, "_break_label", None)
        self._break_label = l_end

        for clause in node.cases:
            if isinstance(clause, ast.CaseClause):
                l_body = self._new_label()
                l_next = self._new_label()

                self._gen_expr(node.expr)
                self._gen_expr(clause.value)
                self._emit("EQ")
                self._emit(f"JMPF {l_next}")
                self._emit(f"LABEL {l_body}")
                for s in clause.body:
                    self._gen_stmt(s)
                self._emit(f"LABEL {l_next}")

            elif isinstance(clause, ast.DefaultClause):
                for s in clause.body:
                    self._gen_stmt(s)

        self._emit(f"LABEL {l_end}")
        self._break_label = saved_break

    # ── return ───────────────────────────────────────────────────────────────

    def _gen_return(self, node: ast.ReturnStmt):
        if node.value:
            self._gen_expr(node.value)
        self._emit("RET")

    # ── expression dispatch ──────────────────────────────────────────────────

    def _gen_expr(self, node):
        if isinstance(node, ast.NumberLiteral):
            self._emit(f"PUSH_CONST {node.value}")

        elif isinstance(node, ast.StringLiteral):
            self._emit(f'PUSH_CONST "{node.value}"')

        elif isinstance(node, ast.BoolLiteral):
            self._emit(f"PUSH_CONST {node.value}")

        elif isinstance(node, ast.IdentifierExpr):
            self._emit(f"PUSH_VAR {self._var(node.name)}")

        elif isinstance(node, ast.ArrayLiteralExpr):
            for elem in node.elements:
                self._gen_expr(elem)
            self._emit(f"MAKE_ARRAY {len(node.elements)}")

        elif isinstance(node, ast.ArrayAccessExpr):
            self._gen_expr(node.index)
            self._emit(f"LOAD_IDX {self._var(node.name)}")

        elif isinstance(node, ast.GroupingExpr):
            self._gen_expr(node.inner)

        elif isinstance(node, ast.BinaryExpr):
            self._gen_binary(node)

        elif isinstance(node, ast.UnaryExpr):
            self._gen_unary(node)

        elif isinstance(node, ast.PostfixExpr):
            self._gen_postfix_expr(node)

        elif isinstance(node, ast.CallExpr):
            self._gen_call(node)

    def _gen_binary(self, node: ast.BinaryExpr):
        self._gen_expr(node.left)
        self._gen_expr(node.right)
        ops = {
            "+": "ADD",  "-": "SUB",  "*": "MUL",  "/": "DIV",  "%": "MOD",
            "==": "EQ",  "!=": "NEQ",
            "<":  "LT",  ">":  "GT",  "<=": "LEQ", ">=": "GEQ",
            "&&": "AND", "||": "OR",
        }
        self._emit(ops.get(node.op, f"UNKNOWN_OP_{node.op}"))

    def _gen_unary(self, node: ast.UnaryExpr):
        if node.op in ("++", "--"):
            if isinstance(node.operand, ast.IdentifierExpr):
                vname = self._var(node.operand.name)
                self._emit(f"PUSH_VAR {vname}")
                self._emit("PUSH_CONST 1")
                self._emit("ADD" if node.op == "++" else "SUB")
                self._emit(f"STORE_VAR {vname}")
                self._emit(f"PUSH_VAR {vname}")
        elif node.op == "-":
            self._gen_expr(node.operand)
            self._emit("NEG")
        elif node.op == "!":
            self._gen_expr(node.operand)
            self._emit("NOT")

    def _gen_postfix_expr(self, node: ast.PostfixExpr):
        """Postfix used as expression (returns OLD value)."""
        if isinstance(node.operand, ast.IdentifierExpr):
            vname = self._var(node.operand.name)
            self._emit(f"PUSH_VAR {vname}")   # old value (return value)
            self._emit(f"PUSH_VAR {vname}")
            self._emit("PUSH_CONST 1")
            self._emit("ADD" if node.op == "++" else "SUB")
            self._emit(f"STORE_VAR {vname}")

    def _gen_call(self, node: ast.CallExpr):
        if node.callee == "console.log":
            for arg in node.arguments:
                self._gen_expr(arg)
                self._emit("PRINT")
        else:
            for arg in node.arguments:
                self._gen_expr(arg)
            self._emit(f"CALL {node.callee}")
