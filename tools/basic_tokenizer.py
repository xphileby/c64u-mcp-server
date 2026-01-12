"""
C64 BASIC Tokenizer

Translates BASIC program text to C64 in-memory representation.

C64 BASIC In-Memory Format:
- Program starts at $0801 (2049 decimal)
- Each line: [next_ptr_lo][next_ptr_hi][line_num_lo][line_num_hi][tokenized_code...][0x00]
- Program ends with two zero bytes (0x00, 0x00)
- Keywords are tokenized to single bytes ($80-$CB)
- Keywords are NOT tokenized inside string literals (quoted text)
"""

import re
from typing import Tuple

# BASIC program start address
BASIC_START = 0x0801  # 2049 decimal

# C64 BASIC tokens (keyword -> token byte)
# Order matters: longer keywords must come before shorter ones with same prefix
BASIC_TOKENS = {
    # Statements (starting at $80)
    "END": 0x80,
    "FOR": 0x81,
    "NEXT": 0x82,
    "DATA": 0x83,
    "INPUT#": 0x84,
    "INPUT": 0x85,
    "DIM": 0x86,
    "READ": 0x87,
    "LET": 0x88,
    "GOTO": 0x89,
    "RUN": 0x8A,
    "IF": 0x8B,
    "RESTORE": 0x8C,
    "GOSUB": 0x8D,
    "RETURN": 0x8E,
    "REM": 0x8F,
    "STOP": 0x90,
    "ON": 0x91,
    "WAIT": 0x92,
    "LOAD": 0x93,
    "SAVE": 0x94,
    "VERIFY": 0x95,
    "DEF": 0x96,
    "POKE": 0x97,
    "PRINT#": 0x98,
    "PRINT": 0x99,
    "CONT": 0x9A,
    "LIST": 0x9B,
    "CLR": 0x9C,
    "CMD": 0x9D,
    "SYS": 0x9E,
    "OPEN": 0x9F,
    "CLOSE": 0xA0,
    "GET": 0xA1,
    "NEW": 0xA2,
    # Secondary keywords
    "TAB(": 0xA3,
    "TO": 0xA4,
    "FN": 0xA5,
    "SPC(": 0xA6,
    "THEN": 0xA7,
    "NOT": 0xA8,
    "STEP": 0xA9,
    # Operators
    "+": 0xAA,
    "-": 0xAB,
    "*": 0xAC,
    "/": 0xAD,
    "^": 0xAE,  # Power/exponentiation
    "AND": 0xAF,
    "OR": 0xB0,
    ">": 0xB1,
    "=": 0xB2,
    "<": 0xB3,
    # Functions
    "SGN": 0xB4,
    "INT": 0xB5,
    "ABS": 0xB6,
    "USR": 0xB7,
    "FRE": 0xB8,
    "POS": 0xB9,
    "SQR": 0xBA,
    "RND": 0xBB,
    "LOG": 0xBC,
    "EXP": 0xBD,
    "COS": 0xBE,
    "SIN": 0xBF,
    "TAN": 0xC0,
    "ATN": 0xC1,
    "PEEK": 0xC2,
    "LEN": 0xC3,
    "STR$": 0xC4,
    "VAL": 0xC5,
    "ASC": 0xC6,
    "CHR$": 0xC7,
    "LEFT$": 0xC8,
    "RIGHT$": 0xC9,
    "MID$": 0xCA,
    "GO": 0xCB,  # GO (used in GO TO as alternative to GOTO)
}

# Reverse mapping: token byte -> keyword (for debugging/listing)
TOKEN_TO_KEYWORD = {v: k for k, v in BASIC_TOKENS.items()}

# Keywords sorted by length (longest first) for proper tokenization
# This ensures "PRINT#" is matched before "PRINT", "INPUT#" before "INPUT", etc.
SORTED_KEYWORDS = sorted(BASIC_TOKENS.keys(), key=len, reverse=True)

# Operators that should NOT be tokenized (kept as single-byte ASCII)
# Note: The C64 does tokenize operators, but we need to be careful with context
ALWAYS_TOKENIZE_OPS = {"+", "-", "*", "/", "^", ">", "=", "<"}


def tokenize_line(line_text: str) -> bytes:
    """
    Tokenize a single BASIC line (without line number).

    Handles string literals correctly (keywords inside quotes are not tokenized).

    Args:
        line_text: The BASIC code without the line number

    Returns:
        Tokenized bytes
    """
    result = bytearray()
    i = 0
    in_string = False
    in_rem = False

    # Convert to uppercase for tokenization (C64 BASIC is case-insensitive for keywords)
    # But we preserve original for string contents
    upper_line = line_text.upper()

    while i < len(line_text):
        char = line_text[i]
        upper_char = upper_line[i]

        # Handle string literals
        if char == '"':
            result.append(ord(char))
            in_string = not in_string
            i += 1
            continue

        # Inside strings or after REM, don't tokenize
        if in_string or in_rem:
            # Convert lowercase to uppercase PETSCII (C64 screen codes)
            if 'a' <= char <= 'z':
                result.append(ord(char) - 32)  # Convert to uppercase
            else:
                result.append(ord(char))
            i += 1
            continue

        # Skip spaces
        if char == ' ':
            result.append(0x20)
            i += 1
            continue

        # Try to match keywords (longest first)
        matched = False
        for keyword in SORTED_KEYWORDS:
            if upper_line[i:i + len(keyword)] == keyword:
                # Check if this is a valid keyword boundary
                # (not part of a variable name like "FOREST" containing "FOR")
                if len(keyword) > 1 and keyword not in ALWAYS_TOKENIZE_OPS:
                    # Check if next character would make this part of a variable name
                    next_pos = i + len(keyword)
                    if next_pos < len(line_text):
                        next_char = upper_line[next_pos]
                        # If followed by alphanumeric, it's a variable name, not keyword
                        if next_char.isalnum() or next_char == '$' or next_char == '%':
                            # Exception: keywords ending with ( or $ are always tokenized
                            if not (keyword.endswith('(') or keyword.endswith('$')):
                                continue

                    # Check if preceded by alphanumeric (part of variable name)
                    if i > 0:
                        prev_char = upper_line[i - 1]
                        if prev_char.isalnum() or prev_char == '$' or prev_char == '%':
                            continue

                result.append(BASIC_TOKENS[keyword])
                i += len(keyword)
                matched = True

                # After REM, everything is comment (not tokenized)
                if keyword == "REM":
                    in_rem = True

                break

        if matched:
            continue

        # Not a keyword, add as PETSCII
        if 'a' <= char <= 'z':
            result.append(ord(char) - 32)  # Convert to uppercase PETSCII
        else:
            result.append(ord(char))
        i += 1

    return bytes(result)


def parse_basic_line(line: str) -> Tuple[int, str]:
    """
    Parse a BASIC line into line number and code.

    Args:
        line: Complete BASIC line (e.g., "10 PRINT \"HELLO\"")

    Returns:
        Tuple of (line_number, code_without_line_number)

    Raises:
        ValueError: If line number is invalid or missing
    """
    line = line.strip()
    if not line:
        raise ValueError("Empty line")

    # Extract line number
    match = re.match(r'^(\d+)\s*(.*)', line)
    if not match:
        raise ValueError(f"Invalid line format (no line number): {line}")

    line_num = int(match.group(1))
    code = match.group(2)

    if line_num < 0 or line_num > 63999:
        raise ValueError(f"Line number out of range (0-63999): {line_num}")

    return line_num, code


def basic_to_bytes(program_text: str, start_address: int = BASIC_START) -> bytes:
    """
    Convert a complete BASIC program to C64 in-memory format.

    Args:
        program_text: Multi-line BASIC program text
        start_address: Memory address where program will be loaded (default $0801)

    Returns:
        Bytes ready to be written to C64 memory

    Raises:
        ValueError: If program has invalid syntax or line numbers
    """
    lines = []

    # Parse all lines
    for line in program_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        # Skip comment lines (not BASIC REM, but input comments like # or //)
        if line.startswith('#') or line.startswith('//'):
            continue

        try:
            line_num, code = parse_basic_line(line)
            tokenized = tokenize_line(code)
            lines.append((line_num, tokenized))
        except ValueError as e:
            raise ValueError(f"Error parsing line: {e}")

    # Sort by line number
    lines.sort(key=lambda x: x[0])

    # Check for duplicate line numbers
    seen = set()
    for line_num, _ in lines:
        if line_num in seen:
            raise ValueError(f"Duplicate line number: {line_num}")
        seen.add(line_num)

    # Build the memory image
    result = bytearray()
    current_addr = start_address

    for line_num, tokenized in lines:
        # Calculate next line pointer
        # Line format: [next_lo][next_hi][linenum_lo][linenum_hi][code...][0x00]
        line_length = 4 + len(tokenized) + 1  # 4 bytes header + code + terminator
        next_addr = current_addr + line_length

        # Add next line pointer (little-endian)
        result.append(next_addr & 0xFF)
        result.append((next_addr >> 8) & 0xFF)

        # Add line number (little-endian)
        result.append(line_num & 0xFF)
        result.append((line_num >> 8) & 0xFF)

        # Add tokenized code
        result.extend(tokenized)

        # Add line terminator
        result.append(0x00)

        current_addr = next_addr

    # Add end-of-program marker (null pointer)
    result.append(0x00)
    result.append(0x00)

    return bytes(result)


def get_program_end_address(program_bytes: bytes, start_address: int = BASIC_START) -> int:
    """
    Calculate the end address of the BASIC program.

    This is the address of the first byte after the program,
    which is used to set the BASIC variables pointer.

    Args:
        program_bytes: The tokenized program bytes
        start_address: Memory address where program starts

    Returns:
        Address of first byte after program
    """
    return start_address + len(program_bytes)


def create_prg_file(program_bytes: bytes, start_address: int = BASIC_START) -> bytes:
    """
    Create a .PRG file from tokenized BASIC program.

    PRG files have a 2-byte load address header followed by the program data.

    Args:
        program_bytes: The tokenized program bytes
        start_address: Memory address where program loads (default $0801)

    Returns:
        Complete PRG file bytes
    """
    result = bytearray()
    # Load address (little-endian)
    result.append(start_address & 0xFF)
    result.append((start_address >> 8) & 0xFF)
    # Program data
    result.extend(program_bytes)
    return bytes(result)
