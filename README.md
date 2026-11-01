# GateOnAI MCP Server

[![Release](https://img.shields.io/github/v/release/giorgio44/gateonai-mcp-server?label=release&color=6c63ff)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-gateonai.com-6c63ff)](https://www.gateonai.com)
<!-- Live numbers: read from the GateOnAI API every time this page is viewed (never hardcoded) -->
![AI tools](https://img.shields.io/badge/dynamic/json?color=6c63ff&url=https%3A%2F%2Fwww.gateonai.com%2Fapi%2Fhomepage%2F&query=%24.stats.tools_count&label=AI%20tools) ![Categories](https://img.shields.io/badge/dynamic/json?color=6c63ff&url=https%3A%2F%2Fwww.gateonai.com%2Fapi%2Fhomepage%2F&query=%24.stats.categories_count&label=categories) ![Connections](https://img.shields.io/badge/dynamic/json?color=6c63ff&url=https%3A%2F%2Fwww.gateonai.com%2Fapi%2Fhomepage%2F&query=%24.stats.connections_count&label=IO%20connections) ![Prompts](https://img.shields.io/badge/dynamic/json?color=6c63ff&url=https%3A%2F%2Fwww.gateonai.com%2Fapi%2Fprompts%2Fstats%2F&query=%24.total_prompts&label=prompts)


**The official MCP server for [GateOnAI](https://www.gateonai.com) — the AI Decision Platform for Business.**

Connect Claude, Cursor, Windsurf, and any MCP-compatible AI client to a live database of **thousands of listed AI tools**, a graph of **millions of computed tool connections** (from automatically assigned input/output tags; not tested), and a prompt library of **thousands of prompts across dozens of professions**.

No API key required. No registration. Works out of the box.

---

## Prompts

Ready-made starting points; MCP clients show them as commands (for example with `/` in Claude Desktop).

| Prompt | Arguments | What it does |
|---|---|---|
| `find_ai_tool` | `task`, optional `budget` | Searches, compares the strongest candidates and recommends one |
| `build_ai_workflow` | `goal`, optional `profession` | Plans one tool per step and returns a shareable board link |
| `compare_tools` | `tools` | Pricing, strengths and the best fit for each use case |

## Tools

| Tool | Description |
|------|-------------|
| `search_ai_tools` | Search GateOnAI's database of thousands of listed AI tools. |
| `get_ai_workflow` | Generate a step-by-step AI workflow for any profession, role, or business task. |
| `compare_ai_tools` | Compare two or three AI tools head-to-head. |
| `get_tool_details` | Get comprehensive details about a specific AI tool by its URL slug. |
| `get_trending_tools` | AI tools with at least 3 website clicks from GateOnAI visitors in the last 7 days (bots not counted); can be empty. |
| `get_eu_gdpr_tools` | Find AI tools whose provider pages refer to the GDPR or state EU hosting. |
| `get_prompts_for_profession` | Get ready-to-use AI prompts for a specific profession from GateOnAI's library of thousands of prompts across dozens of professions. |
| `get_site_stats` | Get current live statistics about the GateOnAI platform including total listed tools, categories, tool compatibility connections, and prompt library size. |
| `get_compatible_tools` | Find AI tools that may connect with a given tool, computed from automatically assigned input/output tags (not tested). |
| `find_ai_pipeline` | Find a computed sequence of AI tools from one content type to another (e.g. audio to a blog post), from automatically assigned input/output tags (not tested). |
| `whats_new` | See AI tools recently added to GateOnAI, based on the date each tool was added. |
| `find_similar_by_philosophy` | Find AI tools that are conceptually or philosophically similar to a given tool - based on semantic embedding similarity of each tool's name and tagline (MiniLM), not just shared category. |
| `get_market_landscape` | A computed statistical snapshot of one GateOnAI category: live tool count, GateOnAI Score distribution (average/median/min/max) and current top-scoring tools. |
| `match_prompt_to_task` | Find the existing prompts that best match a free-text task description (BM25 full-text search). |
| `get_workflow_template` | Get one of GateOnAI's thousands of pre-built, ready-made AI workflows for a specific profession - a deterministic, ordered sequence of steps each matched to a listed tool by category and GateOnAI Score, regenerated live fr |
| `build_workflow_board` | Turn a goal described in plain language into a GateOnAI Workbench board: tools from the GateOnAI catalog, connected step by step when they form a workflow. Returns a share link that contains the board; nothing is stored. |
| `analyze_ai_stack` | Automated observations about a set of AI tools (2-40 GateOnAI tool slugs): tools not currently listed, category overlaps, data connections in GateOnAI's IO-compatibility graph, and (My AI Stack DNA) what the stack can make together by input/output type, output types none of the tools gives with the highest-scored tools that could fill them, tools with identical inputs and outputs, and facts (EU hosting stated by the provider, listed MCP server). A connection means one tool gives out a type the other takes in (GateOnAI tags), not a confirmed integration. |

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

"Find AI tools for legal teams whose providers state EU hosting"
→ Uses: get_eu_gdpr_tools

"Give me 5 ready-to-use prompts for a marketing manager"
→ Uses: get_prompts_for_profession

"How many tools does GateOnAI have?"
→ Uses: get_site_stats
```

---

## Tool Reference

### `search_ai_tools`

Search GateOnAI's database of thousands of listed AI tools. Find tools by name, use case, category, pricing model, or GDPR info on the provider's page. Returns tool names, descriptions, pricing, GateOnAI scores, and direct URLs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | ✅ | Search term — tool name, use case, or description. Examples: 'video editing', 'code assistant', 'ChatGPT alternatives' |
| `category` | string | ❌ | Filter by category slug. Examples: 'writing-assistant', 'development', 'image-generation', 'video-creation', 'marketing' |
| `pricing` | string | ❌ | Filter by pricing model: free, freemium, paid, or free_trial |
| `gdpr_only` | boolean | ❌ | Set to true to return only tools whose provider pages refer to the GDPR |
| `eu_hosted_only` | boolean | ❌ | Set to true to return only tools whose providers state EU hosting |
| `limit` | integer | ❌ | Number of results to return (default: 10, max: 24) |

### `get_ai_workflow`

Generate a step-by-step AI workflow for any profession, role, or business task. Uses GateOnAI's compatibility graph of computed tool connections to suggest a tool sequence.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | ✅ | Describe your role, profession, or goal. Examples: 'freelance graphic designer building a client workflow', 'startup founder automating customer support', 'marketing manager creating YouTube content' |

### `compare_ai_tools`

Compare two or three AI tools head-to-head. Returns pricing, features, GateOnAI scores and pros/cons side by side.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tool1_slug` | string | ✅ | URL slug of the first tool to compare. Examples: 'chatgpt', 'claude', 'midjourney', 'jasper' |
| `tool2_slug` | string | ✅ | URL slug of the second tool to compare. Examples: 'google-gemini', 'dall-e-3', 'elevenlabs', 'notion' |
| `tool3_slug` | string | ❌ | Optional third tool slug for a 3-way comparison (e.g. 'perplexity') |

### `get_tool_details`

Get comprehensive details about a specific AI tool by its URL slug. Returns full description, pricing, GateOnAI score breakdown, pros/cons, integrations, GDPR status, and FAQ.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | ✅ | URL slug of the AI tool. Examples: 'chatgpt', 'midjourney', 'notion', 'github-copilot', 'claude' |

### `get_trending_tools`

Get AI tools that are trending on GateOnAI by a fixed rule: at least 3 clicks to the tool's own website from GateOnAI visitors in the last 7 days (bots not counted). The list can be empty; the answer then says so and suggests whats_new (recently added tools) or search_ai_tools.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | ❌ | Number of trending tools to return (default: 10, max: 20) |

### `get_eu_gdpr_tools`

Find AI tools whose providers, on their own websites, refer to the GDPR or state EU data hosting. Each result quotes the provider's own sentence, links the source page and gives the date of GateOnAI's automatic check (about monthly). These are provider statements, not an audit, verification or certification by GateOnAI - check the provider's current documents before relying on them.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `standard` | string | ❌ | Compliance standard: 'gdpr' for tools whose provider pages refer to the GDPR, 'eu_hosted' for tools whose providers state EU hosting |
| `query` | string | ❌ | Optional: words to match in the tool name or tagline, e.g. 'transcription' or 'chatbot' |
| `category` | string | ❌ | Optional category filter. Examples: 'writing-assistant', 'development', 'marketing', 'legal-ai' |
| `limit` | integer | ❌ | Number of results to return (default: 10, max: 24) |

### `get_prompts_for_profession`

Get ready-to-use AI prompts for a specific profession from GateOnAI's library of thousands of prompts across dozens of professions. Works with ChatGPT, Claude, Gemini, and other LLMs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `profession` | string | ✅ | Profession slug. Examples: 'marketer', 'software-developer', 'designer', 'writer', 'content-creator', 'photographer', 'teacher', 'lawyer', 'doctor', 'entrepreneur' |
| `limit` | integer | ❌ | Number of prompts to return (default: 5, max: 20) |

### `get_site_stats`

Get current live statistics about the GateOnAI platform including total listed tools, categories, tool compatibility connections, and prompt library size.

_No parameters._

### `get_compatible_tools`

Find AI tools that may connect with a given tool, based on GateOnAI's IO-Compatibility Graph - computed automatically by matching the input/output content types that GateOnAI assigns to each tool (text, image, audio, video, code, etc.). The tags are assigned automatically and can be wrong; connections are not tested. Answers questions like 'what tools work well with ChatGPT' or 'what can I feed ChatGPT's output into'.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | ✅ | URL slug of the AI tool to find connections for. Examples: 'chatgpt', 'midjourney', 'claude' |
| `limit` | integer | ❌ | Number of connected tools to return (default: 8, max: 20) |

### `find_ai_pipeline`

Find a computed sequence of AI tools that gets you from one type of content to another - e.g. audio to a finished blog post, or a single image to a full video. Powered by GateOnAI's IO-Compatibility Graph combined with a PostgreSQL recursive path-finding engine (not an LLM improvising) - each step is a listed tool whose tagged output type matches the next tool's tagged input type. The tags are assigned automatically and the pipelines are not tested. Returns multiple ranked alternative pipelines, each scored on tool quality and path length, so you can compare a fast 2-step option against a more thorough 4-step one. Valid content types: text, image, audio, video, data, url, code, pdf, email, social_post, prompt, file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_type` | string | ✅ | The type of content you are starting with |
| `goal_type` | string | ✅ | The type of content you want to end up with |
| `max_steps` | integer | ❌ | Maximum number of tools in the chain (2-6, default 4) |
| `alternatives` | integer | ❌ | Number of alternative pipelines to return (1-5, default 3) |
| `free_only` | boolean | ❌ | If true, only return pipelines where every single tool in the chain is free or freemium |

### `whats_new`

See AI tools recently added to GateOnAI, based on the date each tool was added. Optionally filter by category. Useful for staying current on new tool launches or checking what's new in a specific space (e.g. new AI Agents tools this week).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `days` | integer | ❌ | How many days back to look (1-30, default 7) |
| `category` | string | ❌ | Optional category slug to filter by, e.g. 'ai-agents', 'marketing', 'design'. Omit to see all categories. |

### `find_similar_by_philosophy`

Find AI tools that are conceptually or philosophically similar to a given tool - based on semantic embedding similarity of each tool's name and tagline (MiniLM), not just shared category. Different from get_compatible_tools, which uses the structural IO-Compatibility Graph (real input/output matching) rather than meaning-based similarity. Use this for 'tools like X' questions, get_compatible_tools for 'what connects to X' questions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | ✅ | URL slug of the AI tool to find similar tools for. Examples: 'chatgpt', 'midjourney', 'notion' |
| `limit` | integer | ❌ | Number of similar tools to return (default: 8, max: 20) |

### `get_market_landscape`

A computed statistical snapshot of one GateOnAI category: live tool count, GateOnAI Score distribution (average/median/min/max) and current top-scoring tools. Every number is computed directly from live catalog data at request time - never a prediction, estimate, or industry-wide claim beyond what GateOnAI itself catalogs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | ✅ | Category slug, e.g. 'ai-agents', 'design', 'marketing', 'writing-assistant'. Use search_ai_tools or browse to find valid category slugs if unsure. |

### `match_prompt_to_task`

Given a free-text description of a task (e.g. 'write a cold email to a client'), finds the best-matching existing prompt(s) from GateOnAI's prompt library using real BM25 full-text search - not a semantic guess or an invented relevance score. Each result includes the actual prompt text, which tool it's designed for, and the profession it comes from.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | string | ✅ | Free-text description of the task, e.g. 'write a cold email to a client' or 'summarize a legal contract' |
| `limit` | integer | ❌ | Number of matching prompts to return (1-10, default 5) |

### `get_workflow_template`

Get one of GateOnAI's thousands of pre-built, ready-made AI workflows for a specific profession - a deterministic, ordered sequence of steps each matched to a listed tool by category and GateOnAI Score, regenerated live from current tool data. Different from get_ai_workflow: this returns an existing, curated template for a known profession rather than generating a new custom one from free text - faster and more consistent for common roles.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `profession` | string | ✅ | Profession slug. Examples: 'blogger', 'general-contractor', 'marketing-manager', 'software-developer', '3d-artist'. If unsure of the exact slug, use get_ai_workflow instead with a free-text description. |

### `build_workflow_board`

Turn a goal described in plain language into a GateOnAI Workbench board: tools from the GateOnAI catalog, connected step by step when they form a workflow. Returns the steps and a share link that contains the board itself - nothing is stored on GateOnAI's servers. The user can open the link, clone the board into their own Workbench (free, no account) and share it.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `goal` | string | ✅ | What the user wants to achieve, e.g. 'turn podcast episodes into blog posts and short social clips' |

### `analyze_ai_stack`

Automated observations about a set of AI tools (2-40 GateOnAI tool slugs): tools not currently listed, category overlaps, data connections in GateOnAI's IO-compatibility graph, and (My AI Stack DNA) what the stack can make together by input/output type, output types none of the tools gives with the highest-scored tools that could fill them, tools with identical inputs and outputs, and facts (EU hosting stated by the provider, listed MCP server). A connection means one tool gives out a type the other takes in (GateOnAI tags), not a confirmed integration. Observations from GateOnAI data only - not recommendations and not judgments about any provider.

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

[GateOnAI](https://www.gateonai.com) is the AI Decision Platform for Business — a directory of thousands of AI tools, sorted by an algorithmic GateOnAI Score, with the GDPR and EU-hosting information each provider publishes and practical AI workflows for professionals.

- 🌐 Platform: [gateonai.com](https://www.gateonai.com)
- 🤖 MCP Docs: [gateonai.com/mcp](https://www.gateonai.com/mcp)
- 🔧 AI Workflow Builder: [gateonai.com/build-my-business-ai-workflow](https://www.gateonai.com/build-my-business-ai-workflow)
- 📁 Browse Tools: [gateonai.com/browse](https://www.gateonai.com/browse)
- 🇪🇺 EU/GDPR Tools: [gateonai.com/eu-ai-tools](https://www.gateonai.com/eu-ai-tools)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
