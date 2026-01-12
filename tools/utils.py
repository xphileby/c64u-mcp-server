import base64

from tools.c64_data import SPECIAL_KEYS


def decode_base64_data(data: str) -> bytes:
    """Decode base64 data, handling both pure base64 and data URL formats."""
    # Strip data URL prefix if present (e.g., "data:application/octet-stream;base64,...")
    if data.startswith("data:"):
        data = data.split(",", 1)[1]
    return base64.b64decode(data)

def ascii_to_petscii(text: str) -> bytes:
    """Convert ASCII/Unicode text to PETSCII keyboard codes.

    Supports special key placeholders like {RETURN}, {HOME}, {CLR}, etc.
    """
    result = []

    # Find all special keys and regular text segments
    pattern = r'(\{[A-Z0-9_]+\})'
    parts = re.split(pattern, text)

    for part in parts:
        if part.startswith('{') and part.endswith('}'):
            # Special key placeholder
            upper_part = part.upper()
            if upper_part in SPECIAL_KEYS:
                result.append(SPECIAL_KEYS[upper_part])
            # Skip unknown placeholders
        else:
            # Regular text
            for char in part:
                code = ord(char)
                if char == ' ':
                    result.append(32)  # Space
                elif 'A' <= char <= 'Z':
                    result.append(code)
                elif 'a' <= char <= 'z':
                    # Lowercase -> uppercase PETSCII
                    result.append(code - 32)
                elif '0' <= char <= '9':
                    result.append(code)
                elif char in '!"#$%&\'()*+,-./:;<=>?@[]^':
                    result.append(code)
                # Skip other unmapped characters
    return bytes(result)