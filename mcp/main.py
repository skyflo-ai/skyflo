import argparse
import logging

from config.server import mcp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description="Skyflo.ai MCP Server for cloud-native operations through natural language"
    )
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument(
        "--port", type=int, default=8888, help="Port to run the server on"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to bind the server to"
    )

    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        logger.info(
            f"Starting Skyflo.ai MCP Server on {args.host}:{args.port} with SSE transport"
        )
        mcp.settings.port = args.port
        mcp.settings.host = args.host
        mcp.run(transport="sse")
    else:
        logger.info(
            f"Starting Skyflo.ai MCP Server on {args.host}:{args.port} with HTTP transport"
        )
        mcp.settings.port = args.port
        mcp.settings.host = args.host
        mcp.run()


if __name__ == "__main__":
    main()
