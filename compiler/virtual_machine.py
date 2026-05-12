# =============================================================================
# compiler/virtual_machine.py
# Stack-based virtual machine for the TypeScript compiler.
#
# Memory model:
#   self.memory  — dict: variable_name → value (scalar or list)
#   self.stack   — Python list used as a stack (append / pop)
#   self.labels  — dict: label_name → instruction index (after first pass)
#   self.call_stack — list of return instruction indices
#
# Instruction set matches what code_generator.py emits.
# =============================================================================


class VirtualMachine:
    MAX_STEPS = 200_000   # safety limit against infinite loops

    def __init__(self, asm_code: str):
        self.raw = asm_code
        self.memory: dict = {}
        self.stack:  list = []
        self.instructions: list = []   # list of (opcode, *args)
        self.labels: dict = {}
        self.call_stack: list = []
        self.output_lines: list = []

        self._load(asm_code)

    # ── loader (first pass) ──────────────────────────────────────────────────

    def _load(self, code: str):
        ip = 0
        for raw_line in code.split("\n"):
            # strip inline comments
            if ";" in raw_line:
                raw_line = raw_line[:raw_line.index(";")]
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split(None, 1)   # split op from rest (preserves quoted strings)
            op = parts[0].upper()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if op == "LABEL":
                self.labels[arg] = ip
            else:
                self.instructions.append((op, arg))
                ip += 1

    # ── execution ────────────────────────────────────────────────────────────

    def run(self) -> str:
        self.output_lines = [">>> EXECUTION START"]
        ip     = 0
        steps  = 0
        mem    = self.memory
        stack  = self.stack
        labels = self.labels

        while ip < len(self.instructions):
            if steps > self.MAX_STEPS:
                self.output_lines.append(
                    f"[!] RUNTIME ERROR: step limit of {self.MAX_STEPS} exceeded "
                    f"(possible infinite loop). Stopped.")
                break
            steps += 1

            op, arg = self.instructions[ip]

            try:
                # ── stack / memory ──────────────────────────────────────
                if op == "PUSH_CONST":
                    stack.append(self._parse_literal(arg))

                elif op == "PUSH_VAR":
                    if arg not in mem:
                        stack.append(0)   # uninitialized → default 0
                    else:
                        stack.append(mem[arg])

                elif op == "STORE_VAR":
                    mem[arg] = stack.pop()

                elif op == "LOAD_IDX":
                    index = stack.pop()
                    arr   = mem.get(arg)
                    if not isinstance(arr, list):
                        raise RuntimeError(f"'{arg}' is not an array")
                    if index < 0 or index >= len(arr):
                        raise RuntimeError(
                            f"Index {index} out of range for '{arg}' (size {len(arr)})")
                    stack.append(arr[int(index)])

                elif op == "STORE_IDX":
                    index = stack.pop()
                    value = stack.pop()
                    arr   = mem.get(arg)
                    if not isinstance(arr, list):
                        raise RuntimeError(f"'{arg}' is not an array")
                    if index < 0 or index >= len(arr):
                        raise RuntimeError(
                            f"Index {index} out of range for '{arg}' (size {len(arr)})")
                    arr[int(index)] = value

                elif op == "MAKE_ARRAY":
                    count = int(arg)
                    elems = []
                    for _ in range(count):
                        elems.insert(0, stack.pop())
                    stack.append(elems)

                # ── arithmetic ──────────────────────────────────────────
                elif op == "ADD":
                    b, a = stack.pop(), stack.pop()
                    stack.append(a + b)
                elif op == "SUB":
                    b, a = stack.pop(), stack.pop()
                    stack.append(a - b)
                elif op == "MUL":
                    b, a = stack.pop(), stack.pop()
                    stack.append(a * b)
                elif op == "DIV":
                    b, a = stack.pop(), stack.pop()
                    if b == 0:
                        raise RuntimeError("Division by zero")
                    stack.append(a / b)
                elif op == "MOD":
                    b, a = stack.pop(), stack.pop()
                    stack.append(a % b)
                elif op == "NEG":
                    stack.append(-stack.pop())

                # ── comparison ──────────────────────────────────────────
                elif op == "EQ":
                    b, a = stack.pop(), stack.pop()
                    stack.append(1 if a == b else 0)
                elif op == "NEQ":
                    b, a = stack.pop(), stack.pop()
                    stack.append(1 if a != b else 0)
                elif op == "LT":
                    b, a = stack.pop(), stack.pop()
                    stack.append(1 if a < b else 0)
                elif op == "GT":
                    b, a = stack.pop(), stack.pop()
                    stack.append(1 if a > b else 0)
                elif op == "LEQ":
                    b, a = stack.pop(), stack.pop()
                    stack.append(1 if a <= b else 0)
                elif op == "GEQ":
                    b, a = stack.pop(), stack.pop()
                    stack.append(1 if a >= b else 0)

                # ── logical ─────────────────────────────────────────────
                elif op == "AND":
                    b, a = stack.pop(), stack.pop()
                    stack.append(1 if (a and b) else 0)
                elif op == "OR":
                    b, a = stack.pop(), stack.pop()
                    stack.append(1 if (a or b) else 0)
                elif op == "NOT":
                    stack.append(0 if stack.pop() else 1)

                # ── control flow ────────────────────────────────────────
                elif op == "JMP":
                    ip = labels[arg]
                    continue

                elif op == "JMPF":
                    cond = stack.pop()
                    if not cond:
                        ip = labels[arg]
                        continue

                elif op == "JMPT":
                    cond = stack.pop()
                    if cond:
                        ip = labels[arg]
                        continue

                # ── function call / return ──────────────────────────────
                elif op == "CALL":
                    self.call_stack.append(ip + 1)
                    ip = labels[f"func_{arg}"]
                    continue

                elif op == "RET":
                    if self.call_stack:
                        ip = self.call_stack.pop()
                        continue
                    break

                # ── I/O ────────────────────────────────────────────────
                elif op == "PRINT":
                    val = stack.pop()
                    # Format: strip .0 from whole floats for cleaner output
                    if isinstance(val, float) and val == int(val):
                        val = int(val)
                    self.output_lines.append(str(val))

                elif op == "HALT":
                    break

                else:
                    self.output_lines.append(f"[!] Unknown instruction: {op}")

            except IndexError:
                self.output_lines.append(
                    f"[!] RUNTIME ERROR: stack underflow at IP {ip} ({op})")
                break
            except Exception as exc:
                self.output_lines.append(
                    f"[!] RUNTIME ERROR at IP {ip} ({op} {arg}): {exc}")
                break

            ip += 1

        self.output_lines.append(">>> EXECUTION END")
        return "\n".join(self.output_lines)

    # ── literal parser ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_literal(s: str):
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1]
        if s.startswith("'") and s.endswith("'"):
            return s[1:-1]
        if s == "true":  return 1
        if s == "false": return 0
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s)
        except ValueError:
            pass
        return s
