# GateOnAI MCP Server

[![MCP](https://img.shields.io/badge/MCP-1.0-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-gateonai.com-6c63ff)](https://www.gateonai.com)

**The official MCP server for [GateOnAI](https://www.gateonai.com) — Europe's AI Workflow Intelligence Platform.**

Connect Claude, Cursor, Windsurf, and any MCP-compatible AI client to a live database of **2,756+ verified AI tools**, a compatibility graph of **4,093,220 tool connections**, and a prompt library of **16,000+ curated prompts across 45 professions**.

No API key required. No registration. Works out of the box.

---

## Tools

| Tool | Description |
|------|-------------|
| `search_ai_tools` | Search 2,756+ verified AI tools by name, use case, category, or pricing |
| `get_ai_workflow` | Generate a step-by-step AI workflow for any profession or task |
| `compare_ai_tools` | Head-to-head comparison of two tools with scores, pros/cons, and recommendation |
| `get_tool_details` | Full details for a specific tool: description, pricing, integrations, FAQ |
| `get_trending_tools` | Currently trending AI tools based on real user engagement |
| `get_eu_gdpr_tools` | Find GDPR-compliant or EU-hosted AI tools (manually verified) |
| `get_prompts_for_profession` | Curated prompts for any profession from the GateOnAI Prompt Library |
| `get_site_stats` | Live platform statistics: tool count, categories, connections |

---

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

Search the GateOnAI database of verified AI tools.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | ✅ | Search term — tool name, use case, or description |
| `category` | string | ❌ | Category slug (e.g. `writing`, `coding`, `image-generation`) |
| `pricing` | string | ❌ | One of: `free`, `freemium`, `paid`, `free_trial` |
| `gdpr_only` | boolean | ❌ | If `true`, return only GDPR-compliant tools |
| `eu_hosted_only` | boolean | ❌ | If `true`, return only EU-hosted tools |
| `limit` | integer | ❌ | Number of results, max 24 (default: 10) |

---

### `get_ai_workflow`

Generate a step-by-step AI workflow using GateOnAI's compatibility graph engine.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | ✅ | Your role, profession, or goal |

**Example:** `"I'm a startup founder who needs to automate customer support"`

---

### `compare_ai_tools`

Head-to-head comparison of two AI tools.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tool1_slug` | string | ✅ | Slug of first tool (e.g. `chatgpt`) |
| `tool2_slug` | string | ✅ | Slug of second tool (e.g. `claude`) |

---

### `get_tool_details`

Get full details for a specific AI tool.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | ✅ | Tool slug (e.g. `midjourney`, `notion-ai`) |

---

### `get_trending_tools`

Get currently trending AI tools based on real GateOnAI user engagement.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | ❌ | Number of results, max 20 (default: 10) |

---

### `get_eu_gdpr_tools`

Find GDPR-compliant or EU-hosted AI tools. All compliance data is manually verified by the GateOnAI team.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `standard` | string | ❌ | `gdpr` (default) or `eu_hosted` |
| `category` | string | ❌ | Category filter |
| `limit` | integer | ❌ | Number of results (default: 10) |

---

### `get_prompts_for_profession`

Get ready-to-use AI prompts for a specific profession from GateOnAI's library of 16,000+ prompts.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `profession` | string | ✅ | Profession slug (e.g. `marketer`, `software-developer`, `designer`) |
| `limit` | integer | ❌ | Number of prompts (default: 5, max: 20) |

**Available professions include:** `marketer`, `software-developer`, `designer`, `writer`, `content-creator`, `photographer`, `teacher`, `lawyer`, `doctor`, `entrepreneur`, `accountant`, `data-scientist`, `product-manager`, and 30+ more.

---

### `get_site_stats`

Returns live GateOnAI platform statistics.

No parameters required.

---

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

[GateOnAI](https://www.gateonai.com) is Europe's AI Workflow Intelligence Platform — a curated directory of 2,756+ verified AI tools, with a focus on GDPR compliance, EU-hosted solutions, and practical AI workflows for professionals.

- 🌐 Platform: [gateonai.com](https://www.gateonai.com)
- 🤖 MCP Docs: [gateonai.com/mcp](https://www.gateonai.com/mcp)
- 🔧 AI Workflow Builder: [gateonai.com/build-my-business-ai-workflow](https://www.gateonai.com/build-my-business-ai-workflow)
- 📁 Browse Tools: [gateonai.com/browse](https://www.gateonai.com/browse)
- 🇪🇺 EU/GDPR Tools: [gateonai.com/eu-ai-tools](https://www.gateonai.com/eu-ai-tools)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
