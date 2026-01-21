import io
import base64
import httpx
from enum import Enum
from PIL import Image
from tools.c64_data import C64_PALETTE, C64_CHARSET


class ScreenMode(Enum):
    """C64 VIC-II screen modes."""
    STANDARD_TEXT = "standard_text"
    MULTICOLOR_TEXT = "multicolor_text"
    EXTENDED_BG_COLOR = "extended_bg_color"
    STANDARD_BITMAP = "standard_bitmap"
    MULTICOLOR_BITMAP = "multicolor_bitmap"
    INVALID_ECM_BMM = "invalid_ecm_bmm"
    INVALID_ECM_MCM = "invalid_ecm_mcm"

    @property
    def display_name(self) -> str:
        """Human-readable name for the mode."""
        names = {
            ScreenMode.STANDARD_TEXT: "Standard Text",
            ScreenMode.MULTICOLOR_TEXT: "Multicolor Text",
            ScreenMode.EXTENDED_BG_COLOR: "Extended Background Color",
            ScreenMode.STANDARD_BITMAP: "Standard Bitmap (Hires)",
            ScreenMode.MULTICOLOR_BITMAP: "Multicolor Bitmap",
            ScreenMode.INVALID_ECM_BMM: "Invalid (ECM+BMM)",
            ScreenMode.INVALID_ECM_MCM: "Invalid (ECM+MCM)",
        }
        return names.get(self, self.value)

    @classmethod
    def from_flags(cls, bmm: bool, ecm: bool, mcm: bool) -> "ScreenMode":
        """Determine screen mode from VIC-II flags."""
        if ecm and bmm:
            return cls.INVALID_ECM_BMM
        elif ecm and mcm:
            return cls.INVALID_ECM_MCM
        elif bmm and mcm:
            return cls.MULTICOLOR_BITMAP
        elif bmm:
            return cls.STANDARD_BITMAP
        elif ecm:
            return cls.EXTENDED_BG_COLOR
        elif mcm:
            return cls.MULTICOLOR_TEXT
        else:
            return cls.STANDARD_TEXT


async def read_vic_state(client: httpx.AsyncClient) -> dict:
    """
    Read VIC-II and related registers from C64 memory.
    Returns a dict with all relevant video state.
    """
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

    # Decode mode flags
    bmm = bool(d011 & 0x20)  # Bitmap mode
    ecm = bool(d011 & 0x40)  # Extended color mode
    mcm = bool(d016 & 0x10)  # Multicolor mode

    # Determine screen mode
    mode = ScreenMode.from_flags(bmm, ecm, mcm)

    # Calculate VIC bank base address
    vic_bank = (3 - (cia2_pra & 0x03)) * 0x4000

    # Calculate screen memory address
    screen_offset = ((d018 >> 4) & 0x0F) * 0x0400
    screen_addr = vic_bank + screen_offset

    # Calculate character/bitmap memory address
    char_offset = ((d018 >> 1) & 0x07) * 0x0800
    char_addr = vic_bank + char_offset
    bitmap_addr = vic_bank + (0x2000 if (d018 & 0x08) else 0x0000)

    return {
        "mode": mode,
        "bmm": bmm,
        "ecm": ecm,
        "mcm": mcm,
        "vic_bank": vic_bank,
        "screen_addr": screen_addr,
        "char_addr": char_addr,
        "char_offset": char_offset,
        "bitmap_addr": bitmap_addr,
        "border_color": d020 & 0x0F,
        "bg_colors": [d021 & 0x0F, d022 & 0x0F, d023 & 0x0F, d024 & 0x0F],
        "cia2_pra": cia2_pra,
        "d018": d018,
    }


async def detect_screen_mode_logic(client: httpx.AsyncClient) -> dict:
    """
    Detect the active C64 screen mode and memory configuration.
    Returns mode info including enum value, display name, and memory addresses.
    Properly handles custom screen memory allocation (non-$0400 screen addresses).
    """
    await client.put("/v1/machine:pause")
    try:
        vic_state = await read_vic_state(client)
    finally:
        await client.put("/v1/machine:resume")

    mode = vic_state["mode"]
    vic_bank = vic_state["vic_bank"]
    screen_addr = vic_state["screen_addr"]
    char_addr = vic_state["char_addr"]
    bitmap_addr = vic_state["bitmap_addr"]
    cia2_pra = vic_state["cia2_pra"]
    d018 = vic_state["d018"]

    # Determine VIC bank number (0-3)
    vic_bank_num = 3 - (cia2_pra & 0x03)

    # Check if using standard BASIC screen at $0400
    is_standard_screen = (screen_addr == 0x0400)

    # Calculate screen offset within VIC bank
    screen_offset = ((d018 >> 4) & 0x0F) * 0x0400

    # Build memory layout description
    vic_bank_range = f"${vic_bank:04X}-${vic_bank + 0x3FFF:04X}"

    result = {
        "mode": mode.value,
        "mode_name": mode.display_name,
        "memory_config": {
            "vic_bank": vic_bank_num,
            "vic_bank_range": vic_bank_range,
            "screen_addr": f"${screen_addr:04X}",
            "screen_offset_in_bank": f"${screen_offset:04X}",
            "is_standard_screen": is_standard_screen,
        },
        "registers": {
            "d018": f"${d018:02X}",
            "dd00": f"${cia2_pra:02X}",
        },
    }

    if vic_state["bmm"]:
        result["memory_config"]["bitmap_addr"] = f"${bitmap_addr:04X}"
    else:
        result["memory_config"]["char_addr"] = f"${char_addr:04X}"
        result["memory_config"]["uses_rom_charset"] = (
            (cia2_pra & 0x03) in [0x03, 0x01] and
            vic_state["char_offset"] == 0x1000
        )

    # Add note if using non-standard configuration
    if not is_standard_screen:
        result["note"] = (
            f"Custom screen memory at ${screen_addr:04X} "
            f"(VIC bank {vic_bank_num}, offset ${screen_offset:04X}). "
            "This is common in demos, games, and tools like TASM."
        )

    return result


async def capture_screen_logic(client: httpx.AsyncClient, scale: int = 2, include_border: bool = True):
    # Pause machine before capturing to ensure consistent screen state
    await client.put("/v1/machine:pause")

    try:
        vic_state = await read_vic_state(client)

        mode = vic_state["mode"]
        bmm = vic_state["bmm"]
        ecm = vic_state["ecm"]
        mcm = vic_state["mcm"]
        vic_bank = vic_state["vic_bank"]
        screen_addr = vic_state["screen_addr"]
        char_addr = vic_state["char_addr"]
        char_offset = vic_state["char_offset"]
        bitmap_addr = vic_state["bitmap_addr"]
        border_color = vic_state["border_color"]
        bg_colors = vic_state["bg_colors"]
        cia2_pra = vic_state["cia2_pra"]

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

        # For text modes, we might need to read character data if not using ROM
        use_rom_charset = True
        char_data = None
        if not bmm:
            # Check if charset is in ROM ($1000-$1FFF or $9000-$9FFF in VIC space)
            # Actually VIC sees ROM at $1000-$1FFF and $9000-$9FFF if configured
            # In C64, character ROM is at $D000-$D7FF but VIC sees it at $1000-$1FFF in bank 0 and 2
            is_bank_0_or_2 = (cia2_pra & 0x03) in [0x03, 0x01]
            is_rom_char_offset = (char_offset == 0x1000)
            
            if is_bank_0_or_2 and is_rom_char_offset:
                use_rom_charset = True
            else:
                use_rom_charset = False
                # Read character data from RAM
                resp = await client.get("/v1/machine:readmem", params={
                    "address": f"{char_addr:04X}", "length": 2048
                })
                resp.raise_for_status()
                char_data = resp.content

        # Read bitmap data if in bitmap mode
        bitmap_data = None
        if bmm:
            resp = await client.get("/v1/machine:readmem", params={
                "address": f"{bitmap_addr:04X}", "length": 8000
            })
            resp.raise_for_status()
            bitmap_data = resp.content

    finally:
        # Resume machine as soon as memory is read
        await client.put("/v1/machine:resume")

    # Image dimensions
    pixel_width = 320
    pixel_height = 200
    border_size = 32 if include_border else 0
    img_width = pixel_width + (border_size * 2)
    img_height = pixel_height + (border_size * 2)

    img = Image.new('RGB', (img_width, img_height), C64_PALETTE[border_color])
    
    # We'll render to a pixel buffer first for speed
    pixels = [[C64_PALETTE[bg_colors[0]] for _ in range(320)] for _ in range(200)]

    if bmm:
        if mcm:
            # Multicolor Bitmap: 160x200 double-wide pixels, 4 colors per 8x8 block
            for char_y in range(25):
                for char_x in range(40):
                    cell_idx = char_y * 40 + char_x
                    screen_byte = screen_ram[cell_idx]
                    color_byte = color_ram[cell_idx]
                    
                    # Colors: 
                    # %00 = background ($D021)
                    # %01 = upper 4 bits of screen RAM
                    # %10 = lower 4 bits of screen RAM
                    # %11 = color RAM
                    block_colors = [
                        bg_colors[0],
                        (screen_byte >> 4) & 0x0F,
                        screen_byte & 0x0F,
                        color_byte & 0x0F
                    ]
                    
                    bitmap_offset = cell_idx * 8
                    for row in range(8):
                        byte = bitmap_data[bitmap_offset + row]
                        for col in range(4):
                            shift = 6 - (col * 2)
                            color_idx = (byte >> shift) & 0x03
                            color = block_colors[color_idx]
                            px = char_x * 8 + col * 2
                            py = char_y * 8 + row
                            pixels[py][px] = C64_PALETTE[color]
                            pixels[py][px+1] = C64_PALETTE[color]
        else:
            # Standard Bitmap: 320x200, 2 colors per 8x8 block
            for char_y in range(25):
                for char_x in range(40):
                    cell_idx = char_y * 40 + char_x
                    screen_byte = screen_ram[cell_idx]
                    fg_color = (screen_byte >> 4) & 0x0F
                    bg_color = screen_byte & 0x0F
                    
                    bitmap_offset = cell_idx * 8
                    for row in range(8):
                        byte = bitmap_data[bitmap_offset + row]
                        for col in range(8):
                            px = char_x * 8 + col
                            py = char_y * 8 + row
                            if byte & (0x80 >> col):
                                pixels[py][px] = C64_PALETTE[fg_color]
                            else:
                                pixels[py][px] = C64_PALETTE[bg_color]
    
    elif ecm:
        # Extended Background Color Mode: 40x25, 64 chars, 4 background colors
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
    mode_str = f"Mode: {mode.display_name} | VIC Bank: ${vic_bank:04X} | Screen: ${screen_addr:04X}"
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


def _render_screen_for_mode(
    mode: ScreenMode,
    screen_ram: bytes,
    color_ram: bytes,
    bitmap_data: bytes | None,
    char_data: bytes | None,
    use_rom_charset: bool,
    bg_colors: list[int],
    border_color: int,
    scale: int,
    include_border: bool,
) -> tuple[str, str]:
    """
    Render screen data using the specified mode.
    Returns (png_base64, mode_info_string).
    """
    # Determine mode flags
    bmm = mode in (ScreenMode.STANDARD_BITMAP, ScreenMode.MULTICOLOR_BITMAP)
    ecm = mode in (ScreenMode.EXTENDED_BG_COLOR, ScreenMode.INVALID_ECM_BMM, ScreenMode.INVALID_ECM_MCM)
    mcm = mode in (ScreenMode.MULTICOLOR_TEXT, ScreenMode.MULTICOLOR_BITMAP, ScreenMode.INVALID_ECM_MCM)

    # Image dimensions
    pixel_width = 320
    pixel_height = 200
    border_size = 32 if include_border else 0
    img_width = pixel_width + (border_size * 2)
    img_height = pixel_height + (border_size * 2)

    img = Image.new('RGB', (img_width, img_height), C64_PALETTE[border_color])
    pixels = [[C64_PALETTE[bg_colors[0]] for _ in range(320)] for _ in range(200)]

    if mode == ScreenMode.MULTICOLOR_BITMAP:
        # Multicolor Bitmap: 160x200 double-wide pixels, 4 colors per 8x8 block
        if bitmap_data:
            for char_y in range(25):
                for char_x in range(40):
                    cell_idx = char_y * 40 + char_x
                    screen_byte = screen_ram[cell_idx]
                    color_byte = color_ram[cell_idx]
                    block_colors = [
                        bg_colors[0],
                        (screen_byte >> 4) & 0x0F,
                        screen_byte & 0x0F,
                        color_byte & 0x0F
                    ]
                    bitmap_offset = cell_idx * 8
                    for row in range(8):
                        byte = bitmap_data[bitmap_offset + row]
                        for col in range(4):
                            shift = 6 - (col * 2)
                            color_idx = (byte >> shift) & 0x03
                            color = block_colors[color_idx]
                            px = char_x * 8 + col * 2
                            py = char_y * 8 + row
                            pixels[py][px] = C64_PALETTE[color]
                            pixels[py][px + 1] = C64_PALETTE[color]

    elif mode == ScreenMode.STANDARD_BITMAP:
        # Standard Bitmap: 320x200, 2 colors per 8x8 block
        if bitmap_data:
            for char_y in range(25):
                for char_x in range(40):
                    cell_idx = char_y * 40 + char_x
                    screen_byte = screen_ram[cell_idx]
                    fg_color = (screen_byte >> 4) & 0x0F
                    bg_color = screen_byte & 0x0F
                    bitmap_offset = cell_idx * 8
                    for row in range(8):
                        byte = bitmap_data[bitmap_offset + row]
                        for col in range(8):
                            px = char_x * 8 + col
                            py = char_y * 8 + row
                            if byte & (0x80 >> col):
                                pixels[py][px] = C64_PALETTE[fg_color]
                            else:
                                pixels[py][px] = C64_PALETTE[bg_color]

    elif mode == ScreenMode.EXTENDED_BG_COLOR:
        # Extended Background Color Mode: 40x25, 64 chars, 4 background colors
        for char_y in range(25):
            for char_x in range(40):
                cell_idx = char_y * 40 + char_x
                screen_byte = screen_ram[cell_idx]
                fg_color = color_ram[cell_idx] & 0x0F
                bg_select = (screen_byte >> 6) & 0x03
                char_code = screen_byte & 0x3F
                cell_bg = bg_colors[bg_select]
                char_offset_local = char_code * 8
                if use_rom_charset:
                    char_bitmap = C64_CHARSET[char_offset_local:char_offset_local + 8]
                else:
                    char_bitmap = char_data[char_offset_local:char_offset_local + 8] if char_data else bytes(8)
                for row in range(8):
                    byte = char_bitmap[row] if row < len(char_bitmap) else 0
                    for col in range(8):
                        px = char_x * 8 + col
                        py = char_y * 8 + row
                        if byte & (0x80 >> col):
                            pixels[py][px] = C64_PALETTE[fg_color]
                        else:
                            pixels[py][px] = C64_PALETTE[cell_bg]

    elif mode == ScreenMode.MULTICOLOR_TEXT:
        # Multicolor Text Mode: 40x25, chars with color bit 3 set use multicolor
        for char_y in range(25):
            for char_x in range(40):
                cell_idx = char_y * 40 + char_x
                char_code = screen_ram[cell_idx]
                color_byte = color_ram[cell_idx]
                fg_color = color_byte & 0x0F
                is_multicolor = bool(color_byte & 0x08)
                char_offset_local = char_code * 8
                if use_rom_charset:
                    char_bitmap = C64_CHARSET[char_offset_local:char_offset_local + 8]
                else:
                    char_bitmap = char_data[char_offset_local:char_offset_local + 8] if char_data else bytes(8)
                if is_multicolor:
                    mc_colors = [
                        bg_colors[0],
                        bg_colors[1],
                        bg_colors[2],
                        fg_color & 0x07
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
                    for row in range(8):
                        byte = char_bitmap[row] if row < len(char_bitmap) else 0
                        for col in range(8):
                            px = char_x * 8 + col
                            py = char_y * 8 + row
                            if byte & (0x80 >> col):
                                pixels[py][px] = C64_PALETTE[fg_color]

    else:
        # Standard Text Mode (default) or invalid modes
        for char_y in range(25):
            for char_x in range(40):
                cell_idx = char_y * 40 + char_x
                char_code = screen_ram[cell_idx]
                fg_color = color_ram[cell_idx] & 0x0F
                char_offset_local = char_code * 8
                if use_rom_charset:
                    char_bitmap = C64_CHARSET[char_offset_local:char_offset_local + 8]
                else:
                    char_bitmap = char_data[char_offset_local:char_offset_local + 8] if char_data else bytes(8)
                for row in range(8):
                    byte = char_bitmap[row] if row < len(char_bitmap) else 0
                    for col in range(8):
                        px = char_x * 8 + col
                        py = char_y * 8 + row
                        if byte & (0x80 >> col):
                            pixels[py][px] = C64_PALETTE[fg_color]

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

    mode_info = f"Mode: {mode.display_name}"
    return png_base64, mode_info


async def _read_all_screen_data(client: httpx.AsyncClient, vic_state: dict) -> dict:
    """Read all screen data needed for rendering any mode."""
    screen_addr = vic_state["screen_addr"]
    char_addr = vic_state["char_addr"]
    char_offset = vic_state["char_offset"]
    bitmap_addr = vic_state["bitmap_addr"]
    cia2_pra = vic_state["cia2_pra"]

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

    # Determine if ROM charset is used
    is_bank_0_or_2 = (cia2_pra & 0x03) in [0x03, 0x01]
    is_rom_char_offset = (char_offset == 0x1000)
    use_rom_charset = is_bank_0_or_2 and is_rom_char_offset

    # Read character data from RAM (needed for text modes with custom charset)
    char_data = None
    if not use_rom_charset:
        resp = await client.get("/v1/machine:readmem", params={
            "address": f"{char_addr:04X}", "length": 2048
        })
        resp.raise_for_status()
        char_data = resp.content

    # Read bitmap data (needed for bitmap modes)
    resp = await client.get("/v1/machine:readmem", params={
        "address": f"{bitmap_addr:04X}", "length": 8000
    })
    resp.raise_for_status()
    bitmap_data = resp.content

    return {
        "screen_ram": screen_ram,
        "color_ram": color_ram,
        "char_data": char_data,
        "bitmap_data": bitmap_data,
        "use_rom_charset": use_rom_charset,
    }


async def capture_screen_with_mode_logic(
    client: httpx.AsyncClient,
    mode: ScreenMode,
    scale: int = 2,
    include_border: bool = True
) -> dict:
    """
    Capture screen using an explicit mode, ignoring the active VIC-II mode.
    Useful when the auto-detection may not match the expected rendering.
    """
    await client.put("/v1/machine:pause")
    try:
        vic_state = await read_vic_state(client)
        screen_data = await _read_all_screen_data(client, vic_state)
    finally:
        await client.put("/v1/machine:resume")

    png_base64, mode_info = _render_screen_for_mode(
        mode=mode,
        screen_ram=screen_data["screen_ram"],
        color_ram=screen_data["color_ram"],
        bitmap_data=screen_data["bitmap_data"],
        char_data=screen_data["char_data"],
        use_rom_charset=screen_data["use_rom_charset"],
        bg_colors=vic_state["bg_colors"],
        border_color=vic_state["border_color"],
        scale=scale,
        include_border=include_border,
    )

    vic_bank = vic_state["vic_bank"]
    screen_addr = vic_state["screen_addr"]
    mode_str = f"{mode_info} | VIC Bank: ${vic_bank:04X} | Screen: ${screen_addr:04X}"

    return {
        "type": "image",
        "data": png_base64,
        "mimeType": "image/png",
        "info": mode_str
    }


# Valid modes for capture_all (excluding invalid combinations)
VALID_SCREEN_MODES = [
    ScreenMode.STANDARD_TEXT,
    ScreenMode.MULTICOLOR_TEXT,
    ScreenMode.EXTENDED_BG_COLOR,
    ScreenMode.STANDARD_BITMAP,
    ScreenMode.MULTICOLOR_BITMAP,
]


async def capture_all_screen_modes_logic(
    client: httpx.AsyncClient,
    scale: int = 2,
    include_border: bool = True
) -> list[dict]:
    """
    Capture screenshots for all valid screen modes at once.
    Returns a list of image results, one for each mode.
    """
    await client.put("/v1/machine:pause")
    try:
        vic_state = await read_vic_state(client)
        screen_data = await _read_all_screen_data(client, vic_state)
    finally:
        await client.put("/v1/machine:resume")

    results = []
    for mode in VALID_SCREEN_MODES:
        png_base64, mode_info = _render_screen_for_mode(
            mode=mode,
            screen_ram=screen_data["screen_ram"],
            color_ram=screen_data["color_ram"],
            bitmap_data=screen_data["bitmap_data"],
            char_data=screen_data["char_data"],
            use_rom_charset=screen_data["use_rom_charset"],
            bg_colors=vic_state["bg_colors"],
            border_color=vic_state["border_color"],
            scale=scale,
            include_border=include_border,
        )
        results.append({
            "type": "image",
            "data": png_base64,
            "mimeType": "image/png",
            "mode": mode.value,
            "info": mode_info
        })

    return results
