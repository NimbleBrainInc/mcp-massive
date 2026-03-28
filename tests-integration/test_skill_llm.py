"""
Smoke test: verify the LLM reads the skill resource and selects the correct tool.

Requires ANTHROPIC_API_KEY in environment.
"""

import os

import anthropic
import pytest
from fastmcp import Client

from mcp_massive.server import mcp


def get_anthropic_client() -> anthropic.Anthropic:
    token = os.environ.get("ANTHROPIC_API_KEY")
    if not token:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=token)


async def get_server_context() -> dict:
    """Extract instructions, skill content, and tool definitions from the MCP server."""
    async with Client(mcp) as client:
        init = await client.initialize()
        instructions = init.instructions

        resources = await client.list_resources()
        skill_text = ""
        for r in resources:
            if "skill://" in str(r.uri):
                contents = await client.read_resource(str(r.uri))
                skill_text = contents[0].text if hasattr(contents[0], "text") else str(contents[0])

        tools_list = await client.list_tools()
        tools = []
        for t in tools_list:
            tool_def = {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema,
            }
            tools.append(tool_def)

        return {
            "instructions": instructions,
            "skill": skill_text,
            "tools": tools,
        }


class TestSkillLLMInvocation:
    """Test that an LLM reads the skill and makes correct tool choices."""

    @pytest.mark.asyncio
    async def test_current_price_selects_snapshot(self):
        """When asked 'what's the current price?', the LLM should call get_snapshot, not get_candles.

        The skill explicitly teaches: use get_snapshot for current price + day stats.
        """
        ctx = await get_server_context()
        client = get_anthropic_client()

        system = (
            f"You are a financial data assistant.\n\n"
            f"## Server Instructions\n{ctx['instructions']}\n\n"
            f"## Skill Resource\n{ctx['skill']}"
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": "What's the current price of AAPL?"}],
            tools=[{"type": "custom", **t} for t in ctx["tools"]],
        )

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        assert len(tool_calls) > 0, "LLM did not call any tool"

        tool_name = tool_calls[0].name
        assert tool_name == "get_snapshot", (
            f"LLM called {tool_name} instead of get_snapshot. "
            "Skill instructs: use get_snapshot for current price."
        )
        assert tool_calls[0].input.get("ticker").upper() == "AAPL"

    @pytest.mark.asyncio
    async def test_risk_factors_selects_sec_filing(self):
        """When asked about risk factors, the LLM should start with get_sec_filing to find the filing.

        The skill workflow teaches: first get_sec_filing, then get_sec_filing_section.
        """
        ctx = await get_server_context()
        client = get_anthropic_client()

        system = (
            f"You are a financial data assistant.\n\n"
            f"## Server Instructions\n{ctx['instructions']}\n\n"
            f"## Skill Resource\n{ctx['skill']}"
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": "What are the risk factors for MSFT?"}],
            tools=[{"type": "custom", **t} for t in ctx["tools"]],
        )

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        assert len(tool_calls) > 0, "LLM did not call any tool"

        tool_name = tool_calls[0].name
        assert tool_name == "get_sec_filing", (
            f"LLM called {tool_name} instead of get_sec_filing. "
            "Skill instructs: first get_sec_filing to find the filing, then get_sec_filing_section."
        )

    @pytest.mark.asyncio
    async def test_technical_analysis_selects_indicator(self):
        """When asked for RSI, the LLM should call get_technical_indicator with rsi type."""
        ctx = await get_server_context()
        client = get_anthropic_client()

        system = (
            f"You are a financial data assistant.\n\n"
            f"## Server Instructions\n{ctx['instructions']}\n\n"
            f"## Skill Resource\n{ctx['skill']}"
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": "What's the RSI-14 for TSLA?"}],
            tools=[{"type": "custom", **t} for t in ctx["tools"]],
        )

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        assert len(tool_calls) > 0, "LLM did not call any tool"

        tool_name = tool_calls[0].name
        assert tool_name == "get_technical_indicator", (
            f"LLM called {tool_name} instead of get_technical_indicator. "
            "Skill instructs: use get_technical_indicator for SMA, EMA, RSI, MACD."
        )
        assert tool_calls[0].input.get("indicator_type") == "rsi"

    @pytest.mark.asyncio
    async def test_without_skill_may_choose_wrong_tool(self):
        """Without the skill, the LLM is more likely to pick the wrong tool.

        This is the control test. We don't assert failure (the model might still guess right),
        but we log the result for comparison.
        """
        ctx = await get_server_context()
        client = get_anthropic_client()

        # No skill content, just bare instructions
        system = "You are a financial data assistant."

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": "What are the risk factors for MSFT?"}],
            tools=[{"type": "custom", **t} for t in ctx["tools"]],
        )

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        if tool_calls:
            tool_name = tool_calls[0].name
            used_correct = tool_name == "get_sec_filing"
            print(f"\n  Without skill: LLM called {tool_name} (correct={used_correct})")
        else:
            print("\n  Without skill: LLM did not call any tool")
