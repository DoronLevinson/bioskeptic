from mcp.server.fastmcp import FastMCP

from mcp_server import tools

mcp = FastMCP("bioskeptic")

# Register the shared tool functions as MCP tools (name + schema come from each function's signature/docstring).
for _fn in tools.ALL:
    mcp.tool()(_fn)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
