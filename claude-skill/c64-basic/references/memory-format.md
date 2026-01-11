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
| Next Line Pointer | 2 bytes | Address of next line (little-endian) |
| Line Number | 2 bytes | Line number (little-endian), e.g., 10 = $0A $00 |
| Tokens/Content | Variable | Tokenized BASIC code |
| Terminator | 1 byte | $00 marks end of line |

## CRITICAL: End of Program Structure

### ⚠️ How the $00 $00 End Marker Works

The `$00 $00` end marker is a **null link pointer for a non-existent next line**. It is NOT the link pointer OF the last line.

**BASIC reads link pointers FIRST, before line content.** When BASIC encounters `$00 $00` as a link pointer, it stops immediately—it never reads whatever follows.

### Correct Structure:

```
Last actual line:
  [Link Ptr → end marker location] [Line #] [Content] [00 terminator]

End marker (immediately after):
  [00 00]   ← This is where the last line's link pointer points to
```

### Visual Example:

```
$0810: 18 08    ← Last line's link pointer, points to $0818
$0812: 14 00    ← Line number (20)
$0814: 89 20..  ← Content (GOTO 10)
$0817: 00       ← Line terminator

$0818: 00 00    ← END MARKER (null link pointer)
        ↑
        Last line's link pointer points HERE
        
$081A: ...      ← End-of-BASIC pointer ($002D) points HERE
```

### Common Bug (INCORRECT):

```
$0810: 00 00    ← WRONG! BASIC sees this and stops immediately!
$0812: 14 00    ← Line 20 is never read
$0814: 89 20..  ← Content is never read
```

**Why this is wrong:** BASIC reads the link pointer at $0810 first. It sees `$00 $00` and thinks "end of program" before ever looking at the line number or content.

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

After writing the complete program (including the `$00 $00` end marker), update $002D-$002E to point to the byte AFTER the end marker:

```
Last line's $00 terminator at $0817
End marker ($00 $00) at $0818-$0819
End-of-BASIC = $081A (byte after end marker)

Set $002D-$002E to $1A $08 (little-endian)
```

Also set $002F-$0030 (start of variables) to the same value.

## Complete Multi-Line Example

Program:
```basic
10 POKE 53280,0
20 GOTO 10
```

Memory layout:
```
Address  Bytes       Description
-------  ----------  -----------
$0801    0F 08       Line 10 link → $080F
$0803    0A 00       Line number 10
$0805    97          POKE token
$0806    20          space
$0807    35 33 32    "532"
$080A    38 30       "80"
$080C    2C          comma
$080D    30          "0"
$080E    00          Line 10 terminator

$080F    18 08       Line 20 link → $0818 (where end marker will be)
$0811    14 00       Line number 20
$0813    89          GOTO token
$0814    20          space
$0815    31 30       "10"
$0817    00          Line 20 terminator

$0818    00 00       END OF PROGRAM (null link pointer)

$081A    --          End-of-BASIC pointer points here
```

Hex string: `0F080A00972035333238302C300018081400892031300000`

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
