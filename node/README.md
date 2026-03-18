# @smartbe/secrets

Node.js/Bun SDK for resolving secrets from the SmartBe control plane.

## Installation

```bash
npm install @smartbe/secrets
# or
bun add @smartbe/secrets
```

## Usage

```typescript
import { secret } from '@smartbe/secrets'

const apiKey = await secret('GEMINI_API_KEY')
```

The SDK resolves secrets in this order:
1. In-memory cache (process lifetime)
2. SmartBe control plane API
3. Environment variable fallback (for local dev)

## Configuration

Reads control-plane connection info from `/opt/openclaw/.control-plane-secrets.env`. Override with `SMARTBE_CONFIG_PATH` env var.
