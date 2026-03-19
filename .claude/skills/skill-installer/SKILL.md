# skill-installer

Install skills from any source into the SmartBe SDK catalog. Fetches scripts from GitHub repos, skills.sh, URLs, or local paths — then audits, converts credentials to SmartBe SDK, generates the standard structure, and registers in the catalog.

## Trigger

Use when the user says "install skill", "add skill", "import skill", "convert script to skill", or provides a URL/path to a script they want packaged as a SmartBe skill.

## Arguments

`/skill-installer <source>`

Source can be:
- GitHub URL: `https://github.com/user/repo/blob/main/script.py`
- GitHub repo: `https://github.com/user/repo` (scans for installable scripts)
- skills.sh URL: `https://skills.sh/skill-name`
- Raw URL: `https://example.com/script.py`
- Local path: `./my-script.py` or `/path/to/tool/`

## Procedure

### 1. Fetch the source

- **GitHub URL**: Use `curl` or `gh` to fetch raw file(s). If it's a repo URL, clone or fetch the tree to identify the main script and dependencies.
- **skills.sh**: Fetch the skill manifest and script files.
- **Raw URL**: Download the file directly.
- **Local path**: Read from disk.

Identify ALL files the skill needs (main script, dependencies, config files, etc.).

### 2. Audit the script

Read every file and check for:

**Security issues (BLOCK if found):**
- Hardcoded credentials, API keys, tokens in source code
- Shell injection vectors (`eval`, `exec` with user input, unsanitized `subprocess`)
- Network calls to unexpected hosts (data exfiltration risk)
- File system writes outside the skill directory or workspace
- Attempts to read system files (`/etc/passwd`, SSH keys, etc.)
- Obfuscated code (base64-encoded payloads, minified code with suspicious patterns)
- Package installs from untrusted registries

**Credential patterns (CONVERT):**
- `os.environ.get("KEY")` or `os.environ["KEY"]` → `secret("KEY")`
- `process.env.KEY` → `await secret("KEY")`
- `$ENV_VAR` in bash → `$(smartbe-secret KEY)`
- Any hardcoded API key patterns (`sk-`, `AIza`, `ghp_`, etc.)
- Config files that reference environment variables for secrets

**Dependencies (NOTE):**
- Python: extract from `requirements.txt`, `pyproject.toml`, or PEP 723 inline metadata (`# /// script`)
- Node: extract from `package.json`
- System tools: note any `apt`/`brew` dependencies

Present the audit results to the user before proceeding. If security issues are found, explain them clearly and ask whether to proceed or abort.

### 3. Convert to SmartBe SDK format

**Determine the runtime:**
- `.py` → `python` (use `uv run` with PEP 723 inline deps)
- `.js`/`.ts` → `node` or `bun`
- `.sh` → `bash`

**Generate the slug:**
- From the script/repo name, lowercase, hyphens: `my-cool-tool` → `my-cool-tool`
- Must match `[a-z0-9_-]+`
- Ask user to confirm or rename

**Rewrite credentials:**
- Replace ALL `os.environ.get("KEY")` / `os.environ["KEY"]` with:
  ```python
  from smartbe_secrets import secret
  key = secret("KEY")
  ```
- Replace ALL `process.env.KEY` with:
  ```javascript
  import { secret } from '@smartbe/secrets'
  const key = await secret("KEY")
  ```
- For bash scripts, use the `run` wrapper pattern:
  ```bash
  export KEY="$(smartbe-secret KEY)"
  ```

**Create the directory structure:**
```
skills/{slug}/
  SKILL.md          # Generated from audit findings
  run               # Bash wrapper
  scripts/
    {original files} # Converted script(s)
```

**Generate `SKILL.md`:**
- Frontmatter: name, description, secrets list, runtime
- Body: usage with correct `workspace/skills/{slug}/run` paths, required secrets table with links to where to get them, any notes about the tool

**Generate `run` wrapper:**
- Python: set PYTHONPATH, exec with `uv run`
- Node: exec with `node`
- Bun: exec with `bun run`
- Bash: export secrets via `smartbe-secret`, exec script

**Update `skills/catalog.json`:**
- Add the new skill entry
- Preserve existing entries
- Sort alphabetically by slug

### 4. Present results

Show the user:
1. The complete directory structure created
2. The converted script with credential changes highlighted
3. The generated SKILL.md
4. The catalog.json diff
5. Required secrets and where to set them (Mission Control > Integrations)
6. Any warnings from the audit

### 5. Commit (if user approves)

Stage the new skill files and catalog.json update. Draft a commit message.

## Security Model

This skill enforces a security-first approach to script installation:

**Why auditing matters:**
Scripts from the internet run with the agent's permissions inside the sandbox. A malicious script could exfiltrate secrets, modify the workspace, or abuse API keys. The audit step catches common attack vectors before they reach the server.

**Why SmartBe SDK conversion matters:**
Raw scripts typically read secrets from environment variables (`os.environ`, `process.env`). On SmartBe servers, secrets are NOT in the environment — they're encrypted with AWS KMS in the control plane and resolved at runtime via the SDK. Without conversion, scripts silently fail to find credentials.

Converting to the SDK also means:
- Secrets never touch disk (resolved in-memory, cached per-process)
- Secrets are scoped per-tenant (each server has its own KMS-encrypted store)
- Secret access is auditable (control plane logs every resolution)
- Secrets can be rotated centrally without touching the server

**What the `run` wrapper provides:**
- Consistent entry point for any runtime (Python, Node, Bash)
- PYTHONPATH setup so `uv`'s isolated venv can find the system-installed SDK
- Clean process exec (no shell interpretation of arguments)

**What SKILL.md provides:**
- Machine-readable frontmatter for the catalog
- Agent-readable documentation (appended to TOOLS.md on install)
- Human-readable reference for developers
- Explicit secrets declaration so MC can show missing secrets in the UI

## References

- SmartBe SDK README: `/Users/ivor/Developer/projects/gradion/smartbe-sdk/README.md`
- Existing skill example: `/Users/ivor/Developer/projects/gradion/smartbe-sdk/skills/nano-banana-pro/`
- Catalog format: `/Users/ivor/Developer/projects/gradion/smartbe-sdk/skills/catalog.json`
- Python SDK resolver: `/Users/ivor/Developer/projects/gradion/smartbe-sdk/python/smartbe_secrets/_resolver.py`
