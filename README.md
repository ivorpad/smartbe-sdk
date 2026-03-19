# SmartBe SDK

Libraries and CLI for resolving secrets from the SmartBe control plane. Pre-installed on every SmartBe server.

## Components

| Component | Language | Path on server |
|-----------|----------|----------------|
| [CLI](cli/) | Bash | `/usr/local/bin/smartbe-secret` |
| [Python SDK](python/) | Python 3.10+ | `/usr/lib/python3/dist-packages/smartbe_secrets` |
| [Node SDK](node/) | Node 18+ / Bun | `/usr/lib/node_modules/@smartbe/secrets` |
| [Skills Catalog](skills/) | Any | Installed to `workspace/skills/` via Mission Control |

## Quick Start

```python
# Python
from smartbe_secrets import secret
key = secret("GEMINI_API_KEY")
```

```typescript
// Node.js / Bun
import { secret } from '@smartbe/secrets'
const key = await secret("GEMINI_API_KEY")
```

```bash
# CLI (any language via subprocess)
KEY=$(smartbe-secret GEMINI_API_KEY)
```

## How It Works

Secrets are stored encrypted (AWS KMS) in the SmartBe control plane — never as environment variables on the server. The SDK reads a connection config file and calls the control plane API to resolve secrets at runtime.

**Resolution order:**
1. In-memory cache (process lifetime)
2. Control plane API (KMS-decrypted)
3. Environment variable fallback (for local dev)

---

# Creating Skills

Skills extend agent capabilities. They are scripts (Python, Node, Bash, etc.) that the agent can invoke. Each skill is a directory with a standard structure, listed in `skills/catalog.json`, and installed one-click via Mission Control.

## Skill Directory Structure

```
skills/
  my-skill/
    SKILL.md          # Description, secrets, usage (shown to agent on install)
    run               # Bash wrapper — resolves secrets, then exec's the script
    scripts/
      main.py         # The actual skill code (or .js, .ts, .sh, etc.)
```

## Step 1: Create `SKILL.md`

This file is the **source of truth**. It serves triple duty:
- **Catalog metadata** (YAML frontmatter) — displayed in Mission Control's Skills tab
- **Agent documentation** — appended to the agent's `TOOLS.md` on install, so the agent knows how to use it
- **Human reference** — readable docs for anyone browsing the repo

```markdown
---
name: my-skill
description: One-line description for catalog and agent context. Be specific about what it does.
secrets:
  - MY_API_KEY
  - ANOTHER_SECRET
runtime: python
---

# My Skill Name

What this skill does in 1-2 sentences.

## Usage

Run via the SmartBe wrapper (resolves secrets automatically):

```bash
workspace/skills/my-skill/run --arg1 "value" --arg2 "value"
```

## Required Secrets

| Key | Description | Get it from |
|-----|-------------|-------------|
| `MY_API_KEY` | API key for the service | [example.com/api-keys](https://example.com) |

Set via Mission Control > Integrations > Custom Environment Variables.
```

**Important:** Use `workspace/skills/{slug}/run` as the path in usage examples — this is the path the agent sees inside the sandbox.

## Step 2: Create the `run` Wrapper

The `run` script is a bash wrapper that:
1. Sets up the environment (PYTHONPATH for SDK access)
2. Exec's the actual skill script

```bash
#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

# Make SmartBe Python SDK available to uv's isolated venv
export PYTHONPATH="${PYTHONPATH:-}:/usr/lib/python3/dist-packages"

exec uv run "${SKILL_DIR}/scripts/main.py" "$@"
```

### Runtime-specific wrappers

**Python (with uv):**
```bash
export PYTHONPATH="${PYTHONPATH:-}:/usr/lib/python3/dist-packages"
exec uv run "${SKILL_DIR}/scripts/main.py" "$@"
```

**Node.js:**
```bash
exec node "${SKILL_DIR}/scripts/main.js" "$@"
```

**Bun:**
```bash
exec bun run "${SKILL_DIR}/scripts/main.ts" "$@"
```

**Bash (using CLI):**
```bash
export MY_API_KEY="$(smartbe-secret MY_API_KEY)"
exec "${SKILL_DIR}/scripts/main.sh" "$@"
```

## Step 3: Write the Skill Script

Use the SmartBe SDK to resolve secrets — **never read from `os.environ` directly**.

### Python

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///

from smartbe_secrets import secret

api_key = secret("MY_API_KEY")  # Resolves from control plane
```

### Node.js

```javascript
import { secret } from '@smartbe/secrets'

const apiKey = await secret("MY_API_KEY")
```

### Bash

```bash
#!/usr/bin/env bash
# Use the CLI for bash scripts
MY_API_KEY="$(smartbe-secret MY_API_KEY)"
curl -H "Authorization: Bearer $MY_API_KEY" https://api.example.com/...
```

## Step 4: Register in `catalog.json`

Add your skill to `skills/catalog.json`:

```json
{
  "skills": [
    {
      "slug": "my-skill",
      "name": "My Skill",
      "description": "One-line description matching SKILL.md frontmatter.",
      "runtime": "python",
      "secrets": ["MY_API_KEY"],
      "icon": "package",
      "tags": ["ai", "automation"]
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `slug` | Directory name. Lowercase, hyphens only: `[a-z0-9_-]+` |
| `name` | Display name in Mission Control |
| `description` | Shown in skill card + catalog |
| `runtime` | `python`, `node`, `bun`, or `bash` |
| `secrets` | Array of secret key names the skill needs |
| `icon` | Icon identifier: `image`, `package` (more coming) |
| `tags` | Searchable tags for filtering |

## What Happens on Install

When a user clicks "Install" in Mission Control's agent Skills tab:

1. **Download** — Skill files are fetched from this GitHub repo into the agent's workspace
   - Main agent: `workspace/skills/{slug}/`
   - Other agents: `agents/{agentId}/skills/{slug}/`
2. **Permissions** — Files are `chmod 775` so both MC and sandbox user can manage them
3. **TOOLS.md** — The SKILL.md content (minus frontmatter) is appended to the agent's `TOOLS.md` wrapped in HTML comment markers, so the agent knows the skill exists and how to invoke it
4. **`run` is made executable** — `chmod 755` on the wrapper script

On **uninstall**, the skill directory is removed and the TOOLS.md section is cleanly deleted.

## What Happens at Runtime

When the agent invokes `workspace/skills/my-skill/run --args`:

1. `run` wrapper sets `PYTHONPATH` (for Python) and exec's the script
2. Script calls `secret("MY_API_KEY")` via SmartBe SDK
3. SDK reads connection config from `/opt/openclaw/.openclaw/.control-plane-secrets.env`
4. SDK calls `POST /api/claw/{jobId}/runtime-secrets/resolve` on the SmartBe control plane
5. Control plane decrypts the secret via AWS KMS and returns the value
6. Secret is cached in-memory for the process lifetime — no disk writes

## Setting Secrets

Users set secrets in **Mission Control > Integrations > Custom Environment Variables**.

This stores the value in the SmartBe control plane (KMS-encrypted). The SDK resolves it at runtime. Secrets never appear as OS environment variables on the server.

## Testing Locally

For local development outside a SmartBe server:

```bash
# Option 1: Export as env vars (SDK falls back to env)
export MY_API_KEY="sk-..."
python scripts/main.py --arg value

# Option 2: Point to a local config file
export SMARTBE_CONFIG_PATH=./local-config.env
python scripts/main.py --arg value
```

## Available Skills

| Skill | Description | Runtime | Secrets |
|-------|-------------|---------|---------|
| [nano-banana-pro](skills/nano-banana-pro/) | Image generation/editing with Gemini 3 Pro Image | Python | `GEMINI_API_KEY` |

## License

MIT
