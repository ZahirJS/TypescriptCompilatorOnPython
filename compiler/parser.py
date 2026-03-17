# =============================================================================
# compiler/parser.py
# Validates that tokens are in the correct structural order.
#
# The Lexer answers "what is this?"
# The Parser answers "is this structured correctly?"
# The Semantic analyzer answers "does this make sense?"
# =============================================================================

from compiler.token import Types, VALID_DATA_TYPES
from compiler.lexer import Lexer


# =============================================================================
# Parse result — describes what pattern was found on a line
# =============================================================================

class ParseResult:
    """
    Describes the outcome of parsing one line.
    Stores what pattern was identified and whether the structure is valid.
    """

    def __init__(self, pattern: str, is_valid: bool, message: str, line: int):
        self.pattern  = pattern   # what kind of statement this is
        self.is_valid = is_valid  # whether the structure is correct
        self.message  = message   # description or error detail
        self.line     = line

    def __repr__(self):
        status = "ok" if self.is_valid else "error"
        return f"line {self.line:<4} [{status}]  {self.pattern:<24}  {self.message}"


# =============================================================================
# Parser — checks the structural order of tokens line by line
# =============================================================================

class Parser:
    """
    Walks through the source code line by line and verifies that each line
    matches a known structural pattern of the language.

    It does not check meaning — only structure.
    That means it does not care if a variable was already declared,
    only that the tokens are in the right order.
    """

    def parse(self, source: str) -> list[ParseResult]:
        """
        Entry point — parses every line and returns a result for each one.
        Unlike the semantic analyzer, the parser reports both valid and
        invalid lines so the user can see the full structural picture.
        """
        results = []
        for line_number, line in enumerate(source.splitlines(), start=1):
            line = line.strip()
            if not line or line in ("{", "}"):
                continue
            results.append(self._parse_line(line, line_number))
        return results

    # -------------------------------------------------------------------------
    # Line parsing — identifies which pattern to try
    # -------------------------------------------------------------------------

    def _parse_line(self, line: str, line_number: int) -> ParseResult:
        tokens = Lexer(line).tokenize_all()
        tokens = [t for t in tokens if t.type != Types.END]

        if not tokens:
            return self._unknown("Empty line.", line_number)

        first = tokens[0]

        if first.type in (Types.KEYWORD_LET, Types.KEYWORD_CONST):
            return self._parse_variable_declaration(tokens, line_number)

        if first.type == Types.KEYWORD_FUNCTION:
            return self._parse_function_declaration(tokens, line_number)

        if first.type == Types.IDENTIFIER:
            if first.value == "import":
                return self._parse_import(tokens, line_number)
            if first.value == "console" and len(tokens) > 1 and tokens[1].value == ".":
                return self._parse_console_log(tokens, line_number)
            return self._parse_assignment(tokens, line_number)

        return self._unknown(
            f'Unrecognized pattern starting with "{first.value}".',
            line_number
        )

    # -------------------------------------------------------------------------
    # Pattern 1 — variable declaration
    # let x: number;
    # -------------------------------------------------------------------------

    def _parse_variable_declaration(self, tokens, line_number: int) -> ParseResult:
        """
        Expected structure:  let <identifier> : <data type> ;
        Checks token order only — does not validate meaning.
        """
        if len(tokens) < 5:
            return self._invalid(
                "Variable declaration",
                "Incomplete — expected: let <name> : <type> ;",
                line_number
            )

        identifier = tokens[1]
        colon      = tokens[2]
        data_type  = tokens[3]
        semicolon  = tokens[4]

        if identifier.type != Types.IDENTIFIER:
            return self._invalid(
                "Variable declaration",
                f'Expected an identifier after "{tokens[0].value}" but found "{identifier.value}".',
                line_number
            )

        if colon.type != Types.OP_COLON:
            return self._invalid(
                "Variable declaration",
                f'Expected ":" after "{identifier.value}" but found "{colon.value}".',
                line_number
            )

        if data_type.type not in VALID_DATA_TYPES:
            return self._invalid(
                "Variable declaration",
                f'Expected a data type after ":" but found "{data_type.value}".',
                line_number
            )

        if semicolon.type != Types.SEMICOLON:
            return self._invalid(
                "Variable declaration",
                f'Expected ";" at the end but found "{semicolon.value}".',
                line_number
            )

        return self._valid(
            "Variable declaration",
            f'{tokens[0].value} {identifier.value}: {data_type.value};',
            line_number
        )

    # -------------------------------------------------------------------------
    # Pattern 2 — function declaration
    # function main(): void {
    # -------------------------------------------------------------------------

    def _parse_function_declaration(self, tokens, line_number: int) -> ParseResult:
        """
        Expected structure:  function <identifier> ( ) : <return type> {
        """
        if len(tokens) < 7:
            return self._invalid(
                "Function declaration",
                "Incomplete — expected: function <name> ( ) : <type> {",
                line_number
            )

        name        = tokens[1]
        open_paren  = tokens[2]
        close_paren = tokens[3]
        colon       = tokens[4]
        return_type = tokens[5]
        open_brace  = tokens[6]

        if name.type != Types.IDENTIFIER:
            return self._invalid(
                "Function declaration",
                f'Expected a function name but found "{name.value}".',
                line_number
            )

        if open_paren.type != Types.OPEN_PAREN:
            return self._invalid(
                "Function declaration",
                f'Expected "(" after function name but found "{open_paren.value}".',
                line_number
            )

        if close_paren.type != Types.CLOSE_PAREN:
            return self._invalid(
                "Function declaration",
                f'Expected ")" but found "{close_paren.value}".',
                line_number
            )

        if colon.type != Types.OP_COLON:
            return self._invalid(
                "Function declaration",
                f'Expected ":" before return type but found "{colon.value}".',
                line_number
            )

        if return_type.type not in VALID_DATA_TYPES and return_type.type != Types.KEYWORD_VOID:
            return self._invalid(
                "Function declaration",
                f'Expected a return type but found "{return_type.value}".',
                line_number
            )

        if open_brace.type != Types.OPEN_BRACE:
            return self._invalid(
                "Function declaration",
                f'Expected "{{" to open the function body but found "{open_brace.value}".',
                line_number
            )

        return self._valid(
            "Function declaration",
            f'function {name.value}(): {return_type.value}',
            line_number
        )

    # -------------------------------------------------------------------------
    # Pattern 3 — assignment
    # x = 5;
    # -------------------------------------------------------------------------

    def _parse_assignment(self, tokens, line_number: int) -> ParseResult:
        """
        Expected structure:  <identifier> = <value> ;
        Only checks structure — does not verify the variable was declared.
        """
        if len(tokens) < 2:
            return self._invalid(
                "Assignment",
                "Incomplete — expected: <name> = <value> ;",
                line_number
            )

        identifier = tokens[0]
        operator   = tokens[1]

        if operator.type != Types.OP_ASSIGN:
            return self._invalid(
                "Assignment",
                f'Expected "=" after "{identifier.value}" but found "{operator.value}".',
                line_number
            )

        if tokens[-1].type != Types.SEMICOLON:
            return self._invalid(
                "Assignment",
                f'Missing ";" at the end of statement.',
                line_number
            )

        return self._valid(
            "Assignment",
            f'{identifier.value} = ...',
            line_number
        )

    # -------------------------------------------------------------------------
    # Pattern 4 — import statement
    # import something from "somewhere";
    # import { x, y } from "somewhere";
    # -------------------------------------------------------------------------

    def _parse_import(self, tokens, line_number: int) -> ParseResult:
        """
        Expected structure:  import <identifier or { }> from "<path>" ;
        Checks that the import keyword is followed by a valid structure.
        """

        # minimum:  import  x  from  "path"  ;  → 5 tokens
        if len(tokens) < 5:
            return self._invalid(
                "Import statement",
                'Incomplete — expected: import <name> from "<path>" ;',
                line_number
            )

        # find the "from" keyword position — it separates what we import from where
        from_index = next(
            (i for i, t in enumerate(tokens) if t.value == "from"),
            None
        )

        if from_index is None:
            return self._invalid(
                "Import statement",
                'Missing "from" keyword.',
                line_number
            )

        # after "from" we need a string literal path and a semicolon
        if from_index + 1 >= len(tokens):
            return self._invalid(
                "Import statement",
                'Expected a path after "from".',
                line_number
            )

        path      = tokens[from_index + 1]
        semicolon = tokens[-1]

        if path.type != Types.STRING_LIT:
            return self._invalid(
                "Import statement",
                f'Expected a quoted path after "from" but found "{path.value}".',
                line_number
            )

        if semicolon.type != Types.SEMICOLON:
            return self._invalid(
                "Import statement",
                'Missing ";" at the end of import.',
                line_number
            )

        return self._valid(
            "Import statement",
            f'import ... from "{path.value}";',
            line_number
        )

    # -------------------------------------------------------------------------
    # Pattern 5 — console.log call
    # console.log(x);
    # -------------------------------------------------------------------------

    def _parse_console_log(self, tokens, line_number: int) -> ParseResult:
        """
        Expected structure:  console . log ( <argument> ) ;
        The argument can be an identifier, a number, or a string literal.
        """

        # minimum:  console  .  log  (  x  )  ;  → 7 tokens
        if len(tokens) < 7:
            return self._invalid(
                "console.log",
                "Incomplete — expected: console.log(<value>);",
                line_number
            )

        dot         = tokens[1]
        log         = tokens[2]
        open_paren  = tokens[3]
        argument    = tokens[4]
        close_paren = tokens[5]
        semicolon   = tokens[6]

        if dot.value != ".":
            return self._invalid(
                "console.log",
                f'Expected "." after "console" but found "{dot.value}".',
                line_number
            )

        if log.value != "log":
            return self._invalid(
                "console.log",
                f'Expected "log" but found "{log.value}".',
                line_number
            )

        if open_paren.type != Types.OPEN_PAREN:
            return self._invalid(
                "console.log",
                f'Expected "(" but found "{open_paren.value}".',
                line_number
            )

        # the argument must be an identifier, number, or string literal
        valid_argument_types = {Types.IDENTIFIER, Types.NUMBER, Types.STRING_LIT}
        if argument.type not in valid_argument_types:
            return self._invalid(
                "console.log",
                f'Expected a value inside console.log() but found "{argument.value}".',
                line_number
            )

        if close_paren.type != Types.CLOSE_PAREN:
            return self._invalid(
                "console.log",
                f'Expected ")" but found "{close_paren.value}".',
                line_number
            )

        if semicolon.type != Types.SEMICOLON:
            return self._invalid(
                "console.log",
                'Missing ";" after console.log().',
                line_number
            )

        return self._valid(
            "console.log",
            f'console.log({argument.value})',
            line_number
        )

    # -------------------------------------------------------------------------
    # Result builders
    # -------------------------------------------------------------------------

    def _valid(self, pattern: str, message: str, line: int) -> ParseResult:
        return ParseResult(pattern, True, message, line)

    def _invalid(self, pattern: str, message: str, line: int) -> ParseResult:
        return ParseResult(pattern, False, message, line)

    def _unknown(self, message: str, line: int) -> ParseResult:
        return ParseResult("Unknown", False, message, line)