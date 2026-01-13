# Commodore 64 Ultimate Computer MCP Server

MCP (Model Context Protocol) server for the Commodore 64 Ultimate Computer REST API. This server exposes all Commodore 64 Ultimate Computer REST API endpoints as MCP tools.

## Prerequisites

Enable **Network Services** from the Commodore 64 Ultimate menu: Network Services & Timezone -> Web Remote Control Service -> Enabled

## Installation

```bash
cd c64u-mcp-server
uv sync
```

## Configuration

Set the `C64U_URL` environment variable to your device's IP address:

```bash
export C64U_URL="http://192.168.200.157"
```

Default: `http://192.168.200.157`

## Running the Server

```bash
uv run python server.py
```

## Claude Desktop Configuration

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "commodore64": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/c64u-mcp-server", "python", "server.py"],
      "env": {
        "C64U_URL": "http://192.168.200.157"
      }
    }
  }
}
```

## Available Tools

### About
- `get_version` - Get REST API version

### Runners (SID/MOD/PRG/CRT)
- `sidplay_file` - Play SID file from device filesystem
- `sidplay_upload` - Upload and play SID file (base64)
- `modplay_file` - Play MOD file from device filesystem
- `modplay_upload` - Upload and play MOD file (base64)
- `load_prg_file` - Load PRG without executing
- `load_prg_upload` - Upload and load PRG (base64)
- `run_prg_file` - Load and run PRG from filesystem
- `run_prg_upload` - Upload and run PRG (base64)
- `run_crt_file` - Start cartridge from filesystem
- `run_crt_upload` - Upload and start cartridge (base64)

### Configuration
- `list_config_categories` - List all config categories
- `get_config_category` - Get items in a category
- `get_config_item` - Get specific config item
- `set_config_item` - Set config item value
- `batch_set_config` - Set multiple config items
- `load_config_from_flash` - Restore config from flash
- `save_config_to_flash` - Save config to flash
- `reset_config_to_default` - Reset to factory defaults

### Machine Control
- `machine_reset` - Reset the C64
- `machine_reboot` - Reboot Ultimate device
- `machine_pause` - Pause CPU via DMA
- `machine_resume` - Resume from pause
- `machine_poweroff` - Power off (U64 only)
- `write_memory` - Write hex data to C64 memory
- `write_memory_binary` - Write binary data to memory (base64)
- `read_memory` - Read C64 memory
- `read_debug_register` - Read debug register (U64)
- `write_debug_register` - Write debug register (U64)
- `capture_screen` - Capture C64 screen as PNG image
- `type_text` - Type text into keyboard buffer (supports special keys)
- `send_key` - Send a special key to keyboard buffer
- `enter_basic_program` - Enter BASIC program directly into memory (tokenized)

### Floppy Drives
- `list_drives` - List all drives and mounted images
- `mount_disk_file` - Mount disk from filesystem
- `mount_disk_upload` - Upload and mount disk (base64)
- `drive_reset` - Reset drive
- `drive_remove` - Unmount disk
- `drive_on` - Enable drive
- `drive_off` - Disable drive
- `drive_load_rom_file` - Load custom ROM
- `drive_load_rom_upload` - Upload custom ROM (base64)
- `drive_set_mode` - Change drive type (1541/1571/1581)

### Streams (U64 only)
- `stream_start` - Start video/audio/debug stream
- `stream_stop` - Stop active stream

### File Operations
- `get_file_info` - Get file metadata
- `create_d64` - Create D64 disk image
- `create_d71` - Create D71 disk image
- `create_d81` - Create D81 disk image
- `create_dnp` - Create DNP disk image

## API Reference

Based on: https://1541u-documentation.readthedocs.io/en/latest/api/api_calls.html
