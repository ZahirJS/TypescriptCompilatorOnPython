# =============================================================================
# compiler/lexer.py
# Reads source code character by character and produces tokens.
# This is the first step of the compiler — it has no knowledge of grammar
# or meaning. It only answers: "what kind of thing is this?"
# =============================================================================

from compiler.token import (
    Token, Types,
    RESERVED_WORDS,
    SINGLE_CHAR_SYMBOLS,
)


class Lexer:
    """
    Walks through the source code one character at a time and produces tokens.

    Think of it as a scanner: it never looks at the big picture, it only
    focuses on the character it is currently reading and the one right after.
    """

    def __init__(self, source: str):
        self.source = source  # the full source code as a string
        self.index  = 0       # current reading position
        self.line   = 1       # current line number (increments on newlines)

    # -------------------------------------------------------------------------

    def next_token(self) -> Token:
        """
        Returns the next token found in the source code.
        Each call advances the reading position forward.
        When there is nothing left to read, it returns a Token of type END.
        """
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

    # -------------------------------------------------------------------------
    # Reading methods — each one handles one category of token
    # -------------------------------------------------------------------------

    def _read_number(self) -> Token:
        """
        Reads a full number, including decimals.
        Example: finds '4' and keeps reading until it hits '2' → returns '42'
        """
        start = self.index
        while not self._is_at_end() and self._current_char().isdigit():
            self._advance()

        # handle decimal numbers like 3.14
        if not self._is_at_end() and self._current_char() == ".":
            self._advance()
            while not self._is_at_end() and self._current_char().isdigit():
                self._advance()

        value = self.source[start:self.index]
        return Token(Types.NUMBER, value, self.line)

    def _read_word(self) -> Token:
        """
        Reads a full word (letters, digits, underscores).
        Then checks if it is a reserved word or just an identifier.
        Example: 'let' → KEYWORD_LET,  'myVar' → IDENTIFIER
        """
        start = self.index
        while not self._is_at_end() and (self._current_char().isalnum() or self._current_char() == "_"):
            self._advance()

        value = self.source[start:self.index]

        # look up the word — if it is reserved, use its type; otherwise it is an identifier
        kind = RESERVED_WORDS.get(value, Types.IDENTIFIER)
        return Token(kind, value, self.line)

    def _read_string(self, quote_char: str) -> Token:
        """
        Reads a string literal enclosed in single or double quotes.
        Example: finds '"' and keeps reading until it finds the closing '"'
        """
        self._advance()  # skip the opening quote
        start = self.index

        while not self._is_at_end() and self._current_char() != quote_char:
            self._advance()

        value = self.source[start:self.index]
        self._advance()  # skip the closing quote
        return Token(Types.STRING_LIT, value, self.line)

    def _read_symbol(self) -> Token:
        """
        Reads a single or two-character symbol.
        Two-character operators like == and != require peeking one char ahead.
        """
        current = self._current_char()
        self._advance()

        # check for two-character operators before falling back to single-char
        if current == "=" and not self._is_at_end() and self._current_char() == "=":
            self._advance()
            return Token(Types.OP_EQUAL, "==", self.line)

        if current == "!" and not self._is_at_end() and self._current_char() == "=":
            self._advance()
            return Token(Types.OP_NOT_EQ, "!=", self.line)

        kind = SINGLE_CHAR_SYMBOLS.get(current, Types.INVALID)
        return Token(kind, current, self.line)

    # -------------------------------------------------------------------------
    # Skipping methods — things the compiler does not care about
    # -------------------------------------------------------------------------

    def _skip_whitespace_and_comments(self):
        """
        Skips spaces, tabs, newlines, and both styles of comments.
        Comments are meaningless to the compiler — ignoring them here
        means no other part of the compiler ever has to think about them.
        """
        while not self._is_at_end():
            current = self._current_char()

            if current == "\n":
                self.line += 1  # track line number for error messages
                self._advance()

            elif current in (" ", "\t", "\r"):
                self._advance()

            # single-line comment: // this is ignored until end of line
            elif current == "/" and self._peek() == "/":
                while not self._is_at_end() and self._current_char() != "\n":
                    self._advance()

            # multi-line comment: /* everything in here is ignored */
            elif current == "/" and self._peek() == "*":
                self._advance()
                self._advance()
                while not self._is_at_end():
                    if self._current_char() == "*" and self._peek() == "/":
                        self._advance()
                        self._advance()
                        break
                    if self._current_char() == "\n":
                        self.line += 1
                    self._advance()

            else:
                break

    # -------------------------------------------------------------------------
    # Helper methods — small utilities used by the reading methods above
    # -------------------------------------------------------------------------

    def _current_char(self) -> str:
        return self.source[self.index]

    def _peek(self) -> str:
        """
        Returns the character after the current one without consuming it.
        Used to detect two-character operators like == and !=.
        Returns empty string if already at the end.
        """
        next_index = self.index + 1
        if next_index >= len(self.source):
            return ""
        return self.source[next_index]

    def _advance(self):
        """Moves the reading position forward by one character."""
        self.index += 1

    def _is_at_end(self) -> bool:
        return self.index >= len(self.source)

    # -------------------------------------------------------------------------

    def tokenize_all(self) -> list[Token]:
        """
        Convenience method — runs through the entire source and returns
        all tokens as a list. Useful for testing and for the IDE output panel.
        """
        tokens = []
        while True:
            token = self.next_token()
            tokens.append(token)
            if token.type == Types.END:
                break
        return tokens