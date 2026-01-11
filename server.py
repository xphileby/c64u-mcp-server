"""
MCP Server for Commodore 64 Ultimate Computer REST API

This server provides MCP tools for interacting with the Commodore 64 Ultimate Computer
device via its REST API.
"""

import base64
import io
import os
from typing import Optional
import httpx
from PIL import Image
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

# C64 color palette (RGB values)
C64_PALETTE = [
    (0, 0, 0),        # 0: Black
    (255, 255, 255),  # 1: White
    (136, 57, 50),    # 2: Red
    (103, 182, 189),  # 3: Cyan
    (139, 63, 150),   # 4: Purple
    (85, 160, 73),    # 5: Green
    (64, 49, 141),    # 6: Blue
    (191, 206, 114),  # 7: Yellow
    (139, 84, 41),    # 8: Orange
    (87, 66, 0),      # 9: Brown
    (184, 105, 98),   # 10: Light Red
    (80, 80, 80),     # 11: Dark Gray
    (120, 120, 120),  # 12: Medium Gray
    (148, 224, 137),  # 13: Light Green
    (120, 105, 196),  # 14: Light Blue
    (159, 159, 159),  # 15: Light Gray
]

# C64 uppercase/graphics character set (2048 bytes, 256 chars x 8 bytes each)
# This is the standard C64 character ROM (uppercase + graphics)
C64_CHARSET = bytes([
    # Characters 0-31 (@ A-Z [ \ ] ^ _ and graphics)
    0x3c,0x66,0x6e,0x6e,0x60,0x62,0x3c,0x00,  # @
    0x18,0x3c,0x66,0x7e,0x66,0x66,0x66,0x00,  # A
    0x7c,0x66,0x66,0x7c,0x66,0x66,0x7c,0x00,  # B
    0x3c,0x66,0x60,0x60,0x60,0x66,0x3c,0x00,  # C
    0x78,0x6c,0x66,0x66,0x66,0x6c,0x78,0x00,  # D
    0x7e,0x60,0x60,0x78,0x60,0x60,0x7e,0x00,  # E
    0x7e,0x60,0x60,0x78,0x60,0x60,0x60,0x00,  # F
    0x3c,0x66,0x60,0x6e,0x66,0x66,0x3c,0x00,  # G
    0x66,0x66,0x66,0x7e,0x66,0x66,0x66,0x00,  # H
    0x3c,0x18,0x18,0x18,0x18,0x18,0x3c,0x00,  # I
    0x1e,0x0c,0x0c,0x0c,0x0c,0x6c,0x38,0x00,  # J
    0x66,0x6c,0x78,0x70,0x78,0x6c,0x66,0x00,  # K
    0x60,0x60,0x60,0x60,0x60,0x60,0x7e,0x00,  # L
    0x63,0x77,0x7f,0x6b,0x63,0x63,0x63,0x00,  # M
    0x66,0x76,0x7e,0x7e,0x6e,0x66,0x66,0x00,  # N
    0x3c,0x66,0x66,0x66,0x66,0x66,0x3c,0x00,  # O
    0x7c,0x66,0x66,0x7c,0x60,0x60,0x60,0x00,  # P
    0x3c,0x66,0x66,0x66,0x66,0x3c,0x0e,0x00,  # Q
    0x7c,0x66,0x66,0x7c,0x78,0x6c,0x66,0x00,  # R
    0x3c,0x66,0x60,0x3c,0x06,0x66,0x3c,0x00,  # S
    0x7e,0x18,0x18,0x18,0x18,0x18,0x18,0x00,  # T
    0x66,0x66,0x66,0x66,0x66,0x66,0x3c,0x00,  # U
    0x66,0x66,0x66,0x66,0x66,0x3c,0x18,0x00,  # V
    0x63,0x63,0x63,0x6b,0x7f,0x77,0x63,0x00,  # W
    0x66,0x66,0x3c,0x18,0x3c,0x66,0x66,0x00,  # X
    0x66,0x66,0x66,0x3c,0x18,0x18,0x18,0x00,  # Y
    0x7e,0x06,0x0c,0x18,0x30,0x60,0x7e,0x00,  # Z
    0x3c,0x30,0x30,0x30,0x30,0x30,0x3c,0x00,  # [
    0x0c,0x12,0x30,0x7c,0x30,0x62,0xfc,0x00,  # pound
    0x3c,0x0c,0x0c,0x0c,0x0c,0x0c,0x3c,0x00,  # ]
    0x00,0x18,0x3c,0x7e,0x18,0x18,0x18,0x18,  # up arrow
    0x00,0x10,0x30,0x7f,0x7f,0x30,0x10,0x00,  # left arrow
    # Characters 32-63 (space, !"#$%&'()*+,-./0-9:;<=>?)
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,  # space
    0x18,0x18,0x18,0x18,0x00,0x00,0x18,0x00,  # !
    0x66,0x66,0x66,0x00,0x00,0x00,0x00,0x00,  # "
    0x66,0x66,0xff,0x66,0xff,0x66,0x66,0x00,  # #
    0x18,0x3e,0x60,0x3c,0x06,0x7c,0x18,0x00,  # $
    0x62,0x66,0x0c,0x18,0x30,0x66,0x46,0x00,  # %
    0x3c,0x66,0x3c,0x38,0x67,0x66,0x3f,0x00,  # &
    0x06,0x0c,0x18,0x00,0x00,0x00,0x00,0x00,  # '
    0x0c,0x18,0x30,0x30,0x30,0x18,0x0c,0x00,  # (
    0x30,0x18,0x0c,0x0c,0x0c,0x18,0x30,0x00,  # )
    0x00,0x66,0x3c,0xff,0x3c,0x66,0x00,0x00,  # *
    0x00,0x18,0x18,0x7e,0x18,0x18,0x00,0x00,  # +
    0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x30,  # ,
    0x00,0x00,0x00,0x7e,0x00,0x00,0x00,0x00,  # -
    0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x00,  # .
    0x00,0x03,0x06,0x0c,0x18,0x30,0x60,0x00,  # /
    0x3c,0x66,0x6e,0x76,0x66,0x66,0x3c,0x00,  # 0
    0x18,0x18,0x38,0x18,0x18,0x18,0x7e,0x00,  # 1
    0x3c,0x66,0x06,0x0c,0x30,0x60,0x7e,0x00,  # 2
    0x3c,0x66,0x06,0x1c,0x06,0x66,0x3c,0x00,  # 3
    0x06,0x0e,0x1e,0x66,0x7f,0x06,0x06,0x00,  # 4
    0x7e,0x60,0x7c,0x06,0x06,0x66,0x3c,0x00,  # 5
    0x3c,0x66,0x60,0x7c,0x66,0x66,0x3c,0x00,  # 6
    0x7e,0x66,0x0c,0x18,0x18,0x18,0x18,0x00,  # 7
    0x3c,0x66,0x66,0x3c,0x66,0x66,0x3c,0x00,  # 8
    0x3c,0x66,0x66,0x3e,0x06,0x66,0x3c,0x00,  # 9
    0x00,0x00,0x18,0x00,0x00,0x18,0x00,0x00,  # :
    0x00,0x00,0x18,0x00,0x00,0x18,0x18,0x30,  # ;
    0x0e,0x18,0x30,0x60,0x30,0x18,0x0e,0x00,  # <
    0x00,0x00,0x7e,0x00,0x7e,0x00,0x00,0x00,  # =
    0x70,0x18,0x0c,0x06,0x0c,0x18,0x70,0x00,  # >
    0x3c,0x66,0x06,0x0c,0x18,0x00,0x18,0x00,  # ?
    # Characters 64-95 (graphics characters)
    0x00,0x00,0x00,0xff,0xff,0x00,0x00,0x00,  # horiz line
    0x36,0x7f,0x7f,0x7f,0x3e,0x1c,0x08,0x00,  # spade
    0x18,0x18,0x18,0x18,0x18,0x18,0x18,0x18,  # vert line
    0x00,0x00,0x00,0xff,0xff,0x18,0x18,0x18,  # T up
    0x18,0x18,0x18,0xff,0xff,0x00,0x00,0x00,  # T down
    0x18,0x18,0x18,0xf8,0xf8,0x18,0x18,0x18,  # T left
    0x00,0x00,0x03,0x3e,0x76,0x36,0x36,0x00,  # curve TR
    0x00,0x00,0xc0,0x7c,0x6e,0x6c,0x6c,0x00,  # curve TL
    0x36,0x36,0x76,0x3e,0x03,0x00,0x00,0x00,  # curve BR
    0x6c,0x6c,0x6e,0x7c,0xc0,0x00,0x00,0x00,  # curve BL
    0x18,0x18,0x18,0x1f,0x1f,0x18,0x18,0x18,  # T right
    0x00,0x00,0x00,0x1f,0x1f,0x18,0x18,0x18,  # corner TL
    0x18,0x18,0x18,0x1f,0x1f,0x00,0x00,0x00,  # corner BL
    0x18,0x18,0x18,0xf8,0xf8,0x00,0x00,0x00,  # corner BR
    0x00,0x00,0x00,0xf8,0xf8,0x18,0x18,0x18,  # corner TR
    0x18,0x18,0x18,0xff,0xff,0x18,0x18,0x18,  # cross
    0x00,0x00,0x00,0x0f,0x0f,0x0f,0x0f,0x00,  # block BR
    0x00,0x00,0x00,0xf0,0xf0,0xf0,0xf0,0x00,  # block BL
    0x0f,0x0f,0x0f,0x0f,0x00,0x00,0x00,0x00,  # block TR
    0x08,0x1c,0x3e,0x7f,0x7f,0x1c,0x3e,0x00,  # club
    0xf0,0xf0,0xf0,0xf0,0x00,0x00,0x00,0x00,  # block TL
    0x80,0xc0,0xe0,0xf0,0xe0,0xc0,0x80,0x00,  # triangle left
    0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,  # full block
    0x01,0x03,0x07,0x0f,0x07,0x03,0x01,0x00,  # triangle right
    0x08,0x1c,0x3e,0x7f,0x3e,0x1c,0x08,0x00,  # diamond
    0x18,0x18,0x18,0x18,0xff,0x18,0x18,0x18,  # plus
    0xc0,0xc0,0xc0,0xc0,0xc0,0xc0,0xc0,0xc0,  # left edge
    0x00,0x00,0x00,0xfe,0xfe,0x06,0x06,0x06,  # corner DR
    0x00,0x7e,0x7e,0x7e,0x7e,0x7e,0x7e,0x00,  # square
    0x18,0x7e,0x7e,0x18,0x18,0x7e,0x3c,0x00,  # pi
    0x06,0x06,0x06,0xfe,0xfe,0x00,0x00,0x00,  # corner UR
    0x18,0x3c,0x7e,0x18,0x18,0x18,0x18,0x00,  # arrow up
    0x10,0x30,0x7f,0x7f,0x7f,0x30,0x10,0x00,  # arrow left
    # Characters 96-127 (lowercase letters in PETSCII are graphics)
    0x00,0x00,0x00,0x00,0x00,0x00,0xff,0xff,  # bottom bar
    0x08,0x1c,0x3e,0x7f,0x3e,0x1c,0x08,0x00,  # diamond
    0xff,0xff,0x00,0x00,0x00,0x00,0x00,0x00,  # top bar
    0x00,0x00,0x00,0x00,0x00,0xff,0xff,0xff,  # btm thick bar
    0x03,0x03,0x03,0x03,0x03,0x03,0x03,0x03,  # right edge
    0x00,0x00,0x00,0x00,0x0f,0x0f,0x0f,0x0f,  # btm right quad
    0xf0,0xf0,0xf0,0xf0,0x00,0x00,0x00,0x00,  # top left quad
    0x0f,0x0f,0x0f,0x0f,0xf0,0xf0,0xf0,0xf0,  # checkerboard
    0x0f,0x0f,0x0f,0x0f,0x00,0x00,0x00,0x00,  # top right quad
    0x00,0x00,0x00,0x00,0xf0,0xf0,0xf0,0xf0,  # btm left quad
    0x18,0x18,0x18,0x18,0x00,0x00,0x18,0x18,  # vert split
    0x00,0xc6,0x7c,0xc6,0xc6,0x7c,0xc6,0x00,  # circled times
    0x00,0x00,0x00,0x18,0x18,0x00,0x00,0x00,  # center dot
    0x00,0x00,0x60,0x60,0x00,0x00,0x00,0x00,  # upper left dot
    0xf0,0xf0,0xf0,0xf0,0xf0,0xf0,0xf0,0xf0,  # left half
    0x00,0x00,0x06,0x06,0x00,0x00,0x00,0x00,  # upper right dot
    0xff,0xff,0xff,0xff,0x00,0x00,0x00,0x00,  # top half
    0x36,0x7f,0x7f,0x7f,0x3e,0x1c,0x08,0x00,  # spade
    0x00,0x00,0x00,0x00,0x00,0x00,0x06,0x06,  # lower right dot
    0x66,0x66,0x66,0x66,0x66,0x00,0x66,0x00,  # vert bars
    0x7e,0xdb,0xdb,0x7b,0x1b,0x1b,0x1b,0x00,  # para
    0x3c,0x60,0x3c,0x66,0x3c,0x06,0x3c,0x00,  # section
    0x00,0x00,0x00,0x00,0x00,0x00,0x60,0x60,  # lower left dot
    0x00,0x00,0x00,0x00,0xff,0xff,0xff,0xff,  # btm half
    0x08,0x1c,0x3e,0x7f,0x7f,0x1c,0x3e,0x00,  # club
    0x36,0x36,0x7f,0x7f,0x7f,0x3e,0x1c,0x00,  # heart
    0x0f,0x0f,0x0f,0x0f,0x0f,0x0f,0x0f,0x0f,  # right half
    0x18,0x18,0x18,0x18,0x18,0x18,0x18,0x18,  # vert line
    0x00,0x00,0x00,0x07,0x0f,0x1c,0x18,0x18,  # curve UL
    0x18,0x18,0x1c,0x0f,0x07,0x00,0x00,0x00,  # curve LL
    0x18,0x18,0x38,0xf0,0xe0,0x00,0x00,0x00,  # curve LR
    0x00,0x00,0x00,0xe0,0xf0,0x38,0x18,0x18,  # curve UR
    # Characters 128-159 (reversed @-_ )
    0xc3,0x99,0x91,0x91,0x9f,0x9d,0xc3,0xff,  # @ reversed
    0xe7,0xc3,0x99,0x81,0x99,0x99,0x99,0xff,  # A reversed
    0x83,0x99,0x99,0x83,0x99,0x99,0x83,0xff,  # B reversed
    0xc3,0x99,0x9f,0x9f,0x9f,0x99,0xc3,0xff,  # C reversed
    0x87,0x93,0x99,0x99,0x99,0x93,0x87,0xff,  # D reversed
    0x81,0x9f,0x9f,0x87,0x9f,0x9f,0x81,0xff,  # E reversed
    0x81,0x9f,0x9f,0x87,0x9f,0x9f,0x9f,0xff,  # F reversed
    0xc3,0x99,0x9f,0x91,0x99,0x99,0xc3,0xff,  # G reversed
    0x99,0x99,0x99,0x81,0x99,0x99,0x99,0xff,  # H reversed
    0xc3,0xe7,0xe7,0xe7,0xe7,0xe7,0xc3,0xff,  # I reversed
    0xe1,0xf3,0xf3,0xf3,0xf3,0x93,0xc7,0xff,  # J reversed
    0x99,0x93,0x87,0x8f,0x87,0x93,0x99,0xff,  # K reversed
    0x9f,0x9f,0x9f,0x9f,0x9f,0x9f,0x81,0xff,  # L reversed
    0x9c,0x88,0x80,0x94,0x9c,0x9c,0x9c,0xff,  # M reversed
    0x99,0x89,0x81,0x81,0x91,0x99,0x99,0xff,  # N reversed
    0xc3,0x99,0x99,0x99,0x99,0x99,0xc3,0xff,  # O reversed
    0x83,0x99,0x99,0x83,0x9f,0x9f,0x9f,0xff,  # P reversed
    0xc3,0x99,0x99,0x99,0x99,0xc3,0xf1,0xff,  # Q reversed
    0x83,0x99,0x99,0x83,0x87,0x93,0x99,0xff,  # R reversed
    0xc3,0x99,0x9f,0xc3,0xf9,0x99,0xc3,0xff,  # S reversed
    0x81,0xe7,0xe7,0xe7,0xe7,0xe7,0xe7,0xff,  # T reversed
    0x99,0x99,0x99,0x99,0x99,0x99,0xc3,0xff,  # U reversed
    0x99,0x99,0x99,0x99,0x99,0xc3,0xe7,0xff,  # V reversed
    0x9c,0x9c,0x9c,0x94,0x80,0x88,0x9c,0xff,  # W reversed
    0x99,0x99,0xc3,0xe7,0xc3,0x99,0x99,0xff,  # X reversed
    0x99,0x99,0x99,0xc3,0xe7,0xe7,0xe7,0xff,  # Y reversed
    0x81,0xf9,0xf3,0xe7,0xcf,0x9f,0x81,0xff,  # Z reversed
    0xc3,0xcf,0xcf,0xcf,0xcf,0xcf,0xc3,0xff,  # [ reversed
    0xf3,0xed,0xcf,0x83,0xcf,0x9d,0x03,0xff,  # pound reversed
    0xc3,0xf3,0xf3,0xf3,0xf3,0xf3,0xc3,0xff,  # ] reversed
    0xff,0xe7,0xc3,0x81,0xe7,0xe7,0xe7,0xe7,  # up arrow rev
    0xff,0xef,0xcf,0x80,0x80,0xcf,0xef,0xff,  # left arrow rev
    # Characters 160-191 (reversed space-?)
    0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,  # space reversed
    0xe7,0xe7,0xe7,0xe7,0xff,0xff,0xe7,0xff,  # ! reversed
    0x99,0x99,0x99,0xff,0xff,0xff,0xff,0xff,  # " reversed
    0x99,0x99,0x00,0x99,0x00,0x99,0x99,0xff,  # # reversed
    0xe7,0xc1,0x9f,0xc3,0xf9,0x83,0xe7,0xff,  # $ reversed
    0x9d,0x99,0xf3,0xe7,0xcf,0x99,0xb9,0xff,  # % reversed
    0xc3,0x99,0xc3,0xc7,0x98,0x99,0xc0,0xff,  # & reversed
    0xf9,0xf3,0xe7,0xff,0xff,0xff,0xff,0xff,  # ' reversed
    0xf3,0xe7,0xcf,0xcf,0xcf,0xe7,0xf3,0xff,  # ( reversed
    0xcf,0xe7,0xf3,0xf3,0xf3,0xe7,0xcf,0xff,  # ) reversed
    0xff,0x99,0xc3,0x00,0xc3,0x99,0xff,0xff,  # * reversed
    0xff,0xe7,0xe7,0x81,0xe7,0xe7,0xff,0xff,  # + reversed
    0xff,0xff,0xff,0xff,0xff,0xe7,0xe7,0xcf,  # , reversed
    0xff,0xff,0xff,0x81,0xff,0xff,0xff,0xff,  # - reversed
    0xff,0xff,0xff,0xff,0xff,0xe7,0xe7,0xff,  # . reversed
    0xff,0xfc,0xf9,0xf3,0xe7,0xcf,0x9f,0xff,  # / reversed
    0xc3,0x99,0x91,0x89,0x99,0x99,0xc3,0xff,  # 0 reversed
    0xe7,0xe7,0xc7,0xe7,0xe7,0xe7,0x81,0xff,  # 1 reversed
    0xc3,0x99,0xf9,0xf3,0xcf,0x9f,0x81,0xff,  # 2 reversed
    0xc3,0x99,0xf9,0xe3,0xf9,0x99,0xc3,0xff,  # 3 reversed
    0xf9,0xf1,0xe1,0x99,0x80,0xf9,0xf9,0xff,  # 4 reversed
    0x81,0x9f,0x83,0xf9,0xf9,0x99,0xc3,0xff,  # 5 reversed
    0xc3,0x99,0x9f,0x83,0x99,0x99,0xc3,0xff,  # 6 reversed
    0x81,0x99,0xf3,0xe7,0xe7,0xe7,0xe7,0xff,  # 7 reversed
    0xc3,0x99,0x99,0xc3,0x99,0x99,0xc3,0xff,  # 8 reversed
    0xc3,0x99,0x99,0xc1,0xf9,0x99,0xc3,0xff,  # 9 reversed
    0xff,0xff,0xe7,0xff,0xff,0xe7,0xff,0xff,  # : reversed
    0xff,0xff,0xe7,0xff,0xff,0xe7,0xe7,0xcf,  # ; reversed
    0xf1,0xe7,0xcf,0x9f,0xcf,0xe7,0xf1,0xff,  # < reversed
    0xff,0xff,0x81,0xff,0x81,0xff,0xff,0xff,  # = reversed
    0x8f,0xe7,0xf3,0xf9,0xf3,0xe7,0x8f,0xff,  # > reversed
    0xc3,0x99,0xf9,0xf3,0xe7,0xff,0xe7,0xff,  # ? reversed
    # Characters 192-223 (reversed graphics)
    0xff,0xff,0xff,0x00,0x00,0xff,0xff,0xff,  # horiz line rev
    0xc9,0x80,0x80,0x80,0xc1,0xe3,0xf7,0xff,  # spade rev
    0xe7,0xe7,0xe7,0xe7,0xe7,0xe7,0xe7,0xe7,  # vert line
    0xff,0xff,0xff,0x00,0x00,0xe7,0xe7,0xe7,  # T up rev
    0xe7,0xe7,0xe7,0x00,0x00,0xff,0xff,0xff,  # T down rev
    0xe7,0xe7,0xe7,0x07,0x07,0xe7,0xe7,0xe7,  # T left rev
    0xff,0xff,0xfc,0xc1,0x89,0xc9,0xc9,0xff,  # curve TR rev
    0xff,0xff,0x3f,0x83,0x91,0x93,0x93,0xff,  # curve TL rev
    0xc9,0xc9,0x89,0xc1,0xfc,0xff,0xff,0xff,  # curve BR rev
    0x93,0x93,0x91,0x83,0x3f,0xff,0xff,0xff,  # curve BL rev
    0xe7,0xe7,0xe7,0xe0,0xe0,0xe7,0xe7,0xe7,  # T right rev
    0xff,0xff,0xff,0xe0,0xe0,0xe7,0xe7,0xe7,  # corner TL rev
    0xe7,0xe7,0xe7,0xe0,0xe0,0xff,0xff,0xff,  # corner BL rev
    0xe7,0xe7,0xe7,0x07,0x07,0xff,0xff,0xff,  # corner BR rev
    0xff,0xff,0xff,0x07,0x07,0xe7,0xe7,0xe7,  # corner TR rev
    0xe7,0xe7,0xe7,0x00,0x00,0xe7,0xe7,0xe7,  # cross rev
    0xff,0xff,0xff,0xf0,0xf0,0xf0,0xf0,0xff,  # block BR rev
    0xff,0xff,0xff,0x0f,0x0f,0x0f,0x0f,0xff,  # block BL rev
    0xf0,0xf0,0xf0,0xf0,0xff,0xff,0xff,0xff,  # block TR rev
    0xf7,0xe3,0xc1,0x80,0x80,0xe3,0xc1,0xff,  # club rev
    0x0f,0x0f,0x0f,0x0f,0xff,0xff,0xff,0xff,  # block TL rev
    0x7f,0x3f,0x1f,0x0f,0x1f,0x3f,0x7f,0xff,  # triangle left rev
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,  # full block rev (empty)
    0xfe,0xfc,0xf8,0xf0,0xf8,0xfc,0xfe,0xff,  # triangle right rev
    0xf7,0xe3,0xc1,0x80,0xc1,0xe3,0xf7,0xff,  # diamond rev
    0xe7,0xe7,0xe7,0xe7,0x00,0xe7,0xe7,0xe7,  # plus rev
    0x3f,0x3f,0x3f,0x3f,0x3f,0x3f,0x3f,0x3f,  # left edge rev
    0xff,0xff,0xff,0x01,0x01,0xf9,0xf9,0xf9,  # corner DR rev
    0xff,0x81,0x81,0x81,0x81,0x81,0x81,0xff,  # square rev
    0xe7,0x81,0x81,0xe7,0xe7,0x81,0xc3,0xff,  # pi rev
    0xf9,0xf9,0xf9,0x01,0x01,0xff,0xff,0xff,  # corner UR rev
    0xe7,0xc3,0x81,0xe7,0xe7,0xe7,0xe7,0xff,  # arrow up rev
    0xef,0xcf,0x80,0x80,0x80,0xcf,0xef,0xff,  # arrow left rev
    # Characters 224-255 (more reversed graphics)
    0xff,0xff,0xff,0xff,0xff,0xff,0x00,0x00,  # bottom bar rev
    0xf7,0xe3,0xc1,0x80,0xc1,0xe3,0xf7,0xff,  # diamond rev
    0x00,0x00,0xff,0xff,0xff,0xff,0xff,0xff,  # top bar rev
    0xff,0xff,0xff,0xff,0xff,0x00,0x00,0x00,  # btm thick bar rev
    0xfc,0xfc,0xfc,0xfc,0xfc,0xfc,0xfc,0xfc,  # right edge rev
    0xff,0xff,0xff,0xff,0xf0,0xf0,0xf0,0xf0,  # btm right quad rev
    0x0f,0x0f,0x0f,0x0f,0xff,0xff,0xff,0xff,  # top left quad rev
    0xf0,0xf0,0xf0,0xf0,0x0f,0x0f,0x0f,0x0f,  # checkerboard rev
    0xf0,0xf0,0xf0,0xf0,0xff,0xff,0xff,0xff,  # top right quad rev
    0xff,0xff,0xff,0xff,0x0f,0x0f,0x0f,0x0f,  # btm left quad rev
    0xe7,0xe7,0xe7,0xe7,0xff,0xff,0xe7,0xe7,  # vert split rev
    0xff,0x39,0x83,0x39,0x39,0x83,0x39,0xff,  # circled times rev
    0xff,0xff,0xff,0xe7,0xe7,0xff,0xff,0xff,  # center dot rev
    0xff,0xff,0x9f,0x9f,0xff,0xff,0xff,0xff,  # upper left dot rev
    0x0f,0x0f,0x0f,0x0f,0x0f,0x0f,0x0f,0x0f,  # left half rev
    0xff,0xff,0xf9,0xf9,0xff,0xff,0xff,0xff,  # upper right dot rev
    0x00,0x00,0x00,0x00,0xff,0xff,0xff,0xff,  # top half rev
    0xc9,0x80,0x80,0x80,0xc1,0xe3,0xf7,0xff,  # spade rev
    0xff,0xff,0xff,0xff,0xff,0xff,0xf9,0xf9,  # lower right dot rev
    0x99,0x99,0x99,0x99,0x99,0xff,0x99,0xff,  # vert bars rev
    0x81,0x24,0x24,0x84,0xe4,0xe4,0xe4,0xff,  # para rev
    0xc3,0x9f,0xc3,0x99,0xc3,0xf9,0xc3,0xff,  # section rev
    0xff,0xff,0xff,0xff,0xff,0xff,0x9f,0x9f,  # lower left dot rev
    0xff,0xff,0xff,0xff,0x00,0x00,0x00,0x00,  # btm half rev
    0xf7,0xe3,0xc1,0x80,0x80,0xe3,0xc1,0xff,  # club rev
    0xc9,0xc9,0x80,0x80,0x80,0xc1,0xe3,0xff,  # heart rev
    0xf0,0xf0,0xf0,0xf0,0xf0,0xf0,0xf0,0xf0,  # right half rev
    0xe7,0xe7,0xe7,0xe7,0xe7,0xe7,0xe7,0xe7,  # vert line
    0xff,0xff,0xff,0xf8,0xf0,0xe3,0xe7,0xe7,  # curve UL rev
    0xe7,0xe7,0xe3,0xf0,0xf8,0xff,0xff,0xff,  # curve LL rev
    0xe7,0xe7,0xc7,0x0f,0x1f,0xff,0xff,0xff,  # curve LR rev
    0xff,0xff,0xff,0x1f,0x0f,0xc7,0xe7,0xe7,  # curve UR rev
])

# API base URL - configurable via environment variable
BASE_URL = os.environ.get("C64U_URL", "http://192.168.200.157")

server = Server("c64u-mcp-server")

# HTTP client with reasonable timeout
def get_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)


# ============================================================================
# Tool Definitions
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return list of all available MCP tools."""
    return [
        # About
        Tool(
            name="get_version",
            description="Get the REST API version number from the Commodore 64 Ultimate Computer device",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # Runners - SID
        Tool(
            name="sidplay_file",
            description="Play a SID file from the device filesystem",
            inputSchema={
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "Path to the SID file on the device"},
                    "songnr": {"type": "integer", "description": "Song number to play (optional)"},
                },
                "required": ["file"],
            },
        ),
        Tool(
            name="sidplay_upload",
            description="Upload and play a SID file (base64 encoded)",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Base64 encoded SID file data"},
                    "songnr": {"type": "integer", "description": "Song number to play (optional)"},
                },
                "required": ["data"],
            },
        ),

        # Runners - MOD
        Tool(
            name="modplay_file",
            description="Play an Amiga MOD file from the device filesystem",
            inputSchema={
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "Path to the MOD file on the device"},
                },
                "required": ["file"],
            },
        ),
        Tool(
            name="modplay_upload",
            description="Upload and play an Amiga MOD file (base64 encoded)",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Base64 encoded MOD file data"},
                },
                "required": ["data"],
            },
        ),

        # Runners - PRG
        Tool(
            name="load_prg_file",
            description="Load a program file from filesystem without executing",
            inputSchema={
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "Path to the PRG file on the device"},
                },
                "required": ["file"],
            },
        ),
        Tool(
            name="load_prg_upload",
            description="Upload and load a program file without executing (base64 encoded)",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Base64 encoded PRG file data"},
                },
                "required": ["data"],
            },
        ),
        Tool(
            name="run_prg_file",
            description="Load and execute a program file from filesystem",
            inputSchema={
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "Path to the PRG file on the device"},
                },
                "required": ["file"],
            },
        ),
        Tool(
            name="run_prg_upload",
            description="Upload, load and execute a program file (base64 encoded)",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Base64 encoded PRG file data"},
                },
                "required": ["data"],
            },
        ),

        # Runners - CRT
        Tool(
            name="run_crt_file",
            description="Start a cartridge file from filesystem",
            inputSchema={
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "Path to the CRT file on the device"},
                },
                "required": ["file"],
            },
        ),
        Tool(
            name="run_crt_upload",
            description="Upload and start a cartridge file (base64 encoded)",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Base64 encoded CRT file data"},
                },
                "required": ["data"],
            },
        ),

        # Configuration
        Tool(
            name="list_config_categories",
            description="List all configuration categories",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_config_category",
            description="Get all configuration items in a category",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Configuration category name"},
                },
                "required": ["category"],
            },
        ),
        Tool(
            name="get_config_item",
            description="Get a specific configuration item's details",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Configuration category name"},
                    "item": {"type": "string", "description": "Configuration item name"},
                },
                "required": ["category", "item"],
            },
        ),
        Tool(
            name="set_config_item",
            description="Set a specific configuration item's value",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Configuration category name"},
                    "item": {"type": "string", "description": "Configuration item name"},
                    "value": {"type": "string", "description": "New value for the configuration item"},
                },
                "required": ["category", "item", "value"],
            },
        ),
        Tool(
            name="batch_set_config",
            description="Set multiple configuration items at once",
            inputSchema={
                "type": "object",
                "properties": {
                    "settings": {
                        "type": "object",
                        "description": "Object with category.item keys and their values",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["settings"],
            },
        ),
        Tool(
            name="load_config_from_flash",
            description="Restore configuration from non-volatile memory",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="save_config_to_flash",
            description="Save current configuration to non-volatile memory",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="reset_config_to_default",
            description="Reset configuration to factory defaults",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # Machine
        Tool(
            name="machine_reset",
            description="Send reset signal to the C64",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="machine_reboot",
            description="Restart and reinitialize the Ultimate device",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="machine_pause",
            description="Halt the C64 CPU via DMA line",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="machine_resume",
            description="Resume C64 from paused state",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="machine_poweroff",
            description="Power down the machine (U64 only)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="write_memory",
            description="Write data to C64 memory via DMA",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Memory address in hex (0000-ffff)"},
                    "data": {"type": "string", "description": "Hex string of bytes to write (e.g., 'A9008D2004')"},
                },
                "required": ["address", "data"],
            },
        ),
        Tool(
            name="write_memory_binary",
            description="Write binary data to C64 memory via DMA (base64 encoded)",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Memory address in hex (0000-ffff)"},
                    "data": {"type": "string", "description": "Base64 encoded binary data"},
                },
                "required": ["address", "data"],
            },
        ),
        Tool(
            name="read_memory",
            description="Read data from C64 memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Memory address in hex (0000-ffff)"},
                    "length": {"type": "integer", "description": "Number of bytes to read (default: 256)"},
                },
                "required": ["address"],
            },
        ),
        Tool(
            name="read_debug_register",
            description="Read debug register (U64 only)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="write_debug_register",
            description="Write debug register (U64 only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "value": {"type": "integer", "description": "Value to write to debug register"},
                },
                "required": ["value"],
            },
        ),
        Tool(
            name="capture_screen",
            description="Capture the C64 screen as a PNG image. Auto-detects the active graphics mode and renders accordingly. Supported modes: Standard Text (40x25), Multicolor Text, Extended Background Color (ECM), Standard Bitmap (Hires 320x200), and Multicolor Bitmap (160x200). Returns base64 encoded PNG data with mode info.",
            inputSchema={
                "type": "object",
                "properties": {
                    "scale": {
                        "type": "integer",
                        "description": "Scale factor for the output image (1-4, default: 2)",
                        "minimum": 1,
                        "maximum": 4,
                    },
                    "include_border": {
                        "type": "boolean",
                        "description": "Include the border area in the screenshot (default: true)",
                    },
                },
                "required": [],
            },
        ),

        # Drives
        Tool(
            name="list_drives",
            description="Get information about all floppy drives and mounted images",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="mount_disk_file",
            description="Mount a disk image from filesystem",
            inputSchema={
                "type": "object",
                "properties": {
                    "drive": {"type": "string", "description": "Drive identifier (e.g., 'a', 'b')"},
                    "image": {"type": "string", "description": "Path to disk image on device"},
                    "type": {"type": "string", "description": "Disk type (optional)"},
                    "mode": {"type": "string", "description": "Mount mode (optional)"},
                },
                "required": ["drive", "image"],
            },
        ),
        Tool(
            name="mount_disk_upload",
            description="Upload and mount a disk image (base64 encoded)",
            inputSchema={
                "type": "object",
                "properties": {
                    "drive": {"type": "string", "description": "Drive identifier (e.g., 'a', 'b')"},
                    "data": {"type": "string", "description": "Base64 encoded disk image data"},
                    "type": {"type": "string", "description": "Disk type (optional)"},
                    "mode": {"type": "string", "description": "Mount mode (optional)"},
                },
                "required": ["drive", "data"],
            },
        ),
        Tool(
            name="drive_reset",
            description="Reset a specific drive",
            inputSchema={
                "type": "object",
                "properties": {
                    "drive": {"type": "string", "description": "Drive identifier (e.g., 'a', 'b')"},
                },
                "required": ["drive"],
            },
        ),
        Tool(
            name="drive_remove",
            description="Unmount disk image from drive",
            inputSchema={
                "type": "object",
                "properties": {
                    "drive": {"type": "string", "description": "Drive identifier (e.g., 'a', 'b')"},
                },
                "required": ["drive"],
            },
        ),
        Tool(
            name="drive_on",
            description="Enable a drive",
            inputSchema={
                "type": "object",
                "properties": {
                    "drive": {"type": "string", "description": "Drive identifier (e.g., 'a', 'b')"},
                },
                "required": ["drive"],
            },
        ),
        Tool(
            name="drive_off",
            description="Disable a drive",
            inputSchema={
                "type": "object",
                "properties": {
                    "drive": {"type": "string", "description": "Drive identifier (e.g., 'a', 'b')"},
                },
                "required": ["drive"],
            },
        ),
        Tool(
            name="drive_load_rom_file",
            description="Load custom ROM for drive from filesystem",
            inputSchema={
                "type": "object",
                "properties": {
                    "drive": {"type": "string", "description": "Drive identifier (e.g., 'a', 'b')"},
                    "file": {"type": "string", "description": "Path to ROM file on device"},
                },
                "required": ["drive", "file"],
            },
        ),
        Tool(
            name="drive_load_rom_upload",
            description="Upload and load custom ROM for drive (base64 encoded)",
            inputSchema={
                "type": "object",
                "properties": {
                    "drive": {"type": "string", "description": "Drive identifier (e.g., 'a', 'b')"},
                    "data": {"type": "string", "description": "Base64 encoded ROM data"},
                },
                "required": ["drive", "data"],
            },
        ),
        Tool(
            name="drive_set_mode",
            description="Change drive type (1541/1571/1581)",
            inputSchema={
                "type": "object",
                "properties": {
                    "drive": {"type": "string", "description": "Drive identifier (e.g., 'a', 'b')"},
                    "mode": {"type": "string", "description": "Drive mode (1541, 1571, or 1581)"},
                },
                "required": ["drive", "mode"],
            },
        ),

        # Streams (U64 only)
        Tool(
            name="stream_start",
            description="Start a video/audio/debug stream (U64 only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "stream": {"type": "string", "description": "Stream name (e.g., 'video', 'audio', 'debug')"},
                    "ip": {"type": "string", "description": "Target IP address for stream"},
                },
                "required": ["stream", "ip"],
            },
        ),
        Tool(
            name="stream_stop",
            description="Stop an active stream (U64 only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "stream": {"type": "string", "description": "Stream name (e.g., 'video', 'audio', 'debug')"},
                },
                "required": ["stream"],
            },
        ),

        # Files
        Tool(
            name="get_file_info",
            description="Get metadata about a file on the device",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file on device"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="create_d64",
            description="Create a new D64 disk image",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path where to create the D64 file"},
                    "tracks": {"type": "integer", "description": "Number of tracks (default: 35)"},
                    "diskname": {"type": "string", "description": "Disk name (optional)"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="create_d71",
            description="Create a new D71 disk image",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path where to create the D71 file"},
                    "diskname": {"type": "string", "description": "Disk name (optional)"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="create_d81",
            description="Create a new D81 disk image",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path where to create the D81 file"},
                    "diskname": {"type": "string", "description": "Disk name (optional)"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="create_dnp",
            description="Create a new DNP disk image",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path where to create the DNP file"},
                    "tracks": {"type": "integer", "description": "Number of tracks"},
                    "diskname": {"type": "string", "description": "Disk name (optional)"},
                },
                "required": ["path", "tracks"],
            },
        ),
    ]


# ============================================================================
# Tool Handlers
# ============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent]:
    """Handle tool calls."""
    async with get_client() as client:
        try:
            result = await _handle_tool(client, name, arguments)
            # Handle image responses
            if isinstance(result, dict) and result.get("type") == "image":
                return [
                    TextContent(type="text", text=result.get("info", "")),
                    ImageContent(type="image", data=result["data"], mimeType=result["mimeType"])
                ]
            return [TextContent(type="text", text=result)]
        except httpx.HTTPStatusError as e:
            return [TextContent(type="text", text=f"HTTP Error {e.response.status_code}: {e.response.text}")]
        except httpx.RequestError as e:
            return [TextContent(type="text", text=f"Request Error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_tool(client: httpx.AsyncClient, name: str, args: dict) -> str:
    """Route tool calls to appropriate handlers."""

    # About
    if name == "get_version":
        resp = await client.get("/v1/version")
        resp.raise_for_status()
        return resp.text

    # Runners - SID
    elif name == "sidplay_file":
        params = {"file": args["file"]}
        if "songnr" in args:
            params["songnr"] = args["songnr"]
        resp = await client.put("/v1/runners:sidplay", params=params)
        resp.raise_for_status()
        return resp.text or "SID playback started"

    elif name == "sidplay_upload":
        data = base64.b64decode(args["data"])
        params = {}
        if "songnr" in args:
            params["songnr"] = args["songnr"]
        resp = await client.post("/v1/runners:sidplay", params=params, content=data)
        resp.raise_for_status()
        return resp.text or "SID playback started"

    # Runners - MOD
    elif name == "modplay_file":
        resp = await client.put("/v1/runners:modplay", params={"file": args["file"]})
        resp.raise_for_status()
        return resp.text or "MOD playback started"

    elif name == "modplay_upload":
        data = base64.b64decode(args["data"])
        resp = await client.post("/v1/runners:modplay", content=data)
        resp.raise_for_status()
        return resp.text or "MOD playback started"

    # Runners - PRG
    elif name == "load_prg_file":
        resp = await client.put("/v1/runners:load_prg", params={"file": args["file"]})
        resp.raise_for_status()
        return resp.text or "Program loaded"

    elif name == "load_prg_upload":
        data = base64.b64decode(args["data"])
        resp = await client.post("/v1/runners:load_prg", content=data)
        resp.raise_for_status()
        return resp.text or "Program loaded"

    elif name == "run_prg_file":
        resp = await client.put("/v1/runners:run_prg", params={"file": args["file"]})
        resp.raise_for_status()
        return resp.text or "Program running"

    elif name == "run_prg_upload":
        data = base64.b64decode(args["data"])
        resp = await client.post("/v1/runners:run_prg", content=data)
        resp.raise_for_status()
        return resp.text or "Program running"

    # Runners - CRT
    elif name == "run_crt_file":
        resp = await client.put("/v1/runners:run_crt", params={"file": args["file"]})
        resp.raise_for_status()
        return resp.text or "Cartridge started"

    elif name == "run_crt_upload":
        data = base64.b64decode(args["data"])
        resp = await client.post("/v1/runners:run_crt", content=data)
        resp.raise_for_status()
        return resp.text or "Cartridge started"

    # Configuration
    elif name == "list_config_categories":
        resp = await client.get("/v1/configs")
        resp.raise_for_status()
        return resp.text

    elif name == "get_config_category":
        resp = await client.get(f"/v1/configs/{args['category']}")
        resp.raise_for_status()
        return resp.text

    elif name == "get_config_item":
        resp = await client.get(f"/v1/configs/{args['category']}/{args['item']}")
        resp.raise_for_status()
        return resp.text

    elif name == "set_config_item":
        resp = await client.put(
            f"/v1/configs/{args['category']}/{args['item']}",
            params={"value": args["value"]}
        )
        resp.raise_for_status()
        return resp.text or "Configuration updated"

    elif name == "batch_set_config":
        resp = await client.post("/v1/configs", json=args["settings"])
        resp.raise_for_status()
        return resp.text or "Configuration batch update complete"

    elif name == "load_config_from_flash":
        resp = await client.put("/v1/configs:load_from_flash")
        resp.raise_for_status()
        return resp.text or "Configuration loaded from flash"

    elif name == "save_config_to_flash":
        resp = await client.put("/v1/configs:save_to_flash")
        resp.raise_for_status()
        return resp.text or "Configuration saved to flash"

    elif name == "reset_config_to_default":
        resp = await client.put("/v1/configs:reset_to_default")
        resp.raise_for_status()
        return resp.text or "Configuration reset to defaults"

    # Machine
    elif name == "machine_reset":
        resp = await client.put("/v1/machine:reset")
        resp.raise_for_status()
        return resp.text or "Machine reset"

    elif name == "machine_reboot":
        resp = await client.put("/v1/machine:reboot")
        resp.raise_for_status()
        return resp.text or "Machine rebooting"

    elif name == "machine_pause":
        resp = await client.put("/v1/machine:pause")
        resp.raise_for_status()
        return resp.text or "Machine paused"

    elif name == "machine_resume":
        resp = await client.put("/v1/machine:resume")
        resp.raise_for_status()
        return resp.text or "Machine resumed"

    elif name == "machine_poweroff":
        resp = await client.put("/v1/machine:poweroff")
        resp.raise_for_status()
        return resp.text or "Machine powered off"

    elif name == "write_memory":
        data = bytes.fromhex(args["data"])
        resp = await client.post(
            "/v1/machine:writemem",
            params={"address": args["address"]},
            content=data
        )
        resp.raise_for_status()
        return resp.text or f"Wrote {len(data)} bytes to ${args['address']}"

    elif name == "write_memory_binary":
        data = base64.b64decode(args["data"])
        resp = await client.post(
            "/v1/machine:writemem",
            params={"address": args["address"]},
            content=data
        )
        resp.raise_for_status()
        return resp.text or f"Wrote {len(data)} bytes to ${args['address']}"

    elif name == "read_memory":
        params = {"address": args["address"]}
        if "length" in args:
            params["length"] = args["length"]
        resp = await client.get("/v1/machine:readmem", params=params)
        resp.raise_for_status()
        # Return as hex dump
        data = resp.content
        hex_str = data.hex()
        return f"Read {len(data)} bytes from ${args['address']}: {hex_str}"

    elif name == "read_debug_register":
        resp = await client.get("/v1/machine:debugreg")
        resp.raise_for_status()
        return resp.text

    elif name == "write_debug_register":
        resp = await client.put("/v1/machine:debugreg", params={"value": args["value"]})
        resp.raise_for_status()
        return resp.text or "Debug register written"

    elif name == "capture_screen":
        scale = args.get("scale", 2)
        include_border = args.get("include_border", True)

        # Pause machine before capturing to ensure consistent screen state
        await client.put("/v1/machine:pause")

        try:
            # Read VIC-II registers ($D000-$D02E)
            resp = await client.get("/v1/machine:readmem", params={"address": "D000", "length": 48})
            resp.raise_for_status()
            vic_regs = resp.content

            # Read CIA2 port A ($DD00) for VIC bank selection
            resp = await client.get("/v1/machine:readmem", params={"address": "DD00", "length": 1})
            resp.raise_for_status()
            cia2_pra = resp.content[0]

            # Parse VIC-II registers
            d011 = vic_regs[0x11]  # Control register 1
            d016 = vic_regs[0x16]  # Control register 2
            d018 = vic_regs[0x18]  # Memory pointers
            d020 = vic_regs[0x20]  # Border color
            d021 = vic_regs[0x21]  # Background color 0
            d022 = vic_regs[0x22]  # Background color 1 (multicolor)
            d023 = vic_regs[0x23]  # Background color 2 (multicolor)
            d024 = vic_regs[0x24]  # Background color 3 (ECM)

            border_color = d020 & 0x0F
            bg_colors = [d021 & 0x0F, d022 & 0x0F, d023 & 0x0F, d024 & 0x0F]

            # Decode mode flags
            bmm = bool(d011 & 0x20)  # Bitmap mode
            ecm = bool(d011 & 0x40)  # Extended color mode
            mcm = bool(d016 & 0x10)  # Multicolor mode

            # Determine graphics mode
            if ecm and bmm:
                mode_name = "Invalid (ECM+BMM)"
            elif ecm and mcm:
                mode_name = "Invalid (ECM+MCM)"
            elif bmm and mcm:
                mode_name = "Multicolor Bitmap"
            elif bmm:
                mode_name = "Standard Bitmap (Hires)"
            elif ecm:
                mode_name = "Extended Background Color"
            elif mcm:
                mode_name = "Multicolor Text"
            else:
                mode_name = "Standard Text"

            # Calculate VIC bank base address
            vic_bank = (3 - (cia2_pra & 0x03)) * 0x4000

            # Calculate screen memory address
            screen_offset = ((d018 >> 4) & 0x0F) * 0x0400
            screen_addr = vic_bank + screen_offset

            # Calculate character/bitmap memory address
            char_offset = ((d018 >> 1) & 0x07) * 0x0800
            char_addr = vic_bank + char_offset
            bitmap_addr = vic_bank + (0x2000 if (d018 & 0x08) else 0x0000)

            # Read color RAM ($D800, always at fixed location)
            resp = await client.get("/v1/machine:readmem", params={"address": "D800", "length": 1000})
            resp.raise_for_status()
            color_ram = resp.content

            # Read screen RAM
            resp = await client.get("/v1/machine:readmem", params={
                "address": f"{screen_addr:04X}", "length": 1000
            })
            resp.raise_for_status()
            screen_ram = resp.content

            # For bitmap modes, read bitmap data (8000 bytes)
            bitmap_data = None
            if bmm:
                resp = await client.get("/v1/machine:readmem", params={
                    "address": f"{bitmap_addr:04X}", "length": 8000
                })
                resp.raise_for_status()
                bitmap_data = resp.content

            # For text modes with custom charset, read character data
            # Check if using ROM charset (banks 0 and 2 at offsets $1000-$1FFF mirror ROM)
            char_data = None
            use_rom_charset = False
            if not bmm:
                # In banks 0 and 2, addresses $1000-$1FFF and $9000-$9FFF read from char ROM
                char_mem_addr = vic_bank + char_offset
                if vic_bank in [0x0000, 0x8000] and 0x1000 <= char_offset < 0x2000:
                    use_rom_charset = True
                    char_data = C64_CHARSET
                else:
                    # Read custom character set from RAM
                    resp = await client.get("/v1/machine:readmem", params={
                        "address": f"{char_mem_addr:04X}", "length": 2048
                    })
                    resp.raise_for_status()
                    char_data = resp.content

        finally:
            # Resume machine after capturing memory
            await client.put("/v1/machine:resume")

        # Screen dimensions
        pixel_width, pixel_height = 320, 200
        border_size = 32 if include_border else 0

        # Create image
        img_width = pixel_width + (border_size * 2)
        img_height = pixel_height + (border_size * 2)
        img = Image.new('RGB', (img_width, img_height), C64_PALETTE[border_color])

        # Create pixel buffer for the screen area
        pixels = [[C64_PALETTE[bg_colors[0]] for _ in range(pixel_width)] for _ in range(pixel_height)]

        if bmm and mcm:
            # Multicolor Bitmap Mode: 160x200, 4 colors per 8x8 cell
            for char_y in range(25):
                for char_x in range(40):
                    cell_idx = char_y * 40 + char_x
                    screen_byte = screen_ram[cell_idx]
                    color_byte = color_ram[cell_idx] & 0x0F

                    # Colors for this cell
                    cell_colors = [
                        bg_colors[0],                    # %00 - background
                        (screen_byte >> 4) & 0x0F,       # %01 - screen RAM high nibble
                        screen_byte & 0x0F,              # %10 - screen RAM low nibble
                        color_byte                        # %11 - color RAM
                    ]

                    # Render 8x8 bitmap cell (but 4x8 effective due to multicolor)
                    for row in range(8):
                        bitmap_offset = char_y * 320 + char_x * 8 + row
                        byte = bitmap_data[bitmap_offset]
                        for col in range(4):
                            # Each pair of bits selects a color
                            shift = 6 - (col * 2)
                            color_idx = (byte >> shift) & 0x03
                            color = cell_colors[color_idx]
                            # Double-wide pixels
                            px = char_x * 8 + col * 2
                            py = char_y * 8 + row
                            pixels[py][px] = C64_PALETTE[color]
                            pixels[py][px + 1] = C64_PALETTE[color]

        elif bmm:
            # Standard Bitmap Mode (Hires): 320x200, 2 colors per 8x8 cell
            for char_y in range(25):
                for char_x in range(40):
                    cell_idx = char_y * 40 + char_x
                    screen_byte = screen_ram[cell_idx]
                    fg_color = (screen_byte >> 4) & 0x0F
                    bg_color_cell = screen_byte & 0x0F

                    # Render 8x8 bitmap cell
                    for row in range(8):
                        bitmap_offset = char_y * 320 + char_x * 8 + row
                        byte = bitmap_data[bitmap_offset]
                        for col in range(8):
                            px = char_x * 8 + col
                            py = char_y * 8 + row
                            if byte & (0x80 >> col):
                                pixels[py][px] = C64_PALETTE[fg_color]
                            else:
                                pixels[py][px] = C64_PALETTE[bg_color_cell]

        elif ecm:
            # Extended Background Color Mode: 40x25 text, 4 background colors
            for char_y in range(25):
                for char_x in range(40):
                    cell_idx = char_y * 40 + char_x
                    screen_byte = screen_ram[cell_idx]
                    fg_color = color_ram[cell_idx] & 0x0F

                    # Top 2 bits select background color, remaining 6 bits are char code
                    bg_select = (screen_byte >> 6) & 0x03
                    char_code = screen_byte & 0x3F
                    cell_bg = bg_colors[bg_select]

                    # Get character bitmap
                    char_offset_local = char_code * 8
                    if use_rom_charset:
                        char_bitmap = C64_CHARSET[char_offset_local:char_offset_local + 8]
                    else:
                        char_bitmap = char_data[char_offset_local:char_offset_local + 8]

                    # Render character
                    for row in range(8):
                        byte = char_bitmap[row] if row < len(char_bitmap) else 0
                        for col in range(8):
                            px = char_x * 8 + col
                            py = char_y * 8 + row
                            if byte & (0x80 >> col):
                                pixels[py][px] = C64_PALETTE[fg_color]
                            else:
                                pixels[py][px] = C64_PALETTE[cell_bg]

        elif mcm:
            # Multicolor Text Mode: 40x25, chars with color bit 3 set use multicolor
            for char_y in range(25):
                for char_x in range(40):
                    cell_idx = char_y * 40 + char_x
                    char_code = screen_ram[cell_idx]
                    color_byte = color_ram[cell_idx]
                    fg_color = color_byte & 0x0F
                    is_multicolor = bool(color_byte & 0x08)

                    # Get character bitmap
                    char_offset_local = char_code * 8
                    if use_rom_charset:
                        char_bitmap = C64_CHARSET[char_offset_local:char_offset_local + 8]
                    else:
                        char_bitmap = char_data[char_offset_local:char_offset_local + 8]

                    if is_multicolor:
                        # Multicolor: 4x8 double-wide pixels, 4 colors
                        mc_colors = [
                            bg_colors[0],      # %00 - background
                            bg_colors[1],      # %01 - $D022
                            bg_colors[2],      # %10 - $D023
                            fg_color & 0x07    # %11 - color RAM (low 3 bits only)
                        ]
                        for row in range(8):
                            byte = char_bitmap[row] if row < len(char_bitmap) else 0
                            for col in range(4):
                                shift = 6 - (col * 2)
                                color_idx = (byte >> shift) & 0x03
                                color = mc_colors[color_idx]
                                px = char_x * 8 + col * 2
                                py = char_y * 8 + row
                                pixels[py][px] = C64_PALETTE[color]
                                pixels[py][px + 1] = C64_PALETTE[color]
                    else:
                        # Standard character rendering
                        for row in range(8):
                            byte = char_bitmap[row] if row < len(char_bitmap) else 0
                            for col in range(8):
                                px = char_x * 8 + col
                                py = char_y * 8 + row
                                if byte & (0x80 >> col):
                                    pixels[py][px] = C64_PALETTE[fg_color]
                                # else: keep background

        else:
            # Standard Text Mode: 40x25 characters
            for char_y in range(25):
                for char_x in range(40):
                    cell_idx = char_y * 40 + char_x
                    char_code = screen_ram[cell_idx]
                    fg_color = color_ram[cell_idx] & 0x0F

                    # Get character bitmap
                    char_offset_local = char_code * 8
                    if use_rom_charset:
                        char_bitmap = C64_CHARSET[char_offset_local:char_offset_local + 8]
                    else:
                        char_bitmap = char_data[char_offset_local:char_offset_local + 8]

                    # Render character
                    for row in range(8):
                        byte = char_bitmap[row] if row < len(char_bitmap) else 0
                        for col in range(8):
                            px = char_x * 8 + col
                            py = char_y * 8 + row
                            if byte & (0x80 >> col):
                                pixels[py][px] = C64_PALETTE[fg_color]
                            # else: keep background color

        # Copy pixel buffer to image
        for y in range(pixel_height):
            for x in range(pixel_width):
                img.putpixel((x + border_size, y + border_size), pixels[y][x])

        # Scale the image
        if scale > 1:
            img = img.resize((img_width * scale, img_height * scale), Image.NEAREST)

        # Convert to PNG base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        png_base64 = base64.b64encode(buffer.getvalue()).decode('ascii')

        # Build mode info string
        mode_str = f"Mode: {mode_name} | VIC Bank: ${vic_bank:04X} | Screen: ${screen_addr:04X}"
        if bmm:
            mode_str += f" | Bitmap: ${bitmap_addr:04X}"
        else:
            mode_str += f" | Charset: ${char_addr:04X}"
            if use_rom_charset:
                mode_str += " (ROM)"

        return {
            "type": "image",
            "data": png_base64,
            "mimeType": "image/png",
            "info": mode_str
        }

    # Drives
    elif name == "list_drives":
        resp = await client.get("/v1/drives")
        resp.raise_for_status()
        return resp.text

    elif name == "mount_disk_file":
        params = {"image": args["image"]}
        if "type" in args:
            params["type"] = args["type"]
        if "mode" in args:
            params["mode"] = args["mode"]
        resp = await client.put(f"/v1/drives/{args['drive']}:mount", params=params)
        resp.raise_for_status()
        return resp.text or f"Disk mounted on drive {args['drive']}"

    elif name == "mount_disk_upload":
        data = base64.b64decode(args["data"])
        params = {}
        if "type" in args:
            params["type"] = args["type"]
        if "mode" in args:
            params["mode"] = args["mode"]
        resp = await client.post(
            f"/v1/drives/{args['drive']}:mount",
            params=params,
            content=data
        )
        resp.raise_for_status()
        return resp.text or f"Disk uploaded and mounted on drive {args['drive']}"

    elif name == "drive_reset":
        resp = await client.put(f"/v1/drives/{args['drive']}:reset")
        resp.raise_for_status()
        return resp.text or f"Drive {args['drive']} reset"

    elif name == "drive_remove":
        resp = await client.put(f"/v1/drives/{args['drive']}:remove")
        resp.raise_for_status()
        return resp.text or f"Disk removed from drive {args['drive']}"

    elif name == "drive_on":
        resp = await client.put(f"/v1/drives/{args['drive']}:on")
        resp.raise_for_status()
        return resp.text or f"Drive {args['drive']} enabled"

    elif name == "drive_off":
        resp = await client.put(f"/v1/drives/{args['drive']}:off")
        resp.raise_for_status()
        return resp.text or f"Drive {args['drive']} disabled"

    elif name == "drive_load_rom_file":
        resp = await client.put(
            f"/v1/drives/{args['drive']}:load_rom",
            params={"file": args["file"]}
        )
        resp.raise_for_status()
        return resp.text or f"ROM loaded for drive {args['drive']}"

    elif name == "drive_load_rom_upload":
        data = base64.b64decode(args["data"])
        resp = await client.post(
            f"/v1/drives/{args['drive']}:load_rom",
            content=data
        )
        resp.raise_for_status()
        return resp.text or f"ROM uploaded and loaded for drive {args['drive']}"

    elif name == "drive_set_mode":
        resp = await client.put(
            f"/v1/drives/{args['drive']}:set_mode",
            params={"mode": args["mode"]}
        )
        resp.raise_for_status()
        return resp.text or f"Drive {args['drive']} mode set to {args['mode']}"

    # Streams
    elif name == "stream_start":
        resp = await client.put(
            f"/v1/streams/{args['stream']}:start",
            params={"ip": args["ip"]}
        )
        resp.raise_for_status()
        return resp.text or f"Stream {args['stream']} started to {args['ip']}"

    elif name == "stream_stop":
        resp = await client.put(f"/v1/streams/{args['stream']}:stop")
        resp.raise_for_status()
        return resp.text or f"Stream {args['stream']} stopped"

    # Files
    elif name == "get_file_info":
        resp = await client.get(f"/v1/files/{args['path']}:info")
        resp.raise_for_status()
        return resp.text

    elif name == "create_d64":
        params = {}
        if "tracks" in args:
            params["tracks"] = args["tracks"]
        if "diskname" in args:
            params["diskname"] = args["diskname"]
        resp = await client.put(f"/v1/files/{args['path']}:create_d64", params=params)
        resp.raise_for_status()
        return resp.text or f"D64 image created at {args['path']}"

    elif name == "create_d71":
        params = {}
        if "diskname" in args:
            params["diskname"] = args["diskname"]
        resp = await client.put(f"/v1/files/{args['path']}:create_d71", params=params)
        resp.raise_for_status()
        return resp.text or f"D71 image created at {args['path']}"

    elif name == "create_d81":
        params = {}
        if "diskname" in args:
            params["diskname"] = args["diskname"]
        resp = await client.put(f"/v1/files/{args['path']}:create_d81", params=params)
        resp.raise_for_status()
        return resp.text or f"D81 image created at {args['path']}"

    elif name == "create_dnp":
        params = {"tracks": args["tracks"]}
        if "diskname" in args:
            params["diskname"] = args["diskname"]
        resp = await client.put(f"/v1/files/{args['path']}:create_dnp", params=params)
        resp.raise_for_status()
        return resp.text or f"DNP image created at {args['path']}"

    else:
        return f"Unknown tool: {name}"


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
