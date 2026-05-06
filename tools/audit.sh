#!/usr/bin/env bash
# VibeSafe Audit Tool v1.0
# Usage: ./audit.sh [project_path] [--json] [--quiet]
# Exit codes: 0=clean, 1=critical/high CVEs, 2=unmaintained, 3=error

set -euo pipefail

PROJECT_PATH="${1:-.}"
JSON_OUTPUT=false
QUIET=false
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

for arg in "$@"; do
  case $arg in
    --json) JSON_OUTPUT=true ;;
    --quiet) QUIET=true ;;
  esac
done

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

log() { $QUIET || echo -e "$1"; }
log_section() { log "\n${BOLD}${BLUE}▶ $1${NC}"; }

# ── Result accumulators ───────────────────────────────────────────────────
CRITICAL=0; HIGH=0; MEDIUM=0; LOW=0
UNMAINTAINED=()
BLOCKED_REASONS=()
WARNINGS=()
PACKAGES_CHECKED=()

# ── npm audit ────────────────────────────────────────────────────────────
run_npm_audit() {
  local pkg_json="$PROJECT_PATH/package.json"
  [[ -f "$pkg_json" ]] || return 0

  log_section "npm audit"

  if ! command -v npm &>/dev/null; then
    WARNINGS+=("npm not found — skipping npm audit")
    return 0
  fi

  local audit_out
  audit_out=$(cd "$PROJECT_PATH" && npm audit --json 2>/dev/null) || true

  if [[ -z "$audit_out" ]]; then
    WARNINGS+=("npm audit returned no output")
    return 0
  fi

  local result
  result=$(echo "$audit_out" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    vulns = d.get('vulnerabilities', {})
    critical = sum(1 for v in vulns.values() if v.get('severity') == 'critical')
    high = sum(1 for v in vulns.values() if v.get('severity') == 'high')
    medium = sum(1 for v in vulns.values() if v.get('severity') == 'medium')
    low = sum(1 for v in vulns.values() if v.get('severity') == 'low')
    names = list(vulns.keys())[:20]
    print(f'{critical}|{high}|{medium}|{low}|{\";\".join(names)}')
except Exception as e:
    print(f'0|0|0|0|error:{e}')
" 2>/dev/null)

  IFS='|' read -r c h m l names <<< "$result"
  CRITICAL=$((CRITICAL + c))
  HIGH=$((HIGH + h))
  MEDIUM=$((MEDIUM + m))
  LOW=$((LOW + l))

  IFS=';' read -ra pkg_list <<< "$names"
  PACKAGES_CHECKED+=("${pkg_list[@]}")

  if [[ $c -gt 0 ]]; then
    BLOCKED_REASONS+=("npm: $c critical CVEs")
    log "${RED}✗ Critical: $c  High: $h  Medium: $m  Low: $l${NC}"
  elif [[ $h -gt 0 ]]; then
    WARNINGS+=("npm: $h high severity CVEs — fix with: npm audit fix")
    log "${YELLOW}⚠ High: $h  Medium: $m  Low: $l${NC}"
  else
    log "${GREEN}✓ No critical/high CVEs (medium: $m, low: $l)${NC}"
  fi
}

# ── pip-audit ────────────────────────────────────────────────────────────
run_pip_audit() {
  local has_req=false
  [[ -f "$PROJECT_PATH/requirements.txt" ]] && has_req=true
  [[ -f "$PROJECT_PATH/pyproject.toml" ]] && has_req=true
  [[ -f "$PROJECT_PATH/setup.py" ]] && has_req=true
  $has_req || return 0

  log_section "pip-audit"

  if ! command -v pip-audit &>/dev/null; then
    log "${YELLOW}pip-audit not found. Installing...${NC}"
    pip install pip-audit --quiet 2>/dev/null || {
      WARNINGS+=("pip-audit install failed — skipping Python audit")
      return 0
    }
  fi

  local audit_out
  audit_out=$(cd "$PROJECT_PATH" && pip-audit --format=json 2>/dev/null) || true

  if [[ -z "$audit_out" ]]; then
    WARNINGS+=("pip-audit returned no output")
    return 0
  fi

  local result
  result=$(echo "$audit_out" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    deps = d.get('dependencies', [])
    critical = sum(1 for dep in deps for v in dep.get('vulns', []) if 'CRITICAL' in v.get('id','').upper() or v.get('severity','').upper()=='CRITICAL')
    high = sum(1 for dep in deps for v in dep.get('vulns', []) if v.get('severity','').upper()=='HIGH')
    names = [dep.get('name','?') for dep in deps[:20]]
    print(f'{critical}|{high}|{\";\".join(names)}')
except Exception as e:
    print(f'0|0|error:{e}')
" 2>/dev/null)

  IFS='|' read -r c h names <<< "$result"
  CRITICAL=$((CRITICAL + c))
  HIGH=$((HIGH + h))

  IFS=';' read -ra pkg_list <<< "$names"
  PACKAGES_CHECKED+=("${pkg_list[@]}")

  if [[ $c -gt 0 ]]; then
    BLOCKED_REASONS+=("pip: $c critical vulnerabilities")
    log "${RED}✗ Critical: $c  High: $h${NC}"
  elif [[ $h -gt 0 ]]; then
    WARNINGS+=("pip: $h high severity issues — fix with: pip-audit --fix")
    log "${YELLOW}⚠ High: $h${NC}"
  else
    log "${GREEN}✓ No critical/high Python vulnerabilities${NC}"
  fi
}

# ── OSV.dev single package check ────────────────────────────────────────
check_osv() {
  local pkg="$1" ecosystem="${2:-npm}"
  local result
  result=$(curl -sf -X POST "https://api.osv.dev/v1/query" \
    -H "Content-Type: application/json" \
    -d "{\"package\":{\"name\":\"$pkg\",\"ecosystem\":\"$ecosystem\"}}" \
    --max-time 5 2>/dev/null) || { echo "0"; return; }
  echo "$result" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(len(d.get('vulns',[])))
" 2>/dev/null || echo "0"
}

# ── Maintenance check via GitHub API ─────────────────────────────────────
check_maintenance() {
  local owner="$1" repo="$2" threshold_days="${3:-365}"
  local result
  result=$(curl -sf "https://api.github.com/repos/$owner/$repo/commits?per_page=1" \
    --max-time 5 2>/dev/null) || { echo "unknown"; return; }

  local last_commit
  last_commit=$(echo "$result" | python3 -c "
import json,sys,datetime
d=json.load(sys.stdin)
if not d: print('no-commits'); exit()
date_str = d[0]['commit']['author']['date']
dt = datetime.datetime.fromisoformat(date_str.replace('Z','+00:00'))
now = datetime.datetime.now(datetime.timezone.utc)
days = (now - dt).days
print(f'{days}d:{date_str[:10]}')
" 2>/dev/null || echo "unknown")

  echo "$last_commit"
}

# ── .gitignore secrets check ────────────────────────────────────────────
check_secrets_policy() {
  log_section "Secrets policy"
  local issues=()

  # Check .gitignore
  if [[ -f "$PROJECT_PATH/.gitignore" ]]; then
    grep -q "\.env$\|\.env\." "$PROJECT_PATH/.gitignore" 2>/dev/null || \
      issues+=(".env not in .gitignore")
    grep -q "\*\.key\|\*.pem\|secrets\." "$PROJECT_PATH/.gitignore" 2>/dev/null || \
      WARNINGS+=("Consider adding *.key, *.pem, secrets.* to .gitignore")
  else
    issues+=(".gitignore missing")
  fi

  # Scan for potential secrets in source files
  local secret_patterns='(api_key|api_secret|password|secret|token|credential|private_key)\s*=\s*["\x27][^"\x27${}]{8,}'
  local found_secrets
  found_secrets=$(grep -riE "$secret_patterns" "$PROJECT_PATH" \
    --include="*.js" --include="*.ts" --include="*.py" --include="*.go" \
    --include="*.rb" --include="*.php" --include="*.java" \
    --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=venv \
    --exclude-dir=__pycache__ -l 2>/dev/null | head -5) || true

  if [[ -n "$found_secrets" ]]; then
    BLOCKED_REASONS+=("Potential secrets found in source: $found_secrets")
    log "${RED}✗ Potential hardcoded secrets detected:${NC}"
    echo "$found_secrets" | while read -r f; do log "  ${RED}→ $f${NC}"; done
  fi

  if [[ ${#issues[@]} -gt 0 ]]; then
    for issue in "${issues[@]}"; do
      WARNINGS+=("Secrets policy: $issue")
      log "${YELLOW}⚠ $issue${NC}"
    done
  else
    log "${GREEN}✓ .gitignore configured${NC}"
    [[ -n "$found_secrets" ]] || log "${GREEN}✓ No hardcoded secrets detected${NC}"
  fi
}

# ── Determine status ────────────────────────────────────────────────────
determine_status() {
  if [[ ${#BLOCKED_REASONS[@]} -gt 0 ]]; then
    echo "BLOCKED"
  elif [[ $HIGH -gt 0 || ${#UNMAINTAINED[@]} -gt 0 || ${#WARNINGS[@]} -gt 0 ]]; then
    echo "CONDITIONAL"
  else
    echo "CERTIFIED"
  fi
}

# ── JSON output ──────────────────────────────────────────────────────────
output_json() {
  local status
  status=$(determine_status)
  python3 -c "
import json, sys
data = {
    'timestamp': '$TIMESTAMP',
    'project': '$PROJECT_PATH',
    'status': '$status',
    'summary': {
        'critical': $CRITICAL,
        'high': $HIGH,
        'medium': $MEDIUM,
        'low': $LOW
    },
    'blocked_reasons': $(printf '%s\n' "${BLOCKED_REASONS[@]+"${BLOCKED_REASONS[@]}"}" | python3 -c 'import sys,json; print(json.dumps([l.rstrip() for l in sys.stdin]))'),
    'warnings': $(printf '%s\n' "${WARNINGS[@]+"${WARNINGS[@]}"}" | python3 -c 'import sys,json; print(json.dumps([l.rstrip() for l in sys.stdin]))'),
    'packages_checked': $(printf '%s\n' "${PACKAGES_CHECKED[@]+"${PACKAGES_CHECKED[@]}"}" | python3 -c 'import sys,json; print(json.dumps(list(set(l.rstrip() for l in sys.stdin))))'),
    'unmaintained': $(printf '%s\n' "${UNMAINTAINED[@]+"${UNMAINTAINED[@]}"}" | python3 -c 'import sys,json; print(json.dumps([l.rstrip() for l in sys.stdin]))')
}
print(json.dumps(data, indent=2))
"
}

# ── Human output ─────────────────────────────────────────────────────────
output_human() {
  local status
  status=$(determine_status)
  echo ""
  echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  case "$status" in
    CERTIFIED)
      echo -e "${BOLD}${GREEN}  VibeSafe: ✅ CERTIFIED${NC}"
      echo -e "  All clear — safe to code"
      ;;
    CONDITIONAL)
      echo -e "${BOLD}${YELLOW}  VibeSafe: ⚠️  CONDITIONAL${NC}"
      echo -e "  Risks found — user decision required"
      for w in "${WARNINGS[@]+"${WARNINGS[@]}"}"; do echo -e "  ${YELLOW}• $w${NC}"; done
      ;;
    BLOCKED)
      echo -e "${BOLD}${RED}  VibeSafe: 🔴 BLOCKED${NC}"
      echo -e "  Fix these before coding:"
      for r in "${BLOCKED_REASONS[@]+"${BLOCKED_REASONS[@]}"}"; do echo -e "  ${RED}• $r${NC}"; done
      ;;
  esac
  echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo "  Generate certificate: ./tools/stay-safe-gen.sh '$PROJECT_PATH' '$status'"
  echo ""
}

# ── Main ────────────────────────────────────────────────────────────────
main() {
  $QUIET || echo -e "\n${BOLD}VibeSafe Audit${NC} — $PROJECT_PATH\n"

  run_npm_audit
  run_pip_audit
  check_secrets_policy

  if $JSON_OUTPUT; then
    output_json
  else
    output_human
  fi

  local status
  status=$(determine_status)
  case "$status" in
    CERTIFIED) exit 0 ;;
    CONDITIONAL) exit 2 ;;
    BLOCKED) exit 1 ;;
  esac
}

main "$@"
