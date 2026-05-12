# =============================================================================
# compiler/ast.py
# All AST node types.  Every node carries a source line for diagnostics.
# =============================================================================

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Union, List


# ---------------------------------------------------------------------------
# Forward-declare the union types so dataclasses can reference each other.
# ---------------------------------------------------------------------------

Expr = Union[
    "NumberLiteral", "StringLiteral", "BoolLiteral",
    "IdentifierExpr", "BinaryExpr", "GroupingExpr",
    "CallExpr", "UnaryExpr", "PostfixExpr",
    "ArrayLiteralExpr", "ArrayAccessExpr",
]

Stmt = Union[
    "BlockStmt", "LetStmt", "AssignStmt", "ExprStmt",
    "IfStmt", "WhileStmt", "ForStmt",
    "SwitchStmt", "CaseClause", "DefaultClause",
    "BreakStmt", "ContinueStmt", "ReturnStmt",
    "FunctionDecl",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pad(level: int) -> str:
    return "  " * level


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

@dataclass
class Program:
    statements: List[Stmt] = field(default_factory=list)
    line: int = 1

    def tree(self, level: int = 0) -> str:
        s = f"{_pad(level)}Program\n"
        for st in self.statements:
            s += st.tree(level + 1)
        return s


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class BlockStmt:
    statements: List[Stmt] = field(default_factory=list)
    line: int = 0

    def tree(self, level: int = 0) -> str:
        s = f"{_pad(level)}Block\n"
        for st in self.statements:
            s += st.tree(level + 1)
        return s


@dataclass
class LetStmt:
    """let / const  name : type  [ = initializer ] ;"""
    keyword: str         # "let" | "const"
    name: str
    type_name: str       # "number", "string", "boolean", "void", "number[]", etc.
    initializer: Optional[Expr]
    line: int

    def tree(self, level: int = 0) -> str:
        hdr = f"{_pad(level)}{self.keyword} {self.name}: {self.type_name}"
        if self.initializer:
            return hdr + " =\n" + self.initializer.tree(level + 1)
        return hdr + "\n"


@dataclass
class AssignStmt:
    """name = value  OR  name[index] = value"""
    name: str
    index: Optional[Expr]   # None for simple assignment
    value: Expr
    line: int

    def tree(self, level: int = 0) -> str:
        if self.index is not None:
            return (f"{_pad(level)}Assign {self.name}[...] =\n"
                    + self.index.tree(level + 2)
                    + self.value.tree(level + 1))
        return f"{_pad(level)}Assign {self.name} =\n" + self.value.tree(level + 1)


@dataclass
class ExprStmt:
    expr: Expr
    line: int

    def tree(self, level: int = 0) -> str:
        return f"{_pad(level)}ExprStmt\n" + self.expr.tree(level + 1)


@dataclass
class IfStmt:
    condition: Expr
    then_block: Stmt
    else_block: Optional[Stmt]
    line: int

    def tree(self, level: int = 0) -> str:
        s  = f"{_pad(level)}If\n"
        s += f"{_pad(level+1)}Condition\n" + self.condition.tree(level + 2)
        s += f"{_pad(level+1)}Then\n"      + self.then_block.tree(level + 2)
        if self.else_block:
            s += f"{_pad(level+1)}Else\n" + self.else_block.tree(level + 2)
        return s


@dataclass
class WhileStmt:
    condition: Expr
    body: Stmt
    line: int

    def tree(self, level: int = 0) -> str:
        s  = f"{_pad(level)}While\n"
        s += f"{_pad(level+1)}Condition\n" + self.condition.tree(level + 2)
        s += f"{_pad(level+1)}Body\n"      + self.body.tree(level + 2)
        return s


@dataclass
class ForStmt:
    """for ( init ; condition ; step ) body"""
    init: Optional[Stmt]     # LetStmt or AssignStmt (no semicolon consumed)
    condition: Optional[Expr]
    step: Optional[Stmt]     # AssignStmt or ExprStmt(PostfixExpr)
    body: Stmt
    line: int

    def tree(self, level: int = 0) -> str:
        s  = f"{_pad(level)}For\n"
        if self.init:
            s += f"{_pad(level+1)}Init\n" + self.init.tree(level + 2)
        if self.condition:
            s += f"{_pad(level+1)}Cond\n" + self.condition.tree(level + 2)
        if self.step:
            s += f"{_pad(level+1)}Step\n" + self.step.tree(level + 2)
        s += f"{_pad(level+1)}Body\n" + self.body.tree(level + 2)
        return s


@dataclass
class SwitchStmt:
    expr: Expr
    cases: List[Stmt]   # list of CaseClause / DefaultClause
    line: int

    def tree(self, level: int = 0) -> str:
        s = f"{_pad(level)}Switch\n" + self.expr.tree(level + 1)
        for c in self.cases:
            s += c.tree(level + 1)
        return s


@dataclass
class CaseClause:
    value: Expr
    body: List[Stmt]
    line: int

    def tree(self, level: int = 0) -> str:
        s = f"{_pad(level)}Case\n" + self.value.tree(level + 1)
        for st in self.body:
            s += st.tree(level + 1)
        return s


@dataclass
class DefaultClause:
    body: List[Stmt]
    line: int

    def tree(self, level: int = 0) -> str:
        s = f"{_pad(level)}Default\n"
        for st in self.body:
            s += st.tree(level + 1)
        return s


@dataclass
class BreakStmt:
    line: int

    def tree(self, level: int = 0) -> str:
        return f"{_pad(level)}Break\n"


@dataclass
class ContinueStmt:
    line: int

    def tree(self, level: int = 0) -> str:
        return f"{_pad(level)}Continue\n"


@dataclass
class ReturnStmt:
    value: Optional[Expr]
    line: int

    def tree(self, level: int = 0) -> str:
        if self.value:
            return f"{_pad(level)}Return\n" + self.value.tree(level + 1)
        return f"{_pad(level)}Return\n"


@dataclass
class Param:
    name: str
    type_name: str
    line: int

    def tree(self, level: int = 0) -> str:
        return f"{_pad(level)}Param {self.name}: {self.type_name}\n"


@dataclass
class FunctionDecl:
    name: str
    params: List[Param]
    return_type: str
    body: BlockStmt
    line: int

    def tree(self, level: int = 0) -> str:
        s = f"{_pad(level)}Function {self.name}(...): {self.return_type}\n"
        for p in self.params:
            s += p.tree(level + 1)
        s += self.body.tree(level + 1)
        return s


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class NumberLiteral:
    value: str
    line: int

    def tree(self, level: int = 0) -> str:
        return f"{_pad(level)}Number {self.value}\n"


@dataclass
class StringLiteral:
    value: str
    line: int

    def tree(self, level: int = 0) -> str:
        return f"{_pad(level)}String {self.value!r}\n"


@dataclass
class BoolLiteral:
    value: str
    line: int

    def tree(self, level: int = 0) -> str:
        return f"{_pad(level)}Bool {self.value}\n"


@dataclass
class IdentifierExpr:
    name: str
    line: int

    def tree(self, level: int = 0) -> str:
        return f"{_pad(level)}Id {self.name}\n"


@dataclass
class BinaryExpr:
    """Covers arithmetic, comparison, and logical binary operators."""
    op: str
    left: Expr
    right: Expr
    line: int

    def tree(self, level: int = 0) -> str:
        return (f"{_pad(level)}Binary {self.op!r}\n"
                + self.left.tree(level + 1)
                + self.right.tree(level + 1))


@dataclass
class GroupingExpr:
    inner: Expr
    line: int

    def tree(self, level: int = 0) -> str:
        return f"{_pad(level)}Group\n" + self.inner.tree(level + 1)


@dataclass
class CallExpr:
    """Function call: callee(arg1, arg2, ...)"""
    callee: str
    arguments: List[Expr] = field(default_factory=list)
    line: int = 0

    def tree(self, level: int = 0) -> str:
        s = f"{_pad(level)}Call {self.callee}(\n"
        for a in self.arguments:
            s += a.tree(level + 1)
        s += f"{_pad(level)})\n"
        return s


@dataclass
class UnaryExpr:
    """Prefix unary: -, !, ++x, --x"""
    op: str
    operand: Expr
    line: int

    def tree(self, level: int = 0) -> str:
        return f"{_pad(level)}Unary {self.op}\n" + self.operand.tree(level + 1)


@dataclass
class PostfixExpr:
    """Postfix: x++, x--"""
    op: str
    operand: Expr
    line: int

    def tree(self, level: int = 0) -> str:
        return f"{_pad(level)}Postfix {self.op}\n" + self.operand.tree(level + 1)


@dataclass
class ArrayLiteralExpr:
    """[ expr, expr, ... ]"""
    elements: List[Expr]
    line: int

    def tree(self, level: int = 0) -> str:
        s = f"{_pad(level)}ArrayLiteral\n"
        for e in self.elements:
            s += e.tree(level + 1)
        return s


@dataclass
class ArrayAccessExpr:
    """name[index]"""
    name: str
    index: Expr
    line: int

    def tree(self, level: int = 0) -> str:
        return (f"{_pad(level)}ArrayAccess {self.name}[\n"
                + self.index.tree(level + 1)
                + f"{_pad(level)}]\n")
