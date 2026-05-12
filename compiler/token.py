# =============================================================================
# compiler/token.py
# =============================================================================

class TokenType:
    def __init__(self, name: str, label: str):
        self.name  = name
        self.label = label
    def __repr__(self):
        return f"TokenType({self.name})"


class Token:
    def __init__(self, type: "TokenType", value: str, line: int = 0):
        self.type  = type
        self.value = value
        self.line  = line
    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"


class Types:
    END     = TokenType("END",     "")
    INVALID = TokenType("INVALID", "Invalid Token")

    NUMBER     = TokenType("NUMBER",     "Number Literal")
    STRING_LIT = TokenType("STRING_LIT", "String Literal")
    BOOL_LIT   = TokenType("BOOL_LIT",   "Boolean Literal")

    IDENTIFIER = TokenType("IDENTIFIER", "Identifier")

    KEYWORD_LET      = TokenType("KEYWORD_LET",      "Keyword")
    KEYWORD_CONST    = TokenType("KEYWORD_CONST",     "Keyword")
    KEYWORD_FUNCTION = TokenType("KEYWORD_FUNCTION",  "Keyword")
    KEYWORD_RETURN   = TokenType("KEYWORD_RETURN",    "Keyword")
    KEYWORD_IF       = TokenType("KEYWORD_IF",        "Keyword")
    KEYWORD_ELSE     = TokenType("KEYWORD_ELSE",      "Keyword")
    KEYWORD_WHILE    = TokenType("KEYWORD_WHILE",     "Keyword")
    KEYWORD_FOR      = TokenType("KEYWORD_FOR",       "Keyword")
    KEYWORD_DO       = TokenType("KEYWORD_DO",        "Keyword")
    KEYWORD_SWITCH   = TokenType("KEYWORD_SWITCH",    "Keyword")
    KEYWORD_CASE     = TokenType("KEYWORD_CASE",      "Keyword")
    KEYWORD_BREAK    = TokenType("KEYWORD_BREAK",     "Keyword")
    KEYWORD_DEFAULT  = TokenType("KEYWORD_DEFAULT",   "Keyword")
    KEYWORD_CONTINUE = TokenType("KEYWORD_CONTINUE",  "Keyword")
    KEYWORD_VOID     = TokenType("KEYWORD_VOID",      "Keyword")

    TYPE_NUMBER  = TokenType("TYPE_NUMBER",  "Data Type")
    TYPE_STRING  = TokenType("TYPE_STRING",  "Data Type")
    TYPE_BOOLEAN = TokenType("TYPE_BOOLEAN", "Data Type")
    TYPE_VOID    = TokenType("TYPE_VOID",    "Data Type")

    OP_ASSIGN     = TokenType("OP_ASSIGN",     "Operator")  # =
    OP_ADD        = TokenType("OP_ADD",        "Operator")  # +
    OP_SUB        = TokenType("OP_SUB",        "Operator")  # -
    OP_MUL        = TokenType("OP_MUL",        "Operator")  # *
    OP_DIV        = TokenType("OP_DIV",        "Operator")  # /
    OP_MOD        = TokenType("OP_MOD",        "Operator")  # %
    OP_EQUAL      = TokenType("OP_EQUAL",      "Operator")  # ==
    OP_NOT_EQ     = TokenType("OP_NOT_EQ",     "Operator")  # !=
    OP_INCREMENT  = TokenType("OP_INCREMENT",  "Operator")  # ++
    OP_DECREMENT  = TokenType("OP_DECREMENT",  "Operator")  # --
    OP_GREATER    = TokenType("OP_GREATER",    "Operator")  # >
    OP_LESS       = TokenType("OP_LESS",       "Operator")  # <
    OP_GREATER_EQ = TokenType("OP_GREATER_EQ", "Operator")  # >=
    OP_LESS_EQ    = TokenType("OP_LESS_EQ",    "Operator")  # <=
    OP_AND        = TokenType("OP_AND",        "Operator")  # &&
    OP_OR         = TokenType("OP_OR",         "Operator")  # ||
    OP_NOT        = TokenType("OP_NOT",        "Operator")  # !
    OP_COLON      = TokenType("OP_COLON",      "Operator")  # :
    OP_DOT        = TokenType("OP_DOT",        "Operator")  # .

    SEMICOLON     = TokenType("SEMICOLON",     "Delimiter")  # ;
    COMMA         = TokenType("COMMA",         "Delimiter")  # ,
    OPEN_PAREN    = TokenType("OPEN_PAREN",    "Delimiter")  # (
    CLOSE_PAREN   = TokenType("CLOSE_PAREN",   "Delimiter")  # )
    OPEN_BRACE    = TokenType("OPEN_BRACE",    "Delimiter")  # {
    CLOSE_BRACE   = TokenType("CLOSE_BRACE",   "Delimiter")  # }
    OPEN_BRACKET  = TokenType("OPEN_BRACKET",  "Delimiter")  # [
    CLOSE_BRACKET = TokenType("CLOSE_BRACKET", "Delimiter")  # ]


RESERVED_WORDS: dict = {
    "let":      Types.KEYWORD_LET,
    "const":    Types.KEYWORD_CONST,
    "function": Types.KEYWORD_FUNCTION,
    "return":   Types.KEYWORD_RETURN,
    "if":       Types.KEYWORD_IF,
    "else":     Types.KEYWORD_ELSE,
    "while":    Types.KEYWORD_WHILE,
    "for":      Types.KEYWORD_FOR,
    "do":       Types.KEYWORD_DO,
    "switch":   Types.KEYWORD_SWITCH,
    "case":     Types.KEYWORD_CASE,
    "break":    Types.KEYWORD_BREAK,
    "default":  Types.KEYWORD_DEFAULT,
    "continue": Types.KEYWORD_CONTINUE,
    "void":     Types.KEYWORD_VOID,
    "true":     Types.BOOL_LIT,
    "false":    Types.BOOL_LIT,
    "number":   Types.TYPE_NUMBER,
    "string":   Types.TYPE_STRING,
    "boolean":  Types.TYPE_BOOLEAN,
}

SINGLE_CHAR_SYMBOLS: dict = {
    "=": Types.OP_ASSIGN,
    "+": Types.OP_ADD,
    "-": Types.OP_SUB,
    "*": Types.OP_MUL,
    "/": Types.OP_DIV,
    "%": Types.OP_MOD,
    ">": Types.OP_GREATER,
    "<": Types.OP_LESS,
    "!": Types.OP_NOT,
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

VALID_DATA_TYPES: set = {
    Types.TYPE_NUMBER,
    Types.TYPE_STRING,
    Types.TYPE_BOOLEAN,
    Types.TYPE_VOID,
}
