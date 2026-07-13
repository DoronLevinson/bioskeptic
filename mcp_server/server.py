import os

from mcp.server.fastmcp import FastMCP

from mcp_server import tools

mcp = FastMCP("bioskeptic")

# Register the shared tool functions as MCP tools (name + schema come from each function's signature/docstring).
for _fn in tools.ALL:
    mcp.tool()(_fn)


if __name__ == "__main__":
    # stdio is the default: the client (Claude Desktop / Code) launches this process locally and talks
    # over stdin/stdout — free, and it uses the user's OWN ANTHROPIC_API_KEY. Set MCP_TRANSPORT=streamable-http
    # to instead run a hosted HTTP endpoint.
    mcp.run(transport=os.environ.get("MCP_TRANSPORT", "stdio"))
