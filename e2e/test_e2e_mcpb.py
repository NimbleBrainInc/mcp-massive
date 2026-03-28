"""End-to-end tests for MCPB bundle deployment."""

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
import requests
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pytest_httpserver import HTTPServer
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from .conftest import (
    BASE_IMAGE,
    BUNDLE_NAME,
    BUNDLE_VERSION,
    CONTAINER_PORT,
    PROJECT_ROOT,
)


def build_bundle(output_dir: Path) -> Path:
    """Build MCPB bundle with Linux-compatible deps for Docker testing."""
    deps_dir = PROJECT_ROOT / "deps"

    # Clean any stale macOS deps from prior local builds
    if deps_dir.exists():
        shutil.rmtree(deps_dir)

    try:
        # Vendor Linux deps using Docker (matches mcpb-python base image platform)
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{PROJECT_ROOT}:/work",
                "-w",
                "/work",
                "python:3.14-slim",
                "bash",
                "-c",
                "pip install --target /work/deps .",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Dep vendoring failed: {result.stderr}")

        # Pack the bundle
        bundle_path = output_dir / f"{BUNDLE_NAME}-v{BUNDLE_VERSION}.mcpb"
        result = subprocess.run(
            ["mcpb", "pack", ".", str(bundle_path)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Bundle build failed: {result.stderr}")

        if not bundle_path.exists():
            raise RuntimeError(f"Bundle not found at {bundle_path}")

        return bundle_path

    finally:
        # Always clean up deps/ so we don't leave Linux binaries in the project
        if deps_dir.exists():
            shutil.rmtree(deps_dir)


@pytest.fixture(scope="module")
def bundle_path():
    """Build the MCPB bundle once for all tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = build_bundle(Path(tmpdir))
        # Read bundle content to memory so it survives tmpdir cleanup
        content = path.read_bytes()
        yield path.name, content


@pytest.fixture(scope="module")
def bundle_server(bundle_path):
    """Serve the bundle over HTTP."""
    bundle_name, bundle_content = bundle_path

    # Start HTTP server on a random port
    server = HTTPServer(host="0.0.0.0", port=0)
    server.expect_request(f"/{bundle_name}").respond_with_data(
        bundle_content,
        content_type="application/octet-stream",
    )
    server.start()

    yield server

    server.stop()


@pytest.fixture(scope="module")
def mcpb_container(bundle_server, bundle_path):
    """Run the MCPB container."""
    bundle_name, _ = bundle_path
    bundle_url = f"http://host.docker.internal:{bundle_server.port}/{bundle_name}"

    container = (
        DockerContainer(BASE_IMAGE)
        .with_env("BUNDLE_URL", bundle_url)
        .with_bind_ports(CONTAINER_PORT, None)  # Random host port
        .with_kwargs(extra_hosts={"host.docker.internal": "host-gateway"})
    )

    container.start()

    try:
        # Wait for server to be ready (wait for uvicorn startup message)
        wait_for_logs(container, "Uvicorn running on", timeout=60)

        # Give uvicorn a moment to fully initialize
        time.sleep(1)

        # Get the mapped port
        host_port = container.get_exposed_port(CONTAINER_PORT)
        base_url = f"http://localhost:{host_port}"

        # Wait for health endpoint
        for _ in range(30):
            try:
                resp = requests.get(f"{base_url}/health", timeout=2)
                if resp.status_code == 200:
                    break
            except requests.RequestException:
                time.sleep(0.5)
        else:
            logs = container.get_logs()
            raise RuntimeError(f"Container not healthy. Logs: {logs}")

        yield base_url

    finally:
        container.stop()


def test_health_endpoint(mcpb_container):
    """Test that the health endpoint returns successfully."""
    base_url = mcpb_container

    response = requests.get(f"{base_url}/health", timeout=5)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_mcp_tools_list(mcpb_container):
    """Test that the MCP tools/list endpoint returns all expected tools."""
    base_url = mcpb_container

    async with streamablehttp_client(f"{base_url}/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            tools = tools_response.tools

            assert tools, "No tools returned from MCP server"

            tool_names = {tool.name for tool in tools}
            expected_tools = {
                "get_candles",
                "get_snapshot",
                "get_technical_indicator",
                "get_sec_filing",
                "get_sec_filing_section",
                "get_ticker_details",
                "get_top_movers",
            }

            assert expected_tools.issubset(tool_names), (
                f"Missing tools: {expected_tools - tool_names}"
            )

            for tool in tools:
                assert tool.name
                assert tool.description
                assert tool.inputSchema


@pytest.mark.asyncio
async def test_mcp_tool_call_without_api_key(mcpb_container):
    """Test calling a tool without API key returns graceful error."""
    base_url = mcpb_container

    async with streamablehttp_client(f"{base_url}/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "get_snapshot",
                {"ticker": "AAPL"},
            )

            assert result.content
            assert len(result.content) > 0

            # Server should return a JSON error (not crash)
            text_content = result.content[0].text
            data = json.loads(text_content)
            assert "error" in data
            assert "MASSIVE_API_KEY" in data["error"]
