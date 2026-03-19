# =============================================================================
# token.py
# Define the building blocks of the language.
# Every other piece of the compiler depends on this file.
# =============================================================================


class TokenType:
    """
    A token kind — what category a piece of source code belongs to.
    Separating name from label lets the compiler compare types internally
    while showing something readable to the user.
    """
    def __init__(self, name: str, label: str):
        self.name  = name
        self.label = label

    def __repr__(self):
        return f"TokenType({self.name})"


class Token:
    """
    One unit of meaning found in the source code.
    Stores what it is (type), what it says (value), and where it appeared (line).
    The line number is critical for producing useful error messages later.
    """
    def __init__(self, type: TokenType, value: str, line: int = 0):
        self.type  = type
        self.value = value
        self.line  = line

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"


# =============================================================================
# All token types the compiler recognizes, grouped by category.
# =============================================================================

class Types:
    """
    Central registry of every TokenType.
    Import this wherever a token type needs to be referenced.

        from compiler.token import Types
        if token.type == Types.KEYWORD_LET: ...
    """

    # ── General ──────────────────────────────────────────────────────────────
    END     = TokenType("END",     "")
    INVALID = TokenType("INVALID", "Invalid Token")

    # ── Literals ─────────────────────────────────────────────────────────────
    NUMBER     = TokenType("NUMBER",     "Number Literal")
    STRING_LIT = TokenType("STRING_LIT", "String Literal")
    BOOL_LIT   = TokenType("BOOL_LIT",   "Boolean Literal")

    # ── Identifier ───────────────────────────────────────────────────────────
    IDENTIFIER = TokenType("IDENTIFIER", "Identifier")

    # ── Keywords ─────────────────────────────────────────────────────────────
    KEYWORD_LET      = TokenType("KEYWORD_LET",      "Keyword")
    KEYWORD_CONST    = TokenType("KEYWORD_CONST",    "Keyword")
    KEYWORD_FUNCTION = TokenType("KEYWORD_FUNCTION", "Keyword")
    KEYWORD_RETURN   = TokenType("KEYWORD_RETURN",   "Keyword")
    KEYWORD_IF       = TokenType("KEYWORD_IF",       "Keyword")
    KEYWORD_ELSE     = TokenType("KEYWORD_ELSE",     "Keyword")
    KEYWORD_WHILE    = TokenType("KEYWORD_WHILE",    "Keyword")
    KEYWORD_FOR      = TokenType("KEYWORD_FOR",      "Keyword")
    KEYWORD_VOID     = TokenType("KEYWORD_VOID",     "Keyword")

    # ── Data types ────────────────────────────────────────────────────────────
    # Kept separate from keywords so the semantic analyzer can check
    # "is this token a valid type annotation?" without listing them again.
    TYPE_NUMBER  = TokenType("TYPE_NUMBER",  "Data Type")
    TYPE_STRING  = TokenType("TYPE_STRING",  "Data Type")
    TYPE_BOOLEAN = TokenType("TYPE_BOOLEAN", "Data Type")
    TYPE_VOID    = TokenType("TYPE_VOID",    "Data Type")

    # ── Operators ─────────────────────────────────────────────────────────────
    OP_ASSIGN  = TokenType("OP_ASSIGN",  "Operator")  # =
    OP_ADD     = TokenType("OP_ADD",     "Operator")  # +
    OP_SUB     = TokenType("OP_SUB",     "Operator")  # -
    OP_MUL     = TokenType("OP_MUL",     "Operator")  # *
    OP_DIV     = TokenType("OP_DIV",     "Operator")  # /
    OP_MOD     = TokenType("OP_MOD",     "Operator")  # %
    OP_EQUAL   = TokenType("OP_EQUAL",   "Operator")  # ==
    OP_NOT_EQ  = TokenType("OP_NOT_EQ",  "Operator")  # !=
    OP_GREATER = TokenType("OP_GREATER", "Operator")  # >
    OP_LESS    = TokenType("OP_LESS",    "Operator")  # <
    OP_COLON   = TokenType("OP_COLON",   "Operator")  # : used in type annotations
    OP_DOT     = TokenType("OP_DOT",     "Operator")  # . used in console.log

    # ── Delimiters ────────────────────────────────────────────────────────────
    SEMICOLON     = TokenType("SEMICOLON",     "Delimiter")  # ;
    COMMA         = TokenType("COMMA",         "Delimiter")  # ,
    OPEN_PAREN    = TokenType("OPEN_PAREN",    "Delimiter")  # (
    CLOSE_PAREN   = TokenType("CLOSE_PAREN",   "Delimiter")  # )
    OPEN_BRACE    = TokenType("OPEN_BRACE",    "Delimiter")  # {
    CLOSE_BRACE   = TokenType("CLOSE_BRACE",   "Delimiter")  # }
    OPEN_BRACKET  = TokenType("OPEN_BRACKET",  "Delimiter")  # [
    CLOSE_BRACKET = TokenType("CLOSE_BRACKET", "Delimiter")  # ]


# =============================================================================
# Lookup tables used by the Lexer.
# They live here because they describe what things ARE, not how to read them.
# =============================================================================

# Maps every reserved word to its token type.
# If a word is not here, the Lexer treats it as an IDENTIFIER.
RESERVED_WORDS: dict[str, TokenType] = {
    "let":      Types.KEYWORD_LET,
    "const":    Types.KEYWORD_CONST,
    "function": Types.KEYWORD_FUNCTION,
    "return":   Types.KEYWORD_RETURN,
    "if":       Types.KEYWORD_IF,
    "else":     Types.KEYWORD_ELSE,
    "while":    Types.KEYWORD_WHILE,
    "for":      Types.KEYWORD_FOR,
    "void":     Types.KEYWORD_VOID,
    "true":     Types.BOOL_LIT,
    "false":    Types.BOOL_LIT,
    "number":   Types.TYPE_NUMBER,
    "string":   Types.TYPE_STRING,
    "boolean":  Types.TYPE_BOOLEAN,
}

# Maps every recognized symbol to its token type.
# Two-character operators like == and != are handled separately in the Lexer
# because they require looking one character ahead.
SINGLE_CHAR_SYMBOLS: dict[str, TokenType] = {
    "=": Types.OP_ASSIGN,
    "+": Types.OP_ADD,
    "-": Types.OP_SUB,
    "*": Types.OP_MUL,
    "/": Types.OP_DIV,
    "%": Types.OP_MOD,
    ">": Types.OP_GREATER,
    "<": Types.OP_LESS,
    ":": Types.OP_COLON,
    ".": Types.OP_DOT,
    ";": Types.SEMICOLON,
    ",": Types.COMMA,
    "(": Types.OPEN_PAREN,
    ")": Types.CLOSE_PAREN,
    "{": Types.OPEN_BRACE,
    "}": Types.CLOSE_BRACE,
    "[": Types.OPEN_BRACKET,
    "]": Types.CLOSE_BRACKET,
}

# The semantic analyzer uses this to verify that a type annotation
# like ": number" or ": string" is actually a valid data type.
VALID_DATA_TYPES: set[TokenType] = {
    Types.TYPE_NUMBER,
    Types.TYPE_STRING,
    Types.TYPE_BOOLEAN,
    Types.TYPE_VOID,
}