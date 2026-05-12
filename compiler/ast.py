# =============================================================================
# compiler/ast.py
# Abstract syntax tree nodes for the whole-program parser (parser_program).
# Each node carries a source line for diagnostics.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


# Statement node types used by the program parser (Program is the root, not a Stmt).
Stmt = Union["BlockStmt", "LetStmt", "AssignStmt", "ExprStmt"]

Expr = Union[
    "NumberLiteral",
    "StringLiteral",
    "BoolLiteral",
    "IdentifierExpr",
    "BinaryExpr",
    "GroupingExpr",
    "CallExpr",
]


@dataclass
class Program:
    """Root: top-level statements."""
    statements: list[Stmt] = field(default_factory=list)
    line: int = 1

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        s = f"{pad}Program\n"
        for st in self.statements:
            s += st.tree(level + 1)
        return s


@dataclass
class BlockStmt:
    statements: list[Stmt] = field(default_factory=list)
    line: int = 0

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        s = f"{pad}Block\n"
        for st in self.statements:
            s += st.tree(level + 1)
        return s


@dataclass
class LetStmt:
    keyword: str  # "let" | "const"
    name: str
    type_name: str
    initializer: Optional[Expr]
    line: int

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        init = self.initializer.tree(level + 1) if self.initializer else ""
        hdr = f"{pad}{self.keyword} {self.name}: {self.type_name}"
        if self.initializer:
            hdr += " =\n" + init
        else:
            hdr += "\n"
        return hdr


@dataclass
class AssignStmt:
    name: str
    value: Expr
    line: int

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        return f"{pad}Assign {self.name} =\n" + self.value.tree(level + 1)


@dataclass
class ExprStmt:
    expr: Expr
    line: int

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        return f"{pad}ExprStmt\n" + self.expr.tree(level + 1)


@dataclass
class NumberLiteral:
    value: str
    line: int

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        return f"{pad}Number {self.value}\n"


@dataclass
class StringLiteral:
    value: str
    line: int

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        return f"{pad}String {self.value!r}\n"


@dataclass
class BoolLiteral:
    value: str
    line: int

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        return f"{pad}Bool {self.value}\n"


@dataclass
class IdentifierExpr:
    name: str
    line: int

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        return f"{pad}Id {self.name}\n"


@dataclass
class BinaryExpr:
    op: str
    left: Expr
    right: Expr
    line: int

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        return (
            f"{pad}Binary {self.op!r}\n"
            + self.left.tree(level + 1)
            + self.right.tree(level + 1)
        )


@dataclass
class GroupingExpr:
    inner: Expr
    line: int

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        return f"{pad}Group\n" + self.inner.tree(level + 1)


@dataclass
class CallExpr:
    """Call such as console.log(...)."""
    callee: str
    arguments: list[Expr] = field(default_factory=list)
    line: int = 0

    def tree(self, level: int = 0) -> str:
        pad = "  " * level
        s = f"{pad}Call {self.callee}(\n"
        for a in self.arguments:
            s += a.tree(level + 1)
        s += f"{pad})\n"
        return s
