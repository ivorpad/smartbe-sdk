---
name: skill-installer
description: Fetch, audit, and install skills from GitHub, skills.sh, or any URL. Converts credentials to SmartBe SDK and creates the standard skill structure.
secrets: []
runtime: python
---

# Skill Installer

Fetch scripts from any source, audit them for security, convert credentials to SmartBe SDK, and install as a local skill.

## Usage

**Fetch and analyze a script from a URL:**
```bash
workspace/skills/skill-installer/run fetch "https://github.com/user/repo/blob/main/script.py"
```

**Fetch from a GitHub repo (auto-detects main script):**
```bash
workspace/skills/skill-installer/run fetch "https://github.com/user/repo"
```

**Fetch from skills.sh:**
```bash
workspace/skills/skill-installer/run fetch "https://skills.sh/skill-name"
```

**Scaffold a new skill from fetched source:**
```bash
workspace/skills/skill-installer/run scaffold --slug "my-skill" --name "My Skill" --runtime python --secrets SOME_API_KEY,OTHER_KEY
```

**Show installed skills:**
```bash
workspace/skills/skill-installer/run list
```

## Workflow

When a user asks to install a skill from a URL or describes a script they want to add:

### Step 1: Fetch
Run `workspace/skills/skill-installer/run fetch "<url>"`. This downloads the source files to a temp directory and outputs the path + file listing.

### Step 2: Read and Audit
Read every fetched file. Check for:

**BLOCK — security risks:**
- Hardcoded API keys/tokens in source (`sk-`, `AIza`, `ghp_`, bearer tokens)
- Shell injection (`eval`, `exec` with unsanitized input, `subprocess.call(shell=True)`)
- File access outside workspace (`/etc/`, `~/.ssh/`, `/var/`, absolute paths)
- Network calls to unexpected hosts (anything that isn't the documented API)
- Obfuscated code (base64-encoded payloads, minified suspicious patterns)
- Package installs from untrusted sources

**CONVERT — credential patterns:**
- `os.environ.get("KEY")` or `os.environ["KEY"]` → `from smartbe_secrets import secret; secret("KEY")`
- `process.env.KEY` → `import { secret } from '@smartbe/secrets'; await secret("KEY")`
- `$KEY` in bash → `$(smartbe-secret KEY)`

**NOTE — dependencies:**
- Python: PEP 723 inline metadata, requirements.txt, imports
- Node: package.json dependencies
- System tools needed

Tell the user what you found. If there are security concerns, explain them and ask whether to proceed.

### Step 3: Convert and Install
Run `workspace/skills/skill-installer/run scaffold --slug "<slug>" --name "<name>" --runtime <python|node|bash> --secrets KEY1,KEY2`

This creates:
```
workspace/skills/<slug>/
  SKILL.md     # You fill this in with description + usage
  run          # Pre-generated wrapper for the runtime
  scripts/     # Empty — you copy the converted source here
```

Then:
1. Copy the fetched source files into `scripts/`, with credentials rewritten to use SmartBe SDK
2. Edit the generated SKILL.md with the skill's description, usage examples, and secrets table
3. Verify the `run` wrapper is correct for the runtime

### Step 4: Guide on Secrets
Tell the user which secrets the skill needs and how to set them:
> Set `KEY_NAME` in **Mission Control > Integrations > Custom Environment Variables**.
> Get your API key from [provider's website].

## Security Model

Every script from the internet is untrusted. This skill enforces:

- **Audit before install** — no code runs until you've read and approved it
- **Credential isolation** — secrets resolve at runtime from KMS-encrypted control plane, never stored on disk
- **Sandbox containment** — skills run inside the Docker sandbox with dropped capabilities, no host access
- **No hidden network calls** — audit catches unexpected outbound connections
- **Explicit secrets declaration** — SKILL.md lists every secret so Mission Control can show what's missing

## Output

The `fetch` command outputs:
```
Fetched 3 files to /tmp/skill-fetch-abc123/
  script.py (2.4 KB)
  requirements.txt (45 B)
  README.md (1.1 KB)
```

The `scaffold` command outputs:
```
Created workspace/skills/my-skill/
  SKILL.md (template — edit with description)
  run (python wrapper — ready)
  scripts/ (empty — copy converted source here)
```

The `list` command outputs:
```
Installed skills:
  nano-banana-pro  python  [GEMINI_API_KEY]
  my-skill         node    [OPENAI_API_KEY]
```
