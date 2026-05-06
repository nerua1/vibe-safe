# VibeSafe — VS Code Extension

Security pre-flight for AI vibe-coding agents. Audit your dependencies for CVEs **before** you write a single line of integration code.

## Features

- **One-click audit**: Run `VibeSafe: Audit Project` from the Command Palette (`Cmd+Shift+P`)
- **Problems pane integration**: BLOCKED / CRITICAL / WARN results appear directly in VS Code's Problems panel
- **Full Pre-Flight mode**: Audit + certificate generation in one command
- **JSON output**: Machine-readable audit results for scripting
- **View Certificate**: Quick access to your `stay_safe.md` certificate
- **Status bar indicator**: See audit status at a glance (Clean / BLOCKED)
- **Optional auto-audit on save**: Automatically audit when `package.json`, `requirements.txt`, or similar files change

## Getting Started

1. Install the extension from the VS Code Marketplace (or build from source)
2. Open any project with dependencies (`package.json`, `requirements.txt`, etc.)
3. Press `Cmd+Shift+P` and run **VibeSafe: Audit Project**
4. Results appear in the Output panel and Problems pane

### Requirements

- **bash 4+** (pre-installed on macOS/Linux; use WSL or Git Bash on Windows)
- **Node.js 18+** and npm 8+ (for npm projects)
- **Python 3.9+** and pip-audit (for Python projects)
- **curl** and **jq** (for OSV.dev API lookups)

### Install VibeSafe Tools

The extension needs the VibeSafe audit scripts. Install them:

```bash
git clone https://github.com/nerua1/vibe-safe
```

By default, the extension looks for `../vibe-safe/tools/audit.sh` relative to your workspace root. You can override this in settings:

```json
{
  "vibesafe.toolsPath": "/path/to/vibe-safe/tools"
}
```

## Commands

| Command | Description |
|---------|-------------|
| `VibeSafe: Audit Project` | Run full security audit on workspace dependencies |
| `VibeSafe: Audit Project (JSON output)` | Run audit with machine-readable JSON |
| `VibeSafe: Full Pre-Flight (audit + cert)` | Audit + generate `stay_safe.md` certificate |
| `VibeSafe: View Current Certificate` | Open the current `stay_safe.md` (if certified) |

## Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `vibesafe.auditOnSave` | boolean | `false` | Run audit automatically when dependency files are saved |
| `vibesafe.certPath` | string | `${workspaceFolder}/stay_safe.md` | Path where the certificate is written |
| `vibesafe.toolsPath` | string | `""` | Path to VibeSafe tools directory (auto-detected if empty) |
| `vibesafe.mode` | string | `"interactive"` | Audit mode: `interactive`, `silent`, or `blocking` |

## How It Works

VibeSafe runs `audit.sh` against your workspace root, which:

1. **Detects** your package ecosystem (`package.json`, `requirements.txt`, `Pipfile`, `pyproject.toml`, `go.mod`)
2. **Runs** the appropriate auditor (`npm audit`, `pip-audit`, OSV.dev API)
3. **Reports** CVEs and unmaintained packages
4. **Writes** `stay_safe.md` certificate if the project passes
5. **Blocks** with a detailed report if critical or high CVEs are found

## Pair With

| Extension | Why |
|-----------|-----|
| [Snyk Security](https://marketplace.visualstudio.com/items?itemName=snyk-security.snyk-vulnerability-scanner) | Real-time CVE highlighting in editor |
| [Error Lens](https://marketplace.visualstudio.com/items?itemName=usernamehw.errorlens) | Inline display of VibeSafe BLOCKED results |
| [GitLens](https://marketplace.visualstudio.com/items?itemName=eamodio.gitlens) | Audit when secrets were introduced |

## Building From Source

```bash
git clone https://github.com/nerua1/vibe-safe
cd vibe-safe/vscode/extension
npm install
npm run compile
# To package:
npx vsce package
```

## Contributing

PRs welcome! See the main [VibeSafe repo](https://github.com/nerua1/vibe-safe) for contribution guidelines.

## License

MIT — see [LICENSE](https://github.com/nerua1/vibe-safe/blob/main/LICENSE).

---

Built for the vibe-coding era. Catch CVEs before your AI agent writes the exploit.

☕ **Support:** [PayPal.me/nerudek](https://www.paypal.me/nerudek) | [Dev.to](https://dev.to/nerua1)
