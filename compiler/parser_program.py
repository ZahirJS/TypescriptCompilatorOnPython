# =============================================================================
# compiler/parser_program.py
# Full recursive-descent parser → AST
# =============================================================================

from __future__ import annotations
from dataclasses import dataclass
from compiler import ast
from compiler.lexer import Lexer
from compiler.token import Token, Types


class ProgramParseError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(message)
        self.message = message
        self.line    = line


@dataclass
class ProgramParseResult:
    program: ast.Program
    errors: list


def parse_program_source(source: str) -> ProgramParseResult:
    raw    = Lexer(source).tokenize_all()
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


# =============================================================================
class _ProgramParser:
    def __init__(self, tokens: list):
        self.tokens = tokens
        self.pos    = 0

    # ── utilities ──────────────────────────────────────────────────────────

    def _at_end(self) -> bool:
        return self.pos >= len(self.tokens)

    def _current(self) -> Token:
        return self.tokens[self.pos] if not self._at_end() else Token(Types.END, "", 0)

    def _peek_next(self) -> Token:
        i = self.pos + 1
        return self.tokens[i] if i < len(self.tokens) else Token(Types.END, "", 0)

    def _advance(self) -> Token:
        t = self._current()
        if not self._at_end():
            self.pos += 1
        return t

    def _expect_type(self, *types) -> Token:
        tok = self._current()
        if tok.type in types:
            return self._advance()
        names = "/".join(getattr(t, "name", str(t)) for t in types)
        raise ProgramParseError(
            f"expected {names}, got '{tok.value}' ({tok.type.name})", tok.line)

    def _expect_value(self, token_type, value: str) -> Token:
        tok = self._current()
        if tok.type == token_type and tok.value == value:
            return self._advance()
        raise ProgramParseError(
            f"expected '{value}', got '{tok.value}'", tok.line)

    def _match(self, *types) -> bool:
        return self._current().type in types

    # ── type annotation ─────────────────────────────────────────────────────

    def _parse_type(self) -> str:
        """Returns type name string: 'number', 'string', 'boolean', 'void', 'number[]', etc."""
        tok = self._current()
        base_map = {
            Types.TYPE_NUMBER:  "number",
            Types.TYPE_STRING:  "string",
            Types.TYPE_BOOLEAN: "boolean",
            Types.TYPE_VOID:    "void",
            Types.KEYWORD_VOID: "void",
        }
        if tok.type not in base_map:
            raise ProgramParseError(
                f"expected type annotation, got '{tok.value}'", tok.line)
        base = base_map[tok.type]
        self._advance()
        # Check for array type: number[]
        if self._match(Types.OPEN_BRACKET):
            self._advance()
            self._expect_type(Types.CLOSE_BRACKET)
            return base + "[]"
        return base

    # ── program ─────────────────────────────────────────────────────────────

    def parse_program(self) -> ast.Program:
        line = self._current().line if not self._at_end() else 1
        root = ast.Program(statements=[], line=line)
        while not self._at_end():
            if self._current().type == Types.INVALID:
                t = self._advance()
                raise ProgramParseError(f"invalid token '{t.value}'", t.line)
            root.statements.append(self._parse_statement())
        return root

    # ── statements ──────────────────────────────────────────────────────────

    def _parse_statement(self) -> ast.Stmt:
        tok = self._current()

        if tok.type in (Types.KEYWORD_LET, Types.KEYWORD_CONST):
            return self._parse_let()
        if tok.type == Types.KEYWORD_FUNCTION:
            return self._parse_function()
        if tok.type == Types.KEYWORD_IF:
            return self._parse_if()
        if tok.type == Types.KEYWORD_WHILE:
            return self._parse_while()
        if tok.type == Types.KEYWORD_FOR:
            return self._parse_for()
        if tok.type == Types.KEYWORD_SWITCH:
            return self._parse_switch()
        if tok.type == Types.KEYWORD_RETURN:
            return self._parse_return()
        if tok.type == Types.KEYWORD_BREAK:
            self._advance()
            self._expect_type(Types.SEMICOLON)
            return ast.BreakStmt(tok.line)
        if tok.type == Types.KEYWORD_CONTINUE:
            self._advance()
            self._expect_type(Types.SEMICOLON)
            return ast.ContinueStmt(tok.line)
        if tok.type == Types.OPEN_BRACE:
            return self._parse_block()
        if tok.type == Types.IDENTIFIER:
            return self._parse_identifier_statement()

        raise ProgramParseError(
            f"unexpected token '{tok.value}' starting statement", tok.line)

    def _parse_block(self) -> ast.BlockStmt:
        line = self._current().line
        self._expect_type(Types.OPEN_BRACE)
        body = []
        while not self._at_end() and not self._match(Types.CLOSE_BRACE):
            body.append(self._parse_statement())
        self._expect_type(Types.CLOSE_BRACE)
        return ast.BlockStmt(statements=body, line=line)

    def _parse_let(self) -> ast.LetStmt:
        kw  = self._current(); keyword = kw.value; line = kw.line
        self._advance()
        id_tok = self._expect_type(Types.IDENTIFIER)
        name   = id_tok.value
        self._expect_type(Types.OP_COLON)
        type_name = self._parse_type()

        if self._match(Types.SEMICOLON):
            if keyword == "const":
                raise ProgramParseError("'const' must have an initializer", line)
            self._advance()
            return ast.LetStmt(keyword, name, type_name, None, line)

        if self._match(Types.OP_ASSIGN):
            self._advance()
            init = self._parse_expression()
            self._expect_type(Types.SEMICOLON)
            return ast.LetStmt(keyword, name, type_name, init, line)

        raise ProgramParseError(
            f"expected ';' or '=' after type in {keyword} declaration",
            self._current().line)

    def _parse_function(self) -> ast.FunctionDecl:
        line = self._current().line
        self._advance()  # consume 'function'
        name_tok = self._expect_type(Types.IDENTIFIER)
        name     = name_tok.value

        self._expect_type(Types.OPEN_PAREN)
        params = []
        while not self._at_end() and not self._match(Types.CLOSE_PAREN):
            p_id = self._expect_type(Types.IDENTIFIER)
            self._expect_type(Types.OP_COLON)
            p_type = self._parse_type()
            params.append(ast.Param(p_id.value, p_type, p_id.line))
            if self._match(Types.COMMA):
                self._advance()
        self._expect_type(Types.CLOSE_PAREN)

        ret_type = "void"
        if self._match(Types.OP_COLON):
            self._advance()
            ret_type = self._parse_type()

        body = self._parse_block()
        return ast.FunctionDecl(name, params, ret_type, body, line)

    def _parse_if(self) -> ast.IfStmt:
        line = self._current().line
        self._advance()  # consume 'if'
        self._expect_type(Types.OPEN_PAREN)
        cond = self._parse_expression()
        self._expect_type(Types.CLOSE_PAREN)
        then_block = self._parse_statement()
        else_block = None
        if self._match(Types.KEYWORD_ELSE):
            self._advance()
            else_block = self._parse_statement()
        return ast.IfStmt(cond, then_block, else_block, line)

    def _parse_while(self) -> ast.WhileStmt:
        line = self._current().line
        self._advance()
        self._expect_type(Types.OPEN_PAREN)
        cond = self._parse_expression()
        self._expect_type(Types.CLOSE_PAREN)
        body = self._parse_statement()
        return ast.WhileStmt(cond, body, line)

    def _parse_for(self) -> ast.ForStmt:
        line = self._current().line
        self._advance()  # consume 'for'
        self._expect_type(Types.OPEN_PAREN)

        # Init: let declaration or assignment (semicolon IS the separator here)
        init = None
        if self._match(Types.KEYWORD_LET, Types.KEYWORD_CONST):
            init = self._parse_for_let_init()
        elif not self._match(Types.SEMICOLON):
            init = self._parse_for_assign_init()
        self._expect_type(Types.SEMICOLON)

        # Condition
        cond = None
        if not self._match(Types.SEMICOLON):
            cond = self._parse_expression()
        self._expect_type(Types.SEMICOLON)

        # Step (no trailing semicolon — ends at ')')
        step = None
        if not self._match(Types.CLOSE_PAREN):
            step = self._parse_for_step()
        self._expect_type(Types.CLOSE_PAREN)

        body = self._parse_statement()
        return ast.ForStmt(init, cond, step, body, line)

    def _parse_for_let_init(self) -> ast.LetStmt:
        """let / const  name : type  [ = expr ]  — no trailing semicolon."""
        kw = self._current(); keyword = kw.value; line = kw.line
        self._advance()
        id_tok = self._expect_type(Types.IDENTIFIER)
        self._expect_type(Types.OP_COLON)
        type_name = self._parse_type()
        if self._match(Types.OP_ASSIGN):
            self._advance()
            init = self._parse_expression()
            return ast.LetStmt(keyword, id_tok.value, type_name, init, line)
        return ast.LetStmt(keyword, id_tok.value, type_name, None, line)

    def _parse_for_assign_init(self) -> ast.AssignStmt:
        """name = expr  or  name[idx] = expr — no trailing semicolon."""
        name_tok = self._expect_type(Types.IDENTIFIER)
        name = name_tok.value; line = name_tok.line
        if self._match(Types.OPEN_BRACKET):
            self._advance()
            idx = self._parse_expression()
            self._expect_type(Types.CLOSE_BRACKET)
            self._expect_type(Types.OP_ASSIGN)
            val = self._parse_expression()
            return ast.AssignStmt(name, idx, val, line)
        self._expect_type(Types.OP_ASSIGN)
        val = self._parse_expression()
        return ast.AssignStmt(name, None, val, line)

    def _parse_for_step(self) -> ast.Stmt:
        """name = expr  |  name[idx] = expr  |  name++  |  name-- — no semicolon."""
        name_tok = self._expect_type(Types.IDENTIFIER)
        name = name_tok.value; line = name_tok.line
        if self._match(Types.OPEN_BRACKET):
            self._advance()
            idx = self._parse_expression()
            self._expect_type(Types.CLOSE_BRACKET)
            self._expect_type(Types.OP_ASSIGN)
            val = self._parse_expression()
            return ast.AssignStmt(name, idx, val, line)
        if self._match(Types.OP_ASSIGN):
            self._advance()
            val = self._parse_expression()
            return ast.AssignStmt(name, None, val, line)
        if self._match(Types.OP_INCREMENT, Types.OP_DECREMENT):
            op = self._current().value; self._advance()
            return ast.ExprStmt(ast.PostfixExpr(op, ast.IdentifierExpr(name, line), line), line)
        raise ProgramParseError(f"invalid for-step starting with '{name}'", line)

    def _parse_switch(self) -> ast.SwitchStmt:
        line = self._current().line
        self._advance()
        self._expect_type(Types.OPEN_PAREN)
        expr = self._parse_expression()
        self._expect_type(Types.CLOSE_PAREN)
        self._expect_type(Types.OPEN_BRACE)

        cases = []
        while not self._at_end() and not self._match(Types.CLOSE_BRACE):
            if self._match(Types.KEYWORD_CASE):
                cl = self._current().line; self._advance()
                val = self._parse_expression()
                self._expect_type(Types.OP_COLON)
                body = []
                while (not self._at_end() and
                       not self._match(Types.KEYWORD_CASE, Types.KEYWORD_DEFAULT, Types.CLOSE_BRACE)):
                    body.append(self._parse_statement())
                cases.append(ast.CaseClause(val, body, cl))
            elif self._match(Types.KEYWORD_DEFAULT):
                dl = self._current().line; self._advance()
                self._expect_type(Types.OP_COLON)
                body = []
                while (not self._at_end() and
                       not self._match(Types.KEYWORD_CASE, Types.KEYWORD_DEFAULT, Types.CLOSE_BRACE)):
                    body.append(self._parse_statement())
                cases.append(ast.DefaultClause(body, dl))
            else:
                t = self._current()
                raise ProgramParseError(f"expected 'case' or 'default', got '{t.value}'", t.line)

        self._expect_type(Types.CLOSE_BRACE)
        return ast.SwitchStmt(expr, cases, line)

    def _parse_return(self) -> ast.ReturnStmt:
        line = self._current().line
        self._advance()
        if self._match(Types.SEMICOLON):
            self._advance()
            return ast.ReturnStmt(None, line)
        val = self._parse_expression()
        self._expect_type(Types.SEMICOLON)
        return ast.ReturnStmt(val, line)

    def _parse_identifier_statement(self) -> ast.Stmt:
        name_tok = self._current()
        name = name_tok.value; line = name_tok.line

        # console.log
        if name == "console":
            return self._parse_console_log_stmt()

        self._advance()  # consume the identifier

        # arr[idx] = expr ;
        if self._match(Types.OPEN_BRACKET):
            self._advance()
            idx = self._parse_expression()
            self._expect_type(Types.CLOSE_BRACKET)
            self._expect_type(Types.OP_ASSIGN)
            val = self._parse_expression()
            self._expect_type(Types.SEMICOLON)
            return ast.AssignStmt(name, idx, val, line)

        # x = expr ;
        if self._match(Types.OP_ASSIGN):
            self._advance()
            val = self._parse_expression()
            self._expect_type(Types.SEMICOLON)
            return ast.AssignStmt(name, None, val, line)

        # i++ ;  or  i-- ;
        if self._match(Types.OP_INCREMENT, Types.OP_DECREMENT):
            op = self._current().value; self._advance()
            self._expect_type(Types.SEMICOLON)
            return ast.ExprStmt(ast.PostfixExpr(op, ast.IdentifierExpr(name, line), line), line)

        # func(args) ;
        if self._match(Types.OPEN_PAREN):
            call = self._parse_call_args(name, line)
            self._expect_type(Types.SEMICOLON)
            return ast.ExprStmt(call, line)

        raise ProgramParseError(f"unexpected token after '{name}'", self._current().line)

    def _parse_console_log_stmt(self) -> ast.ExprStmt:
        line = self._current().line
        call = self._parse_console_log_call()
        self._expect_type(Types.SEMICOLON)
        return ast.ExprStmt(call, line)

    def _parse_console_log_call(self) -> ast.CallExpr:
        line = self._current().line
        self._advance()               # console
        self._expect_type(Types.OP_DOT)
        log = self._expect_type(Types.IDENTIFIER)
        if log.value != "log":
            raise ProgramParseError(f"expected 'log' after 'console.', got '{log.value}'", log.line)
        self._expect_type(Types.OPEN_PAREN)
        args = []
        if not self._match(Types.CLOSE_PAREN):
            args.append(self._parse_expression())
            while self._match(Types.COMMA):
                self._advance()
                args.append(self._parse_expression())
        self._expect_type(Types.CLOSE_PAREN)
        return ast.CallExpr("console.log", args, line)

    def _parse_call_args(self, name: str, line: int) -> ast.CallExpr:
        self._expect_type(Types.OPEN_PAREN)
        args = []
        if not self._match(Types.CLOSE_PAREN):
            args.append(self._parse_expression())
            while self._match(Types.COMMA):
                self._advance()
                args.append(self._parse_expression())
        self._expect_type(Types.CLOSE_PAREN)
        return ast.CallExpr(name, args, line)

    # ── expressions ─────────────────────────────────────────────────────────
    # Precedence (lowest to highest):
    #   logical-or > logical-and > equality > relational >
    #   additive > multiplicative > unary > postfix > primary

    def _parse_expression(self) -> ast.Expr:
        return self._parse_logical_or()

    def _parse_logical_or(self) -> ast.Expr:
        left = self._parse_logical_and()
        while self._match(Types.OP_OR):
            op = self._advance().value
            right = self._parse_logical_and()
            left  = ast.BinaryExpr(op, left, right, left.line)
        return left

    def _parse_logical_and(self) -> ast.Expr:
        left = self._parse_equality()
        while self._match(Types.OP_AND):
            op = self._advance().value
            right = self._parse_equality()
            left  = ast.BinaryExpr(op, left, right, left.line)
        return left

    def _parse_equality(self) -> ast.Expr:
        left = self._parse_relational()
        while self._match(Types.OP_EQUAL, Types.OP_NOT_EQ):
            op = self._advance().value
            right = self._parse_relational()
            left  = ast.BinaryExpr(op, left, right, left.line)
        return left

    def _parse_relational(self) -> ast.Expr:
        left = self._parse_additive()
        while self._match(Types.OP_LESS, Types.OP_GREATER,
                          Types.OP_LESS_EQ, Types.OP_GREATER_EQ):
            op = self._advance().value
            right = self._parse_additive()
            left  = ast.BinaryExpr(op, left, right, left.line)
        return left

    def _parse_additive(self) -> ast.Expr:
        left = self._parse_multiplicative()
        while self._match(Types.OP_ADD, Types.OP_SUB):
            op = self._advance().value
            right = self._parse_multiplicative()
            left  = ast.BinaryExpr(op, left, right, left.line)
        return left

    def _parse_multiplicative(self) -> ast.Expr:
        left = self._parse_unary()
        while self._match(Types.OP_MUL, Types.OP_DIV, Types.OP_MOD):
            op = self._advance().value
            right = self._parse_unary()
            left  = ast.BinaryExpr(op, left, right, left.line)
        return left

    def _parse_unary(self) -> ast.Expr:
        if self._match(Types.OP_SUB, Types.OP_NOT, Types.OP_INCREMENT, Types.OP_DECREMENT):
            tok = self._advance()
            operand = self._parse_unary()
            return ast.UnaryExpr(tok.value, operand, tok.line)
        return self._parse_postfix()

    def _parse_postfix(self) -> ast.Expr:
        node = self._parse_primary()
        if self._match(Types.OP_INCREMENT, Types.OP_DECREMENT):
            op  = self._advance().value
            return ast.PostfixExpr(op, node, node.line)
        return node

    def _parse_primary(self) -> ast.Expr:
        tok = self._current()

        if tok.type == Types.NUMBER:
            self._advance(); return ast.NumberLiteral(tok.value, tok.line)

        if tok.type == Types.STRING_LIT:
            self._advance(); return ast.StringLiteral(tok.value, tok.line)

        if tok.type == Types.BOOL_LIT:
            self._advance(); return ast.BoolLiteral(tok.value, tok.line)

        if tok.type == Types.OPEN_BRACKET:
            return self._parse_array_literal()

        if tok.type == Types.OPEN_PAREN:
            self._advance()
            inner = self._parse_expression()
            self._expect_type(Types.CLOSE_PAREN)
            return ast.GroupingExpr(inner, tok.line)

        if tok.type == Types.IDENTIFIER and tok.value == "console":
            return self._parse_console_log_call()

        if tok.type == Types.IDENTIFIER:
            self._advance()
            # arr[index]
            if self._match(Types.OPEN_BRACKET):
                self._advance()
                idx = self._parse_expression()
                self._expect_type(Types.CLOSE_BRACKET)
                return ast.ArrayAccessExpr(tok.value, idx, tok.line)
            # func(args)
            if self._match(Types.OPEN_PAREN):
                return self._parse_call_args(tok.value, tok.line)
            return ast.IdentifierExpr(tok.value, tok.line)

        raise ProgramParseError(
            f"unexpected token in expression: '{tok.value}'", tok.line)

    def _parse_array_literal(self) -> ast.ArrayLiteralExpr:
        line = self._current().line
        self._advance()  # consume '['
        elements = []
        if not self._match(Types.CLOSE_BRACKET):
            elements.append(self._parse_expression())
            while self._match(Types.COMMA):
                self._advance()
                elements.append(self._parse_expression())
        self._expect_type(Types.CLOSE_BRACKET)
        return ast.ArrayLiteralExpr(elements, line)
