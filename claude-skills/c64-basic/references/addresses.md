# Important C64 Memory Addresses

## BASIC Program Area

| Address | Purpose | Notes |
|---------|---------|-------|
| $0801 | Start of BASIC program | Always write programs starting here |
| $002D-$002E | End of BASIC pointer | Points to byte after last program byte |
| $002F-$0030 | Start of variables | Should match end of BASIC |
| $0033-$0034 | Start of arrays | Managed by BASIC |
| $0037-$0038 | End of arrays | Managed by BASIC |

## Keyboard Buffer

| Address | Purpose | Notes |
|---------|---------|-------|
| $0277-$0280 | Keyboard buffer | 10 bytes max for typed commands |
| $00C6 | Keyboard buffer count | Number of characters in buffer |

Use these to inject commands like "LIST" and "RUN" automatically.

## Screen and Color Memory

| Address | Purpose | Notes |
|---------|---------|-------|
| $0400-$07E7 | Screen memory | 40x25 characters (1000 bytes) |
| $D800-$DBE7 | Color RAM | Color for each screen position |

## VIC-II Video Registers

| Address | Purpose | Common Values |
|---------|---------|---------------|
| $D000-$D001 | Sprite 0 X/Y position | Sprite coordinates |
| $D020 | Border color | 0-15 (black to light gray) |
| $D021 | Background color | 0-15 |

### Common Color Values
- 0 = Black
- 1 = White
- 2 = Red
- 3 = Cyan
- 4 = Purple
- 5 = Green
- 6 = Blue
- 7 = Yellow

Example: `POKE 53280,0` sets border to black ($D020 = 53280 decimal)

## SID Sound Registers

| Address | Purpose | Notes |
|---------|---------|-------|
| $D400-$D418 | SID chip registers | Sound synthesis |

## CIA Timer/Keyboard

| Address | Purpose | Notes |
|---------|---------|-------|
| $DC00-$DC01 | CIA #1 keyboard/joystick | Read keyboard matrix |
| $DD00-$DD0F | CIA #2 serial/timers | RS-232, timers |

## Commonly Used Addresses in BASIC Programs

| Decimal | Hex | Purpose | Example Usage |
|---------|-----|---------|---------------|
| 53280 | $D020 | Border color | `POKE 53280,0` |
| 53281 | $D021 | Background color | `POKE 53281,1` |
| 1024 | $0400 | Screen memory start | `POKE 1024,1` (A in top-left) |
| 55296 | $D800 | Color RAM start | `POKE 55296,5` (green color) |
| 56576 | $DD00 | CIA #2 port A | VIC bank switching |

## Zero Page Working Area

| Address | Purpose | Notes |
|---------|---------|-------|
| $00FB-$00FE | User workspace | Free for ML routines |
| $0002 | Unused | Can be used by programs |

The zero page ($0000-$00FF) is mostly used by BASIC and the OS, but a few bytes are available for user programs.

## Conversion Helper

### Decimal to Hex Quick Reference
| Decimal | Hex |
|---------|-----|
| 53280 | $D020 |
| 53281 | $D021 |
| 2049 | $0801 |
| 1024 | $0400 |
| 55296 | $D800 |

To convert: Use Python `hex(decimal)` or use a programmer's calculator.
