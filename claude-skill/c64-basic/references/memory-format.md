# C64 BASIC Memory Format Reference

## Memory Layout

### BASIC Program Area
- **BASIC program start**: $0801 (2049 decimal)
- **End of BASIC pointer**: $002D-$002E (low byte, high byte)
- **Start of variables pointer**: $002F-$0030 (should match end of BASIC)

### Input/Control Areas
- **Keyboard buffer**: $0277-$0280 (10 bytes max)
- **Keyboard buffer count**: $00C6

## BASIC Line Structure

Each BASIC line has the following format:

```
[Next Line Ptr Lo] [Next Line Ptr Hi] [Line # Lo] [Line # Hi] [Tokens...] [00]
```

| Field | Size | Description |
|-------|------|-------------|
| Next Line Pointer | 2 bytes | Address of next line (little-endian), $0000 = end of program |
| Line Number | 2 bytes | Line number (little-endian), e.g., 10 = $0A $00 |
| Tokens/Content | Variable | Tokenized BASIC code |
| Terminator | 1 byte | $00 marks end of line |

### End of Program

The program ends when a line has `$00 $00` as its next line pointer. This null pointer tells LIST and the BASIC interpreter that there are no more lines.

## Line Pointer Calculation Details

Calculate the next line pointer by counting ALL bytes in the current line:

```
Line structure:
  2 bytes: next line pointer
  2 bytes: line number
  N bytes: tokenized content
  1 byte:  $00 terminator
  Total:   5 + N bytes

Next address = Current address + (5 + N)
```

**Example:**
```
Line at $0801:
  $0801-$0802: $0F $08 (next line pointer)
  $0803-$0804: $0A $00 (line 10)
  $0805:       $97     (POKE token)
  $0806:       $20     (space)
  $0807-$080B: $35 $33 $32 $38 $30 ("53280")
  $080C:       $2C     (comma)
  $080D:       $30     ("0")
  $080E:       $00     (terminator)

Total bytes: 14 ($0E)
Next line: $0801 + $0E = $080F

So the pointer at $0801-$0802 should be $0F $08 (little-endian)
```

## Setting End-of-BASIC Pointer

After writing the complete program, update $002D-$002E to point to the byte AFTER the last $00 terminator:

```
Program ends at $0817 (last $00 terminator)
End-of-BASIC = $0818
Set $002D-$002E to $18 $08 (little-endian)
```

Also set $002F-$0030 (start of variables) to the same value.

## Non-Tokenized Characters (PETSCII)

Characters that are NOT keywords are stored as PETSCII values:

| Character | PETSCII | Notes |
|-----------|---------|-------|
| Space | $20 | Required after many tokens |
| Comma | $2C | NOT $AC (multiply token) |
| Colon | $3A | Statement separator |
| Semicolon | $3B | Used in PRINT |
| Equals | $3D | In some contexts (LET) |
| 0-9 | $30-$39 | Digits stored as characters |
| A-Z | $41-$5A | Variables and string literals |

### Number Storage

**CRITICAL**: Numbers in BASIC code are stored as PETSCII character strings, NOT as binary values.

Examples:
- `10` → $31 $30 (two bytes: "1" "0")
- `255` → $32 $35 $35 (three bytes: "2" "5" "5")
- `53280` → $35 $33 $32 $38 $30 (five bytes: "5" "3" "2" "8" "0")

Do NOT convert numbers to binary. Store them as ASCII/PETSCII digit characters.
