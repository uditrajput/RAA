---
name: raa-mcp-mesh-manager
description: Dynamic discovery, connection, schema inspection, and lifecycle management for external third-party MCP servers.
version: 1.0.0
compatible_registry: "0.1.x"
tools: [mcp_mesh_connect, mcp_mesh_disconnect, mcp_mesh_list, mcp_mesh_inspect, mcp_mesh_test, mcp_mesh_toggle]
---

# RAA MCP Mesh Manager Skill

Orchestrates external third-party MCP servers (GitHub, Playwright, Jira, databases, scanners).

## Key Capabilities
- Multi-transport: stdio child processes and remote sse/streamable-http
- Dynamic tool discovery and schema ingestion
- Real-time latency probes and connection health tracking
