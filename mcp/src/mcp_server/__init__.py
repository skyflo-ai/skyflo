"""
Skyflo.ai MCP Server - Open Source AI Agent for Cloud Native.
"""

from importlib import metadata as importlib_metadata


def get_version() -> str:
    try:
        return importlib_metadata.version(__name__)
    except importlib_metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"


__version__ = get_version()

__all__ = ["run"]
