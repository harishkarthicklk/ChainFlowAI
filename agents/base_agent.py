
import json
import sys
from pathlib import Path
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parent.parent


class MCPAgent:
    def __init__(self, name, server_name):
        self.name = name
        self.server_name = server_name
        self.stack = None
        self.session = None

    async def connect(self):
        server_file = ROOT / "mcp_servers" / f"{self.server_name}_server.py"

        if not server_file.exists():
            raise FileNotFoundError(
                f"MCP server file not found: {server_file}"
            )

        if self.session is not None:
            return

        stack = AsyncExitStack()
        await stack.__aenter__()
        self.stack = stack

        try:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=[
                    "-u",
                    "-m",
                    f"mcp_servers.{self.server_name}_server",
                ],
                cwd=str(ROOT),
            )

            read_stream, write_stream = (
                await stack.enter_async_context(
                    stdio_client(parameters)
                )
            )

            self.session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            await self.session.initialize()

            result = await self.session.list_tools()
            tool_names = [tool.name for tool in result.tools]

            print(
                f"[CONNECTED] {self.name} -> "
                f"{self.server_name} MCP"
            )
            print(f"[TOOLS] {', '.join(tool_names)}")

        except BaseException:
            self.session = None
            self.stack = None
            await stack.aclose()
            raise

    async def call_tool(self, tool_name, arguments):
        if self.session is None:
            raise RuntimeError(
                f"{self.name} is not connected to its MCP server."
            )

        result = await self.session.call_tool(
            tool_name,
            arguments=arguments,
        )

        if result.isError:
            messages = [
                item.text
                for item in result.content
                if hasattr(item, "text")
            ]
            raise RuntimeError(
                f"{self.name} tool error: " + " | ".join(messages)
            )

        output = []

        for item in result.content:
            if hasattr(item, "text"):
                try:
                    output.append(json.loads(item.text))
                except json.JSONDecodeError:
                    output.append(item.text)

        response = output[0] if len(output) == 1 else output

        print(f"\n[{self.name}] {tool_name}")
        print(json.dumps(response, indent=2, default=str))

        return response

    async def close(self):
        if self.stack is not None:
            stack = self.stack
            self.stack = None
            self.session = None
            await stack.aclose()
            print(f"[DISCONNECTED] {self.name}")
