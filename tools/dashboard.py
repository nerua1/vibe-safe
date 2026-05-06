#!/usr/bin/env python3
"""
VibeSafe Dashboard — security overview for all projects.
Usage: python3 tools/dashboard.py [--dir /path/to/projects]
Outputs: terminal dashboard + HTML report.
"""

import json, os, sys, glob
from datetime import datetime

def scan_projects(base_dir="."):
    projects = []
    for path in glob.glob(f"{base_dir}/**/stay_safe.md", recursive=True):
        if "node_modules" in path or ".git" in path:
            continue
        
        proj_dir = os.path.dirname(path)
        proj_name = os.path.basename(proj_dir)
        
        try:
            with open(path) as f:
                content = f.read()
        except:
            continue
        
        status = "UNKNOWN"
        if "CERTIFIED" in content:
            status = "🟢 CERTIFIED"
        elif "CONDITIONAL" in content:
            status = "🟡 CONDITIONAL"
        elif "BLOCKED" in content:
            status = "🔴 BLOCKED"
        elif "user-waived" in content:
            status = "⚪ WAIVED"
        
        # Count vulnerabilities
        cve_count = content.count("CVE-")
        
        projects.append({
            "name": proj_name,
            "status": status,
            "cves": cve_count,
            "path": proj_dir,
            "cert_date": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
        })
    
    return sorted(projects, key=lambda p: {"🔴": 0, "🟡": 1, "🟢": 2, "⚪": 3}.get(p["status"][:2], 99))

def terminal_dashboard(projects):
    if not projects:
        print("No projects with stay_safe.md found. Run audit first.")
        return
    
    print("╔══════════════════════════════════════════════════════╗")
    print("║         VibeSafe Security Dashboard                ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║ Projects: {len(projects):<3}  │  Updated: {datetime.now().strftime('%Y-%m-%d %H:%M'):<16} ║")
    print("╠══════════════════════════════════════════════════════╣")
    
    certified = sum(1 for p in projects if "🟢" in p["status"])
    conditional = sum(1 for p in projects if "🟡" in p["status"])
    blocked = sum(1 for p in projects if "🔴" in p["status"])
    total_cves = sum(p["cves"] for p in projects)
    
    print(f"║ 🟢 Certified: {certified:<2}  🟡 Conditional: {conditional:<2}  🔴 Blocked: {blocked:<2}  ║")
    print(f"║ Total CVEs found: {total_cves:<3}                              ║")
    print("╠══════════════════════════════════════════════════════╣")
    
    for p in projects:
        name = p["name"][:25]
        cves = f"{p['cves']} CVEs" if p["cves"] > 0 else "clean"
        print(f"║ {p['status']}  {name:<25} {cves:>10} ║")
    
    print("╚══════════════════════════════════════════════════════╝")

def html_dashboard(projects, output="dashboard.html"):
    html = f"""<!DOCTYPE html><html><head><title>VibeSafe Dashboard</title>
<style>
body{{font-family:system-ui;background:#0d1117;color:#c9d1d9;padding:20px}}
h1{{color:#58a6ff}} .cert{{color:#3fb950}} .cond{{color:#d29922}} .block{{color:#f85149}}
table{{border-collapse:collapse;width:100%;margin-top:20px}}
th,td{{padding:12px;text-align:left;border-bottom:1px solid #21262d}}
th{{color:#8b949e}} tr:hover{{background:#161b22}}
</style></head><body>
<h1>VibeSafe Security Dashboard</h1>
<p>{len(projects)} projects | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<table><tr><th>Project</th><th>Status</th><th>CVEs</th><th>Date</th></tr>
"""
    for p in projects:
        cls = {"🟢": "cert", "🟡": "cond", "🔴": "block"}.get(p["status"][:2], "")
        html += f"<tr><td>{p['name']}</td><td class='{cls}'>{p['status']}</td><td>{p['cves']}</td><td>{p['cert_date']}</td></tr>\n"
    
    html += "</table></body></html>"
    with open(output, "w") as f:
        f.write(html)
    print(f"HTML dashboard: {output}")

if __name__ == "__main__":
    base = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--dir" else "."
    projects = scan_projects(base)
    terminal_dashboard(projects)
    
    if "--html" in sys.argv:
        html_dashboard(projects)
