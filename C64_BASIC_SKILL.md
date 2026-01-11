# C64 BASIC Program Creation via Commodore 64 Ultimate

## Overview

This skill documents how to create and run BASIC programs on a Commodore 64 by writing tokenized BASIC directly to memory using the Commodore 64 Ultimate REST API tools.

## C64 BASIC Memory Format

### Memory Layout

- **BASIC program start**: $0801 (2049 decimal)
- **End of BASIC pointer**: $002D-$002E (low byte, high byte)
- **Start of variables pointer**: $002F-$0030 (should match end of BASIC)
- **Keyboard buffer**: $0277-$0280 (10 bytes max)
- **Keyboard buffer count**: $00C6

### BASIC Line Structure

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

## BASIC Tokens

Common BASIC keywords are stored as single-byte tokens:

| Token | Keyword |
|-------|---------|
| $81 | FOR |
| $82 | NEXT |
| $89 | GOTO |
| $97 | POKE |
| $A4 | TO |
| $B2 | = |

### Non-Tokenized Characters

These are stored as PETSCII values:

| Character | PETSCII |
|-----------|---------|
| Space | $20 |
| Comma | $2C |
| Colon | $3A |
| 0-9 | $30-$39 |
| A-Z | $41-$5A |

**IMPORTANT**: Numbers in BASIC code (like `53280` or `10`) are stored as PETSCII character strings, NOT as binary values. For example, `53280` is stored as `$35 $33 $32 $38 $30` ("5" "3" "2" "8" "0").

## Critical Rules

### 1. Include Spaces

BASIC stores spaces explicitly. Include space ($20) after tokens where needed:
- `POKE 53280` = `$97 $20 $35 $33 $32 $38 $30`
- `GOTO 10` = `$89 $20 $31 $30`

Without spaces, the listing will show `POKE53280` and `GOTO10` (technically works but looks wrong).

### 2. Calculate Line Pointers Correctly

Each line pointer must point to the EXACT start address of the next line. Count bytes carefully:

```
Line at $0801:
  $0801-$0802: next line pointer (2 bytes)
  $0803-$0804: line number (2 bytes)
  $0805-$080E: content + null terminator (variable)
  
If line ends at $080E, next line starts at $080F
So pointer should be $0F $08 (little-endian)
```

### 3. Last Line Points to $0000

The final line's "next line pointer" must be `$00 $00` to mark end of program.

### 4. Update BASIC Pointers

After writing the program, update these zero-page pointers:
- $002D-$002E: End of BASIC (points to byte AFTER last $00 terminator)
- $002F-$0030: Start of variables (same as end of BASIC)

### 5. Use Correct Token Values

Common mistake: Using wrong token values
- Comma is $2C (not $AC which is multiply `*`)
- Equals for assignment is the character $3D in some contexts, but $B2 as a token

## Example: Complete Program

### Target Program
```basic
10 POKE 53280,0
20 GOTO 10
```

### Memory Layout

```
Address  Bytes                          Meaning
-------  -----                          -------
$0801    0F 08                          Next line at $080F
$0803    0A 00                          Line number 10
$0805    97                             POKE token
$0806    20                             Space
$0807    35 33 32 38 30                 "53280"
$080C    2C                             Comma
$080D    30                             "0"
$080E    00                             End of line

$080F    00 00                          Next line = 0 (end of program)
$0811    14 00                          Line number 20
$0813    89                             GOTO token
$0814    20                             Space
$0815    31 30                          "10"
$0817    00                             End of line
```

### Hex String
```
0F080A00972035333238302C300000001400892031300000
```

### Commands to Execute

```
1. Reset C64:
   c64u-mcp-server:machine_reset

2. Write program to $0801:
   c64u-mcp-server:write_memory
   address: "0801"
   data: "0F080A00972035333238302C300000001400892031300000"

3. Set end-of-BASIC pointer ($002D-$002E):
   c64u-mcp-server:write_memory
   address: "002D"
   data: "1808"

4. Set start-of-variables pointer ($002F-$0030):
   c64u-mcp-server:write_memory
   address: "002F"
   data: "1808"

5. Inject "LIST" + CR + "RUN" + CR into keyboard buffer:
   c64u-mcp-server:write_memory
   address: "0277"
   data: "4C4953540D52554E0D"

6. Set keyboard buffer count to 9:
   c64u-mcp-server:write_memory
   address: "00C6"
   data: "09"
```

## Running Programs

### Method: Keyboard Buffer Injection

Write commands to keyboard buffer at $0277 and set count at $00C6:

| Command | Hex (with CR) | Length |
|---------|---------------|--------|
| LIST | 4C 49 53 54 0D | 5 |
| RUN | 52 55 4E 0D | 4 |
| LIST+RUN | 4C 49 53 54 0D 52 55 4E 0D | 9 |

**Always LIST before RUN** to verify the program is correctly encoded.

## Debugging Tips

### Garbled Listing
- **Wrong line numbers**: Next-line pointers are incorrect
- **Missing keywords**: Wrong token values used
- **Symbols instead of commas**: Used wrong byte (e.g., $AC instead of $2C)
- **Garbage after program**: End-of-BASIC pointer ($002D) is too high

### Syntax Errors on RUN
- Check token values are correct
- Verify commas, colons, and other punctuation use correct PETSCII values
- Ensure spaces are included where BASIC expects them

### Program Won't Run
- Verify next-line pointers form a valid chain ending in $0000
- Check that $002D-$002E points just past the program end
- Ensure keyboard buffer count matches actual command length

## Common Token Reference

| Token | Hex | Keyword |
|-------|-----|---------|
| END | $80 | END |
| FOR | $81 | FOR |
| NEXT | $82 | NEXT |
| DATA | $83 | DATA |
| INPUT | $85 | INPUT |
| DIM | $86 | DIM |
| READ | $87 | READ |
| LET | $88 | LET |
| GOTO | $89 | GOTO |
| RUN | $8A | RUN |
| IF | $8B | IF |
| RESTORE | $8C | RESTORE |
| GOSUB | $8D | GOSUB |
| RETURN | $8E | RETURN |
| REM | $8F | REM |
| STOP | $90 | STOP |
| ON | $91 | ON |
| PRINT | $99 | PRINT |
| DEF | $96 | DEF |
| POKE | $97 | POKE |
| CONT | $9A | CONT |
| LIST | $9B | LIST |
| CLR | $9C | CLR |
| SYS | $9E | SYS |
| NEW | $A2 | NEW |
| TO | $A4 | TO |
| STEP | $A9 | STEP |
| AND | $AF | AND |
| OR | $B0 | OR |
| PEEK | $C2 | PEEK |
| RND | $BB | RND |

## Important Addresses

| Address | Purpose |
|---------|---------|
| $0801 | Start of BASIC program |
| $002D-$002E | End of BASIC pointer |
| $002F-$0030 | Start of variables |
| $0277-$0280 | Keyboard buffer |
| $00C6 | Keyboard buffer count |
| $D020 | Border color register |
| $D021 | Background color register |
