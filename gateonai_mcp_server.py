import contextlib
#!/usr/bin/env python3
import asyncio, sys, os, re, logging, uuid, json, datetime
import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.types import Tool, TextContent, CallToolResult, ListToolsResult, Resource
from pydantic import AnyUrl
try:
    import redis.asyncio as aioredis
except ImportError:  # standalone installs (pip/uvx) do not need Redis
    aioredis = None
import mcp.server.stdio as stdio

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("gateonai-mcp")

# Redis (usage stats + resource subscriptions) is used only on the hosted gateonai.com server,
# where the service sets GATEONAI_MCP_REDIS=1. Every tool works without it.
REDIS_ENABLED = aioredis is not None and os.getenv("GATEONAI_MCP_REDIS", "") == "1"

SERVER_VERSION = "1.2.0"

# One typed output contract for every tool (2026-09-28). call_tool() fills structuredContent
# from the final text in ONE place, so no tool can drift from it; the text content is unchanged
# for clients that do not read structured output.
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "description": "Name of the tool that produced this result"},
        "markdown": {"type": "string", "description": "The full result as Markdown (same as the text content), including GateOnAI's disclaimer"},
        "links": {"type": "array", "items": {"type": "string"}, "description": "gateonai.com URLs referenced in the result, in order of appearance"},
        "is_error": {"type": "boolean", "description": "True if the tool could not complete the request"},
    },
    "required": ["tool", "markdown", "links", "is_error"],
    "additionalProperties": False,
}
_LINK_RE = re.compile(r"https://www\.gateonai\.com[^\s)\]>\"'`]*")  # bump here for every release (also pyproject.toml)

BASE_URL = "https://www.gateonai.com"
API_BASE = f"{BASE_URL}/api"
TIMEOUT  = 15.0
HEADERS  = {"User-Agent": "GateOnAI-MCP/1.0", "Accept": "application/json"}

async def _get(path, params=None):
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as c:
        r = await c.get(f"{API_BASE}{path}", params=params or {})
        r.raise_for_status(); return r.json()

async def _post(path, body):
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as c:
        r = await c.post(f"{API_BASE}{path}", json=body)
        r.raise_for_status(); return r.json()

WORKFLOW_TIMEOUT = 45.0  # /workflow-ai/ plans steps with Groq for uncached goals; can exceed 15 s (2026-09-28)

async def _post_slow(path, body):
    async with httpx.AsyncClient(timeout=WORKFLOW_TIMEOUT, headers=HEADERS) as c:
        r = await c.post(f"{API_BASE}{path}", json=body)
        r.raise_for_status(); return r.json()

def _fmt(t, v=False):
    lines = [f"**{t.get('name','?')}** ({t.get('pricing_type','?')})"]
    if t.get('tagline'): lines.append(f"  {t['tagline']}")
    if t.get('category_name'): lines.append(f"  Category: {t['category_name']}")
    if t.get('gateonai_score'): lines.append(f"  Score: {t['gateonai_score']}/100")
    tags = " · ".join(filter(None,["✅ GDPR" if t.get('gdpr_compliant') else "","🇪🇺 EU" if t.get('eu_hosted') else ""]))
    if tags: lines.append(f"  {tags}")
    slug = t.get('slug','')
    if slug: lines.append(f"  → {BASE_URL}/tools/{slug}")
    if v:
        if t.get('best_for'): lines.append(f"  Best for: {t['best_for']}")
        if t.get('pros'):
            p = t['pros'] if isinstance(t['pros'],str) else " | ".join(t['pros'][:3])
            lines.append(f"  Pros: {p}")
    return "\n".join(lines)

server = Server("gateonai", version=SERVER_VERSION)

# ── Usage analytics (George's own dashboard, not a third-party metering
# service - built after declining an outside MCP-metering vendor pitch) ──
# Simple, strictly non-personal counters: which tool was called, how many
# times, per day, plus lifetime totals per tool. No IPs, no session or
# client identifiers, nothing that could tie a call to a specific person
# or organisation - purely aggregate usage volume, so George can see
# genuine demand before deciding whether the MCP server is popular enough
# to ever be worth building anything further around (rate limiting,
# per-caller quotas, eventually paid tiers if it ever made sense) - all
# decisions he can make with real data instead of guessing.
_stats_redis = None

async def _get_stats_redis():
    global _stats_redis
    if _stats_redis is None:
        _stats_redis = aioredis.from_url("redis://127.0.0.1:6379/1")
    return _stats_redis

async def _record_tool_call(name: str) -> None:
    if not REDIS_ENABLED:
        return
    """Fire-and-forget usage counter increment. Never raises - a stats
    recording failure must never be allowed to break the actual tool
    call it's trying to measure."""
    try:
        r = await _get_stats_redis()
        today = datetime.date.today().isoformat()
        pipe = r.pipeline()
        # Per-day, per-tool call count - 90 day TTL, enough for meaningful
        # trend history without keys accumulating forever.
        pipe.incr(f"mcp:stats:daily:{today}:{name}")
        pipe.expire(f"mcp:stats:daily:{today}:{name}", 90 * 86400)
        # Per-day total across all tools combined.
        pipe.incr(f"mcp:stats:daily:{today}:_total")
        pipe.expire(f"mcp:stats:daily:{today}:_total", 90 * 86400)
        # Permanent monthly counters (no expiry) - daily counters only
        # keep 90 days of history, which isn't enough for genuine
        # month/year views over time. These accumulate indefinitely so
        # the dashboard can show real month and year history as it
        # builds up, not just a recent window.
        month_key = today[:7]  # "YYYY-MM"
        pipe.incr(f"mcp:stats:monthly:{month_key}:{name}")
        pipe.incr(f"mcp:stats:monthly:{month_key}:_total")
        pipe.sadd("mcp:stats:known_months", month_key)
        # Lifetime total per tool - no expiry, this is the running total.
        pipe.incr(f"mcp:stats:lifetime:{name}")
        pipe.incr("mcp:stats:lifetime:_total")
        # Track which tools have ever actually been called, for the
        # dashboard to know the full set of names to show (including
        # ones with zero calls today).
        pipe.sadd("mcp:stats:known_tools", name)
        # Record first-seen / last-seen timestamps for this tool.
        now_iso = datetime.datetime.utcnow().isoformat()
        pipe.setnx(f"mcp:stats:first_seen:{name}", now_iso)
        pipe.set(f"mcp:stats:last_seen:{name}", now_iso)
        await pipe.execute()
    except Exception as e:
        logger.warning(f"MCP usage stats recording failed (non-fatal): {e}")

# ── Live resource subscriptions (push notifications over SSE) ──────────
# In-memory registry: resource URI string -> set of active ServerSession
# objects currently subscribed to it. Lives only inside this single
# process (systemd service), which is fine since MCP subscriptions are
# inherently tied to a live, open session/connection anyway - there is
# no durable "notify me even if I'm offline" concept in MCP itself.
_subscriptions: dict[str, set] = {}

AVAILABLE_RESOURCES = [
    Resource(
        uri="gateonai://tools/new",
        name="Newly Approved AI Tools",
        description=(
            "Live feed of AI tools newly approved on GateOnAI. Subscribe to "
            "this resource to receive a push notification the moment a new "
            "tool passes editorial review (checked every 6 hours)."
        ),
        mimeType="application/json",
    ),
]


@server.list_resources()
async def list_resources():
    return AVAILABLE_RESOURCES


@server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    if str(uri) == "gateonai://tools/new":
        data = await _get("/tools/", {"ordering": "-id", "limit": 10})
        return json.dumps(data.get("results", []), indent=2)
    raise ValueError(f"Unknown resource URI: {uri}")


@server.subscribe_resource()
async def subscribe_resource(uri: AnyUrl) -> None:
    session = server.request_context.session
    _subscriptions.setdefault(str(uri), set()).add(session)
    logger.warning(f"MCP client subscribed to {uri} (now {len(_subscriptions[str(uri)])} subscriber(s))")


@server.unsubscribe_resource()
async def unsubscribe_resource(uri: AnyUrl) -> None:
    session = server.request_context.session
    _subscriptions.get(str(uri), set()).discard(session)
    logger.warning(f"MCP client unsubscribed from {uri}")


async def _redis_subscription_listener():
    if not REDIS_ENABLED:
        return
    """
    Background task: listens on Redis pub/sub for events published by the
    Django/Celery side (e.g. when the scout-new-ai-tools task approves a
    new tool), then pushes a resources/updated notification to every
    currently-subscribed SSE session for the matching resource URI.
    Runs for the lifetime of the MCP server process.
    """
    channel_to_uri = {"gateonai:mcp:new_tool": "gateonai://tools/new"}
    while True:
        try:
            redis_client = aioredis.from_url("redis://127.0.0.1:6379/1")
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(*channel_to_uri.keys())
            logger.warning(f"MCP Redis subscription listener connected, watching: {list(channel_to_uri.keys())}")
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                channel = message["channel"]
                channel = channel.decode() if isinstance(channel, bytes) else channel
                uri = channel_to_uri.get(channel)
                if not uri:
                    continue
                sessions = _subscriptions.get(uri, set())
                if not sessions:
                    continue
                dead = set()
                for session in list(sessions):
                    try:
                        await session.send_resource_updated(AnyUrl(uri))
                    except Exception:
                        dead.add(session)
                for d in dead:
                    sessions.discard(d)
                logger.warning(f"Pushed resources/updated for {uri} to {len(sessions)} subscriber(s)")
        except Exception as e:
            logger.warning(f"MCP Redis listener error, retrying in 5s: {e}")
            await asyncio.sleep(5)

async def _list_tools_raw():
    # Fetch live site stats so the tool descriptions AI agents read never
    # go stale - fixed 2026-08-22 after finding hardcoded numbers here
    # (2,756 tools, 4,093,220 connections, 16,000 prompts across 45
    # professions) that had already drifted from the real, current
    # figures (2,886+ tools, 19,686+ prompts across 57 professions).
    # Falls back to the last-known-good figures if the API call fails,
    # rather than crashing tool discovery entirely.
    try:
        _home = await _get("/homepage/")
        _pstats = await _get("/prompts/stats/")
        tool_count = _home.get("stats", {}).get("tools_count", 2886)
        connections_count = _home.get("stats", {}).get("connections_count", 4100000)
        prompt_count = _pstats.get("total_prompts", 19686)
        profession_count = _pstats.get("total_professions", 57)
    except Exception:
        tool_count, connections_count, prompt_count, profession_count = 2886, 4100000, 19686, 57
    try:
        _wflist = await _get("/workflows/dynamic/")
        workflow_count = _wflist.get("total", 2627)
    except Exception:
        workflow_count = 2627
    return ListToolsResult(tools=[
        Tool(
            name="search_ai_tools",
            title="Search AI Tools",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": True},
            description=f"Search GateOnAI's database of {tool_count:,}+ verified AI tools. Find tools by name, use case, category, pricing model, or GDPR compliance status. Returns tool names, descriptions, pricing, GateOnAI scores, and direct URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term — tool name, use case, or description. Examples: 'video editing', 'code assistant', 'ChatGPT alternatives'"},
                    "category": {"type": "string", "description": "Filter by category slug. Examples: 'writing', 'coding', 'image-generation', 'video', 'marketing'"},
                    "pricing": {"type": "string", "enum": ["free", "freemium", "paid", "free_trial"], "description": "Filter by pricing model: free, freemium, paid, or free_trial"},
                    "gdpr_only": {"type": "boolean", "description": "Set to true to return only GDPR-compliant tools suitable for European businesses"},
                    "eu_hosted_only": {"type": "boolean", "description": "Set to true to return only tools hosted on EU infrastructure"},
                    "limit": {"type": "integer", "default": 10, "description": "Number of results to return (default: 10, max: 24)"}
                },
                "required": ["query"]
            },
        ),
        Tool(
            name="get_ai_workflow",
            title="Get AI Workflow",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": True},
            description=f"Generate a step-by-step AI workflow for any profession, role, or business task. Uses GateOnAI's compatibility graph of {connections_count:,} tool connections to recommend the optimal tool sequence.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Describe your role, profession, or goal. Examples: 'freelance graphic designer building a client workflow', 'startup founder automating customer support', 'marketing manager creating YouTube content'"}
                },
                "required": ["query"]
            },
        ),
        Tool(
            name="compare_ai_tools",
            title="Compare AI Tools",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": True},
            description="Compare two AI tools head-to-head. Returns pricing, features, GateOnAI scores, pros/cons, and a recommendation on which tool to choose.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool1_slug": {"type": "string", "description": "URL slug of the first tool to compare. Examples: 'chatgpt', 'claude', 'midjourney', 'jasper'"},
                    "tool2_slug": {"type": "string", "description": "URL slug of the second tool to compare. Examples: 'gemini', 'dall-e', 'copy-ai', 'notion-ai'"}
                },
                "required": ["tool1_slug", "tool2_slug"]
            },
        ),
        Tool(
            name="get_tool_details",
            title="Get Tool Details",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": True},
            description="Get comprehensive details about a specific AI tool by its URL slug. Returns full description, pricing, GateOnAI score breakdown, pros/cons, integrations, GDPR status, and FAQ.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "URL slug of the AI tool. Examples: 'chatgpt', 'midjourney', 'notion-ai', 'github-copilot', 'claude'"}
                },
                "required": ["slug"]
            },
        ),
        Tool(
            name="get_trending_tools",
            title="Get Trending Tools",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": False},
            description="Get the currently trending AI tools on GateOnAI based on real user engagement data. Returns the most actively explored tools this week across all categories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10, "description": "Number of trending tools to return (default: 10, max: 20)"}
                }
            },
        ),
        Tool(
            name="get_eu_gdpr_tools",
            title="Get EU and GDPR Tools",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": True},
            description="Find AI tools that are GDPR-compliant or EU-hosted. Essential for European businesses, healthcare, legal, and any use case requiring data sovereignty. All compliance data is manually verified by GateOnAI.",
            inputSchema={
                "type": "object",
                "properties": {
                    "standard": {"type": "string", "enum": ["gdpr", "eu_hosted"], "default": "gdpr", "description": "Compliance standard: 'gdpr' for GDPR-compliant tools, 'eu_hosted' for tools with EU-based infrastructure"},
                    "category": {"type": "string", "description": "Optional category filter. Examples: 'writing', 'coding', 'marketing', 'legal'"},
                    "limit": {"type": "integer", "default": 10, "description": "Number of results to return (default: 10, max: 24)"}
                }
            },
        ),
        Tool(
            name="get_prompts_for_profession",
            title="Get Prompts for Profession",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": True},
            description=f"Get curated, ready-to-use AI prompts for a specific profession from GateOnAI's library of {prompt_count:,}+ prompts across {profession_count} professions. Works with ChatGPT, Claude, Gemini, and other LLMs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "profession": {"type": "string", "description": "Profession slug. Examples: 'marketer', 'software-developer', 'designer', 'writer', 'content-creator', 'photographer', 'teacher', 'lawyer', 'doctor', 'entrepreneur'"},
                    "limit": {"type": "integer", "default": 5, "description": "Number of prompts to return (default: 5, max: 20)"}
                },
                "required": ["profession"]
            },
        ),
        Tool(
            name="get_site_stats",
            title="Get Site Statistics",
            annotations={"readOnlyHint": True, "openWorldHint": False, "destructiveHint": False, "idempotentHint": True},
            description="Get current live statistics about the GateOnAI platform including total verified tools, categories, tool compatibility connections, and prompt library size.",
            inputSchema={
                "type": "object",
                "properties": {}
            },
        ),
        Tool(
            name="get_compatible_tools",
            title="Get Compatible AI Tools",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": True},
            description=f"Find AI tools that genuinely connect with a given tool, based on GateOnAI's IO-Compatibility Graph - a real, computed structural match between what one tool outputs and what another accepts as input (text, image, audio, video, code, etc.), not a category-similarity guess. Answers questions like 'what tools work well with ChatGPT' or 'what can I feed ChatGPT's output into'. Backed by {connections_count:,}+ real computed connections across the platform.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "URL slug of the AI tool to find connections for. Examples: 'chatgpt', 'midjourney', 'claude'"},
                    "limit": {"type": "integer", "default": 8, "description": "Number of connected tools to return (default: 8, max: 20)"}
                },
                "required": ["slug"]
            },
        ),
        Tool(
            name="find_ai_pipeline",
            title="Find AI Tool Pipeline (Input to Output)",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": False},
            description="Find a real, structurally computed sequence of AI tools that gets you from one type of content to another - e.g. audio to a finished blog post, or a single image to a full video. Powered by GateOnAI's IO-Compatibility Graph combined with a PostgreSQL recursive path-finding engine (not a guess, a template, or an LLM improvising) - each step is a real tool whose actual output type matches the next tool's actual input type, verified against real tagged data. Returns multiple ranked alternative pipelines, each scored on tool quality and path length, so you can compare a fast 2-step option against a more thorough 4-step one. Valid content types: text, image, audio, video, data, url, code, pdf, email, social_post, prompt, file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_type": {"type": "string", "enum": ["text","image","audio","video","data","url","code","pdf","email","social_post","prompt","file"], "description": "The type of content you are starting with"},
                    "goal_type": {"type": "string", "enum": ["text","image","audio","video","data","url","code","pdf","email","social_post","prompt","file"], "description": "The type of content you want to end up with"},
                    "max_steps": {"type": "integer", "default": 4, "description": "Maximum number of tools in the chain (2-6, default 4)"},
                    "alternatives": {"type": "integer", "default": 3, "description": "Number of alternative pipelines to return (1-5, default 3)"},
                    "free_only": {"type": "boolean", "default": False, "description": "If true, only return pipelines where every single tool in the chain is free or freemium"},
                },
                "required": ["start_type", "goal_type"]
            },
        ),
        Tool(
            name="whats_new",
            title="What's New on GateOnAI",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": False},
            description="See real AI tools recently added to GateOnAI - based on genuine addition timestamps, not a guess or a static list. Optionally filter by category. Useful for staying current on new tool launches or checking what's new in a specific space (e.g. new AI Agents tools this week).",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "default": 7, "description": "How many days back to look (1-30, default 7)"},
                    "category": {"type": "string", "description": "Optional category slug to filter by, e.g. 'ai-agents', 'marketing', 'design'. Omit to see all categories."},
                },
                "required": []
            },
        ),
        Tool(
            name="find_similar_by_philosophy",
            title="Find Conceptually Similar AI Tools",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": True},
            description="Find AI tools that are conceptually or philosophically similar to a given tool - based on real semantic embedding similarity of each tool's name and tagline (MiniLM), not just shared category. Different from get_compatible_tools, which uses the structural IO-Compatibility Graph (real input/output matching) rather than meaning-based similarity. Use this for 'tools like X' questions, get_compatible_tools for 'what connects to X' questions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "URL slug of the AI tool to find similar tools for. Examples: 'chatgpt', 'midjourney', 'notion'"},
                    "limit": {"type": "integer", "default": 8, "description": "Number of similar tools to return (default: 8, max: 20)"}
                },
                "required": ["slug"]
            },
        ),
        Tool(
            name="get_market_landscape",
            title="Get AI Category Market Landscape",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": True},
            description="A real, computed statistical snapshot of one GateOnAI category: live tool count, real GateOnAI Score distribution (average/median/min/max) and current top-scoring tools. Every number is computed directly from live catalog data at request time - never a prediction, estimate, or industry-wide claim beyond what GateOnAI itself catalogs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category slug, e.g. 'ai-agents', 'design', 'marketing', 'writing-assistant'. Use search_ai_tools or browse to find valid category slugs if unsure."},
                },
                "required": ["category"]
            },
        ),
        Tool(
            name="match_prompt_to_task",
            title="Match a Prompt to My Task",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": False},
            description="Given a free-text description of a task (e.g. 'write a cold email to a client'), finds the best-matching existing prompt(s) from GateOnAI's verified prompt library using real BM25 full-text search - not a semantic guess or an invented relevance score. Each result includes the actual prompt text, which tool it's designed for, and the profession it comes from.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Free-text description of the task, e.g. 'write a cold email to a client' or 'summarize a legal contract'"},
                    "limit": {"type": "integer", "default": 5, "description": "Number of matching prompts to return (1-10, default 5)"},
                },
                "required": ["task"]
            },
        ),
        Tool(
            name="get_workflow_template",
            title="Get Pre-Built Workflow Template",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": True},
            description=f"Get one of GateOnAI's {workflow_count:,}+ pre-built, ready-made AI workflows for a specific profession - a deterministic, ordered sequence of steps each matched to a real tool by category and GateOnAI Score, regenerated live from current tool data. Different from get_ai_workflow: this returns an existing, curated template for a known profession rather than generating a new custom one from free text - faster and more consistent for common roles.",
            inputSchema={
                "type": "object",
                "properties": {
                    "profession": {"type": "string", "description": "Profession slug. Examples: 'blogger', 'general-contractor', 'marketing-manager', 'software-developer', '3d-artist'. If unsure of the exact slug, use get_ai_workflow instead with a free-text description."}
                },
                "required": ["profession"]
            },
        ),
        Tool(
            name="build_workflow_board",
            title="Build AI Workflow Board",
            annotations={"readOnlyHint": False, "openWorldHint": True, "destructiveHint": False, "idempotentHint": False},
            description="Turn a goal described in plain language into a shareable GateOnAI Workbench board: real tools from the GateOnAI catalog, connected step by step when they form a workflow. Returns the steps and a public link the user can open, share or clone into their own Workbench (free, no account). Boards created this way are never indexed by search engines.",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "What the user wants to achieve, e.g. 'turn podcast episodes into blog posts and short social clips'"},
                },
                "required": ["goal"],
            },
        ),
        Tool(
            name="analyze_ai_stack",
            title="Analyze AI Tool Stack",
            annotations={"readOnlyHint": True, "openWorldHint": True, "destructiveHint": False, "idempotentHint": True},
            description="Automated observations about a set of AI tools (2-40 GateOnAI tool slugs): tools not currently listed, category overlaps and data connections found in GateOnAI's IO-compatibility graph. Observations from GateOnAI data only - not recommendations and not judgments about any provider.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_slugs": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 40, "description": "GateOnAI tool slugs, e.g. ['chatgpt', 'elevenlabs', 'opus-clip'] (slugs appear in search results and tool URLs)"},
                },
                "required": ["tool_slugs"],
            },
        ),
    ])

@server.list_tools()
async def list_tools():
    """Every tool declares the same output contract (OUTPUT_SCHEMA), filled in call_tool()."""
    result = await _list_tools_raw()
    for t in result.tools:
        t.outputSchema = OUTPUT_SCHEMA
    return result


async def _call_tool_impl(name, arguments):
    try:
        if name == "search_ai_tools":
            query = arguments.get("query", "")
            limit = min(arguments.get("limit", 10), 24)
            has_filters = any(arguments.get(k) for k in ("category", "pricing", "gdpr_only", "eu_hosted_only"))
            # Fixed 2026-08-22: this used plain keyword ?search= matching,
            # which noticeably under-performs GateOnAI's own MiniLM-based
            # semantic search (e.g. "remove background noise from podcast"
            # keyword-matched on "remove"/"background" independently and
            # surfaced a generic noise-generator tool ahead of the actual
            # best match, Cleanvoice AI, a purpose-built podcast editor).
            # The semantic endpoint only accepts a free-text query, no
            # filters - so use it for genuine natural-language queries
            # (the common case), and fall back to the filterable keyword
            # endpoint whenever category/pricing/gdpr/eu_hosted filters
            # are actually requested, since semantic search can't apply
            # them at all.
            if has_filters:
                p = {"search": query, "page_size": limit, "ordering": "-gateonai_score"}
                if arguments.get("category"): p["category__slug"] = arguments["category"]
                if arguments.get("pricing"):  p["pricing_type"] = arguments["pricing"]
                if arguments.get("gdpr_only"): p["gdpr_compliant"] = "true"
                if arguments.get("eu_hosted_only"): p["eu_hosted"] = "true"
                d = await _get("/tools/", p)
                r = d.get("results", [])
                count = d.get("count", len(r))
                mode_note = ""
            else:
                d = await _post("/semantic-search/", {"query": query})
                r = (d.get("results") or [])[:limit]
                count = len(r)
                mode_note = " (semantic match)"
            if not r:
                return CallToolResult(content=[TextContent(type="text",text=f"No tools found for '{query}'.")])
            lines = [f"## Search: '{query}' — {count} results{mode_note}\n"]
            for t in r: lines.append(_fmt(t)); lines.append("")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "get_ai_workflow":
            d = await _post_slow("/workflow-ai/", {"query":arguments.get("query","")})
            tools=d.get("tools",[]); wflows=d.get("workflows",[]); prof=d.get("meta",{}).get("profession","your role")
            lines=[f"# AI Workflow: {(arguments.get('query') or prof)[:80]}\n"]
            src = wflows or tools
            for i,s in enumerate(src,1):
                n=s.get("step",s.get("name",f"Step {i}")); desc=s.get("description",s.get("why_text",s.get("tagline","")))
                lines.append(f"**Step {i}: {n}**")
                if desc: lines.append(f"  {desc}")
                url=s.get("tool_url",""); slug=s.get("slug","")
                if url: lines.append(f"  → {url}")
                elif slug: lines.append(f"  → {BASE_URL}/tools/{slug}")
                lines.append("")
            lines.append(f"🔗 {BASE_URL}/build-my-business-ai-workflow")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "build_workflow_board":
            goal = str(arguments.get("goal", "")).strip()[:400]
            if len(goal) < 8:
                return CallToolResult(content=[TextContent(type="text", text="Please describe the goal in a bit more detail (at least a short sentence).")])
            d = await _post_slow("/workflow-ai/", {"query": goal})
            if d.get("needs_clarification"):
                opts = ", ".join(o.get("label", "") for o in (d.get("clarification_options") or []))
                return CallToolResult(content=[TextContent(type="text", text=f"The goal is too broad to build a workflow. {d.get('clarification_question', '')} Options: {opts}. Call build_workflow_board again with a more specific goal.")])
            steps = [s for s in (d.get("tools") or []) if s.get("slug")][:6]
            if not steps:
                return CallToolResult(content=[TextContent(type="text", text=f"No suitable tools were found in the GateOnAI catalog for: {goal}")])
            is_wf = d.get("is_workflow") is True
            blocks = [{"id": f"b{i}", "x": 80 + i * 300, "y": 220, "tool_slug": s["slug"], "tool_name": s.get("name", s["slug"]),
                       "tool_logo": s.get("logo_url") or "", "website_url": s.get("visit_url") or "", "pricing_type": s.get("pricing_type"),
                       "category": None, "note": "", "groupId": None} for i, s in enumerate(steps)]
            conns = [{"id": f"c{i}", "from": f"b{i-1}", "to": f"b{i}"} for i in range(1, len(blocks))] if is_wf else []
            title = (goal[0].upper() + goal[1:])[:80]
            saved = await _post("/workbench/save/", {"blocks": blocks, "connections": conns, "groups": [], "notes": [],
                                                     "checklists": [], "title": title, "source": "mcp"})
            url = f"{BASE_URL}{saved.get('url', '')}" if saved.get("id") else ""
            lines = [f"# Workflow board: {saved.get('title') or title}\n"]
            for i, s in enumerate(steps, 1):
                lines.append(f"**Step {i}: {s.get('action_label') or s.get('name')}** - {s.get('name')}")
                if s.get("why_text"): lines.append(f"  {s['why_text']}")
                lines.append(f"  → {BASE_URL}/tools/{s['slug']}")
            if url:
                lines.append(f"\n🔗 Open, share or clone this board (free, no account): {url}")
            else:
                lines.append(f"\n(The board could not be saved right now. Build it interactively at {BASE_URL}/workbench)")
            lines.append(f"\n_Generated automatically from GateOnAI catalog data. Tool availability, features and pricing change often - verify with each provider. Terms: {BASE_URL}/terms_")
            return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])
        elif name == "analyze_ai_stack":
            slugs = [str(s).strip().lower() for s in (arguments.get("tool_slugs") or []) if str(s).strip()][:40]
            if len(slugs) < 2:
                return CallToolResult(content=[TextContent(type="text", text="Provide at least 2 GateOnAI tool slugs.")])
            d = await _get("/tools/analyze-stack/", {"slugs": ",".join(slugs)})
            names = {t["slug"]: t["name"] for t in d.get("tools_found", [])}
            lines = ["# Stack observations (GateOnAI data)\n", "_Automated observations - not recommendations and not judgments about any provider._\n"]
            nf = d.get("tools_not_found") or []
            if nf: lines.append("**Not currently listed in the GateOnAI catalog:** " + ", ".join(nf))
            for o in d.get("category_overlaps") or []:
                lines.append(f"- {len(o['tools'])} tools in {o['category']}: " + ", ".join(t['name'] for t in o['tools']) + " (depending on use, you may not need all of them)")
            edges = sorted(d.get("stack_connections") or [], key=lambda e: e.get("weight", 0), reverse=True)[:8]
            if edges:
                lines.append("\n**Data connections in GateOnAI's compatibility graph:**")
                for e in edges:
                    lines.append(f"- {names.get(e['from'], e['from'])} → {names.get(e['to'], e['to'])} ({', '.join((e.get('shared_types') or [])[:3])})")
                lines.append("_A missing connection does not mean two tools cannot work together: the graph keeps only each tool's strongest links._")
            lines.append(f"\n🔗 Explore and connect these tools visually: {BASE_URL}/workbench")
            lines.append(f"\n_Provided as is, for general information only, without any warranty; not professional or purchasing advice. Verify with each provider. Terms: {BASE_URL}/terms_")
            return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])
        elif name == "compare_ai_tools":
            s1=arguments.get("tool1_slug","").lower().strip(); s2=arguments.get("tool2_slug","").lower().strip()
            d=await _get(f"/compare/{s1}/{s2}/")
            t1=d.get("tool1",{}); t2=d.get("tool2",{})
            lines=[f"## {t1.get('name',s1)} vs {t2.get('name',s2)}\n### Tool 1\n{_fmt(t1,True)}\n### Tool 2\n{_fmt(t2,True)}"]
            if d.get("recommendation"): lines.append(f"\n### 🏆 Recommendation\n{d['recommendation']}")
            sc1=t1.get("gateonai_score",0) or 0; sc2=t2.get("gateonai_score",0) or 0
            if sc1 and sc2: lines.append(f"\n**Winner:** {t1.get('name') if sc1>=sc2 else t2.get('name')} ({max(sc1,sc2)}/100)")
            lines.append(f"\n🔗 {BASE_URL}/compare/{s1}/{s2}")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "get_tool_details":
            slug=arguments.get("slug","").lower().strip(); d=await _get(f"/tools/{slug}/")
            lines=[f"## {d.get('name',slug)}\n",_fmt(d,True)]
            desc=d.get("description","")
            if desc: lines.append(f"\n### Description\n{desc[:500]}{'...' if len(desc)>500 else ''}")
            if d.get("cons"):
                c=d["cons"] if isinstance(d["cons"],str) else " | ".join(d["cons"][:3])
                lines.append(f"\n**Cons:** {c}")
            faq=d.get("faq",[])
            if faq:
                lines.append("\n### FAQ")
                for f in faq[:3]: lines.append(f"**Q: {f.get('question')}**\nA: {f.get('answer')}\n")
            lines.append(f"\n🔗 {BASE_URL}/tools/{slug}")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "get_trending_tools":
            d=await _get("/tools/trending/")
            tools=(d if isinstance(d,list) else d.get("results",[]))[:min(arguments.get("limit",10),20)]
            lines=["## 🔥 Trending AI Tools\n"]
            for i,t in enumerate(tools,1): lines.append(f"{i}. {_fmt(t)}\n")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "get_eu_gdpr_tools":
            std=arguments.get("standard","gdpr")
            p={"ordering":"-gateonai_score","page_size":min(arguments.get("limit",10),24)}
            if std=="eu_hosted": p["eu_hosted"]="true"; title="🇪🇺 EU-Hosted AI Tools"
            else: p["gdpr_compliant"]="true"; title="🛡️ GDPR-Compliant AI Tools"
            if arguments.get("category"): p["category__slug"]=arguments["category"]
            d=await _get("/tools/",p); r=d.get("results",[])
            lines=[f"## {title} — {d.get('count',0)} found\n"]
            for t in r: lines.append(_fmt(t)); lines.append("")
            lines.append(f"\n🔗 {BASE_URL}/eu-ai-tools")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "get_prompts_for_profession":
            prof=arguments.get("profession","").lower().strip()
            d=await _get("/prompts/",{"profession":prof,"page_size":min(arguments.get("limit",5),20)})
            r=d.get("results",[])
            if not r: return CallToolResult(content=[TextContent(type="text",text=f"No prompts for '{prof}'.")])
            lines=[f"## ✍️ Prompts for {prof.replace('-',' ').title()}\n"]
            for i,p in enumerate(r,1):
                lines.append(f"### {i}. {p.get('title','')}")
                if p.get("tool_name"): lines.append(f"*Tool: {p['tool_name']}*")
                if p.get("prompt_text"): lines.append(f"\n```\n{p['prompt_text'][:300]}\n```\n")
            lines.append(f"\n🔗 {BASE_URL}/prompts/{prof}/")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "get_site_stats":
            # Fixed 2026-08-22: this tool's entire purpose is live stats,
            # but connections/prompts/GDPR/EU-hosted counts were hardcoded
            # and had already drifted from reality (e.g. prompts showed
            # 16,000 when the real figure was 19,686+). Now fetches every
            # figure live; each field falls back independently if its own
            # call fails, so one slow/broken sub-fetch can't blank the rest.
            d = await _get("/homepage/"); s = d.get("stats", {})
            try:
                pstats = await _get("/prompts/stats/")
                prompt_count = pstats.get("total_prompts", 19686)
            except Exception:
                prompt_count = 19686
            try:
                gdpr = await _get("/tools/", {"gdpr_compliant": "true", "page_size": 1})
                gdpr_count = gdpr.get("count", 1050)
            except Exception:
                gdpr_count = 1050
            try:
                eu = await _get("/tools/", {"eu_hosted": "true", "page_size": 1})
                eu_count = eu.get("count", 8)
            except Exception:
                eu_count = 8
            return CallToolResult(content=[TextContent(type="text",text="\n".join([
                "## 📊 GateOnAI Statistics",
                f"🔧 Tools: {s.get('tools_count', 2886):,}+",
                f"📂 Categories: {s.get('categories_count', 45)}",
                f"🔗 Connections: {s.get('connections_count', 4100000):,}+",
                f"✍️ Prompts: {prompt_count:,}+",
                f"🛡️ GDPR Tools: {gdpr_count:,}+",
                f"🇪🇺 EU-Hosted: {eu_count}+",
                f"🌐 {BASE_URL}",
            ]))])
        elif name == "get_compatible_tools":
            slug = arguments.get("slug","").lower().strip()
            limit = min(arguments.get("limit", 8), 20)
            d = await _get(f"/io-graph/expand/{slug}/")
            nodes = {n["slug"]: n for n in d.get("nodes", [])}
            center = d.get("center", slug)
            edges = [e for e in d.get("edges", []) if e.get("source") != e.get("target")]
            edges.sort(key=lambda e: e.get("weight", 0), reverse=True)
            edges = edges[:limit]
            if not edges:
                return CallToolResult(content=[TextContent(type="text",text=f"No compatibility data found for '{slug}'. Check the slug is correct via search_ai_tools first.")])
            center_name = nodes.get(center, {}).get("name", slug)
            lines = [f"## 🌐 Tools that genuinely connect with {center_name}",
                     "(GateOnAI IO-Compatibility Graph — real input/output type matching, not a category guess)\n"]
            for e in edges:
                other_slug = e["target"] if e["source"] == center else e["source"]
                other = nodes.get(other_slug, {})
                lines.append(f"**{other.get('name', other_slug)}** ({other.get('category','?')}) — connection strength {e.get('weight',0):.1f}")
                lines.append(f"  → {BASE_URL}/tools/{other_slug}")
                lines.append("")
            lines.append(f"🔗 Full interactive graph: {BASE_URL}/graph")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "find_ai_pipeline":
            IO_TYPES_MCP = ["text","image","audio","video","data","url","code","pdf","email","social_post","prompt","file"]
            start_type = str(arguments.get("start_type","")).lower().strip()
            goal_type  = str(arguments.get("goal_type","")).lower().strip()
            max_steps    = max(2, min(int(arguments.get("max_steps", 4)), 6))
            alternatives = max(1, min(int(arguments.get("alternatives", 3)), 5))
            free_only    = bool(arguments.get("free_only", False))

            if start_type not in IO_TYPES_MCP:
                return CallToolResult(content=[TextContent(type="text",text=f"Invalid start_type '{start_type}'. Valid types: {', '.join(IO_TYPES_MCP)}")])
            if goal_type not in IO_TYPES_MCP:
                return CallToolResult(content=[TextContent(type="text",text=f"Invalid goal_type '{goal_type}'. Valid types: {', '.join(IO_TYPES_MCP)}")])

            d = await _get("/workflow/find/", {"start": start_type, "goal": goal_type, "steps": max_steps, "limit": alternatives * 2})
            workflows = d.get("workflows", [])
            graph_stats = d.get("graph_stats", {})

            if free_only:
                workflows = [w for w in workflows if all(s.get("pricing_type") in ("free", "freemium") for s in w.get("steps", []))]
            workflows = workflows[:alternatives]

            if not workflows:
                return CallToolResult(content=[TextContent(type="text",text=(
                    f"No computed pipeline found from '{start_type}' to '{goal_type}'"
                    + (" with the free_only filter applied" if free_only else "")
                    + f". This graph currently has {graph_stats.get('edges', 0):,} real computed connections "
                    f"across {graph_stats.get('nodes', 0):,} active tools — try a different max_steps value, "
                    f"disable free_only, or explore {BASE_URL}/graph to see what's actually connected."
                ))])

            lines = [
                f"# 🔗 AI Pipeline: {start_type} → {goal_type}",
                f"Computed from GateOnAI's real IO-Compatibility Graph ({graph_stats.get('edges',0):,} connections "
                f"across {graph_stats.get('nodes',0):,} active tools) — not a guess or a template.",
                f"Found {len(workflows)} ranked alternative{'s' if len(workflows) != 1 else ''}:\n",
            ]
            for i, wf in enumerate(workflows, 1):
                steps = wf.get("steps", [])
                lines.append(f"## Option {i} — {len(steps)} step{'s' if len(steps) != 1 else ''} (quality score: {wf.get('score', 0):.0f})")
                for s in steps:
                    connects = s.get("connects_via", [])
                    connects_str = f" (connects via: {', '.join(connects)})" if connects else ""
                    lines.append(
                        f"{s['step']}. **{s['name']}** — {s.get('tagline','')} "
                        f"[{s.get('pricing_type','?')}, score {s.get('gateonai_score',0)}/100]{connects_str}"
                    )
                    lines.append(f"   → {BASE_URL}/tools/{s['slug']}")
                lines.append("")
            lines.append(f"🔗 Explore the full graph interactively: {BASE_URL}/graph")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "whats_new":
            days = max(1, min(int(arguments.get("days", 7)), 30))
            category = str(arguments.get("category", "")).strip()
            params = {"days": days}
            if category:
                params["category"] = category
            d = await _get("/tools/whats-new/", params)
            tools = d.get("tools", [])
            cat_label = d.get("category_name") or "all categories"

            if not tools:
                return CallToolResult(content=[TextContent(type="text",text=(
                    f"No new tools found in {cat_label} over the last {days} day(s). "
                    f"Try a longer window with the days parameter, or check {BASE_URL}/browse for the full catalog."
                ))])

            lines = [
                f"# 🆕 New on GateOnAI — {cat_label}, last {days} day(s)",
                f"{d.get('count', len(tools))} tool(s) found:\n",
            ]
            for t in tools:
                lines.append(
                    f"**{t['name']}** ({t.get('category_name','')}) — {t.get('tagline','')} "
                    f"[{t.get('pricing_type','?')}]"
                )
                lines.append(f"  → {BASE_URL}/tools/{t['slug']}")
                lines.append("")
            lines.append(f"🔍 Browse everything: {BASE_URL}/browse")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "find_similar_by_philosophy":
            slug = arguments.get("slug","").lower().strip()
            limit = min(arguments.get("limit", 8), 20)
            d = await _get(f"/tools/{slug}/similar-by-meaning/", {"limit": limit})

            if "error" in d:
                return CallToolResult(content=[TextContent(type="text",text=f"Error: {d['error']}")])

            results = d.get("results", [])
            if not results:
                return CallToolResult(content=[TextContent(type="text",text=f"No conceptually similar tools found for '{slug}' above the similarity threshold. Try get_compatible_tools instead for structural IO-connections.")])

            lines = [
                f"# 🧭 Tools conceptually similar to {slug}",
                f"({d.get('method', 'semantic embedding similarity')})\n",
            ]
            for r in results:
                lines.append(f"**{r['name']}** ({r.get('category_name','')}) — {r.get('tagline','')} [{r.get('pricing_type','?')}, score {r.get('gateonai_score',0)}/100, similarity {r.get('similarity',0)}]")
                lines.append(f"  → {BASE_URL}/tools/{r['slug']}")
                lines.append("")
            lines.append(f"💡 For real structural input/output connections instead of meaning-based similarity, use get_compatible_tools.")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "get_market_landscape":
            category = arguments.get("category","").lower().strip()
            d = await _get(f"/tools/market-landscape/{category}/")

            if "error" in d:
                return CallToolResult(content=[TextContent(type="text",text=f"Error: {d['error']}")])

            if d.get("tool_count", 0) == 0:
                return CallToolResult(content=[TextContent(type="text",text=f"No active tools currently found in category \'{category}\' on GateOnAI.")])

            stats = d.get("score_stats") or {}
            leaders = d.get("top_scoring_tools", [])

            lines = [
                f"# 📈 Market Landscape — {d['category']}",
                f"**{d['tool_count']} tools** currently active in this category on GateOnAI.\n",
            ]
            if stats:
                lines.append(f"**GateOnAI Score distribution:** avg {stats['average']}, median {stats['median']}, range {stats['min']}-{stats['max']}\n")

            lines.append("")

            lines.append("**Current top-scoring tools:**")
            for t in leaders:
                lines.append(f"- **{t['name']}** ({t['gateonai_score']}/100, {t['pricing_type']}) — {t.get('tagline','')}")
                lines.append(f"  → {BASE_URL}/tools/{t['slug']}")
            lines.append("")
            lines.append(f"⚖️ {d.get('disclaimer','')}")

            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "match_prompt_to_task":
            task = arguments.get("task","").strip()
            limit = min(arguments.get("limit", 5), 10)
            d = await _get("/prompts/match-to-task/", {"task": task, "limit": limit})

            if "error" in d:
                return CallToolResult(content=[TextContent(type="text",text=f"Error: {d['error']}")])

            results = d.get("results", [])
            if not results:
                return CallToolResult(content=[TextContent(type="text",text=f"No closely matching verified prompt found for \'{task}\'. Try different wording, or browse the full library at {BASE_URL}/prompts/.")])

            lines = [f"# 📝 Prompts matching: \"{task}\"\n"]
            for r in results:
                lines.append(f"## {r['title']}")
                lines.append(f"*For {r['profession']}, designed for {r['tool_slug']}*\n")
                lines.append(f"> {r['prompt_text']}\n")
            lines.append(f"⚖️ {d.get('method', '')}")
            lines.append(f"🔍 Full library: {BASE_URL}/prompts/")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        elif name == "get_workflow_template":
            prof = arguments.get("profession","").lower().strip()
            d = await _get(f"/workflows/dynamic/{prof}/")
            steps = d.get("steps", [])
            if not steps:
                return CallToolResult(content=[TextContent(type="text",text=f"No pre-built workflow found for '{prof}'. Try get_ai_workflow with a free-text description instead, or browse {BASE_URL}/workflows for valid profession slugs.")])
            title = d.get("profession", prof.replace("-"," ").title())
            lines = [f"# Pre-Built AI Workflow: {title}", f"Sector: {d.get('sector','')}\n"]
            for s in steps:
                t = s.get("tool", {})
                lines.append(f"**Step {s.get('step_number','?')}: {s.get('action_label','')}**")
                if s.get("purpose"): lines.append(f"  {s['purpose']}")
                if t:
                    lines.append(f"  Tool: {t.get('name','')} ({t.get('pricing_type','?')}) — Score {t.get('gateonai_score','?')}/100")
                    if t.get("tagline"): lines.append(f"  {t['tagline']}")
                    if t.get("slug"): lines.append(f"  → {BASE_URL}/tools/{t['slug']}")
                lines.append("")
            lines.append(f"🔗 {BASE_URL}/workflows/{prof}")
            return CallToolResult(content=[TextContent(type="text",text="\n".join(lines))])
        else:
            return CallToolResult(content=[TextContent(type="text",text=f"Unknown tool: {name}")], isError=True)
    except Exception as e:
        logger.error(f"{name} failed: {e}")
        msg = str(e) or ("the GateOnAI API did not respond in time, please try again" if isinstance(e, httpx.TimeoutException) else type(e).__name__)
        return CallToolResult(content=[TextContent(type="text", text=f"Error: {msg}")], isError=True)

# GateOnAI data/scores are independent editorial assessment, not a
# guarantee or certification - this notice is embedded directly in every
# MCP tool response (not only shown on the website) so the reminder
# travels with the data itself, regardless of how a downstream AI agent
# processes, summarizes, or re-presents it to its own end user.
_DISCLAIMER = (
    "\n\n---\n⚠️ GateOnAI data (scores, descriptions, categorisation) is "
    "independent editorial assessment based on publicly available "
    "information at the time of scoring - not a guarantee, warranty, or "
    "certification. Verify independently before relying on it for any "
    "decision."
)

@server.call_tool()
async def call_tool(name, arguments):
    # Record usage first (independent of whether the call itself
    # succeeds or fails below) - a failed call is still a real signal
    # that someone is actively using this tool.
    asyncio.create_task(_record_tool_call(name))
    result = await _call_tool_impl(name, arguments)
    try:
        for block in result.content:
            if getattr(block, "type", None) == "text":
                block.text = block.text + _DISCLAIMER
    except Exception as e:
        logger.error(f"failed to append disclaimer: {e}")
    text = "\n".join(b.text for b in result.content if getattr(b, "type", None) == "text")
    links = [u.rstrip(".,;:_*") for u in _LINK_RE.findall(text)]
    result.structuredContent = {"tool": name, "markdown": text, "links": list(dict.fromkeys(links))[:50],
                                "is_error": bool(getattr(result, "isError", False))}
    return result

def _get_init_opts():
    capabilities = server.get_capabilities(
        notification_options=NotificationOptions(),
        experimental_capabilities={},
    )
    # The installed mcp SDK hardcodes subscribe=False in get_capabilities();
    # override it here since we do implement subscribe_resource/
    # unsubscribe_resource handlers and genuinely support subscriptions.
    if capabilities.resources is not None:
        capabilities.resources.subscribe = True
    return InitializationOptions(
        server_name="gateonai",
        server_version=SERVER_VERSION,
        capabilities=capabilities,
    )

async def main():
    transport="stdio"; port=8765
    if "--transport" in sys.argv:
        i=sys.argv.index("--transport")
        if i+1<len(sys.argv): transport=sys.argv[i+1]
    if "--port" in sys.argv:
        i=sys.argv.index("--port")
        if i+1<len(sys.argv): port=int(sys.argv[i+1])

    if transport in ("sse", "http"):
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        from starlette.requests import Request
        from starlette.responses import Response
        import uvicorn

        # SSE (backward compat)
        from mcp.server.sse import SseServerTransport
        sse = SseServerTransport("/mcp/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await server.run(streams[0], streams[1], _get_init_opts())

        # Streamable HTTP (new standard)
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        session_manager = StreamableHTTPSessionManager(
            app=server,
            json_response=False,
            stateless=True,
        )

        async def handle_streamable_http(scope, receive, send):
            await session_manager.handle_request(scope, receive, send)

        @contextlib.asynccontextmanager
        async def lifespan(app):
            async with session_manager.run():
                listener_task = asyncio.create_task(_redis_subscription_listener())
                logger.warning(f"GateOnAI MCP running on port {port} (SSE + Streamable HTTP)")
                try:
                    yield
                finally:
                    listener_task.cancel()

        app = Starlette(
            lifespan=lifespan,
            routes=[
                Route("/mcp/sse", endpoint=handle_sse),
                Mount("/mcp/messages/", app=sse.handle_post_message),
                Mount("/mcp/", app=handle_streamable_http),
            ]
        )

        cfg = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
        await uvicorn.Server(cfg).serve()
    else:
        async with stdio.stdio_server() as (r,w):
            await server.run(r, w, _get_init_opts())

def main_sync():
    """Entry point for the `gateonai-mcp` command (pip/uvx installs)."""
    asyncio.run(main())


if __name__=="__main__":
    asyncio.run(main())
