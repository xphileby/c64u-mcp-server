#!/usr/bin/env python3
"""
Command-line test client for the C64 Ultimate MCP Server.

Usage (with virtual environment):
    .venv/Scripts/python test_client.py           # Windows
    .venv/bin/python test_client.py               # Linux/macOS

Usage (with system Python if dependencies installed):
    python test_client.py [--url URL]

Features:
    - Lists all available MCP tools
    - Interactive menu to select and execute tools
    - Predefined test parameters for common tools
    - Saves base64-encoded binary data to files

Requirements:
    - httpx
    - pillow (for the server)
    - mcp
"""

import argparse
import asyncio
import base64
import json
import os
import sys
from datetime import datetime

import httpx

# Default server URL
DEFAULT_URL = os.environ.get("C64U_URL", "http://192.168.200.157")

# Predefined test parameters for tools
PREDEFINED_PARAMS = {
    "get_version": {},
    "get_screen_mode": {},
    "capture_screen": {"scale": 2, "include_border": True},
    "capture_screen_with_mode": {"mode": "standard_text", "scale": 2, "include_border": True},
    "capture_screen_with_config": {"mode": "standard_text", "screen_addr": "0400", "scale": 2},
    "capture_all_screen_modes": {"scale": 2, "include_border": True},
    "machine_reset": {},
    "machine_pause": {},
    "machine_resume": {},
    "list_drives": {},
    "list_config_categories": {},
    "read_memory": {"address": "0400", "length": 256},
    "read_debug_register": {},
    "type_text": {"text": "HELLO WORLD{RETURN}", "wait_ms": 100},
    "send_key": {"key": "RETURN"},
    "enter_basic_program": {
        "program": '10 PRINT "HELLO WORLD"\n20 GOTO 10',
        "auto_run": False
    },
}


class MCPTestClient:
    """Test client for the C64 Ultimate MCP Server."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.tools = []
        self.output_dir = "test_output"

    async def fetch_tools(self) -> list[dict]:
        """Fetch the list of available tools from the server."""
        # Since this is an MCP server, we need to interact with it differently
        # For testing, we'll import the server module directly
        print(f"Connecting to server at {self.base_url}...")

        # Try a simple version check to verify connectivity
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            try:
                resp = await client.get("/v1/version")
                resp.raise_for_status()
                print(f"Server version: {resp.text}")
            except Exception as e:
                print(f"Warning: Could not connect to C64 Ultimate device: {e}")
                print("Tool list will be loaded from server module.\n")

        # Import tools from the server module
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from server import list_tools
            self.tools = await list_tools()
            return self.tools
        except Exception as e:
            print(f"Error loading tools: {e}")
            return []

    async def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool and return the result."""
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from server import call_tool
            result = await call_tool(tool_name, arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_binary_data(self, data: str, filename: str, mime_type: str = None) -> str:
        """Decode base64 data and save to file."""
        os.makedirs(self.output_dir, exist_ok=True)

        # Determine file extension from mime type
        ext = ".bin"
        if mime_type:
            ext_map = {
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/gif": ".gif",
                "application/octet-stream": ".bin",
            }
            ext = ext_map.get(mime_type, ".bin")

        # Add timestamp to filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_filename = f"{filename}_{timestamp}{ext}"
        filepath = os.path.join(self.output_dir, full_filename)

        # Decode and save
        try:
            binary_data = base64.b64decode(data)
            with open(filepath, "wb") as f:
                f.write(binary_data)
            return filepath
        except Exception as e:
            return f"Error saving file: {e}"

    def display_menu(self):
        """Display the tool selection menu."""
        print("\n" + "=" * 60)
        print("C64 Ultimate MCP Server - Test Client")
        print("=" * 60)
        print("\nAvailable Tools:")
        print("-" * 60)

        for i, tool in enumerate(self.tools, 1):
            name = tool.name
            desc = tool.description[:50] + "..." if len(tool.description) > 50 else tool.description
            predefined = " [P]" if name in PREDEFINED_PARAMS else ""
            print(f"  {i:3}. {name}{predefined}")
            print(f"       {desc}")

        print("-" * 60)
        print("  [P] = Predefined parameters available")
        print("   0. Exit")
        print()

    def get_tool_params(self, tool) -> dict | None:
        """Get parameters for a tool (predefined or user input)."""
        tool_name = tool.name
        schema = tool.inputSchema
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        if not properties:
            print(f"\nTool '{tool_name}' requires no parameters.")
            return {}

        print(f"\nTool: {tool_name}")
        print(f"Description: {tool.description}")
        print("\nParameters:")
        for name, prop in properties.items():
            req = " (required)" if name in required else " (optional)"
            prop_type = prop.get("type", "any")
            desc = prop.get("description", "No description")
            enum_vals = prop.get("enum", [])
            print(f"  - {name}: {prop_type}{req}")
            print(f"    {desc}")
            if enum_vals:
                print(f"    Allowed values: {enum_vals}")

        # Check if predefined params exist
        if tool_name in PREDEFINED_PARAMS:
            print(f"\nPredefined parameters available:")
            print(f"  {json.dumps(PREDEFINED_PARAMS[tool_name], indent=2)}")
            choice = input("\nUse predefined parameters? [Y/n]: ").strip().lower()
            if choice != "n":
                return PREDEFINED_PARAMS[tool_name]

        # Get user input for parameters
        print("\nEnter parameters (press Enter to skip optional ones):")
        params = {}

        for name, prop in properties.items():
            is_required = name in required
            prop_type = prop.get("type", "string")
            enum_vals = prop.get("enum", [])
            default = prop.get("default")

            prompt = f"  {name}"
            if enum_vals:
                prompt += f" {enum_vals}"
            if default is not None:
                prompt += f" [default: {default}]"
            prompt += ": "

            while True:
                value = input(prompt).strip()

                if not value:
                    if is_required and default is None:
                        print(f"    Error: {name} is required")
                        continue
                    elif default is not None:
                        params[name] = default
                    break

                # Type conversion
                try:
                    if prop_type == "integer":
                        params[name] = int(value)
                    elif prop_type == "boolean":
                        params[name] = value.lower() in ("true", "yes", "1", "y")
                    elif prop_type == "number":
                        params[name] = float(value)
                    elif prop_type == "object":
                        params[name] = json.loads(value)
                    elif prop_type == "array":
                        params[name] = json.loads(value)
                    else:
                        if enum_vals and value not in enum_vals:
                            print(f"    Error: Must be one of {enum_vals}")
                            continue
                        params[name] = value
                    break
                except (ValueError, json.JSONDecodeError) as e:
                    print(f"    Error: Invalid value - {e}")

        return params

    def process_result(self, result: dict, tool_name: str):
        """Process and display the tool execution result."""
        print("\n" + "=" * 60)
        print("Result:")
        print("=" * 60)

        if not result.get("success"):
            print(f"Error: {result.get('error')}")
            return

        contents = result.get("result", [])
        saved_files = []

        for i, content in enumerate(contents):
            content_type = content.type

            if content_type == "text":
                print(f"\n[Text Content {i+1}]")
                print(content.text)

            elif content_type == "image":
                print(f"\n[Image Content {i+1}]")
                print(f"  MIME Type: {content.mimeType}")
                print(f"  Data length: {len(content.data)} chars (base64)")

                # Save the image
                filename = f"{tool_name}_{i+1}"
                filepath = self.save_binary_data(content.data, filename, content.mimeType)
                saved_files.append(filepath)
                print(f"  Saved to: {filepath}")

            else:
                print(f"\n[Unknown Content Type: {content_type}]")
                print(f"  {content}")

        if saved_files:
            print(f"\n{len(saved_files)} file(s) saved to '{self.output_dir}/' directory")

    async def run_interactive(self):
        """Run the interactive test client."""
        # Fetch tools
        await self.fetch_tools()

        if not self.tools:
            print("No tools available. Exiting.")
            return

        while True:
            self.display_menu()

            try:
                choice = input("Select tool number (0 to exit): ").strip()
                if not choice:
                    continue

                choice_num = int(choice)

                if choice_num == 0:
                    print("\nExiting...")
                    break

                if choice_num < 1 or choice_num > len(self.tools):
                    print(f"\nInvalid choice. Please enter 1-{len(self.tools)} or 0 to exit.")
                    continue

                tool = self.tools[choice_num - 1]
                params = self.get_tool_params(tool)

                if params is None:
                    print("\nCancelled.")
                    continue

                print(f"\nExecuting '{tool.name}' with parameters:")
                print(f"  {json.dumps(params, indent=2)}")

                confirm = input("\nProceed? [Y/n]: ").strip().lower()
                if confirm == "n":
                    print("Cancelled.")
                    continue

                print("\nExecuting...")
                result = await self.execute_tool(tool.name, params)
                self.process_result(result, tool.name)

                input("\nPress Enter to continue...")

            except ValueError:
                print("\nInvalid input. Please enter a number.")
            except KeyboardInterrupt:
                print("\n\nInterrupted. Exiting...")
                break
            except Exception as e:
                print(f"\nError: {e}")
                input("Press Enter to continue...")


async def run_single_tool(client: MCPTestClient, tool_name: str, params_json: str = None):
    """Run a single tool non-interactively."""
    await client.fetch_tools()

    # Find the tool
    tool = None
    for t in client.tools:
        if t.name == tool_name:
            tool = t
            break

    if not tool:
        print(f"Error: Tool '{tool_name}' not found")
        print(f"Available tools: {[t.name for t in client.tools]}")
        return

    # Parse parameters
    if params_json:
        try:
            params = json.loads(params_json)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON parameters: {e}")
            return
    elif tool_name in PREDEFINED_PARAMS:
        params = PREDEFINED_PARAMS[tool_name]
        print(f"Using predefined parameters: {json.dumps(params)}")
    else:
        params = {}

    print(f"Executing '{tool_name}'...")
    result = await client.execute_tool(tool_name, params)
    client.process_result(result, tool_name)


def main():
    parser = argparse.ArgumentParser(
        description="Test client for C64 Ultimate MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Interactive mode
  %(prog)s --tool get_version           # Run single tool
  %(prog)s --tool capture_screen        # Capture screen with predefined params
  %(prog)s --tool read_memory --params '{"address": "C000", "length": 64}'
  %(prog)s --list                       # List all tools and exit
        """
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"C64 Ultimate device URL (default: {DEFAULT_URL})"
    )
    parser.add_argument(
        "--tool",
        help="Execute a specific tool non-interactively"
    )
    parser.add_argument(
        "--params",
        help="JSON parameters for the tool (use with --tool)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available tools and exit"
    )
    parser.add_argument(
        "--output-dir",
        default="test_output",
        help="Directory for saving binary output files (default: test_output)"
    )

    args = parser.parse_args()

    # Set environment variable for the server
    os.environ["C64U_URL"] = args.url

    client = MCPTestClient(args.url)
    client.output_dir = args.output_dir

    if args.list:
        # Just list tools
        async def list_only():
            await client.fetch_tools()
            print("\nAvailable Tools:")
            print("-" * 60)
            for tool in client.tools:
                predefined = " [P]" if tool.name in PREDEFINED_PARAMS else ""
                print(f"  {tool.name}{predefined}")
                print(f"    {tool.description[:70]}...")
            print("-" * 60)
            print(f"\nTotal: {len(client.tools)} tools")
            print("[P] = Predefined test parameters available")

        asyncio.run(list_only())

    elif args.tool:
        # Run single tool
        asyncio.run(run_single_tool(client, args.tool, args.params))

    else:
        # Interactive mode
        asyncio.run(client.run_interactive())


if __name__ == "__main__":
    main()
