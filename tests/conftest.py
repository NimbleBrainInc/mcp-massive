"""Test configuration and fixtures for massive MCP server."""

import pytest

from mcp_massive.server import mcp


@pytest.fixture
def mcp_server():
    """Return the MCP server instance."""
    return mcp
