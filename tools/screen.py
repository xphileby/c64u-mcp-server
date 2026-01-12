import io
import base64
import httpx
from PIL import Image
from tools.c64_data import C64_PALETTE, C64_CHARSET

async def capture_screen_logic(client: httpx.AsyncClient, scale: int = 2, include_border: bool = True):
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
