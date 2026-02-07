# MCP `list_ready_tasks` Capabilities Contract

`list_ready_tasks(project_id, agent_id, capabilities)` accepts capability filters in either form:

1. List form (preferred):

```json
{
  "project_id": "66b79018-c5e0-4880-864e-e2462be613d2",
  "agent_id": "codex",
  "capabilities": ["backend", "mcp"]
}
```

2. String form (normalized deterministically):

```json
{
  "project_id": "66b79018-c5e0-4880-864e-e2462be613d2",
  "agent_id": "codex",
  "capabilities": "backend,mcp"
}
```

Also valid: `"capabilities": "backend"` and whitespace is trimmed.

Invalid payloads (for example non-string list items or non-string/non-list values) return domain error code `INVALID_CAPABILITIES`.
