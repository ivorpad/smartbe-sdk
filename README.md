# SmartBe SDK

Libraries and CLI for resolving secrets from the SmartBe control plane inside sandbox environments.

## Components

| Component | Language | Install |
|-----------|----------|---------|
| [CLI](cli/) | Bash | Pre-installed in sandbox |
| [Python SDK](python/) | Python 3.9+ | `pip install smartbe-secrets` |
| [Node SDK](node/) | Node 18+ / Bun | `npm install @smartbe/secrets` |

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
smartbe-secret GEMINI_API_KEY
```

## How It Works

Scripts running inside SmartBe sandbox containers need access to API keys and secrets. These secrets are stored securely in the SmartBe control plane (not as environment variables).

The SDK reads a config file mounted into the sandbox at `/opt/openclaw/.control-plane-secrets.env` and calls the control plane's secret resolution API.

**Resolution order:**
1. In-memory cache (process lifetime)
2. Control plane API
3. Environment variable fallback (for local dev / non-SmartBe environments)

## Configuration

The SDK automatically reads from `/opt/openclaw/.control-plane-secrets.env`. For local development, set `SMARTBE_CONFIG_PATH` to point to your config file, or just export the secrets as regular environment variables.

## License

MIT
