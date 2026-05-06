# VibeSafe Security Policy — HARNESS Addition (§14)

> Paste this as **Section 14** of your HARNESS.md file.
> Compatible with: Claude Code, Kimi, Hermes/Vox, OpenClaw, any LLM agent.

---

## 14. SECURITY PRE-FLIGHT — VibeSafe Protocol

**MANDATORY before any code that installs external packages.**

### Quick rule
```
New dependency → VibeSafe pre-flight → stay_safe.md CERTIFIED → code starts
```

### For ALL agents (interactive mode):
1. Before writing code with external libs: invoke vibe-safe skill or run `./tools/audit.sh`
2. If `stay_safe.md` shows **CERTIFIED** → proceed
3. If `stay_safe.md` shows **CONDITIONAL** → show user the risks, get explicit approval, then proceed
4. If `stay_safe.md` shows **BLOCKED** → redesign, pick alternative lib, re-audit. Do NOT code until certified.

### For autonomous agents (Vox, Hermes, Goose):
- Do NOT block the user mid-flow for audits
- Run pre-flight if you have time; otherwise code first
- ALWAYS run post-coding scan (Phase 5)
- ALWAYS append `risk-report.md` to session output
- User sees risks after the work is done, not during

### Secrets policy (ABSOLUTE — no exceptions):
```
FORBIDDEN in source code:
  - API keys, tokens, passwords
  - Database connection strings with credentials
  - Private keys, certificates
  - Any value that starts with "sk-", "ghp_", "xoxb-", etc.

REQUIRED:
  - All secrets → .env file (local, gitignored)
  - .env.example → committed (dummy values only)
  - .gitignore → covers .env, *.key, secrets.*, credentials.*
  - Document all required env vars in README or .env.example
```

**If a library REQUIRES secrets in source code → BLOCKED. Find alternative or refactor.**

### When to skip (legitimate):
- Pure logic/refactoring with zero new dependencies → skip
- User explicitly types `/skip-audit` → log it, proceed, run post-scan
- Emergency hotfix (user says "ship now") → proceed, run post-scan, flag in handoff

### Audit tools available:
```bash
# Quick audit (any project):
/Volumes/2TB_APFS/projekty/vibe-safe/tools/audit.sh [project_path]

# Generate stay_safe.md:
/Volumes/2TB_APFS/projekty/vibe-safe/tools/stay-safe-gen.sh [audit_json]

# OSV check for single package (no tools needed):
curl -s -X POST https://api.osv.dev/v1/query \
  -d '{"package":{"name":"PKGNAME","ecosystem":"npm"}}' | python3 -m json.tool
```

### stay_safe.md location:
Always in **project root**. Never in subdirectory. Committed to git (it's documentation, not a secret).

### Re-audit triggers:
- Any new `npm install X` or `pip install X`
- stay_safe.md older than 7 days
- Before production deploy
- After `npm audit` or `pip-audit` reports new issues in CI

---

*VibeSafe v1.0 — github.com/nerua1/vibe-safe*
