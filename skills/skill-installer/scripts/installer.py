#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
SmartBe Skill Installer — fetch, scaffold, and list skills.

Usage:
    installer.py fetch <url>
    installer.py scaffold --slug <slug> --name <name> --runtime <runtime> [--secrets KEY1,KEY2]
    installer.py list
"""

import argparse
import os
import re
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

WORKSPACE = os.environ.get("WORKSPACE", os.path.expanduser("~/workspace"))
SKILLS_DIR = Path(WORKSPACE) / "skills"

# --- Fetch -------------------------------------------------------------------

def cmd_fetch(url: str) -> None:
    """Download source files from a URL to a temp directory."""
    tmp = Path(tempfile.mkdtemp(prefix="skill-fetch-"))

    # GitHub blob URL → raw URL
    gh_blob = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)", url
    )
    if gh_blob:
        owner, repo, branch, path = gh_blob.groups()
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        name = Path(path).name
        dest = tmp / name
        print(f"Fetching {raw_url}")
        urllib.request.urlretrieve(raw_url, str(dest))
        print(f"\nFetched 1 file to {tmp}/")
        print(f"  {name} ({dest.stat().st_size:,} B)")
        return

    # GitHub repo URL → fetch tree via API
    gh_repo = re.match(r"https://github\.com/([^/]+)/([^/]+)/?$", url)
    if gh_repo:
        owner, repo = gh_repo.groups()
        _fetch_github_repo(owner, repo, tmp)
        return

    # skills.sh URL
    if "skills.sh" in url:
        _fetch_skills_sh(url, tmp)
        return

    # Generic URL → single file download
    name = Path(urllib.request.urlparse(url).path).name or "script"
    dest = tmp / name
    print(f"Fetching {url}")
    urllib.request.urlretrieve(url, str(dest))
    print(f"\nFetched 1 file to {tmp}/")
    print(f"  {name} ({dest.stat().st_size:,} B)")


def _fetch_github_repo(owner: str, repo: str, tmp: Path) -> None:
    """Fetch key files from a GitHub repo (README, main scripts, config)."""
    import json

    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
    req = urllib.request.Request(
        api_url, headers={"User-Agent": "SmartBe-Skill-Installer/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            tree = json.loads(resp.read())
    except Exception as e:
        print(f"Error fetching repo tree: {e}", file=sys.stderr)
        sys.exit(1)

    # Filter to interesting files (scripts, configs, docs)
    extensions = {".py", ".js", ".ts", ".sh", ".md", ".json", ".yaml", ".yml", ".toml"}
    skip_dirs = {"node_modules", ".git", "__pycache__", "dist", "build", ".venv"}
    files = []
    for item in tree.get("tree", []):
        if item.get("type") != "blob":
            continue
        path = item["path"]
        if any(path.startswith(d + "/") for d in skip_dirs):
            continue
        if Path(path).suffix in extensions or Path(path).name in {"Makefile", "Dockerfile"}:
            files.append(path)

    # Limit to first 20 files
    files = files[:20]
    count = 0
    for fpath in files:
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{fpath}"
        dest = tmp / fpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(raw_url, str(dest))
            count += 1
        except Exception:
            pass

    print(f"\nFetched {count} files to {tmp}/")
    for fpath in sorted(files):
        dest = tmp / fpath
        if dest.exists():
            print(f"  {fpath} ({dest.stat().st_size:,} B)")


def _fetch_skills_sh(url: str, tmp: Path) -> None:
    """Fetch a skill from skills.sh."""
    # skills.sh serves raw scripts — just download
    name = url.rstrip("/").split("/")[-1]
    dest = tmp / name
    print(f"Fetching from skills.sh: {url}")
    try:
        urllib.request.urlretrieve(url, str(dest))
        print(f"\nFetched 1 file to {tmp}/")
        print(f"  {name} ({dest.stat().st_size:,} B)")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


# --- Scaffold ----------------------------------------------------------------

RUN_TEMPLATES = {
    "python": """#!/usr/bin/env bash
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="${{PYTHONPATH:-}}:/usr/lib/python3/dist-packages"
exec uv run "${{SKILL_DIR}}/scripts/main.py" "$@"
""",
    "node": """#!/usr/bin/env bash
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
exec node "${{SKILL_DIR}}/scripts/main.js" "$@"
""",
    "bun": """#!/usr/bin/env bash
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
exec bun run "${{SKILL_DIR}}/scripts/main.ts" "$@"
""",
    "bash": """#!/usr/bin/env bash
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
{secrets_exports}
exec "${{SKILL_DIR}}/scripts/main.sh" "$@"
""",
}

SKILL_MD_TEMPLATE = """---
name: {slug}
description: TODO — one-line description of what this skill does.
secrets:{secrets_yaml}
runtime: {runtime}
---

# {name}

TODO — describe what this skill does.

## Usage

```bash
workspace/skills/{slug}/run [arguments]
```

## Required Secrets

{secrets_table}

Set via Mission Control > Integrations > Custom Environment Variables.
"""


def cmd_scaffold(slug: str, name: str, runtime: str, secrets: list[str]) -> None:
    """Create a skill directory with templates."""
    if not re.match(r"^[a-z0-9_-]+$", slug):
        print(f"Error: invalid slug '{slug}'. Use lowercase, hyphens, underscores.", file=sys.stderr)
        sys.exit(1)

    skill_dir = SKILLS_DIR / slug
    if skill_dir.exists():
        print(f"Error: {skill_dir} already exists.", file=sys.stderr)
        sys.exit(1)

    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True)

    # Generate SKILL.md
    secrets_yaml = "\n" + "\n".join(f"  - {s}" for s in secrets) if secrets else " []"
    if secrets:
        rows = "\n".join(f"| `{s}` | TODO — description | TODO — link |" for s in secrets)
        secrets_table = "| Key | Description | Get it from |\n|-----|-------------|-------------|\n" + rows
    else:
        secrets_table = "No secrets required."

    skill_md = SKILL_MD_TEMPLATE.format(
        slug=slug, name=name, runtime=runtime,
        secrets_yaml=secrets_yaml, secrets_table=secrets_table,
    )
    (skill_dir / "SKILL.md").write_text(skill_md)

    # Generate run wrapper
    template = RUN_TEMPLATES.get(runtime, RUN_TEMPLATES["bash"])
    if runtime == "bash" and secrets:
        exports = "\n".join(f'export {s}="$(smartbe-secret {s})"' for s in secrets)
        run_content = template.format(secrets_exports=exports)
    else:
        run_content = template.format(secrets_exports="")
    (skill_dir / "run").write_text(run_content)
    os.chmod(skill_dir / "run", 0o755)

    print(f"Created {skill_dir}/")
    print(f"  SKILL.md (template — edit with description)")
    print(f"  run ({runtime} wrapper — ready)")
    print(f"  scripts/ (empty — copy converted source here)")


# --- List --------------------------------------------------------------------

def cmd_list() -> None:
    """List installed skills."""
    if not SKILLS_DIR.exists():
        print("No skills directory found.")
        return

    skills = sorted(d for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "run").exists())
    if not skills:
        print("No skills installed.")
        return

    print("Installed skills:")
    for skill_dir in skills:
        skill_md = skill_dir / "SKILL.md"
        runtime = "?"
        secrets = []
        if skill_md.exists():
            content = skill_md.read_text()
            rm = re.search(r"^runtime:\s*(\w+)", content, re.MULTILINE)
            if rm:
                runtime = rm.group(1)
            for sm in re.finditer(r"^\s+-\s+([A-Z_]+)", content, re.MULTILINE):
                secrets.append(sm.group(1))

        secrets_str = ", ".join(secrets) if secrets else "none"
        print(f"  {skill_dir.name:<24} {runtime:<8} [{secrets_str}]")


# --- Main --------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="SmartBe Skill Installer")
    sub = parser.add_subparsers(dest="command")

    fetch_p = sub.add_parser("fetch", help="Fetch source files from a URL")
    fetch_p.add_argument("url", help="GitHub URL, skills.sh URL, or raw file URL")

    scaffold_p = sub.add_parser("scaffold", help="Create skill directory structure")
    scaffold_p.add_argument("--slug", required=True, help="Skill slug (lowercase, hyphens)")
    scaffold_p.add_argument("--name", required=True, help="Display name")
    scaffold_p.add_argument("--runtime", required=True, choices=["python", "node", "bun", "bash"])
    scaffold_p.add_argument("--secrets", default="", help="Comma-separated secret key names")

    sub.add_parser("list", help="List installed skills")

    args = parser.parse_args()

    if args.command == "fetch":
        cmd_fetch(args.url)
    elif args.command == "scaffold":
        secrets = [s.strip() for s in args.secrets.split(",") if s.strip()] if args.secrets else []
        cmd_scaffold(args.slug, args.name, args.runtime, secrets)
    elif args.command == "list":
        cmd_list()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
