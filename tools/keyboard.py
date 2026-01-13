import asyncio
from tools.utils import ascii_to_petscii
from tools.c64_data import KEYBUF_ADDR, KEYBUF_LEN_ADDR, KEYBUF_MAX_SIZE

async def wait_for_empty_buffer(client):
    """Wait for the C64 keyboard buffer to be empty."""
    for _ in range(50):  # Max 50 attempts (5 seconds)
        resp = await client.get("/v1/machine:readmem", params={
            "address": f"{KEYBUF_LEN_ADDR:02X}", "length": 1
        })
        resp.raise_for_status()
        if resp.content[0] == 0:
            return True
        await asyncio.sleep(0.1)
    return False

async def type_text_logic(client, text, wait_ms=100):
    """Externalized logic for typing text into the C64 keyboard buffer."""
    # Convert text to PETSCII
    petscii_bytes = ascii_to_petscii(text)

    if len(petscii_bytes) == 0:
        return "No valid characters to type"

    total_typed = 0
    for i in range(0, len(petscii_bytes), KEYBUF_MAX_SIZE):
        chunk = petscii_bytes[i:i + KEYBUF_MAX_SIZE]
        chunk_len = len(chunk)

        # Wait for keyboard buffer to be empty before writing
        if not await wait_for_empty_buffer(client):
            # If we timed out, we might still try to write, but it's risky
            # The original code just breaks the wait loop and continues
            pass

        # Write characters to keyboard buffer
        resp = await client.post(
            "/v1/machine:writemem",
            params={"address": f"{KEYBUF_ADDR:04X}"},
            content=chunk
        )
        resp.raise_for_status()

        # Set buffer length
        resp = await client.post(
            "/v1/machine:writemem",
            params={"address": f"{KEYBUF_LEN_ADDR:02X}"},
            content=bytes([chunk_len])
        )
        resp.raise_for_status()

        total_typed += chunk_len

        # Wait for processing if more chunks to come
        if i + KEYBUF_MAX_SIZE < len(petscii_bytes):
            await asyncio.sleep(wait_ms / 1000.0)

    # Final wait for buffer processing
    if wait_ms > 0:
        await asyncio.sleep(wait_ms / 1000.0)

    return f"Typed {total_typed} characters"

async def send_key_logic(client, key):
    """Externalized logic for sending a single special key to the C64."""
    # Map key names to PETSCII codes
    key_codes = {
        "RETURN": 13,
        "HOME": 19,
        "CLR": 147,
        "DEL": 20,
        "INS": 148,
        "UP": 145,
        "DOWN": 17,
        "LEFT": 157,
        "RIGHT": 29,
        "F1": 133,
        "F2": 137,
        "F3": 134,
        "F4": 138,
        "F5": 135,
        "F6": 139,
        "F7": 136,
        "F8": 140,
        "RUN_STOP": 3,
    }

    if key not in key_codes:
        return f"Unknown key: {key}"

    code = key_codes[key]

    # Wait for keyboard buffer to be empty
    await wait_for_empty_buffer(client)

    # Write key to keyboard buffer
    resp = await client.post(
        "/v1/machine:writemem",
        params={"address": f"{KEYBUF_ADDR:04X}"},
        content=bytes([code])
    )
    resp.raise_for_status()

    # Set buffer length to 1
    resp = await client.post(
        "/v1/machine:writemem",
        params={"address": f"{KEYBUF_LEN_ADDR:02X}"},
        content=bytes([1])
    )
    resp.raise_for_status()

    return f"Sent key: {key} (PETSCII ${code:02X})"
