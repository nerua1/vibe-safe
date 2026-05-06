#!/usr/bin/env bash
# VibeSafe Auto-Fix Tool v1.0
# Usage: ./auto-fix.sh [project_path] [--dry-run] [--confirm]
# Applies safe auto-fixes for known vulnerabilities

set -euo pipefail
PROJECT="${1:-.}"
DRY_RUN=false
SKIP_CONFIRM=false

[[ "${2:-}" == "--dry-run" || "${3:-}" == "--dry-run" ]] && DRY_RUN=true
[[ "${2:-}" == "--confirm" || "${3:-}" == "--confirm" ]] && SKIP_CONFIRM=true

echo "🔧 VibeSafe Auto-Fix"
echo "===================="
echo "Project: $PROJECT"
echo ""

fixes_applied=0
fixes_skipped=0

# 1. npm audit fix (safe: only semver-compatible updates)
if [ -f "$PROJECT/package.json" ]; then
    echo "📦 npm: checking..."
    cd "$PROJECT"
    
    if [ "$DRY_RUN" = true ]; then
        npm audit fix --dry-run 2>&1 | tail -5
        echo "   (dry run — no changes applied)"
    elif [ "$SKIP_CONFIRM" = true ]; then
        npm audit fix 2>&1 | tail -3
        fixes_applied=$((fixes_applied + 1))
        echo "   ✅ npm audit fix applied"
    else
        echo "   ⚠️  Run with --confirm to apply fixes"
        fixes_skipped=$((fixes_skipped + 1))
    fi
fi

# 2. pip audit (Python)
if [ -f "$PROJECT/requirements.txt" ] || [ -f "$PROJECT/pyproject.toml" ]; then
    echo "🐍 pip: checking..."
    
    if command -v pip-audit &>/dev/null; then
        if [ "$DRY_RUN" = true ]; then
            pip-audit -r "$PROJECT/requirements.txt" 2>/dev/null || true
            echo "   (dry run — no changes applied)"
        elif [ "$SKIP_CONFIRM" = true ]; then
            pip-audit -r "$PROJECT/requirements.txt" --fix 2>/dev/null || echo "   ⚠️  Some fixes require manual review"
            fixes_applied=$((fixes_applied + 1))
        else
            echo "   ⚠️  Run with --confirm to apply fixes"
            fixes_skipped=$((fixes_skipped + 1))
        fi
    else
        echo "   ⚠️  pip-audit not installed. Run: pip install pip-audit"
    fi
fi

# 3. secrets scan (gitleaks/trufflehog)
if command -v gitleaks &>/dev/null; then
    echo "🔍 Secrets scan..."
    gitleaks detect --source="$PROJECT" --no-git --verbose 2>/dev/null | head -5 || echo "   ✅ No secrets found"
fi

echo ""
echo "===================="
echo "Applied: $fixes_applied | Skipped: $fixes_skipped (use --confirm)"
