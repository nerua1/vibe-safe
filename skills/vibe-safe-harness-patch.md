# VibeSafe — HARNESS Patch (Section §14)

> **How to use this file:**
> Copy the block below and APPEND it to your HARNESS.md as Section 14.
> This makes VibeSafe protocol available to every agent that reads the HARNESS.
>
> Compatible with: Claude Code, Kimi CLI, Hermes/Vox, Goose, OpenClaw, any LLM agent.

---

## §14. SECURITY PRE-FLIGHT — VibeSafe Protocol

**STATUS: MANDATORY**
Run before any code that installs or uses external packages/libraries.

---

### Core Rule

```
external dependency discovered
         |
         v
invoke VibeSafe (./tools/audit.sh OR /vibe-safe skill)
         |
    _____|_____
   |           |
CERTIFIED   CONDITIONAL    BLOCKED
   |           |              |
 code       get user       redesign
 freely     approval       required
```

### Interactive Mode (Claude Code, Kimi interactive, Cursor)

**Before writing any code that uses external packages:**

1. List every planned library in a dependency table (Phase 1 of vibe-safe skill)
2. Run: `./tools/audit.sh [project_path]`
   - If not available: use OSV API directly (no tools required — see below)
3. Read `stay_safe.md` status:
   - `CERTIFIED` → proceed immediately
   - `CONDITIONAL` → show user the risks, wait for explicit "I accept" or `/skip-audit`
   - `BLOCKED` → tell user, redesign with alternative library, re-audit
4. Once certified: code starts

**Skip mechanism:** If user types `/skip-audit`:
- Log it in stay_safe.md: `Status: USER-WAIVED — skipped at [timestamp]`
- Proceed to coding
- Still run post-coding scan (step 5)

### Autonomous Mode (Hermes/Vox, Goose, OpenClaw headless)

**NEVER block user flow for security questions in autonomous mode.**

Instead:
1. Code first (do not pause for pre-flight)
2. AFTER all code is written: run `./tools/audit.sh --json > .vibesafe/post-summary.json`
3. Run: `./tools/stay-safe-gen.sh .vibesafe/post-summary.json --template=risk-report`
4. ALWAYS append `risk-report.md` to session output
5. If critical CVEs found post-scan: prepend WARNING to output:

```
WARNING — VibeSafe Post-Coding Scan
Critical CVEs in installed packages: N
See risk-report.md — fix before deploying
```

### OSV API (no local tools required — works everywhere)

When audit.sh is not available, use this directly in any shell or tool call:

```bash
# Check any single package for known CVEs:
curl -s -X POST https://api.osv.dev/v1/query \
  -H "Content-Type: application/json" \
  -d '{"package":{"name":"PKGNAME","ecosystem":"npm"}}' \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
vulns=d.get('vulns',[])
print(f'{len(vulns)} CVEs found')
for v in vulns[:3]:
    print(' -', v['id'], v.get('summary','')[:60])
"
# Ecosystems: npm, PyPI, Go, crates.io, RubyGems, Maven, NuGet
```

### Secrets Policy — ABSOLUTE, NO EXCEPTIONS

```
FORBIDDEN in any source file (.js .ts .py .go .rb .java .rs .php):
  API keys, tokens, passwords, connection strings with credentials,
  private keys, certificates, secrets of any kind.

  Patterns to NEVER write:
    api_key = "sk-..."
    password = "hunter2"
    DATABASE_URL = "postgres://user:pass@host/db"
    PRIVATE_KEY = "-----BEGIN RSA..."

REQUIRED for every project with secrets:
  .env              ← real secrets, GITIGNORED, never committed
  .env.example      ← dummy/placeholder values, committed to repo
  .gitignore        ← must cover: .env, .env.*, *.key, *.pem, secrets.*, credentials.*

ACCESS pattern:
  Node.js:  process.env.MY_SECRET
  Python:   os.environ["MY_SECRET"] or os.getenv("MY_SECRET", "")
  Go:       os.Getenv("MY_SECRET")
  Bash:     ${MY_SECRET}
  Rust:     std::env::var("MY_SECRET")
```

If a library's documented usage requires secrets in source code → BLOCKED. Find alternative.

### Audit Tool Locations

```bash
# Full audit (auto-detects Node/Python):
/Volumes/2TB_APFS/projekty/vibe-safe/tools/audit.sh [project_path]

# Generate stay_safe.md from audit results:
/Volumes/2TB_APFS/projekty/vibe-safe/tools/stay-safe-gen.sh [audit_json]

# Python audit (alternative, more features):
python3 /Volumes/2TB_APFS/projekty/vibe-safe/tools/audit.py [project_path] --generate-cert

# Quick OSV check (no tools):
curl -s -X POST https://api.osv.dev/v1/query \
  -d '{"package":{"name":"PKG","ecosystem":"npm"}}'
```

### Skill File

All agents can read the full skill specification from:
`/Volumes/2TB_APFS/projekty/vibe-safe/skills/vibe-safe.md`

### stay_safe.md

- Always written to **project root**
- Always committed to git (it documents security decisions, not secrets)
- Expires after 7 days — re-audit before production deploy
- Re-audit also required when: new package installed, CI flags new CVE, before any deploy

### When VibeSafe Can Be Skipped (Legitimate)

- Pure refactoring with zero new external dependencies
- Documentation, comments, test data changes only
- User says "skip audit" or `/skip-audit` (log it, run post-scan anyway)
- Emergency hotfix under explicit time pressure (log it, run post-scan, note in handoff)

### Re-audit Triggers

- Any `npm install X` or `pip install X` during a session
- `stay_safe.md` is older than 7 days
- Before any production, staging, or demo deploy
- CI/CD pipeline reports new vulnerabilities in `security-gate.yml`
- A new CVE is publicly disclosed for a package in use

---

*VibeSafe §14 — appended to HARNESS by backend-architect agent, 2026-05-02*
*Full docs: /Volumes/2TB_APFS/projekty/vibe-safe/*
