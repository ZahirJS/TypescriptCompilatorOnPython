# =============================================================================
# compiler/lexer.py
# =============================================================================

from compiler.token import (
    Token, Types,
    RESERVED_WORDS,
    SINGLE_CHAR_SYMBOLS,
)


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.index  = 0
        self.line   = 1

    def next_token(self) -> Token:
        self._skip_whitespace_and_comments()
        if self._is_at_end():
            return Token(Types.END, "", self.line)
        current = self._current_char()
        if current.isdigit():
            return self._read_number()
        if current.isalpha() or current == "_":
            return self._read_word()
        if current == '"' or current == "'":
            return self._read_string(current)
        return self._read_symbol()

    # ── readers ──────────────────────────────────────────────────────────────

    def _read_number(self) -> Token:
        start = self.index
        while not self._is_at_end() and self._current_char().isdigit():
            self._advance()
        if not self._is_at_end() and self._current_char() == ".":
            self._advance()
            while not self._is_at_end() and self._current_char().isdigit():
                self._advance()
        return Token(Types.NUMBER, self.source[start:self.index], self.line)

    def _read_word(self) -> Token:
        start = self.index
        while not self._is_at_end() and (self._current_char().isalnum() or self._current_char() == "_"):
            self._advance()
        value = self.source[start:self.index]
        kind  = RESERVED_WORDS.get(value, Types.IDENTIFIER)
        return Token(kind, value, self.line)

    def _read_string(self, quote_char: str) -> Token:
        self._advance()
        start = self.index
        while not self._is_at_end() and self._current_char() != quote_char:
            self._advance()
        value = self.source[start:self.index]
        self._advance()
        return Token(Types.STRING_LIT, value, self.line)

    def _read_symbol(self) -> Token:
        current = self._current_char()
        self._advance()
        nxt = self._current_char() if not self._is_at_end() else ""

        # Two-character operators — check before single-char fallback
        if current == "+" and nxt == "+":
            self._advance(); return Token(Types.OP_INCREMENT, "++", self.line)
        if current == "-" and nxt == "-":
            self._advance(); return Token(Types.OP_DECREMENT, "--", self.line)
        if current == "=" and nxt == "=":
            self._advance(); return Token(Types.OP_EQUAL, "==", self.line)
        if current == "!" and nxt == "=":
            self._advance(); return Token(Types.OP_NOT_EQ, "!=", self.line)
        if current == ">" and nxt == "=":
            self._advance(); return Token(Types.OP_GREATER_EQ, ">=", self.line)
        if current == "<" and nxt == "=":
            self._advance(); return Token(Types.OP_LESS_EQ, "<=", self.line)
        if current == "&" and nxt == "&":
            self._advance(); return Token(Types.OP_AND, "&&", self.line)
        if current == "|" and nxt == "|":
            self._advance(); return Token(Types.OP_OR, "||", self.line)

        kind = SINGLE_CHAR_SYMBOLS.get(current, Types.INVALID)
        return Token(kind, current, self.line)

    # ── skippers ─────────────────────────────────────────────────────────────

    def _skip_whitespace_and_comments(self):
        while not self._is_at_end():
            c = self._current_char()
            if c == "\n":
                self.line += 1; self._advance()
            elif c in (" ", "\t", "\r"):
                self._advance()
            elif c == "/" and self._peek() == "/":
                while not self._is_at_end() and self._current_char() != "\n":
                    self._advance()
            elif c == "/" and self._peek() == "*":
                self._advance(); self._advance()
                while not self._is_at_end():
                    if self._current_char() == "*" and self._peek() == "/":
                        self._advance(); self._advance(); break
                    if self._current_char() == "\n":
                        self.line += 1
                    self._advance()
            else:
                break

    # ── helpers ──────────────────────────────────────────────────────────────

    def _current_char(self) -> str:
        return self.source[self.index]

    def _peek(self) -> str:
        ni = self.index + 1
        return self.source[ni] if ni < len(self.source) else ""

    def _advance(self):
        self.index += 1

    def _is_at_end(self) -> bool:
        return self.index >= len(self.source)

    def tokenize_all(self) -> list:
        tokens = []
        while True:
            t = self.next_token()
            tokens.append(t)
            if t.type == Types.END:
                break
        return tokens
