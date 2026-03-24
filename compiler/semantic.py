# =============================================================================
# compiler/semantic.py
# Validates that the tokens produced by the Lexer form meaningful statements.
# This is where the compiler understands intent, not just syntax.
#
# The Lexer answers "what is this?"
# The semantic analyzer answers "does this make sense?"
# =============================================================================

from compiler.token import Types, VALID_DATA_TYPES
from compiler.lexer import Lexer


# =============================================================================
# Severity — how serious is the problem?
# Errors mean the code cannot compile. Warnings mean something is suspicious
# but the compiler can continue processing.
# =============================================================================

class Severity:
    ERROR   = "error"
    WARNING = "warning"


# =============================================================================
# Results — every analysis produces one of these
# =============================================================================

class AnalysisResult:
    """
    Wraps the outcome of analyzing one line.
    Keeps the display logic out of the analyzer itself.
    """
    def __init__(self, message: str, line: int, severity: str = Severity.ERROR):
        self.message  = message
        self.line     = line
        self.severity = severity

    def is_error(self):
        return self.severity == Severity.ERROR

    def is_warning(self):
        return self.severity == Severity.WARNING

    def __repr__(self):
        return f"[{self.severity.upper()}] line {self.line}: {self.message}"


# =============================================================================
# Symbol table — remembers every variable that has been declared
# =============================================================================

class SymbolTable:
    """
    Stores every declared variable and its type.
    Used to detect when the same variable is declared twice with different types.

    Structure:
        { "x": { "type": "number", "line": 1 } }
    """

    def __init__(self):
        self._table: dict = {}

    def declare(self, name: str, type_name: str, line: int):
        self._table[name] = { "type": type_name, "line": line }

    def lookup(self, name: str) -> dict | None:
        return self._table.get(name)

    def exists(self, name: str) -> bool:
        return name in self._table

    def all_entries(self) -> dict:
        return dict(self._table)


# =============================================================================
# Semantic analyzer — reads tokens line by line and validates patterns
# =============================================================================

class SemanticAnalyzer:
    """
    Takes source code, tokenizes it line by line, and validates each line
    against the patterns the language supports.

    Each line either matches a known pattern and gets validated,
    or is reported as unrecognized.
    """

    def __init__(self):
        self.symbol_table = SymbolTable()

    def analyze(self, source: str) -> list[AnalysisResult]:
        """
        Entry point — analyzes every line in the source and returns only
        errors and warnings. Lines that are valid produce nothing.
        """
        results = []
        for line_number, line in enumerate(source.splitlines(), start=1):
            line = line.strip()
            if not line or line in ("{", "}"):
                continue
            result = self._analyze_line(line, line_number)
            if result is not None:
                results.append(result)
        return results

    # -------------------------------------------------------------------------
    # Line analysis — decides which pattern to try
    # -------------------------------------------------------------------------

    def _analyze_line(self, line: str, line_number: int) -> AnalysisResult | None:
        """
        Tokenizes a single line and decides which pattern it matches.
        """
        tokens = Lexer(line).tokenize_all()
        tokens = [t for t in tokens if t.type != Types.END]

        if not tokens:
            return None

        first = tokens[0]

        if first.type in (Types.KEYWORD_LET, Types.KEYWORD_CONST):
            return self._validate_variable_declaration(tokens, line_number)

        if first.type == Types.KEYWORD_FUNCTION:
            return self._validate_function_declaration(tokens, line_number)

        if first.type == Types.KEYWORD_IF:
            return self._validate_if_statement(tokens, line_number)

        if first.type == Types.IDENTIFIER:
            if first.value == "console" and len(tokens) > 1 and tokens[1].value == ".":
                return self._validate_console_log(tokens, line_number)
            if first.value == "import":
                return None
            return self._validate_assignment(tokens, line_number)

        return None

    # -------------------------------------------------------------------------
    # Pattern 1 — variable declaration
    # let x: number;
    # const _name: string;
    # -------------------------------------------------------------------------

    def _validate_variable_declaration(self, tokens, line_number: int) -> AnalysisResult | None:
        """
        Validates meaning only — structure is the parser's responsibility.
        Checks: is the type valid? was this variable already declared?
        Does NOT check identifier validity — that belongs to the parser.
        """
        if len(tokens) < 5:
            return None  # incomplete structure — parser will catch this

        identifier = tokens[1]
        data_type  = tokens[3]

        # if the identifier is not valid, the parser already reported it
        if identifier.type != Types.IDENTIFIER:
            return None

        # the type annotation must be a recognized data type
        if data_type.type not in VALID_DATA_TYPES:
            return self._invalid(
                f'"{data_type.value}" is not a valid data type. '
                f'Valid types are: number, string, boolean.',
                line_number
            )

        name      = identifier.value
        type_name = data_type.value

        # check if this variable was already declared
        existing = self.symbol_table.lookup(name)
        if existing:
            if existing["type"] != type_name:
                return self._ambiguous(
                    f'"{name}" was already declared as {existing["type"]} on line {existing["line"]}. '
                    f'Now declared as {type_name}.',
                    line_number
                )
            else:
                return self._invalid(
                    f'"{name}" was already declared on line {existing["line"]}.',
                    line_number
                )

        # all good — register the variable in the symbol table
        self.symbol_table.declare(name, type_name, line_number)
        return None

    # -------------------------------------------------------------------------
    # Pattern 2 — function declaration
    # function main(): void {
    # -------------------------------------------------------------------------

    def _validate_function_declaration(self, tokens, line_number: int) -> AnalysisResult | None:
        """
        Validates the pattern:  function <identifier> ( ) : <return type> {
        """
        if len(tokens) < 7:
            return None  # incomplete structure — parser will catch this

        name        = tokens[1]
        return_type = tokens[5]

        if name.type != Types.IDENTIFIER:
            return None  # parser already caught this

        if return_type.type not in VALID_DATA_TYPES and return_type.type != Types.KEYWORD_VOID:
            return self._invalid(
                f'"{return_type.value}" is not a valid return type.',
                line_number
            )

        return None

    # -------------------------------------------------------------------------
    # Pattern 3 — assignment
    # x = 0;
    # Semicolon validation belongs to the parser — structure is its responsibility.
    # The semantic analyzer only checks meaning: was this variable declared?
    # -------------------------------------------------------------------------

    def _validate_assignment(self, tokens, line_number: int) -> AnalysisResult | None:
        """
        Validates the pattern:  <identifier> = <value> ;
        Only checks whether the variable was declared — nothing else.
        """
        name = tokens[0].value

        if not self.symbol_table.exists(name):
            return self._warning(
                f'"{name}" is used but was never declared.',
                line_number
            )

        return None

    # -------------------------------------------------------------------------
    # Pattern 4 — console.log call
    # console.log(x);
    # Only checks if the argument variable exists in the symbol table.
    # Structure validation belongs to the parser.
    # -------------------------------------------------------------------------

    def _validate_console_log(self, tokens, line_number: int) -> AnalysisResult | None:
        """
        Checks that the argument passed to console.log was declared.
        Numbers and string literals are always valid — no declaration needed.
        """
        if len(tokens) < 7:
            return None  # incomplete structure — parser will catch this

        argument = tokens[4]

        if argument.type in (Types.NUMBER, Types.STRING_LIT):
            return None

        if argument.type == Types.IDENTIFIER:
            if not self.symbol_table.exists(argument.value):
                return self._warning(
                    f'"{argument.value}" passed to console.log was never declared.',
                    line_number
                )

        return None

    # -------------------------------------------------------------------------
    # Pattern 5 — if statement
    # if( x == 3 ){
    # Only checks if the variable in the condition was declared.
    # Structure validation (operators, braces) belongs to the parser.
    # -------------------------------------------------------------------------

    def _validate_if_statement(self, tokens, line_number: int) -> AnalysisResult | None:
        """
        Validates that the variable used in the if condition was declared.

        Valid:    if( x == 3 ){      — x exists in symbol table
        Warning:  if( cargo == 3 ){  — cargo was never declared
        """
        if len(tokens) < 7:
            return None  # incomplete structure — parser will catch this

        identifier = tokens[2]

        # only validate if the condition is well-formed
        if identifier.type != Types.IDENTIFIER:
            return None

        if not self.symbol_table.exists(identifier.value):
            return self._warning(
                f'"{identifier.value}" used in if condition was never declared.',
                line_number
            )

        return None

    # -------------------------------------------------------------------------
    # Result builders — keep the result construction in one place
    # -------------------------------------------------------------------------

    def _invalid(self, message: str, line: int) -> AnalysisResult:
        return AnalysisResult(message, line, Severity.ERROR)

    def _warning(self, message: str, line: int) -> AnalysisResult:
        return AnalysisResult(message, line, Severity.WARNING)

    def _ambiguous(self, message: str, line: int) -> AnalysisResult:
        # ambiguous means the same variable exists with a different type —
        # the compiler cannot know which one the programmer intended
        return AnalysisResult(f"AMBIGUITY — {message}", line, Severity.WARNING)