0#!/usr/bin/env python3
"""Two-pass Hack Assembler (Nand to Tetris, Capstone Part B).

Roll No: 2501730361   K = 61   (K mod 3 = 1)
Custom feature: every invalid line is reported as
    Line <n>: <message>
using the original 1-based source line number, instead of crashing.
No .hack file is written if any error was found.

Usage: python3 assembler.py path/to/Program.asm
"""

import os
import re
import sys

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

# comp mnemonic -> 7 bits ("a" bit followed by the 6 "c" bits)
COMP = {
    # a = 0
    "0":   "0101010", "1":   "0111111", "-1":  "0111010",
    "D":   "0001100", "A":   "0110000", "!D":  "0001101",
    "!A":  "0110001", "-D":  "0001111", "-A":  "0110011",
    "D+1": "0011111", "A+1": "0110111", "D-1": "0001110",
    "A-1": "0110010", "D+A": "0000010", "D-A": "0010011",
    "A-D": "0000111", "D&A": "0000000", "D|A": "0010101",
    # a = 1
    "M":   "1110000", "!M":  "1110001", "-M":  "1110011",
    "M+1": "1110111", "M-1": "1110010", "D+M": "1000010",
    "D-M": "1010011", "M-D": "1000111", "D&M": "1000000",
    "D|M": "1010101",
}

# dest mnemonic -> 3 bits (d1 = A, d2 = D, d3 = M)
DEST = {
    "null": "000", "M":  "001", "D":   "010", "MD":  "011",
    "A":    "100", "AM": "101", "AD":  "110", "AMD": "111",
}

# jump mnemonic -> 3 bits
JUMP = {
    "null": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT":  "100", "JNE": "101", "JLE": "110", "JMP": "111",
}

SYMBOL_RE = re.compile(r"[A-Za-z_.$:][A-Za-z0-9_.$:]*")  # not starting with a digit
NUMBER_RE = re.compile(r"[0-9]+")


def predefined_symbols():
    """Return a fresh symbol table holding the standard Hack symbols."""
    table = {"R%d" % i: i for i in range(16)}
    table.update({"SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
                  "SCREEN": 16384, "KBD": 24576})
    return table


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_line(raw):
    """Remove a // comment and surrounding whitespace from one source line."""
    return raw.split("//", 1)[0].strip()


def is_valid_symbol(name):
    """True if name is a legal Hack symbol (letters, digits, _ . $ :, no leading digit)."""
    return SYMBOL_RE.fullmatch(name) is not None


def encode_a_instruction(value, symbols, next_var):
    """Encode '@value' (value = text after '@').

    Returns (binary_string_or_None, updated_next_var).
    None means the instruction is invalid. New variables get next_var onwards.
    """
    if NUMBER_RE.fullmatch(value):                 # @123
        number = int(value)
        if number > 32767:                         # must fit in 15 bits
            return None, next_var
    elif is_valid_symbol(value):                   # @LOOP or @i
        if value not in symbols:                   # new variable -> next free RAM slot
            symbols[value] = next_var
            next_var += 1
        number = symbols[value]
    else:                                          # @, @-1, @123var, @bad sym ...
        return None, next_var
    return "0" + format(number, "015b"), next_var


def encode_c_instruction(line):
    """Encode 'dest=comp;jump'. Returns a 16-bit string, or None if invalid."""
    if line.count("=") > 1 or line.count(";") > 1:
        return None

    dest, jump = "null", "null"
    comp = line
    if ";" in comp:
        comp, jump = comp.split(";")
        jump = jump.strip()
        if jump == "":                             # empty jump after ';'
            return None
    if "=" in comp:                                # '=' must come before ';'
        dest, comp = comp.split("=")
        dest = dest.strip()
        if dest == "":                             # empty dest before '='
            return None
    comp = comp.strip()

    # "null" is not valid source text for dest/jump, only an internal default
    if comp not in COMP or dest not in DEST or jump not in JUMP:
        return None
    if (dest == "null" and "=" in line) or (jump == "null" and ";" in line):
        return None
    return "111" + COMP[comp] + DEST[dest] + JUMP[jump]


# ---------------------------------------------------------------------------
# The two passes
# ---------------------------------------------------------------------------

def first_pass(lines, symbols):
    """Record each (LABEL) with the ROM address of the next instruction.

    Returns a list of (line_number, message) errors.
    """
    errors = []
    rom_address = 0
    for line_num, raw in enumerate(lines, start=1):
        line = clean_line(raw)
        if line == "":
            continue
        if line.startswith("("):
            label = line[1:-1] if line.endswith(")") else None
            if label is None or not is_valid_symbol(label):
                errors.append((line_num, "invalid label declaration"))
            elif label in symbols:
                errors.append((line_num, "duplicate label '%s'" % label))
            else:
                symbols[label] = rom_address       # labels take no ROM space
        else:
            rom_address += 1                       # real instruction
    return errors


def second_pass(lines, symbols):
    """Translate every instruction to 16 bits, allocating variables from 16.

    Returns (list_of_binary_lines, list_of_(line_number, message)_errors).
    """
    output, errors = [], []
    next_var = 16
    for line_num, raw in enumerate(lines, start=1):
        line = clean_line(raw)
        if line == "" or line.startswith("("):     # blanks; labels done in pass 1
            continue
        if line.startswith("@"):
            code, next_var = encode_a_instruction(line[1:], symbols, next_var)
        else:
            code = encode_c_instruction(line)
        if code is None:
            errors.append((line_num, "invalid instruction"))
        else:
            output.append(code)
    return output, errors


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 assembler.py path/to/Program.asm")
        return 1
    asm_path = sys.argv[1]

    try:
        with open(asm_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError as e:
        print("Error: cannot read '%s' (%s)" % (asm_path, e.strerror))
        return 1

    symbols = predefined_symbols()
    errors = first_pass(lines, symbols)
    output, pass2_errors = second_pass(lines, symbols)
    errors += pass2_errors

    if errors:
        for line_num, message in sorted(errors):
            print("Line %d: %s" % (line_num, message))
        print("Assembly failed: %d error(s). No .hack file written." % len(errors))
        return 1

    hack_path = os.path.splitext(asm_path)[0] + ".hack"
    try:
        with open(hack_path, "w", newline="\n") as f:
            f.write("".join(code + "\n" for code in output))
    except OSError as e:
        print("Error: cannot write '%s' (%s)" % (hack_path, e.strerror))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
