"""
MCP Server for Commodore 64 Ultimate Computer REST API

This server provides MCP tools for interacting with the Commodore 64 Ultimate Computer
device via its REST API.
"""

import base64
import os
from typing import Optional
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

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
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    async with get_client() as client:
        try:
            result = await _handle_tool(client, name, arguments)
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
        resp = await client.put(
            "/v1/machine:writemem",
            params={"address": args["address"], "data": args["data"]}
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
