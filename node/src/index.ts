/**
 * SmartBe Secrets SDK — resolve secrets from the SmartBe control plane.
 */

import { readFileSync } from 'node:fs'
import { existsSync } from 'node:fs'

const CONFIG_PATH = process.env.SMARTBE_CONFIG_PATH || '/opt/openclaw/.control-plane-secrets.env'

const cache = new Map<string, string>()
let config: Record<string, string> | null = null

function loadConfig(): Record<string, string> {
  if (config !== null) return config

  if (!existsSync(CONFIG_PATH)) {
    config = {}
    return config
  }

  const cfg: Record<string, string> = {}
  const content = readFileSync(CONFIG_PATH, 'utf-8')
  for (const line of content.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq > 0) {
      cfg[trimmed.slice(0, eq).trim()] = trimmed.slice(eq + 1).trim()
    }
  }

  config = cfg
  return config
}

async function resolveFromControlPlane(key: string): Promise<string | null> {
  const cfg = loadConfig()
  const baseUrl = cfg.OPENCLAW_CONTROL_PLANE_BASE_URL
  const jobId = cfg.OPENCLAW_CONTROL_PLANE_JOB_ID
  const token = cfg.OPENCLAW_CONTROL_PLANE_TOKEN

  if (!baseUrl || !jobId || !token) return null

  try {
    const res = await fetch(`${baseUrl}/api/claw/${jobId}/runtime-secrets/resolve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-OpenClaw-Callback-Secret': token,
      },
      body: JSON.stringify({ protocolVersion: 1, ids: [key] }),
      signal: AbortSignal.timeout(10000),
    })

    if (!res.ok) return null

    const body = await res.json() as { values?: Record<string, string> }
    const value = body.values?.[key]
    return typeof value === 'string' && value.length > 0 ? value : null
  } catch {
    return null
  }
}

/**
 * Resolve a secret by key name.
 *
 * Resolution order:
 * 1. In-memory cache
 * 2. Control plane API
 * 3. Environment variable fallback
 *
 * @throws Error if the secret cannot be found
 */
export async function secret(key: string): Promise<string> {
  const cached = cache.get(key)
  if (cached !== undefined) return cached

  // Try control plane
  const value = await resolveFromControlPlane(key)
  if (value !== null) {
    cache.set(key, value)
    return value
  }

  // Fallback to environment variable
  const envValue = process.env[key]
  if (envValue) {
    cache.set(key, envValue)
    return envValue
  }

  throw new Error(`Secret '${key}' not found in control plane or environment`)
}

/** Clear the in-memory secret cache. */
export function clearCache(): void {
  cache.clear()
}
