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
        self.pattern  = pattern
        self.is_valid = is_valid
        self.message  = message
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
    """

    # relational operators valid inside an if condition
    RELATIONAL_OPS = {
        Types.OP_EQUAL,
        Types.OP_NOT_EQ,
        Types.OP_GREATER,
        Types.OP_LESS,
    }

    def parse(self, source: str) -> list[ParseResult]:
        """
        Entry point — parses every line and returns a result for each one.
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

        if first.type == Types.KEYWORD_IF:
            return self._parse_if_statement(tokens, line_number)

        if first.type == Types.KEYWORD_SWITCH:
            return self._parse_switch_statement(tokens, line_number)

        if first.type == Types.KEYWORD_CASE:
            return self._parse_case_statement(tokens, line_number)

        if first.type == Types.KEYWORD_DEFAULT:
            return self._parse_default_statement(tokens, line_number)

        if first.type == Types.KEYWORD_BREAK:
            return self._parse_break_statement(tokens, line_number)

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
        """
        if len(tokens) < 5:
            return self._invalid(
                "Variable declaration",
                "Incomplete — expected: let <n> : <type> ;",
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
                "Incomplete — expected: function <n> ( ) : <type> {",
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
        """
        if len(tokens) < 2:
            return self._invalid(
                "Assignment",
                "Incomplete — expected: <n> = <value> ;",
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
                'Missing ";" at the end of statement.',
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
    # -------------------------------------------------------------------------

    def _parse_import(self, tokens, line_number: int) -> ParseResult:
        """
        Expected structure:  import <identifier> from "<path>" ;
        """
        if len(tokens) < 5:
            return self._invalid(
                "Import statement",
                'Incomplete — expected: import <n> from "<path>" ;',
                line_number
            )

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
        """
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
    # Pattern 6 — if statement
    # if( variable == 3 ){
    # -------------------------------------------------------------------------

    def _parse_if_statement(self, tokens, line_number: int) -> ParseResult:
        """
        Expected structure:  if ( <identifier> <relational_op> <value> ) {
        """
        if len(tokens) < 7:
            return self._invalid(
                "If statement",
                "Incomplete — expected: if( <var> <op> <value> ){",
                line_number
            )

        open_paren  = tokens[1]
        identifier  = tokens[2]
        operator    = tokens[3]
        value       = tokens[4]
        close_paren = tokens[5]
        open_brace  = tokens[6]

        if open_paren.type != Types.OPEN_PAREN:
            return self._invalid(
                "If statement",
                f'Expected "(" after "if" but found "{open_paren.value}".',
                line_number
            )

        if identifier.type != Types.IDENTIFIER:
            return self._invalid(
                "If statement",
                f'Expected a variable inside the condition but found "{identifier.value}".',
                line_number
            )

        if operator.type == Types.OP_ASSIGN:
            return self._invalid(
                "If statement",
                'Expected a relational operator (==, !=, >, <) but found "=" — did you mean "=="?',
                line_number
            )

        if operator.type not in self.RELATIONAL_OPS:
            return self._invalid(
                "If statement",
                f'Expected a relational operator (==, !=, >, <) but found "{operator.value}".',
                line_number
            )

        valid_value_types = {Types.NUMBER, Types.STRING_LIT, Types.BOOL_LIT, Types.IDENTIFIER}
        if value.type not in valid_value_types:
            return self._invalid(
                "If statement",
                f'Expected a value to compare against but found "{value.value}".',
                line_number
            )

        if close_paren.type != Types.CLOSE_PAREN:
            return self._invalid(
                "If statement",
                f'Expected ")" to close the condition but found "{close_paren.value}".',
                line_number
            )

        if open_brace.type != Types.OPEN_BRACE:
            return self._invalid(
                "If statement",
                'Expected "{" to open the if body.',
                line_number
            )

        return self._valid(
            "If statement",
            f'if( {identifier.value} {operator.value} {value.value} ){{',
            line_number
        )

    # -------------------------------------------------------------------------
    # Pattern 7 — switch statement
    # switch( variable ){
    # -------------------------------------------------------------------------

    def _parse_switch_statement(self, tokens, line_number: int) -> ParseResult:
        """
        Expected structure:  switch ( <identifier> ) {

        Valid:    switch( x ){
        Invalid:  switch( x )     ← missing {
        Invalid:  switch( ){      ← missing variable
        """

        # minimum:  switch  (  x  )  {  → 5 tokens
        if len(tokens) < 5:
            return self._invalid(
                "Switch statement",
                "Incomplete — expected: switch( <var> ){",
                line_number
            )

        open_paren  = tokens[1]
        identifier  = tokens[2]
        close_paren = tokens[3]
        open_brace  = tokens[4]

        if open_paren.type != Types.OPEN_PAREN:
            return self._invalid(
                "Switch statement",
                f'Expected "(" after "switch" but found "{open_paren.value}".',
                line_number
            )

        if identifier.type != Types.IDENTIFIER:
            return self._invalid(
                "Switch statement",
                f'Expected a variable inside switch() but found "{identifier.value}".',
                line_number
            )

        if close_paren.type != Types.CLOSE_PAREN:
            return self._invalid(
                "Switch statement",
                f'Expected ")" but found "{close_paren.value}".',
                line_number
            )

        if open_brace.type != Types.OPEN_BRACE:
            return self._invalid(
                "Switch statement",
                'Expected "{" to open the switch body.',
                line_number
            )

        return self._valid(
            "Switch statement",
            f'switch( {identifier.value} ){{',
            line_number
        )

    # -------------------------------------------------------------------------
    # Pattern 8 — case statement
    # case 1: instruction; break;
    # -------------------------------------------------------------------------

    def _parse_case_statement(self, tokens, line_number: int) -> ParseResult:
        """
        Expected structure:  case <value> : <instruction> ; break ;

        Valid:    case 1: x = 1; break;
        Invalid:  case 1: x = 1;        ← missing break
        Invalid:  case x = 1; break;    ← missing colon after value
        """

        # minimum:  case  1  :  x  =  1  ;  break  ;  → 9 tokens
        if len(tokens) < 9:
            return self._invalid(
                "Case statement",
                "Incomplete — expected: case <value>: <instruction>; break;",
                line_number
            )

        value      = tokens[1]
        colon      = tokens[2]
        # tokens[3...-3] are the instruction
        break_kw   = tokens[-2]
        semicolon  = tokens[-1]

        if value.type not in {Types.NUMBER, Types.STRING_LIT, Types.BOOL_LIT, Types.IDENTIFIER}:
            return self._invalid(
                "Case statement",
                f'Expected a value after "case" but found "{value.value}".',
                line_number
            )

        if colon.type != Types.OP_COLON:
            return self._invalid(
                "Case statement",
                f'Expected ":" after case value but found "{colon.value}".',
                line_number
            )

        if break_kw.type != Types.KEYWORD_BREAK:
            return self._invalid(
                "Case statement",
                'Missing "break" at the end of case.',
                line_number
            )

        if semicolon.type != Types.SEMICOLON:
            return self._invalid(
                "Case statement",
                'Missing ";" after break.',
                line_number
            )

        return self._valid(
            "Case statement",
            f'case {value.value}: ... break;',
            line_number
        )

    # -------------------------------------------------------------------------
    # Pattern 9 — default statement
    # default: instruction;
    # -------------------------------------------------------------------------

    def _parse_default_statement(self, tokens, line_number: int) -> ParseResult:
        """
        Expected structure:  default : <instruction> ;
        The default case does not require a break.
        """

        # minimum:  default  :  x  =  1  ;  → 6 tokens
        if len(tokens) < 4:
            return self._invalid(
                "Default statement",
                "Incomplete — expected: default: <instruction>;",
                line_number
            )

        colon     = tokens[1]
        semicolon = tokens[-1]

        if colon.type != Types.OP_COLON:
            return self._invalid(
                "Default statement",
                f'Expected ":" after "default" but found "{colon.value}".',
                line_number
            )

        if semicolon.type != Types.SEMICOLON:
            return self._invalid(
                "Default statement",
                'Missing ";" at the end of default.',
                line_number
            )

        return self._valid(
            "Default statement",
            'default: ...;',
            line_number
        )

    # -------------------------------------------------------------------------
    # Pattern 10 — break statement
    # break;
    # -------------------------------------------------------------------------

    def _parse_break_statement(self, tokens, line_number: int) -> ParseResult:
        """
        Expected structure:  break ;
        A standalone break is valid inside switch and loop bodies.
        """
        if len(tokens) < 2 or tokens[-1].type != Types.SEMICOLON:
            return self._invalid(
                "Break statement",
                'Expected ";" after break.',
                line_number
            )

        return self._valid(
            "Break statement",
            "break;",
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