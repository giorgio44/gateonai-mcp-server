#!/usr/bin/env python3
"""
GateOnAI MCP Server v1.0
═══════════════════════════════════════════════════════════════════
Model Context Protocol server for GateOnAI — Europe's AI tools
intelligence platform (https://www.gateonai.com)

Allows Claude, ChatGPT, and any MCP-compatible LLM to:
  - Search 2,756+ verified AI tools with semantic intelligence
  - Get step-by-step AI workflows for any profession/task
  - Compare AI tools head-to-head
  - Find GDPR-compliant and EU-hosted tools
  - Browse tools by category, pricing, or use case
  - Get curated prompts for any profession

Usage:
  python3 gateonai_mcp_server.py

Claude Desktop config (~/.claude/claude_desktop_config.json):
  {
    "mcpServers": {
      "gateonai": {
        "command": "python3",
        "args": ["/path/to/gateonai_mcp_server.py"]
      }
    }
  }

HTTP/SSE mode (for remote access):
  python3 gateonai_mcp_server.py --transport sse --port 8765
═══════════════════════════════════════════════════════════════════
"""

import asyncio
import sys
import json
import logging
from typing import Any
import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    ListToolsResult,
)
import mcp.server.stdio as stdio

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("gateonai-mcp")

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL = "https://www.gateonai.com"
API_BASE = f"{BASE_URL}/api"
TIMEOUT  = 15.0
HEADERS  = {
    "User-Agent": "GateOnAI-MCP/1.0 (https://www.gateonai.com/mcp)",
    "Accept":     "application/json",
}

# ── HTTP client ───────────────────────────────────────────────────────────────
async def _get(path: str, params: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        r = await client.get(f"{API_BASE}{path}", params=params or {})
        r.raise_for_status()
        return r.json()

async def _post(path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        r = await client.post(f"{API_BASE}{path}", json=body)
        r.raise_for_status()
        return r.json()

# ── Formatters ────────────────────────────────────────────────────────────────
def _fmt_tool(t: dict, verbose: bool = False) -> str:
    name     = t.get("name", "Unknown")
    tagline  = t.get("tagline", "")
    pricing  = t.get("pricing_type", "unknown")
    score    = t.get("gateonai_score")
    cat      = t.get("category_name", "")
    url      = t.get("website_url", "")
    slug     = t.get("slug", "")
    gdpr     = "✅ GDPR" if t.get("gdpr_compliant") else ""
    eu       = "🇪🇺 EU-hosted" if t.get("eu_hosted") else ""
    detail   = f"{BASE_URL}/tools/{slug}" if slug else url

    lines = [f"**{name}** ({pricing})"]
    if tagline:
        lines.append(f"  {tagline}")
    if cat:
        lines.append(f"  Category: {cat}")
    if score:
        lines.append(f"  GateOnAI Score: {score}/100")
    if gdpr or eu:
        lines.append(f"  {' · '.join(filter(None, [gdpr, eu]))}")
    if detail:
        lines.append(f"  → {detail}")

    if verbose:
        best_for = t.get("best_for")
        pros     = t.get("pros")
        if best_for:
            lines.append(f"  Best for: {best_for}")
        if pros:
            pros_str = pros if isinstance(pros, str) else " | ".join(pros[:3])
            lines.append(f"  Pros: {pros_str}")

    return "\n".join(lines)


def _fmt_workflow(data: dict) -> str:
    tools    = data.get("tools", [])
    meta     = data.get("meta", {})
    prof     = meta.get("profession", "your role")
    wflows   = data.get("workflows", [])

    lines = [f"# AI Workflow for: {prof}\n"]

    if wflows:
        for i, step in enumerate(wflows, 1):
            step_name = step.get("step", f"Step {i}")
            desc      = step.get("description", "")
            tool_name = step.get("tool_name", "")
            tool_url  = step.get("tool_url", "")
            lines.append(f"**Step {i}: {step_name}**")
            if desc:
                lines.append(f"  {desc}")
            if tool_name:
                entry = f"  Tool: {tool_name}"
                if tool_url:
                    entry += f" → {tool_url}"
                lines.append(entry)
            lines.append("")
    elif tools:
        for i, t in enumerate(tools, 1):
            why  = t.get("why_text", t.get("tagline", ""))
            name = t.get("name", "")
            slug = t.get("slug", "")
            url  = f"{BASE_URL}/tools/{slug}" if slug else t.get("website_url", "")
            lines.append(f"**Step {i}: {name}**")
            if why:
                lines.append(f"  {why}")
            lines.append(f"  → {url}")
            lines.append("")
    else:
        lines.append("No workflow steps found. Try a more specific query.")

    lines.append(f"\n🔗 Build your own workflow: {BASE_URL}/build-my-business-ai-workflow")
    return "\n".join(lines)


# ── MCP Server ────────────────────────────────────────────────────────────────
server = Server("gateonai")


@server.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(tools=[

        Tool(
            name="search_ai_tools",
            description=(
                "Search GateOnAI's database of 2,756+ verified AI tools. "
                "Use this to find AI tools by name, category, use case, or description. "
                "Returns tool names, descriptions, pricing, GateOnAI scores, and URLs. "
                "Example queries: 'video editing', 'code assistant', 'ChatGPT alternatives', "
                "'free AI writing tools', 'GDPR compliant AI tools for marketing'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — tool name, use case, or description"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category slug (e.g. 'writing', 'coding', 'image-generation')"
                    },
                    "pricing": {
                        "type": "string",
                        "enum": ["free", "freemium", "paid", "free_trial"],
                        "description": "Filter by pricing type"
                    },
                    "gdpr_only": {
                        "type": "boolean",
                        "description": "If true, return only GDPR-compliant tools"
                    },
                    "eu_hosted_only": {
                        "type": "boolean",
                        "description": "If true, return only EU-hosted tools"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 10, max: 24)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),

        Tool(
            name="get_ai_workflow",
            description=(
                "Generate a step-by-step AI workflow for any profession, role, or task. "
                "GateOnAI's workflow engine uses a compatibility graph of 4,093,220 tool "
                "connections to recommend the best tool sequence. "
                "Example: 'I'm a marketing manager who wants to create YouTube content', "
                "'freelance graphic designer building a client workflow', "
                "'startup founder who needs to automate customer support'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Describe your role, profession, or what you want to accomplish with AI"
                    }
                },
                "required": ["query"]
            }
        ),

        Tool(
            name="compare_ai_tools",
            description=(
                "Compare two AI tools head-to-head. Returns pricing, features, "
                "GateOnAI scores, pros/cons, and a recommendation. "
                "Example: compare ChatGPT vs Claude, Midjourney vs DALL-E, "
                "Jasper vs Copy.ai."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool1_slug": {
                        "type": "string",
                        "description": "Slug of the first tool (e.g. 'chatgpt', 'claude', 'midjourney')"
                    },
                    "tool2_slug": {
                        "type": "string",
                        "description": "Slug of the second tool"
                    }
                },
                "required": ["tool1_slug", "tool2_slug"]
            }
        ),

        Tool(
            name="get_tool_details",
            description=(
                "Get comprehensive details about a specific AI tool by slug. "
                "Returns full description, pricing, GateOnAI score breakdown, "
                "pros/cons, integrations, GDPR status, and related tools. "
                "Use this when a user asks about a specific tool."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "Tool slug (e.g. 'chatgpt', 'midjourney', 'notion-ai')"
                    }
                },
                "required": ["slug"]
            }
        ),

        Tool(
            name="get_trending_tools",
            description=(
                "Get the currently trending AI tools on GateOnAI, based on real "
                "user engagement data. Returns the most actively explored tools "
                "this week across all categories."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of trending tools to return (default: 10)",
                        "default": 10
                    }
                }
            }
        ),

        Tool(
            name="get_eu_gdpr_tools",
            description=(
                "Find AI tools that are GDPR-compliant or EU-hosted. "
                "Essential for European businesses, healthcare, legal, and "
                "any use case requiring data sovereignty. "
                "GateOnAI manually verifies every GDPR claim."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "standard": {
                        "type": "string",
                        "enum": ["gdpr", "eu_hosted"],
                        "description": "'gdpr' for GDPR-compliant tools, 'eu_hosted' for EU-based infrastructure",
                        "default": "gdpr"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 10)",
                        "default": 10
                    }
                }
            }
        ),

        Tool(
            name="get_prompts_for_profession",
            description=(
                "Get curated AI prompts for a specific profession from GateOnAI's "
                "Prompt Library of 16,000+ prompts across 45 professions. "
                "Returns ready-to-use prompts for ChatGPT, Claude, Gemini, and more. "
                "Professions include: marketer, developer, designer, writer, "
                "photographer, teacher, lawyer, doctor, entrepreneur, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "profession": {
                        "type": "string",
                        "description": "Profession slug (e.g. 'marketer', 'software-developer', 'content-creator')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of prompts to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["profession"]
            }
        ),

        Tool(
            name="get_site_stats",
            description=(
                "Get current statistics about the GateOnAI platform: "
                "total tools, categories, prompts, and tool compatibility connections."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),

    ])


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    try:
        if name == "search_ai_tools":
            return await _search_ai_tools(arguments)
        elif name == "get_ai_workflow":
            return await _get_ai_workflow(arguments)
        elif name == "compare_ai_tools":
            return await _compare_ai_tools(arguments)
        elif name == "get_tool_details":
            return await _get_tool_details(arguments)
        elif name == "get_trending_tools":
            return await _get_trending_tools(arguments)
        elif name == "get_eu_gdpr_tools":
            return await _get_eu_gdpr_tools(arguments)
        elif name == "get_prompts_for_profession":
            return await _get_prompts(arguments)
        elif name == "get_site_stats":
            return await _get_site_stats(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")]
            )
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error calling GateOnAI API: {str(e)}")]
        )


# ── Tool implementations ──────────────────────────────────────────────────────

async def _search_ai_tools(args: dict) -> CallToolResult:
    params = {
        "search": args.get("query", ""),
        "page_size": min(args.get("limit", 10), 24),
        "ordering": "-gateonai_score",
    }
    if args.get("category"):
        params["category__slug"] = args["category"]
    if args.get("pricing"):
        params["pricing_type"] = args["pricing"]
    if args.get("gdpr_only"):
        params["gdpr_compliant"] = "true"
    if args.get("eu_hosted_only"):
        params["eu_hosted"] = "true"

    data    = await _get("/tools/", params)
    results = data.get("results", [])
    count   = data.get("count", 0)

    if not results:
        return CallToolResult(content=[TextContent(type="text",
            text=f"No tools found for '{args.get('query')}'. Try a different search term."
        )])

    lines = [f"## GateOnAI Search: '{args.get('query')}'\n"]
    lines.append(f"Found {count} tools. Showing top {len(results)}:\n")
    for t in results:
        lines.append(_fmt_tool(t))
        lines.append("")

    lines.append(f"\n🔍 See all results: {BASE_URL}/browse?search={args.get('query', '').replace(' ', '+')}")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])


async def _get_ai_workflow(args: dict) -> CallToolResult:
    data = await _post("/workflow-ai/", {"query": args.get("query", "")})
    text = _fmt_workflow(data)
    return CallToolResult(content=[TextContent(type="text", text=text)])


async def _compare_ai_tools(args: dict) -> CallToolResult:
    slug1 = args.get("tool1_slug", "").lower().strip()
    slug2 = args.get("tool2_slug", "").lower().strip()

    data  = await _get(f"/compare/{slug1}/{slug2}/")

    t1    = data.get("tool1", {})
    t2    = data.get("tool2", {})
    rec   = data.get("recommendation", "")

    lines = [f"## {t1.get('name', slug1)} vs {t2.get('name', slug2)}\n"]
    lines.append("### Tool 1")
    lines.append(_fmt_tool(t1, verbose=True))
    lines.append("\n### Tool 2")
    lines.append(_fmt_tool(t2, verbose=True))

    if rec:
        lines.append(f"\n### 🏆 Recommendation\n{rec}")

    score1 = t1.get("gateonai_score", 0) or 0
    score2 = t2.get("gateonai_score", 0) or 0
    if score1 and score2:
        winner = t1.get("name") if score1 >= score2 else t2.get("name")
        lines.append(f"\n**GateOnAI Score Winner:** {winner} ({max(score1, score2)}/100)")

    lines.append(f"\n🔗 Full comparison: {BASE_URL}/compare/{slug1}/{slug2}")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])


async def _get_tool_details(args: dict) -> CallToolResult:
    slug = args.get("slug", "").lower().strip()
    data = await _get(f"/tools/{slug}/")

    lines = [f"## {data.get('name', slug)}\n"]
    lines.append(_fmt_tool(data, verbose=True))

    desc = data.get("description", "")
    if desc:
        lines.append(f"\n### Description\n{desc[:500]}{'...' if len(desc) > 500 else ''}")

    cons = data.get("cons")
    if cons:
        cons_str = cons if isinstance(cons, str) else " | ".join(cons[:3])
        lines.append(f"\n**Cons:** {cons_str}")

    integrations = data.get("integrations")
    if integrations:
        int_str = integrations if isinstance(integrations, str) else ", ".join(integrations[:5])
        lines.append(f"\n**Integrations:** {int_str}")

    faq = data.get("faq", [])
    if faq:
        lines.append("\n### Frequently Asked Questions")
        for f in faq[:3]:
            lines.append(f"**Q: {f.get('question')}**")
            lines.append(f"A: {f.get('answer')}\n")

    lines.append(f"\n🔗 Full details: {BASE_URL}/tools/{slug}")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])


async def _get_trending_tools(args: dict) -> CallToolResult:
    limit = min(args.get("limit", 10), 20)
    data  = await _get("/tools/trending/")

    tools = data if isinstance(data, list) else data.get("results", [])
    tools = tools[:limit]

    lines = ["## 🔥 Trending AI Tools on GateOnAI\n"]
    lines.append("Based on real user engagement data:\n")
    for i, t in enumerate(tools, 1):
        lines.append(f"{i}. {_fmt_tool(t)}")
        lines.append("")

    lines.append(f"\n🔗 See all trending: {BASE_URL}/browse?sort=trending")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])


async def _get_eu_gdpr_tools(args: dict) -> CallToolResult:
    standard = args.get("standard", "gdpr")
    limit    = min(args.get("limit", 10), 24)

    params = {
        "ordering": "-gateonai_score",
        "page_size": limit,
    }
    if standard == "eu_hosted":
        params["eu_hosted"] = "true"
        title = "🇪🇺 EU-Hosted AI Tools"
        subtitle = "Data centers physically located in the European Union"
    else:
        params["gdpr_compliant"] = "true"
        title = "🛡️ GDPR-Compliant AI Tools"
        subtitle = "Verified GDPR compliance — suitable for European businesses"

    if args.get("category"):
        params["category__slug"] = args["category"]

    data    = await _get("/tools/", params)
    results = data.get("results", [])
    count   = data.get("count", 0)

    lines = [f"## {title}\n{subtitle}\n"]
    lines.append(f"Found {count} verified tools. Showing top {len(results)}:\n")
    for t in results:
        lines.append(_fmt_tool(t))
        lines.append("")

    lines.append(f"\n🔗 Full EU/GDPR directory: {BASE_URL}/eu-ai-tools")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])


async def _get_prompts(args: dict) -> CallToolResult:
    profession = args.get("profession", "").lower().strip()
    limit      = min(args.get("limit", 5), 20)

    data    = await _get(f"/prompts/profession/{profession}/", {"page_size": limit})
    results = data.get("results", [])

    if not results:
        return CallToolResult(content=[TextContent(type="text",
            text=f"No prompts found for '{profession}'. Try: marketer, developer, designer, writer, photographer."
        )])

    lines = [f"## ✍️ AI Prompts for {profession.replace('-', ' ').title()}\n"]
    lines.append(f"From GateOnAI's library of 16,000+ curated prompts:\n")

    for i, p in enumerate(results[:limit], 1):
        title   = p.get("title", "")
        prompt  = p.get("prompt_text", "")
        tool    = p.get("tool_name", "")
        lines.append(f"### {i}. {title}")
        if tool:
            lines.append(f"*Tool: {tool}*")
        if prompt:
            lines.append(f"\n```\n{prompt[:300]}{'...' if len(prompt) > 300 else ''}\n```")
        lines.append("")

    lines.append(f"\n🔗 Full prompt library: {BASE_URL}/prompts/{profession}/")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])


async def _get_site_stats(args: dict) -> CallToolResult:
    data = await _get("/homepage/")
    stats = data.get("stats", {})

    lines = [
        "## 📊 GateOnAI Platform Statistics\n",
        f"🔧 **AI Tools:** {stats.get('tools_count', '2,756+')}+ verified & curated",
        f"📂 **Categories:** {stats.get('categories_count', 45)}",
        f"🔗 **Tool Connections:** {stats.get('connections_count', '4,093,220')+':,}' if isinstance(stats.get('connections_count'), int) else stats.get('connections_count', '4,093,220+')}",
        f"✍️ **Prompts:** 16,000+ across 45 professions",
        f"🛡️ **GDPR Tools:** 1,035+ verified",
        f"🇪🇺 **EU-Hosted Tools:** 7 verified",
        f"\n🌐 Platform: {BASE_URL}",
        f"📖 MCP Documentation: {BASE_URL}/mcp",
    ]
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])


# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    async with stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="gateonai",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )

def main_sync():
    """Synchronous entry point for pyproject.toml [project.scripts]."""
    asyncio.run(main())

if __name__ == "__main__":
    main_sync()
