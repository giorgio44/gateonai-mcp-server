# Changelog

## 1.2.0 - 2026-09-28

### Added
- Structured output on all 17 tools: every tool declares an `outputSchema` and returns `structuredContent` with `tool`, `markdown`, `links` and `is_error` (the text content is unchanged for older clients).
- `Dockerfile` (runs the stdio server; no API key, Redis or configuration needed) and `glama.json`.

### Fixed
- `get_prompts_for_profession` called an API route that no longer existed.
- Failures are now flagged with `isError`, with a readable message (timeouts used to return an empty error).
- Workflow tools (`get_ai_workflow`, `build_workflow_board`) wait up to 45 s for goal planning on new requests.

## 1.1.1 - 2026-09-27

### Changed
- `analyze_ai_stack` and `get_market_landscape` no longer report pricing breakdowns. As a precaution, analyses and notifications never make claims about third-party pricing; tool listings still show the catalog's pricing label only.

## 1.1.0 - 2026-09-26

### Added
- `build_workflow_board`: turns a goal described in plain language into a shareable GateOnAI Workbench board (public link to open, share or clone). Boards created through MCP are never indexed by search engines.
- `analyze_ai_stack`: automated, observation-only notes about a set of tools (category overlaps, data connections in the IO-compatibility graph, pricing-model mix), with a disclaimer.
- Seven more tools that were already live on the hosted server: `get_compatible_tools`, `find_ai_pipeline`, `whats_new`, `find_similar_by_philosophy`, `get_market_landscape`, `match_prompt_to_task`, `get_workflow_template`.

### Changed
- Workflows now come from the user's goal (steps planned from the request), not from a fixed per-profession template.
- The server now runs without Redis: usage stats and resource subscriptions are enabled only on the hosted gateonai.com service.
- Dependency pinned to `mcp>=1.28,<2`: mcp 2.x changed the server API.

### Fixed
- Resource URIs are plain strings (required by newer mcp releases).
