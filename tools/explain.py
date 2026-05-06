#!/usr/bin/env python3
"""
VibeSafe AI Explain Layer — translates CVE data into human language.
Usage: python3 tools/explain.py audit_result.json [--model lmstudio]
Output: human-readable risk explanations appended to audit output.
"""

import json, sys, os

def explain_with_lmstudio(vuln):
    """Use local LM Studio to explain a vulnerability in plain language."""
    import urllib.request
    
    prompt = f"""Explain this software vulnerability in plain, non-technical language. One paragraph. Focus on: what could actually happen to my project, and should I be worried?

Package: {vuln.get('package', 'unknown')}
Severity: {vuln.get('severity', 'unknown')}
CVE: {vuln.get('cve', 'N/A')}
Description: {vuln.get('description', 'No description available')}

Answer in this exact format:
RISK: [LOW/MEDIUM/HIGH/CRITICAL]
WHAT IT MEANS: [1-2 sentences in plain language]
SHOULD I WORRY? [Yes/No/Maybe — one sentence why]"""

    try:
        req = urllib.request.Request(
            "http://127.0.0.1:1234/v1/chat/completions",
            data=json.dumps({
                "model": "qwen3.5-9b-uncensored-hauhaucs-aggressive",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200
            }).encode(),
            headers={"Content-Type": "application/json"}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"RISK: UNKNOWN\nWHAT IT MEANS: Could not analyze this vulnerability (error: {str(e)[:50]})\nSHOULD I WORRY? Check manually"

def explain_static(vuln):
    """Static fallback explanation without LLM (offline-safe)."""
    severity = vuln.get("severity", "unknown").upper()
    pkg = vuln.get("package", "unknown package")
    
    templates = {
        "CRITICAL": f"RISK: CRITICAL\nWHAT IT MEANS: {pkg} has a known security hole that attackers are actively exploiting. Your project could be compromised.\nSHOULD I WORRY? YES — fix immediately or find alternative.",
        "HIGH": f"RISK: HIGH\nWHAT IT MEANS: {pkg} has a vulnerability that could expose your data or allow unauthorized access.\nSHOULD I WORRY? Yes — update or replace before production use.",
        "MODERATE": f"RISK: MEDIUM\nWHAT IT MEANS: {pkg} has a moderate issue — could be problematic in some configurations but probably won't affect most projects.\nSHOULD I WORRY? Maybe — review the details and decide.",
        "LOW": f"RISK: LOW\nWHAT IT MEANS: {pkg} has a minor issue — unlikely to affect your project in practice.\nSHOULD I WORRY? No — safe to use, just keep it updated.",
    }
    return templates.get(severity, templates["LOW"])

def main():
    audit_file = sys.argv[1] if len(sys.argv) > 1 else "audit_result.json"
    use_llm = "--llm" in sys.argv
    
    try:
        with open(audit_file) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {audit_file} not found. Run audit.sh first.")
        sys.exit(1)
    
    vulnerabilities = data.get("vulnerabilities", [])
    if not vulnerabilities:
        print("No vulnerabilities found. Nothing to explain.")
        return
    
    print(f"## AI Risk Analysis ({len(vulnerabilities)} vulnerabilities)\n")
    
    for i, vuln in enumerate(vulnerabilities, 1):
        print(f"### {i}. {vuln.get('package', 'unknown')}")
        
        if use_llm:
            explanation = explain_with_lmstudio(vuln)
        else:
            explanation = explain_static(vuln)
        
        print(explanation)
        print()

if __name__ == "__main__":
    main()
