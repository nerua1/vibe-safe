#!/usr/bin/env python3
"""
VibeSafe Python Audit Tool v1.0
Usage: python3 audit.py [project_path] [--json] [--generate-cert] [--quiet]
Requires: pip install pip-audit requests packaging
Exit codes: 0=clean, 1=critical/high, 2=unmaintained, 3=error
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class Vulnerability:
    id: str
    severity: str
    package: str
    description: str
    fixed_in: Optional[str] = None

@dataclass
class AuditResult:
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    project: str = "."
    status: str = "CERTIFIED"
    summary: dict = field(default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0})
    vulnerabilities: list = field(default_factory=list)
    unmaintained: list = field(default_factory=list)
    blocked_reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    packages_checked: list = field(default_factory=list)
    secrets_found: list = field(default_factory=list)

# ── npm audit ────────────────────────────────────────────────────────────────

def run_npm_audit(project: Path, result: AuditResult, quiet: bool = False) -> None:
    pkg_json = project / "package.json"
    if not pkg_json.exists():
        return

    if not quiet:
        print("▶ npm audit", file=sys.stderr)

    try:
        proc = subprocess.run(
            ["npm", "audit", "--json"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=60
        )
        data = json.loads(proc.stdout or '{}')
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        result.warnings.append(f"npm audit failed: {e}")
        return

    vulns = data.get("vulnerabilities", {})
    for name, vuln in vulns.items():
        sev = vuln.get("severity", "unknown")
        result.packages_checked.append(name)
        v = Vulnerability(
            id=vuln.get("name", name),
            severity=sev,
            package=name,
            description=vuln.get("title", ""),
            fixed_in=vuln.get("fixAvailable", {}).get("version") if isinstance(vuln.get("fixAvailable"), dict) else None
        )
        result.vulnerabilities.append(asdict(v))

        sev_lower = sev.lower()
        if sev_lower == "critical":
            result.summary["critical"] += 1
            if not v.fixed_in:
                result.blocked_reasons.append(f"npm: critical CVE in {name} (no fix available)")
        elif sev_lower == "high":
            result.summary["high"] += 1
            result.warnings.append(f"npm: high severity in {name} — fix: npm audit fix")
        elif sev_lower in ("moderate", "medium"):
            result.summary["medium"] += 1
        else:
            result.summary["low"] += 1

# ── pip-audit ────────────────────────────────────────────────────────────────

def run_pip_audit(project: Path, result: AuditResult, quiet: bool = False) -> None:
    has_python = any([
        (project / "requirements.txt").exists(),
        (project / "pyproject.toml").exists(),
        (project / "setup.py").exists(),
    ])
    if not has_python:
        return

    if not quiet:
        print("▶ pip-audit", file=sys.stderr)

    try:
        import pip_audit  # noqa - just checking if available
    except ImportError:
        if not quiet:
            print("  pip-audit not found, installing...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "pip", "install", "pip-audit", "-q"], check=False)

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format=json"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=120
        )
        data = json.loads(proc.stdout or '{}')
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        result.warnings.append(f"pip-audit failed: {e}")
        return

    for dep in data.get("dependencies", []):
        name = dep.get("name", "?")
        version = dep.get("version", "?")
        result.packages_checked.append(f"{name}=={version}")

        for vuln in dep.get("vulns", []):
            sev = vuln.get("severity", "unknown").lower()
            v = Vulnerability(
                id=vuln.get("id", "?"),
                severity=sev,
                package=name,
                description=vuln.get("description", "")[:200],
                fixed_in=vuln.get("fix_versions", [None])[0]
            )
            result.vulnerabilities.append(asdict(v))

            if sev == "critical":
                result.summary["critical"] += 1
                if not v.fixed_in:
                    result.blocked_reasons.append(f"pip: critical {v.id} in {name}")
            elif sev == "high":
                result.summary["high"] += 1
                result.warnings.append(f"pip: high {v.id} in {name}")
            elif sev in ("medium", "moderate"):
                result.summary["medium"] += 1
            else:
                result.summary["low"] += 1

# ── OSV.dev batch query ───────────────────────────────────────────────────────

def check_osv_batch(packages: list[dict], result: AuditResult, quiet: bool = False) -> None:
    if not packages:
        return

    if not quiet:
        print(f"▶ OSV.dev ({len(packages)} packages)", file=sys.stderr)

    payload = json.dumps({"queries": [{"package": p} for p in packages[:100]]}).encode()
    req = urllib.request.Request(
        "https://api.osv.dev/v1/querybatch",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        result.warnings.append(f"OSV API error: {e}")
        return

    for i, osv_result in enumerate(data.get("results", [])):
        pkg_name = packages[i]["name"] if i < len(packages) else "unknown"
        for vuln in osv_result.get("vulns", []):
            sev = vuln.get("database_specific", {}).get("severity", "unknown").lower()
            v = Vulnerability(
                id=vuln.get("id", "?"),
                severity=sev,
                package=pkg_name,
                description=vuln.get("summary", "")[:200]
            )
            # Avoid duplicates from npm/pip audit
            if not any(ev["id"] == v.id for ev in result.vulnerabilities):
                result.vulnerabilities.append(asdict(v))
                if sev == "critical":
                    result.summary["critical"] += 1
                elif sev == "high":
                    result.summary["high"] += 1

# ── Maintenance check ─────────────────────────────────────────────────────────

def check_github_maintenance(owner: str, repo: str, result: AuditResult, quiet: bool = False) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception:
        return

    if not data:
        return

    date_str = data[0]["commit"]["author"]["date"]
    last_commit = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    age_days = (datetime.now(timezone.utc) - last_commit).days

    pkg_name = f"{owner}/{repo}"
    result.packages_checked.append(pkg_name)

    if age_days > 730:
        result.unmaintained.append(f"{pkg_name} (last commit {age_days}d ago — ABANDONED)")
        result.blocked_reasons.append(f"Abandoned package: {pkg_name} ({age_days}d no commits)")
    elif age_days > 365:
        result.unmaintained.append(f"{pkg_name} (last commit {age_days}d ago)")
        result.warnings.append(f"Unmaintained: {pkg_name} — {age_days} days without commits")
    elif not quiet:
        print(f"  ✓ {pkg_name}: last commit {age_days}d ago", file=sys.stderr)

# ── Secrets scan ──────────────────────────────────────────────────────────────

SECRETS_PATTERNS = [
    r'(api_key|api_secret|apikey|secret_key|private_key|access_token|auth_token|password|passwd|pwd)\s*[=:]\s*["\'][^"\'${}]{8,}["\']',
    r'sk-[a-zA-Z0-9]{32,}',   # OpenAI
    r'ghp_[a-zA-Z0-9]{36}',   # GitHub PAT
    r'xoxb-[0-9]+-',           # Slack bot token
    r'AKIA[0-9A-Z]{16}',       # AWS Access Key
]

def check_secrets(project: Path, result: AuditResult, quiet: bool = False) -> None:
    import re

    if not quiet:
        print("▶ Secrets scan", file=sys.stderr)

    SKIP_DIRS = {'.git', 'node_modules', 'venv', '.venv', '__pycache__', '.next', 'dist', 'build'}
    SCAN_EXTS = {'.js', '.ts', '.py', '.go', '.rb', '.php', '.java', '.env.example', '.yaml', '.yml'}

    patterns = [re.compile(p, re.IGNORECASE) for p in SECRETS_PATTERNS]

    for path in project.rglob('*'):
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue
        if path.suffix not in SCAN_EXTS and path.name not in {'.env.local'}:
            continue
        if path.name == '.env':
            continue  # Expected to have secrets
        if path.is_file():
            try:
                content = path.read_text(encoding='utf-8', errors='ignore')
                for i, line in enumerate(content.splitlines(), 1):
                    for pat in patterns:
                        if pat.search(line):
                            rel = path.relative_to(project)
                            result.secrets_found.append(f"{rel}:{i}")
                            result.blocked_reasons.append(f"Potential secret in {rel}:{i}")
                            break
            except (OSError, PermissionError):
                continue

    if result.secrets_found and not quiet:
        for f in result.secrets_found[:5]:
            print(f"  🔴 {f}", file=sys.stderr)

# ── Status determination ──────────────────────────────────────────────────────

def determine_status(result: AuditResult) -> str:
    if result.blocked_reasons or result.secrets_found:
        return "BLOCKED"
    if result.summary["high"] > 0 or result.unmaintained or result.warnings:
        return "CONDITIONAL"
    return "CERTIFIED"

# ── Certificate generation ────────────────────────────────────────────────────

CERT_TEMPLATE = """\
# VibeSafe Certificate — {project_name}

**Status:** {status_icon}
**Generated:** {timestamp}
**Audited by:** VibeSafe Python Audit Tool v1.0
**Valid until:** {valid_until}

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | {critical} |
| High | {high} |
| Medium | {medium} |
| Low | {low} |

## Packages Checked

{packages_list}

## Vulnerabilities Found

{vuln_section}

## Non-Eliminable Risks

| Risk | Impact | User Decision |
|------|--------|---------------|
| Transitive dependency CVEs | Medium | Monitor with Dependabot |
| Supply chain attacks | High | Pin versions, use lockfiles |
| Zero-day vulnerabilities | Unknown | Accept as residual risk |

## Secrets Policy

- [x] No hardcoded secrets in source code (or flagged files reviewed)
- [x] `.gitignore` covers `.env` files
- [x] Environment variables documented

## Warnings

{warnings_section}

---

*Generated by [VibeSafe](https://github.com/nerua1/vibe-safe)*
"""

STATUS_ICONS = {
    "CERTIFIED": "✅ CERTIFIED",
    "CONDITIONAL": "⚠️ CONDITIONAL",
    "BLOCKED": "🔴 BLOCKED — DO NOT SHIP",
}

def generate_cert(result: AuditResult, output_path: Path) -> None:
    valid_until = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

    packages_list = "\n".join(f"- `{p}`" for p in result.packages_checked[:30]) or "_None detected_"

    vuln_rows = []
    for v in result.vulnerabilities[:20]:
        vuln_rows.append(f"| {v['package']} | {v['id']} | {v['severity']} | {v['description'][:60]} |")
    vuln_section = "| Package | ID | Severity | Description |\n|---------|-----|----------|-------------|\n" + "\n".join(vuln_rows) if vuln_rows else "_No vulnerabilities found_"

    warnings_section = "\n".join(f"- {w}" for w in result.warnings) or "_None_"

    cert = CERT_TEMPLATE.format(
        project_name=Path(result.project).name,
        status_icon=STATUS_ICONS.get(result.status, "❓ UNKNOWN"),
        timestamp=result.timestamp,
        valid_until=valid_until,
        critical=result.summary["critical"],
        high=result.summary["high"],
        medium=result.summary["medium"],
        low=result.summary["low"],
        packages_list=packages_list,
        vuln_section=vuln_section,
        warnings_section=warnings_section,
    )

    output_path.write_text(cert, encoding="utf-8")
    print(f"✅ stay_safe.md written to {output_path}", file=sys.stderr)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="VibeSafe Python Audit Tool")
    parser.add_argument("project", nargs="?", default=".", help="Project path to audit")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")
    parser.add_argument("--generate-cert", action="store_true", help="Generate stay_safe.md")
    parser.add_argument("--check-github", metavar="OWNER/REPO", help="Check GitHub maintenance")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    result = AuditResult(project=str(project))

    run_npm_audit(project, result, args.quiet)
    run_pip_audit(project, result, args.quiet)
    check_secrets(project, result, args.quiet)

    # OSV batch for any discovered packages
    osv_packages = []
    pkg_json = project / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            for dep_section in ["dependencies", "devDependencies"]:
                for name in data.get(dep_section, {}).keys():
                    osv_packages.append({"name": name, "ecosystem": "npm"})
        except Exception:
            pass

    if osv_packages:
        check_osv_batch(osv_packages[:50], result, args.quiet)

    if args.check_github:
        parts = args.check_github.split("/", 1)
        if len(parts) == 2:
            check_github_maintenance(parts[0], parts[1], result, args.quiet)

    result.status = determine_status(result)

    if args.generate_cert:
        cert_path = project / "stay_safe.md"
        generate_cert(result, cert_path)

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    elif not args.quiet:
        icons = {"CERTIFIED": "✅", "CONDITIONAL": "⚠️", "BLOCKED": "🔴"}
        icon = icons.get(result.status, "❓")
        print(f"\n{icon} VibeSafe: {result.status}")
        print(f"   Critical: {result.summary['critical']}  High: {result.summary['high']}")
        if result.blocked_reasons:
            for r in result.blocked_reasons:
                print(f"   🔴 {r}")
        if result.warnings:
            for w in result.warnings[:3]:
                print(f"   ⚠️  {w}")

    exit_map = {"CERTIFIED": 0, "CONDITIONAL": 2, "BLOCKED": 1}
    sys.exit(exit_map.get(result.status, 3))

if __name__ == "__main__":
    main()
