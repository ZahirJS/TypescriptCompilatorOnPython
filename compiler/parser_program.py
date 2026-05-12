# =============================================================================
# compiler/parser_program.py
# Whole-source recursive-descent parser → AST (compiler.ast).
# Consumes the same Token stream as the line-based Parser (compiler.lexer).
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass

from compiler import ast
from compiler.lexer import Lexer
from compiler.token import Token, Types


class ProgramParseError(Exception):
    """Raised when the program parser cannot recover."""

    def __init__(self, message: str, line: int):
        super().__init__(message)
        self.message = message
        self.line = line


@dataclass
class ProgramParseResult:
    """Outcome of parse_program_source."""
    program: ast.Program
    errors: list[str]


def parse_program_source(source: str) -> ProgramParseResult:
    """
    Tokenize full source, build a Program AST, or return structured errors.
    """
    raw = Lexer(source).tokenize_all()
    tokens = [t for t in raw if t.type != Types.END]
    parser = _ProgramParser(tokens)
    try:
        program = parser.parse_program()
        return ProgramParseResult(program=program, errors=[])
    except ProgramParseError as e:
        return ProgramParseResult(
            program=ast.Program(statements=[], line=1),
            errors=[f"line {e.line}: {e.message}"],
        )


class _ProgramParser:
    """Recursive-descent parser over a flat token list."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # ------------------------------------------------------------------ utils

    def _at_end(self) -> bool:
        return self.pos >= len(self.tokens)

    def _current(self) -> Token:
        if self._at_end():
            return Token(Types.END, "", 0)
        return self.tokens[self.pos]

    def _advance(self) -> None:
        if not self._at_end():
            self.pos += 1

    def _expect_type(self, *types: object) -> Token:
        tok = self._current()
        if tok.type in types:
            self._advance()
            return tok
        names = "/".join(getattr(t, "name", str(t)) for t in types)
        raise ProgramParseError(
            f"expected {names}, got {tok.type.name} {tok.value!r}",
            tok.line,
        )

    def _expect_value(self, token_type: object, value: str) -> Token:
        tok = self._current()
        if tok.type == token_type and tok.value == value:
            self._advance()
            return tok
        raise ProgramParseError(
            f"expected {value!r} ({token_type.name}), got {tok.value!r}",
            tok.line,
        )

    # ------------------------------------------------------------------ program

    def parse_program(self) -> ast.Program:
        line = self._current().line if not self._at_end() else 1
        root = ast.Program(statements=[], line=line)
        while not self._at_end():
            if self._current().type == Types.INVALID:
                t = self._current()
                self._advance()
                raise ProgramParseError(f"invalid token {t.value!r}", t.line)
            root.statements.append(self._parse_statement())
        return root

    # ------------------------------------------------------------------ statements

    def _parse_statement(self) -> ast.Stmt:
        tok = self._current()

        if tok.type in (Types.KEYWORD_LET, Types.KEYWORD_CONST):
            return self._parse_let()

        if tok.type == Types.OPEN_BRACE:
            return self._parse_block()

        if tok.type == Types.IDENTIFIER and tok.value == "console":
            return self._parse_console_log_statement()

        if tok.type == Types.IDENTIFIER:
            return self._parse_assign()

        raise ProgramParseError(
            f"unexpected token starting statement: {tok.type.name} {tok.value!r}",
            tok.line,
        )

    def _parse_block(self) -> ast.BlockStmt:
        line = self._current().line
        self._expect_type(Types.OPEN_BRACE)
        body: list[ast.Stmt] = []
        while not self._at_end() and self._current().type != Types.CLOSE_BRACE:
            body.append(self._parse_statement())
        self._expect_type(Types.CLOSE_BRACE)
        return ast.BlockStmt(statements=body, line=line)

    def _parse_let(self) -> ast.LetStmt:
        kw_tok = self._current()
        keyword = kw_tok.value
        line = kw_tok.line
        self._expect_type(Types.KEYWORD_LET, Types.KEYWORD_CONST)

        id_tok = self._expect_type(Types.IDENTIFIER)
        name = id_tok.value

        self._expect_type(Types.OP_COLON)
        type_tok = self._current()
        type_name = _token_to_type_name(type_tok)
        if type_name is None:
            raise ProgramParseError(
                f"expected type annotation (number|string|boolean|void), got {type_tok.value!r}",
                type_tok.line,
            )
        self._advance()

        if self._current().type == Types.SEMICOLON:
            if keyword == "const":
                raise ProgramParseError(
                    "'const' declarations must have an initializer",
                    line,
                )
            self._advance()
            return ast.LetStmt(keyword, name, type_name, None, line)

        if self._current().type == Types.OP_ASSIGN:
            self._advance()
            init = self._parse_expression()
            self._expect_type(Types.SEMICOLON)
            return ast.LetStmt(keyword, name, type_name, init, line)

        raise ProgramParseError(
            f"expected ';' or '=' after type in {keyword} declaration",
            self._current().line,
        )

    def _parse_assign(self) -> ast.AssignStmt:
        id_tok = self._expect_type(Types.IDENTIFIER)
        line = id_tok.line
        self._expect_type(Types.OP_ASSIGN)
        value = self._parse_expression()
        self._expect_type(Types.SEMICOLON)
        return ast.AssignStmt(id_tok.value, value, line)

    def _parse_console_log_statement(self) -> ast.ExprStmt:
        line = self._current().line
        call = self._parse_console_log_call()
        self._expect_type(Types.SEMICOLON)
        return ast.ExprStmt(call, line)

    def _parse_console_log_call(self) -> ast.CallExpr:
        line = self._current().line
        self._expect_type(Types.IDENTIFIER)  # console
        self._expect_type(Types.OP_DOT)
        log_tok = self._expect_type(Types.IDENTIFIER)
        if log_tok.value != "log":
            raise ProgramParseError(
                f"expected 'log' after 'console.', got {log_tok.value!r}",
                log_tok.line,
            )
        self._expect_type(Types.OPEN_PAREN)
        args: list[ast.Expr] = []
        if self._current().type != Types.CLOSE_PAREN:
            args.append(self._parse_expression())
            while self._current().type == Types.COMMA:
                self._advance()
                args.append(self._parse_expression())
        self._expect_type(Types.CLOSE_PAREN)
        return ast.CallExpr("console.log", args, line)

    # ------------------------------------------------------------------ expressions

    def _parse_expression(self) -> ast.Expr:
        return self._parse_additive()

    def _parse_additive(self) -> ast.Expr:
        left = self._parse_multiplicative()
        while self._current().type in (Types.OP_ADD, Types.OP_SUB):
            op = self._current().value
            line = self._current().line
            self._advance()
            right = self._parse_multiplicative()
            left = ast.BinaryExpr(op, left, right, line)
        return left

    def _parse_multiplicative(self) -> ast.Expr:
        left = self._parse_primary()
        while self._current().type in (Types.OP_MUL, Types.OP_DIV, Types.OP_MOD):
            op = self._current().value
            line = self._current().line
            self._advance()
            right = self._parse_primary()
            left = ast.BinaryExpr(op, left, right, line)
        return left

    def _parse_primary(self) -> ast.Expr:
        tok = self._current()

        if tok.type == Types.NUMBER:
            self._advance()
            return ast.NumberLiteral(tok.value, tok.line)

        if tok.type == Types.STRING_LIT:
            self._advance()
            return ast.StringLiteral(tok.value, tok.line)

        if tok.type == Types.BOOL_LIT:
            self._advance()
            return ast.BoolLiteral(tok.value, tok.line)

        if tok.type == Types.OPEN_PAREN:
            line = tok.line
            self._advance()
            inner = self._parse_expression()
            self._expect_type(Types.CLOSE_PAREN)
            return ast.GroupingExpr(inner, line)

        if tok.type == Types.IDENTIFIER and tok.value == "console":
            return self._parse_console_log_call()

        if tok.type == Types.IDENTIFIER:
            self._advance()
            return ast.IdentifierExpr(tok.value, tok.line)

        raise ProgramParseError(
            f"expected expression, got {tok.type.name} {tok.value!r}",
            tok.line,
        )


def _token_to_type_name(tok: Token) -> str | None:
    if tok.type == Types.TYPE_NUMBER:
        return "number"
    if tok.type == Types.TYPE_STRING:
        return "string"
    if tok.type == Types.TYPE_BOOLEAN:
        return "boolean"
    if tok.type == Types.TYPE_VOID:
        return "void"
    if tok.type == Types.KEYWORD_VOID:
        return "void"
    return None
