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
- Last line: Next pointer = $0000 (marks end)

**Critical Pointers:**
- $002D-$002E: End of BASIC (points after last $00)
- $002F-$0030: Start of variables (same as end of BASIC)

See references/memory-format.md for complete memory layout details.

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

**Last line**: Always use $00 $00 as next pointer to mark program end.

## Complete Example

Program:
```basic
10 POKE 53280,0
20 GOTO 10
```

Tokenized hex:
```
0F080A00972035333238302C300000001400892031300000
```

Breakdown:
```
0F08     - Next line at $080F
0A00     - Line 10
97       - POKE
20       - Space
3533323830 - "53280"
2C       - Comma
30       - "0"
00       - End line

0000     - No next line (program end)
1400     - Line 20
89       - GOTO
20       - Space
3130     - "10"
00       - End line
```

Commands:
```
1. commodore64:machine_reset

2. commodore64:write_memory
   address: "0801"
   data: "0F080A00972035333238302C300000001400892031300000"

3. commodore64:write_memory
   address: "002D"
   data: "1808"  (program ends at $0818)

4. commodore64:write_memory
   address: "002F"
   data: "1808"  (variables start at $0818)

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

**Garbled listing:**
- Wrong line pointers → recalculate byte positions
- Wrong token values → check references/tokens.md
- Wrong punctuation → comma is $2C, not $AC

**Syntax errors on RUN:**
- Missing spaces after tokens
- Wrong PETSCII values for numbers/symbols
- Incorrect token for keyword

**Program won't run:**
- Last line pointer not $0000
- End-of-BASIC pointer ($002D) incorrect
- Keyboard buffer count doesn't match command length

## Reference Files

- **references/memory-format.md**: Complete memory layout and structure details
- **references/tokens.md**: Full BASIC token table and PETSCII values
- **references/addresses.md**: Important memory addresses

Load these when you need detailed reference information.
