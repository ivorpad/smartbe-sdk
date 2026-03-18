# smartbe-secrets

Python SDK for resolving secrets from the SmartBe control plane.

## Installation

```bash
pip install smartbe-secrets
```

## Usage

```python
from smartbe_secrets import secret

api_key = secret("GEMINI_API_KEY")
```

The SDK resolves secrets in this order:
1. In-memory cache (process lifetime)
2. SmartBe control plane API
3. Environment variable fallback (for local dev)

## Configuration

The SDK reads control-plane connection info from `/opt/openclaw/.control-plane-secrets.env`. Override with `SMARTBE_CONFIG_PATH` env var.
