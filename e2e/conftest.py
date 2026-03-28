"""E2E test configuration and fixtures."""

from pathlib import Path

# Test configuration
BASE_IMAGE = "docker.io/nimbletools/mcpb-python:3.14"
CONTAINER_PORT = 8000
BUNDLE_NAME = "mcp-massive"
BUNDLE_VERSION = "0.0.1"

PROJECT_ROOT = Path(__file__).parent.parent
