# Changelog

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
