---
name: c64-basic
description: Create and run Commodore 64 BASIC programs by writing tokenized BASIC directly to C64 memory using the Commodore 64 Ultimate REST API. Use when the user asks to create, write, or run BASIC programs on the C64, convert BASIC code to tokenized format, or work with C64 memory and BASIC internals.
---

# C64 BASIC Program Creation

This skill enables creating and running BASIC programs on a Commodore 64 by writing tokenized BASIC directly to memory using the available Commodore 64 tools.

## Quick Start Workflow

1. **Reset the C64**: Always start with a clean state
   ```
   commodore64:machine_reset
   ```

2. **Build tokenized BASIC**: Convert BASIC code to hex format following the memory structure in references/memory-format.md

3. **Write program to memory**: Write to $0801 (BASIC program start)
   ```
   commodore64:write_memory
   address: "0801"
   data: "<hex-encoded-program>"
   ```

4. **Update BASIC pointers**: Set end-of-BASIC ($002D-$002E) and start-of-variables ($002F-$0030)

5. **Inject keyboard commands**: Write "LIST" + CR + "RUN" + CR to keyboard buffer ($0277) and set count ($00C6)

## Memory Structure Overview

**BASIC Program Format:**
- Start address: $0801 (2049 decimal)
- Each line: `[Next Line Ptr] [Line Number] [Tokenized Content] [00]`
- Program termination: After the last line's $00 terminator, write `$00 $00` as a null link pointer

**Critical Pointers:**
- $002D-$002E: End of BASIC (points after the final $00 $00 terminator)
- $002F-$0030: Start of variables (same as end of BASIC)

See references/memory-format.md for complete memory layout details.

## CRITICAL: End-of-Program Marker Placement

**⚠️ IMPORTANT**: The `$00 $00` end-of-program marker is NOT the link pointer OF the last line. It comes AFTER the last line as a separate null link pointer.

### Correct Structure:
```
[Last Line Link Ptr] [Line Number] [Content] [00 terminator] [00 00 end marker]
                                                              ↑
                                              This is a SEPARATE null pointer
                                              that would be the link for a
                                              non-existent "next line"
```

### Incorrect (BUG):
```
[00 00] [Line Number] [Content] [00]   ← WRONG! BASIC stops before reading this line!
```

### Why This Matters:
BASIC reads the link pointer FIRST, BEFORE the line content. If the link pointer is $0000, BASIC thinks "end of program" and stops—it never reads the line number or content that follows.

## Tokenization Rules

### Numbers as PETSCII Strings
Numbers in BASIC code are stored as character strings, NOT binary:
- `10` → $31 $30 ("1" "0")
- `53280` → $35 $33 $32 $38 $30 ("5" "3" "2" "8" "0")

### Include Spaces
Spaces are explicit in memory:
- `POKE 53280,0` → `$97 $20 $35 $33 $32 $38 $30 $2C $30`
  - $97 = POKE token
  - $20 = space
  - $35 $33 $32 $38 $30 = "53280"
  - $2C = comma
  - $30 = "0"

Without spaces, LIST shows `POKE53280,0` (works but looks wrong).

### Common Tokens
Consult references/tokens.md for complete token table. Most common:
- $89 = GOTO
- $97 = POKE
- $99 = PRINT
- $2C = comma (PETSCII, not token)
- $3A = colon (PETSCII)

## Line Pointer Calculation

Each line's "next line pointer" must point to the exact start of the next line:

```
Example: Line at $0801
  $0801-$0802: next line pointer (2 bytes)
  $0803-$0804: line number (2 bytes)
  $0805-$080E: content + $00 terminator (10 bytes)
  Total: 14 bytes

Next line starts at $0801 + 14 = $080F
Pointer: $0F $08 (little-endian)
```

**Last line**: The last line needs a VALID link pointer pointing to where the end marker will be, then content, then $00 terminator, then `$00 $00` end marker.

## Complete Example

Program:
```basic
10 POKE 53280,0
20 GOTO 10
```

### Correct Tokenized Hex:
```
0F080A00972035333238302C3000 18081400892031300000
```

### Breakdown:
```
LINE 10 at $0801:
0F08     - Next line at $080F (points to line 20)
0A00     - Line 10
97       - POKE
20       - Space
3533323830 - "53280"
2C       - Comma
30       - "0"
00       - End of line 10

LINE 20 at $080F:
1808     - Next line at $0818 (points to end marker location)
1400     - Line 20
89       - GOTO
20       - Space
3130     - "10"
00       - End of line 20

END MARKER at $0818:
0000     - Null pointer = END OF PROGRAM
```

### Memory Map:
```
$0801: 0F 08  ─┐ Line 10 link → $080F
$0803: 0A 00   │ Line number 10
$0805: 97 ...  │ POKE 53280,0
$080E: 00     ─┘ Line 10 terminator

$080F: 18 08  ─┐ Line 20 link → $0818
$0811: 14 00   │ Line number 20  
$0813: 89 ...  │ GOTO 10
$0817: 00     ─┘ Line 20 terminator

$0818: 00 00  ── END OF PROGRAM MARKER

$081A: (End of BASIC - pointers point here)
```

### Commands:
```
1. commodore64:machine_reset

2. commodore64:write_memory
   address: "0801"
   data: "0F080A00972035333238302C300018081400892031300000"

3. commodore64:write_memory
   address: "002D"
   data: "1A08"  (program ends at $081A, after the 00 00)

4. commodore64:write_memory
   address: "002F"
   data: "1A08"  (variables start at $081A)

5. commodore64:write_memory
   address: "0277"
   data: "4C4953540D52554E0D"  (LIST+CR+RUN+CR)

6. commodore64:write_memory
   address: "00C6"
   data: "09"  (9 characters in buffer)
```

## Running Programs via Keyboard Buffer

Inject commands at $0277 (keyboard buffer) with count at $00C6:

| Command | Hex | Length |
|---------|-----|--------|
| LIST | 4C4953540D | 5 |
| RUN | 52554E0D | 4 |
| LIST+RUN | 4C4953540D52554E0D | 9 |

**Always LIST before RUN** to verify correct encoding.

## Debugging Common Issues

**Last line not showing in LIST:**
- ⚠️ Most common bug: `$00 $00` placed AS the last line's link pointer instead of AFTER the last line
- The last line's link pointer must point to a valid address where `$00 $00` is stored
- Fix: Last line needs `[valid link ptr] [line#] [content] [00]` then `[00 00]` after

**Garbled listing:**
- Wrong line pointers → recalculate byte positions
- Wrong token values → check references/tokens.md
- Wrong punctuation → comma is $2C, not $AC

**Syntax errors on RUN:**
- Missing spaces after tokens
- Wrong PETSCII values for numbers/symbols
- Incorrect token for keyword

**Program won't run:**
- End-of-BASIC pointer ($002D) incorrect
- Keyboard buffer count doesn't match command length

## Validation Checklist

Before finalizing a program, verify:

1. ☐ Each line's link pointer points to the NEXT line's first byte
2. ☐ Last line's link pointer points to where `$00 $00` is stored
3. ☐ `$00 $00` end marker comes AFTER last line's `$00` terminator
4. ☐ $002D-$002E points to byte AFTER the `$00 $00` end marker
5. ☐ $002F-$0030 matches $002D-$002E
6. ☐ Keyboard buffer count matches command string length

## Reference Files

- **references/memory-format.md**: Complete memory layout and structure details
- **references/tokens.md**: Full BASIC token table and PETSCII values
- **references/addresses.md**: Important memory addresses

Load these when you need detailed reference information.
