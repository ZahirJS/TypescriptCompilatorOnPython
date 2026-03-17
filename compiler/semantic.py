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

        if first.type == Types.IDENTIFIER:
            return self._validate_assignment(tokens, line_number)

        return self._invalid(
            f'Unrecognized pattern starting with "{first.value}".',
            line_number
        )

    # -------------------------------------------------------------------------
    # Pattern 1 — variable declaration
    # let x: number;
    # const _name: string;
    # -------------------------------------------------------------------------

    def _validate_variable_declaration(self, tokens, line_number: int) -> AnalysisResult | None:
        """
        Validates the pattern:  let <identifier> : <data type> ;
        Also checks the symbol table for duplicate declarations.

        Valid:      let x: number;
        Invalid:    let 2x: number;   (identifier starts with digit)
        Ambiguous:  let x: string;    (x was already declared as number)
        """

        # we need at least:  let  x  :  number  ;  → 5 tokens
        if len(tokens) < 5:
            return self._invalid(
                "Incomplete variable declaration.",
                line_number
            )

        keyword    = tokens[0]   # let / const
        identifier = tokens[1]   # variable name
        colon      = tokens[2]   # :
        data_type  = tokens[3]   # number / string / boolean
        semicolon  = tokens[4]   # ;

        # the name must be a valid identifier
        if identifier.type != Types.IDENTIFIER:
            return self._invalid(
                f'"{identifier.value}" is not a valid identifier. '
                f'Variable names must start with a letter or underscore.',
                line_number
            )

        # the colon must be present
        if colon.type != Types.OP_COLON:
            return self._invalid(
                f'Expected ":" after "{identifier.value}" but found "{colon.value}".',
                line_number
            )

        # the type annotation must be a recognized data type
        if data_type.type not in VALID_DATA_TYPES:
            return self._invalid(
                f'"{data_type.value}" is not a valid data type. '
                f'Valid types are: number, string, boolean.',
                line_number
            )

        # the statement must end with a semicolon
        if semicolon.type != Types.SEMICOLON:
            return self._invalid(
                f'Expected ";" at the end of the declaration but found "{semicolon.value}".',
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

        # we need at least:  function  main  (  )  :  void  {  → 7 tokens
        if len(tokens) < 7:
            return self._invalid(
                "Incomplete function declaration.",
                line_number
            )

        keyword     = tokens[0]   # function
        name        = tokens[1]   # function name
        open_paren  = tokens[2]   # (
        close_paren = tokens[3]   # )
        colon       = tokens[4]   # :
        return_type = tokens[5]   # void / number / string / boolean
        open_brace  = tokens[6]   # {

        if name.type != Types.IDENTIFIER:
            return self._invalid(
                f'Expected a function name but found "{name.value}".',
                line_number
            )

        if open_paren.type != Types.OPEN_PAREN:
            return self._invalid(
                f'Expected "(" after function name but found "{open_paren.value}".',
                line_number
            )

        if close_paren.type != Types.CLOSE_PAREN:
            return self._invalid(
                f'Expected ")" but found "{close_paren.value}".',
                line_number
            )

        if colon.type != Types.OP_COLON:
            return self._invalid(
                f'Expected ":" before return type but found "{colon.value}".',
                line_number
            )

        if return_type.type not in VALID_DATA_TYPES and return_type.type != Types.KEYWORD_VOID:
            return self._invalid(
                f'"{return_type.value}" is not a valid return type.',
                line_number
            )

        if open_brace.type != Types.OPEN_BRACE:
            return self._invalid(
                f'Expected "{{" to open the function body but found "{open_brace.value}".',
                line_number
            )

        return None

    # -------------------------------------------------------------------------
    # Pattern 3 — assignment
    # x = 0;
    # -------------------------------------------------------------------------

    def _validate_assignment(self, tokens, line_number: int) -> AnalysisResult | None:
        """
        Validates the pattern:  <identifier> = <value> ;
        Warns if the variable was never declared.
        """
        name = tokens[0].value

        # if the variable was never declared, warn the user
        if not self.symbol_table.exists(name):
            return self._warning(
                f'"{name}" is used but was never declared.',
                line_number
            )

        return None

    # -------------------------------------------------------------------------
    # Result builders — keep the result construction in one place
    # -------------------------------------------------------------------------

    def _valid(self, message: str, line: int) -> None:
        return None

    def _invalid(self, message: str, line: int) -> AnalysisResult:
        return AnalysisResult(message, line, Severity.ERROR)

    def _warning(self, message: str, line: int) -> AnalysisResult:
        return AnalysisResult(message, line, Severity.WARNING)

    def _ambiguous(self, message: str, line: int) -> AnalysisResult:
        # ambiguous means the same variable exists with a different type —
        # the compiler cannot know which one the programmer intended
        return AnalysisResult(f"AMBIGUITY — {message}", line, Severity.WARNING)