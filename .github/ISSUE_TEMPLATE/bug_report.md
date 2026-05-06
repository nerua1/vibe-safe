---
name: Bug report
about: Something is broken or behaving unexpectedly
title: "[BUG] "
labels: bug
assignees: ''
---

## What happened

<!-- A clear, concise description of the bug. -->

## What you expected to happen

<!-- What should have happened instead? -->

## Steps to reproduce

```bash
# Paste the exact command(s) you ran
./tools/audit.sh /path/to/project
```

## Output / error

```
# Paste the full terminal output here
```

## Environment

- OS: <!-- e.g. macOS 15.4, Ubuntu 22.04 -->
- bash version: <!-- bash --version -->
- Node version (if npm project): <!-- node --version -->
- Python version (if Python project): <!-- python --version -->
- pip-audit version (if applicable): <!-- pip-audit --version -->
- jq version: <!-- jq --version -->
- curl version: <!-- curl --version | head -1 -->

## Project manifest

<!-- What does your project look like? Check all that apply -->
- [ ] package.json (Node/npm)
- [ ] requirements.txt (Python pip)
- [ ] pyproject.toml (Python)
- [ ] Pipfile (Python pipenv)
- [ ] go.mod (Go)
- [ ] Cargo.toml (Rust)
- [ ] Gemfile (Ruby)
- [ ] pom.xml (Java Maven)
- [ ] Other: ___

## Agent context (if relevant)

<!-- Were you running VibeSafe through an AI agent? Which one? -->
- [ ] Claude Code (`/vibe-safe` skill)
- [ ] Kimi (skill file)
- [ ] Hermes / Vox (HARNESS §14)
- [ ] OpenClaw (webhook)
- [ ] Direct CLI (no agent)

## Additional context

<!-- Anything else that might help diagnose the issue -->
