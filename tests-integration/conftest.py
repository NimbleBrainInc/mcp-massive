"""Integration test configuration."""

import os

import pytest

from mcp_massive.server import mcp


@pytest.fixture
def mcp_server():
    """Return the MCP server instance."""
    return mcp


@pytest.fixture(autouse=True)
def require_massive_key():
    """Skip integration tests when MASSIVE_API_KEY is not set."""
    if not os.environ.get("MASSIVE_API_KEY"):
        pytest.skip("MASSIVE_API_KEY not set")
