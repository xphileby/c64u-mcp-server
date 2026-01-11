# C64 BASIC Token Reference

## Common BASIC Tokens

BASIC keywords are stored as single-byte tokens:

| Token | Hex | Keyword |
|-------|-----|---------|
| END | $80 | END |
| FOR | $81 | FOR |
| NEXT | $82 | NEXT |
| DATA | $83 | DATA |
| INPUT# | $84 | INPUT# |
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
| WAIT | $92 | WAIT |
| LOAD | $93 | LOAD |
| SAVE | $94 | SAVE |
| VERIFY | $95 | VERIFY |
| DEF | $96 | DEF |
| POKE | $97 | POKE |
| PRINT# | $98 | PRINT# |
| PRINT | $99 | PRINT |
| CONT | $9A | CONT |
| LIST | $9B | LIST |
| CLR | $9C | CLR |
| CMD | $9D | CMD |
| SYS | $9E | SYS |
| OPEN | $9F | OPEN |
| CLOSE | $A0 | CLOSE |
| GET | $A1 | GET |
| NEW | $A2 | NEW |
| TAB( | $A3 | TAB( |
| TO | $A4 | TO |
| FN | $A5 | FN |
| SPC( | $A6 | SPC( |
| THEN | $A7 | THEN |
| NOT | $A8 | NOT |
| STEP | $A9 | STEP |
| + | $AA | + |
| - | $AB | - |
| * | $AC | * |
| / | $AD | / |
| ^ | $AE | ^ (power) |
| AND | $AF | AND |
| OR | $B0 | OR |
| > | $B1 | > |
| = | $B2 | = |
| < | $B3 | < |
| SGN | $B4 | SGN |
| INT | $B5 | INT |
| ABS | $B6 | ABS |
| USR | $B7 | USR |
| FRE | $B8 | FRE |
| POS | $B9 | POS |
| SQR | $BA | SQR |
| RND | $BB | RND |
| LOG | $BC | LOG |
| EXP | $BD | EXP |
| COS | $BE | COS |
| SIN | $BF | SIN |
| TAN | $C0 | TAN |
| ATN | $C1 | ATN |
| PEEK | $C2 | PEEK |
| LEN | $C3 | LEN |
| STR$ | $C4 | STR$ |
| VAL | $C5 | VAL |
| ASC | $C6 | ASC |
| CHR$ | $C7 | CHR$ |
| LEFT$ | $C8 | LEFT$ |
| RIGHT$ | $C9 | RIGHT$ |
| MID$ | $CA | MID$ |
| GO | $CB | GO |

## Operator Tokens

Mathematical and logical operators have tokens:

| Token | Hex | Operator |
|-------|-----|----------|
| + | $AA | Addition |
| - | $AB | Subtraction |
| * | $AC | Multiplication |
| / | $AD | Division |
| ^ | $AE | Exponentiation |
| AND | $AF | Logical AND |
| OR | $B0 | Logical OR |
| > | $B1 | Greater than |
| = | $B2 | Equals (comparison/assignment) |
| < | $B3 | Less than |

**Note**: Some operators like `=` can appear as either the token $B2 or the PETSCII character $3D depending on context.

## PETSCII Characters (Not Tokens)

Common characters stored as PETSCII:

| Character | PETSCII | Hex | Usage |
|-----------|---------|-----|-------|
| Space | 32 | $20 | After tokens, between words |
| ! | 33 | $21 | - |
| " | 34 | $22 | String delimiters |
| # | 35 | $23 | Variable suffix |
| $ | 36 | $24 | Variable suffix |
| % | 37 | $25 | Variable suffix |
| & | 38 | $26 | - |
| ' | 39 | $27 | - |
| ( | 40 | $28 | Parentheses |
| ) | 41 | $29 | Parentheses |
| , | 44 | $2C | Comma separator |
| - | 45 | $2D | Minus (when used as character) |
| . | 46 | $2E | Decimal point |
| : | 58 | $3A | Statement separator |
| ; | 59 | $3B | PRINT separator |
| = | 61 | $3D | Equals (in some contexts) |
| ? | 63 | $3F | Shorthand for PRINT |
| @ | 64 | $40 | - |
| 0-9 | 48-57 | $30-$39 | Digit characters |
| A-Z | 65-90 | $41-$5A | Letters |

## Special Characters

| Character | PETSCII | Hex | Usage |
|-----------|---------|-----|-------|
| CR (Return) | 13 | $0D | End of keyboard buffer command |
| Line terminator | 0 | $00 | End of BASIC line |

## Common Mistakes

### Comma vs. Multiply
- Comma: $2C (PETSCII character)
- Multiply: $AC (token)

Using $AC instead of $2C will show a `*` instead of `,` in listings.

### Space After Tokens
Most tokens should be followed by a space ($20):
- `POKE 53280,0` → $97 $20 ... (not $97 $35...)
- `GOTO 10` → $89 $20 ... (not $89 $31...)

Without the space, the listing will run together: `POKE53280,0`

### Equals Sign Context
The `=` character can be:
- Token $B2 in comparisons: `IF A=5 THEN`
- PETSCII $3D in assignments: `LET A=5`

When in doubt, use the token $B2 for `=` in most contexts.
