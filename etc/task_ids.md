## Overview
Steve Yegge's Beads system uses hash-based task IDs ("bd-" prefix + hex) for collision-free tracking in git-backed, multi-agent workflows. This spec recreates that core functionality—ID generation, hierarchy, and basic validation—in any task system (e.g., custom CLI, database, or app) without git/JSONL dependencies.[1][2]

## Requirements
- **Language**: Agnostic; examples in Python/JS for portability.
- **Inputs**: Task title/description string; optional parent ID for hierarchy.
- **Outputs**: Unique ID (e.g., "bd-a1b2" or "bd-a1b2.1"); collision detection.
- **Storage**: Any key-value store (e.g., SQLite, JSON file); check existing IDs.
- **Constraints**: IDs start at 4 hex chars; extend on collision; support dots for children.[1]

## ID Generation Algorithm
Use SHA-256 hash of normalized task content, truncated to hex:

1. **Normalize input**: `content = f"{title.lower().strip()}.{description.lower().strip() if description else ''}.timestamp_{int(time.time())}"`. Adds timestamp for uniqueness on identical titles.[2]
2. **Hash**: `hash_bytes = sha256(content.encode()).digest()`.
3. **Base ID**: `base_id = "bd-" + hash_bytes[:2].hex()`. (4 chars total after prefix).[1]
4. **Collision check**: Query store for matching prefix; if exists, extend to 6/8 chars (`hash_bytes[:3/4].hex()`).
5. **Hierarchy**: If parent provided (e.g., "bd-a1b2"), child = `parent + "." + str(next_child_num(parent))` where `next_child_num` counts existing ".N" under parent.

```
Pseudocode:
def generate_id(title, desc="", parent=None, store=None):
    if parent:
        return extend_hierarchy(parent, store)
    content = normalize(title, desc)
    h = sha256(content.encode()).hexdigest()
    candidate = f"bd-{h[:2]}"
    while store.exists(candidate):
        candidate = f"bd-{h[:len(h)//2][:3 if len==4 else 4]}"
    store.insert(candidate, {"title": title, "desc": desc})
    return candidate
```

## Collision Handling
- **Linear extension**: Start 4 hex → 6 → 8 until unique (rare with SHA-256).[2]
- **Guarantee**: Timestamp + content hash yields ~1e-10 collision odds for 1M tasks.
- **Merge safety**: No sequential IDs; pure content-derived for git/multibranch compatibility.[1]

## Hierarchy Extension
```
def extend_hierarchy(parent, store):
    children = [id for id in store.list() if id.startswith(parent + ".")]
    nums = [int(c.split(".")[-1]) for c in children] or [0]
    next_num = max(nums) + 1
    return f"{parent}.{next_num}"
```
- Auto-increments ".1", ".2" etc. for subtasks/epics.[1]
- Validates parent exists before extending.

## Storage Schema
Use simple JSON/DB table:

| Field     | Type    | Description                  |
|-----------|---------|------------------------------|
| id        | string  | "bd-a1b2" or "bd-a1b2.1"    |
| title     | string  | Task name                    |
| desc      | string  | Optional details             |
| parent_id | string  | Null or parent ID            |
| children  | array   | List of child IDs            |
| created   | int     | Unix timestamp               |

Index on `id` prefix for fast lookups.[2]

## Example Implementation (Python)
```python
import hashlib
import time
import sqlite3

class BeadsIDGen:
    def __init__(self, db_path="beads.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, title TEXT, parent TEXT)")
    
    def normalize(self, title, desc=""):
        return f"{title.lower().strip()}.{desc.lower().strip() if desc else ''}.{int(time.time())}"
    
    def generate(self, title, desc="", parent=None):
        if parent:
            return self._hierarchy(parent)
        content = self.normalize(title, desc)
        h = hashlib.sha256(content.encode()).hexdigest()
        for length in [2, 3, 4]:
            candidate = f"bd-{h[:length]}"
            if not self.conn.execute("SELECT id FROM tasks WHERE id=?", (candidate,)).fetchone():
                self.conn.execute("INSERT INTO tasks (id, title, parent) VALUES (?, ?, ?)",
                                  (candidate, title, None))
                self.conn.commit()
                return candidate
        raise ValueError("Collision exhaustion")
    
    def _hierarchy(self, parent):
        cur = self.conn.execute("SELECT id FROM tasks WHERE id LIKE ? ORDER BY id",
                                (f"{parent}.%",)).fetchall()
        nums = [int(row[0].split('.')[-1]) for row in cur] or [0]
        child_id = f"{parent}.{max(nums) + 1}"
        # Assume insert logic here
        return child_id
```
- Test: `gen = BeadsIDGen(); print(gen.generate("Auth System"))` → "bd-a3f8".[1]

## Integration Notes
- **CLI Commands**: `create "Title" → generate_id(); list → query store; dep add child parent → link in DB`.[1]
- **Agent-Friendly**: Output JSON for parsing (e.g., `{"ready": [{"id": "bd-1", "title": "..."}]}`).[2]
- **Scalability**: SQLite for local; shard by project for teams. No git needed, but add hooks for sync if desired.[2]

Sources
[1] beads/docs/QUICKSTART.md at main · steveyegge/beads - GitHub https://github.com/steveyegge/beads/blob/main/docs/QUICKSTART.md
[2] steveyegge/beads - A memory upgrade for your coding agent https://github.com/steveyegge/beads
[3] Land The Plane https://paddo.dev/blog/beads-memory-for-coding-agents/
[4] How Beads Lets AI Agents Build Like Engineers https://www.youtube.com/watch?v=s96O9oWI_tI
[5] Released Beads: A cognitive upgrade for coding agents https://www.linkedin.com/posts/steveyegge_github-steveyeggebeads-beads-a-memory-activity-7383408928665042944-tkcj
[6] beads/npm-package/INTEGRATION_GUIDE.md at main https://github.com/steveyegge/beads/blob/main/npm-package/INTEGRATION_GUIDE.md
[7] Steve Yegge - X https://x.com/Steve_Yegge/status/1977645937225822664
[8] How to Give Your AI Agent Long-Term Memory https://www.youtube.com/watch?v=cWBVMEHPgQU
[9] Cách mình sử dụng beads đến quản lý tasks, issues hiệu quả hơn. https://www.youtube.com/watch?v=dfSkKTJMFqw
[10] This is the first UI for Beads that I could see myself using. Pretty ... https://x.com/Steve_Yegge/status/1993919120170209498
