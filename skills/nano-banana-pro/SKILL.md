---
name: nano-banana-pro
description: Generate/edit images with Nano Banana Pro (Gemini 3 Pro Image). Use for image create/modify requests incl. edits. Supports text-to-image + image-to-image; 1K/2K/4K.
secrets:
  - GEMINI_API_KEY
runtime: python
---

# Nano Banana Pro Image Generation & Editing

Generate new images or edit existing ones using Google's Nano Banana Pro API (Gemini 3 Pro Image).

## Usage

Run via the SmartBe wrapper (resolves secrets automatically):

**Generate new image:**
```bash
~/.smartbe/skills/nano-banana-pro/run --prompt "your image description" --filename "output.png" [--resolution 1K|2K|4K]
```

**Edit existing image:**
```bash
~/.smartbe/skills/nano-banana-pro/run --prompt "editing instructions" --filename "output.png" --input-image "path/to/input.png" [--resolution 1K|2K|4K]
```

**Important:** Always run from the user's current working directory so images are saved where the user is working.

## Required Secrets

| Key | Description | Get it from |
|-----|-------------|-------------|
| `GEMINI_API_KEY` | Google AI Studio API key | [aistudio.google.com](https://aistudio.google.com/apikey) |

Set via Mission Control Integrations > Custom Environment Variables.

## Default Workflow (draft > iterate > final)

- Draft (1K): quick feedback loop
  - `~/.smartbe/skills/nano-banana-pro/run --prompt "<draft prompt>" --filename "yyyy-mm-dd-hh-mm-ss-draft.png" --resolution 1K`
- Iterate: adjust prompt in small diffs; keep filename new per run
- Final (4K): only when prompt is locked
  - `~/.smartbe/skills/nano-banana-pro/run --prompt "<final prompt>" --filename "yyyy-mm-dd-hh-mm-ss-final.png" --resolution 4K`

## Resolution Options

- **1K** (default) - ~1024px resolution
- **2K** - ~2048px resolution
- **4K** - ~4096px resolution

## Prompt Templates

- Generation: "Create an image of: <subject>. Style: <style>. Composition: <camera/shot>. Lighting: <lighting>."
- Editing: "Change ONLY: <single change>. Keep identical: subject, composition, pose, lighting, color palette, background."

## Output

- Saves PNG to current directory
- Script outputs the full path to the generated image

## Filename Generation

Format: `{timestamp}-{descriptive-name}.png` (e.g., `2026-03-18-14-23-05-japanese-garden.png`)
