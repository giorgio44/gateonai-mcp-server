# GateOnAI MCP Server

[![Release](https://img.shields.io/github/v/release/giorgio44/gateonai-mcp-server?label=release&color=6c63ff)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-gateonai.com-6c63ff)](https://www.gateonai.com)
[![smithery badge](https://smithery.ai/badge/info-gateonai/gateonai-mcp-server)](https://smithery.ai/servers/info-gateonai/gateonai-mcp-server)
<!-- Live numbers: read from the GateOnAI API every time this page is viewed (never hardcoded) -->
![AI tools](https://img.shields.io/badge/dynamic/json?color=6c63ff&url=https%3A%2F%2Fwww.gateonai.com%2Fapi%2Fhomepage%2F&query=%24.stats.tools_count&label=AI%20tools) ![Categories](https://img.shields.io/badge/dynamic/json?color=6c63ff&url=https%3A%2F%2Fwww.gateonai.com%2Fapi%2Fhomepage%2F&query=%24.stats.categories_count&label=categories) ![Connections](https://img.shields.io/badge/dynamic/json?color=6c63ff&url=https%3A%2F%2Fwww.gateonai.com%2Fapi%2Fhomepage%2F&query=%24.stats.connections_count&label=IO%20connections) ![Prompts](https://img.shields.io/badge/dynamic/json?color=6c63ff&url=https%3A%2F%2Fwww.gateonai.com%2Fapi%2Fprompts%2Fstats%2F&query=%24.total_prompts&label=prompts)


**The official MCP server for [GateOnAI](https://www.gateonai.com) — Europe's AI Workflow Intelligence Platform.**

Connect Claude, Cursor, Windsurf, and any MCP-compatible AI client to a live database of **thousands of verified AI tools**, a compatibility graph of **millions of tool connections**, and a prompt library of **thousands of curated prompts across dozens of professions**.

No API key required. No registration. Works out of the box.

---

## Tools

| Tool | Description |
|------|-------------|
| `search_ai_tools` | Search GateOnAI's database of thousands of verified AI tools. |
| `get_ai_workflow` | Generate a step-by-step AI workflow for any profession, role, or business task. |
| `compare_ai_tools` | Compare two AI tools head-to-head. |
| `get_tool_details` | Get comprehensive details about a specific AI tool by its URL slug. |
| `get_trending_tools` | Get the currently trending AI tools on GateOnAI based on real user engagement data. |
| `get_eu_gdpr_tools` | Find AI tools that are GDPR-compliant or EU-hosted. |
| `get_prompts_for_profession` | Get curated, ready-to-use AI prompts for a specific profession from GateOnAI's library of thousands of prompts across dozens of professions. |
| `get_site_stats` | Get current live statistics about the GateOnAI platform including total verified tools, categories, tool compatibility connections, and prompt library size. |
| `get_compatible_tools` | Find AI tools that genuinely connect with a given tool, based on GateOnAI's IO-Compatibility Graph - a real, computed structural match between what one tool outputs and what another accepts as input (text, image, audio,  |
| `find_ai_pipeline` | Find a real, structurally computed sequence of AI tools that gets you from one type of content to another - e.g. |
| `whats_new` | See real AI tools recently added to GateOnAI - based on genuine addition timestamps, not a guess or a static list. |
| `find_similar_by_philosophy` | Find AI tools that are conceptually or philosophically similar to a given tool - based on real semantic embedding similarity of each tool's name and tagline (MiniLM), not just shared category. |
| `get_market_landscape` | A real, computed statistical snapshot of one GateOnAI category: live tool count, real GateOnAI Score distribution (average/median/min/max) and current top-scoring tools. |
| `match_prompt_to_task` | Given a free-text description of a task (e.g. |
| `get_workflow_template` | Get one of GateOnAI's thousands of pre-built, ready-made AI workflows for a specific profession - a deterministic, ordered sequence of steps each matched to a real tool by category and GateOnAI Score, regenerated live fr |
| `build_workflow_board` | Turn a goal described in plain language into a shareable GateOnAI Workbench board: real tools from the GateOnAI catalog, connected step by step when they form a workflow. |
| `analyze_ai_stack` | Automated observations about a set of AI tools (2-40 GateOnAI tool slugs): tools not currently listed, category overlaps and data connections found in GateOnAI's IO-compatibility graph. |

## Structured output

Every tool declares the same `outputSchema` and returns `structuredContent`:

| Field | Type | Description |
|-------|------|-------------|
| `tool` | string | Name of the tool that produced the result |
| `markdown` | string | The full result as Markdown (same as the text content) |
| `links` | array of string | gateonai.com URLs referenced in the result |
| `is_error` | boolean | True if the tool could not complete the request |

## Installation

### Prerequisites
- Python 3.10+
- pip

### 1. Clone the repository

```bash
git clone https://github.com/giorgio44/gateonai-mcp-server.git
cd gateonai-mcp-server
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
python gateonai_mcp_server.py
```

---

## Claude Desktop Configuration

Edit `~/.claude/claude_desktop_config.json` (macOS/Linux) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "gateonai": {
      "command": "python",
      "args": ["/absolute/path/to/gateonai_mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop. You should see the GateOnAI tools available in your conversation.

---

## Cursor Configuration

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "gateonai": {
      "command": "python",
      "args": ["/absolute/path/to/gateonai_mcp_server.py"]
    }
  }
}
```

---

## Claude Code Configuration

```bash
claude mcp add gateonai python /absolute/path/to/gateonai_mcp_server.py
```

---

## Usage Examples

Once connected, ask your AI assistant naturally:

```
"Find me the best free AI tools for video editing"
→ Uses: search_ai_tools

"Build me an AI workflow for a freelance graphic designer"
→ Uses: get_ai_workflow

"Compare ChatGPT vs Claude"
→ Uses: compare_ai_tools

"Tell me everything about Midjourney"
→ Uses: get_tool_details

"What AI tools are trending right now?"
→ Uses: get_trending_tools

"Find GDPR-compliant AI tools for legal teams in Europe"
→ Uses: get_eu_gdpr_tools

"Give me 5 ready-to-use prompts for a marketing manager"
→ Uses: get_prompts_for_profession

"How many tools does GateOnAI have?"
→ Uses: get_site_stats
```

---

## Tool Reference

### `search_ai_tools`

Search GateOnAI's database of thousands of verified AI tools. Find tools by name, use case, category, pricing model, or GDPR compliance status. Returns tool names, descriptions, pricing, GateOnAI scores, and direct URLs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | ✅ | Search term — tool name, use case, or description. Examples: 'video editing', 'code assistant', 'ChatGPT alternatives' |
| `category` | string | ❌ | Filter by category slug. Examples: 'writing', 'coding', 'image-generation', 'video', 'marketing' |
| `pricing` | string | ❌ | Filter by pricing model: free, freemium, paid, or free_trial |
| `gdpr_only` | boolean | ❌ | Set to true to return only GDPR-compliant tools suitable for European businesses |
| `eu_hosted_only` | boolean | ❌ | Set to true to return only tools hosted on EU infrastructure |
| `limit` | integer | ❌ | Number of results to return (default: 10, max: 24) |

### `get_ai_workflow`

Generate a step-by-step AI workflow for any profession, role, or business task. Uses GateOnAI's compatibility graph of millions of tool connections to recommend the optimal tool sequence.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | ✅ | Describe your role, profession, or goal. Examples: 'freelance graphic designer building a client workflow', 'startup founder automating customer support', 'marketing manager creating YouTube content' |

### `compare_ai_tools`

Compare two AI tools head-to-head. Returns pricing, features, GateOnAI scores, pros/cons, and a recommendation on which tool to choose.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tool1_slug` | string | ✅ | URL slug of the first tool to compare. Examples: 'chatgpt', 'claude', 'midjourney', 'jasper' |
| `tool2_slug` | string | ✅ | URL slug of the second tool to compare. Examples: 'gemini', 'dall-e', 'copy-ai', 'notion-ai' |

### `get_tool_details`

Get comprehensive details about a specific AI tool by its URL slug. Returns full description, pricing, GateOnAI score breakdown, pros/cons, integrations, GDPR status, and FAQ.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | ✅ | URL slug of the AI tool. Examples: 'chatgpt', 'midjourney', 'notion-ai', 'github-copilot', 'claude' |

### `get_trending_tools`

Get the currently trending AI tools on GateOnAI based on real user engagement data. Returns the most actively explored tools this week across all categories.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | ❌ | Number of trending tools to return (default: 10, max: 20) |

### `get_eu_gdpr_tools`

Find AI tools that are GDPR-compliant or EU-hosted. Essential for European businesses, healthcare, legal, and any use case requiring data sovereignty. All compliance data is manually verified by GateOnAI.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `standard` | string | ❌ | Compliance standard: 'gdpr' for GDPR-compliant tools, 'eu_hosted' for tools with EU-based infrastructure |
| `category` | string | ❌ | Optional category filter. Examples: 'writing', 'coding', 'marketing', 'legal' |
| `limit` | integer | ❌ | Number of results to return (default: 10, max: 24) |

### `get_prompts_for_profession`

Get curated, ready-to-use AI prompts for a specific profession from GateOnAI's library of thousands of prompts across dozens of professions. Works with ChatGPT, Claude, Gemini, and other LLMs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `profession` | string | ✅ | Profession slug. Examples: 'marketer', 'software-developer', 'designer', 'writer', 'content-creator', 'photographer', 'teacher', 'lawyer', 'doctor', 'entrepreneur' |
| `limit` | integer | ❌ | Number of prompts to return (default: 5, max: 20) |

### `get_site_stats`

Get current live statistics about the GateOnAI platform including total verified tools, categories, tool compatibility connections, and prompt library size.

_No parameters._

### `get_compatible_tools`

Find AI tools that genuinely connect with a given tool, based on GateOnAI's IO-Compatibility Graph - a real, computed structural match between what one tool outputs and what another accepts as input (text, image, audio, video, code, etc.), not a category-similarity guess. Answers questions like 'what tools work well with ChatGPT' or 'what can I feed ChatGPT's output into'. Backed by millions of real computed connections across the platform.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | ✅ | URL slug of the AI tool to find connections for. Examples: 'chatgpt', 'midjourney', 'claude' |
| `limit` | integer | ❌ | Number of connected tools to return (default: 8, max: 20) |

### `find_ai_pipeline`

Find a real, structurally computed sequence of AI tools that gets you from one type of content to another - e.g. audio to a finished blog post, or a single image to a full video. Powered by GateOnAI's IO-Compatibility Graph combined with a PostgreSQL recursive path-finding engine (not a guess, a template, or an LLM improvising) - each step is a real tool whose actual output type matches the next tool's actual input type, verified against real tagged data. Returns multiple ranked alternative pipelines, each scored on tool quality and path length, so you can compare a fast 2-step option against a more thorough 4-step one. Valid content types: text, image, audio, video, data, url, code, pdf, email, social_post, prompt, file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_type` | string | ✅ | The type of content you are starting with |
| `goal_type` | string | ✅ | The type of content you want to end up with |
| `max_steps` | integer | ❌ | Maximum number of tools in the chain (2-6, default 4) |
| `alternatives` | integer | ❌ | Number of alternative pipelines to return (1-5, default 3) |
| `free_only` | boolean | ❌ | If true, only return pipelines where every single tool in the chain is free or freemium |

### `whats_new`

See real AI tools recently added to GateOnAI - based on genuine addition timestamps, not a guess or a static list. Optionally filter by category. Useful for staying current on new tool launches or checking what's new in a specific space (e.g. new AI Agents tools this week).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `days` | integer | ❌ | How many days back to look (1-30, default 7) |
| `category` | string | ❌ | Optional category slug to filter by, e.g. 'ai-agents', 'marketing', 'design'. Omit to see all categories. |

### `find_similar_by_philosophy`

Find AI tools that are conceptually or philosophically similar to a given tool - based on real semantic embedding similarity of each tool's name and tagline (MiniLM), not just shared category. Different from get_compatible_tools, which uses the structural IO-Compatibility Graph (real input/output matching) rather than meaning-based similarity. Use this for 'tools like X' questions, get_compatible_tools for 'what connects to X' questions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | ✅ | URL slug of the AI tool to find similar tools for. Examples: 'chatgpt', 'midjourney', 'notion' |
| `limit` | integer | ❌ | Number of similar tools to return (default: 8, max: 20) |

### `get_market_landscape`

A real, computed statistical snapshot of one GateOnAI category: live tool count, real GateOnAI Score distribution (average/median/min/max) and current top-scoring tools. Every number is computed directly from live catalog data at request time - never a prediction, estimate, or industry-wide claim beyond what GateOnAI itself catalogs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | ✅ | Category slug, e.g. 'ai-agents', 'design', 'marketing', 'writing-assistant'. Use search_ai_tools or browse to find valid category slugs if unsure. |

### `match_prompt_to_task`

Given a free-text description of a task (e.g. 'write a cold email to a client'), finds the best-matching existing prompt(s) from GateOnAI's verified prompt library using real BM25 full-text search - not a semantic guess or an invented relevance score. Each result includes the actual prompt text, which tool it's designed for, and the profession it comes from.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | string | ✅ | Free-text description of the task, e.g. 'write a cold email to a client' or 'summarize a legal contract' |
| `limit` | integer | ❌ | Number of matching prompts to return (1-10, default 5) |

### `get_workflow_template`

Get one of GateOnAI's thousands of pre-built, ready-made AI workflows for a specific profession - a deterministic, ordered sequence of steps each matched to a real tool by category and GateOnAI Score, regenerated live from current tool data. Different from get_ai_workflow: this returns an existing, curated template for a known profession rather than generating a new custom one from free text - faster and more consistent for common roles.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `profession` | string | ✅ | Profession slug. Examples: 'blogger', 'general-contractor', 'marketing-manager', 'software-developer', '3d-artist'. If unsure of the exact slug, use get_ai_workflow instead with a free-text description. |

### `build_workflow_board`

Turn a goal described in plain language into a shareable GateOnAI Workbench board: real tools from the GateOnAI catalog, connected step by step when they form a workflow. Returns the steps and a public link the user can open, share or clone into their own Workbench (free, no account). Boards created this way are never indexed by search engines.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `goal` | string | ✅ | What the user wants to achieve, e.g. 'turn podcast episodes into blog posts and short social clips' |

### `analyze_ai_stack`

Automated observations about a set of AI tools (2-40 GateOnAI tool slugs): tools not currently listed, category overlaps and data connections found in GateOnAI's IO-compatibility graph. Observations from GateOnAI data only - not recommendations and not judgments about any provider.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tool_slugs` | array of string | ✅ | GateOnAI tool slugs, e.g. ['chatgpt', 'elevenlabs', 'opus-clip'] (slugs appear in search results and tool URLs) |

## Docker

```bash
docker build -t gateonai-mcp .
docker run -i --rm gateonai-mcp
```

## Transport

This server runs over **stdio** (standard input/output), which is the default for local MCP servers and is supported by all major MCP clients.

For remote/HTTP access:

```bash
python gateonai_mcp_server.py --transport sse --port 8765
```

---

## No API Key Required

GateOnAI's public API is open and does not require authentication. The MCP server connects directly to `https://www.gateonai.com/api`.

---

## About GateOnAI

[GateOnAI](https://www.gateonai.com) is Europe's AI Workflow Intelligence Platform — a curated directory of thousands of verified AI tools, with a focus on GDPR compliance, EU-hosted solutions, and practical AI workflows for professionals.

- 🌐 Platform: [gateonai.com](https://www.gateonai.com)
- 🤖 MCP Docs: [gateonai.com/mcp](https://www.gateonai.com/mcp)
- 🔧 AI Workflow Builder: [gateonai.com/build-my-business-ai-workflow](https://www.gateonai.com/build-my-business-ai-workflow)
- 📁 Browse Tools: [gateonai.com/browse](https://www.gateonai.com/browse)
- 🇪🇺 EU/GDPR Tools: [gateonai.com/eu-ai-tools](https://www.gateonai.com/eu-ai-tools)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
