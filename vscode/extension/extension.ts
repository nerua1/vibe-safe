import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { exec, execSync } from 'child_process';

/**
 * VibeSafe VS Code Extension
 * Security pre-flight for AI vibe-coding agents.
 * Runs audit.sh on the workspace root and shows results in the Problems pane.
 */

// ── Problem Matcher Diagnostics ────────────────────────────────────────────

const diagnosticCollection =
  vscode.languages.createDiagnosticCollection('vibesafe');

function clearDiagnostics(): void {
  diagnosticCollection.clear();
}

function reportDiagnostic(
  filePath: string,
  line: number,
  message: string,
  severity: vscode.DiagnosticSeverity
): void {
  const uri = vscode.Uri.file(filePath);
  const range = new vscode.Range(line - 1, 0, line - 1, 0);
  const diagnostic = new vscode.Diagnostic(range, message, severity);
  diagnostic.source = 'VibeSafe';
  diagnosticCollection.set(uri, [...(diagnosticCollection.get(uri) || []), diagnostic]);
}

// ── Output Channel ─────────────────────────────────────────────────────────

const outputChannel = vscode.window.createOutputChannel('VibeSafe', { log: true });

// ── Audit Runner ───────────────────────────────────────────────────────────

interface AuditResult {
  success: boolean;
  exitCode: number;
  stdout: string;
  stderr: string;
}

async function runAudit(
  workspaceRoot: string,
  args: string[] = []
): Promise<AuditResult> {
  // Resolve tools path
  const config = vscode.workspace.getConfiguration('vibesafe');
  let toolsPath = config.get<string>('toolsPath', '');

  if (!toolsPath) {
    // Try relative path from workspace: <workspace>/../vibe-safe/tools
    const relativePath = path.resolve(workspaceRoot, '..', 'vibe-safe', 'tools');
    if (fs.existsSync(path.join(relativePath, 'audit.sh'))) {
      toolsPath = relativePath;
    } else {
      // Fallback: look for VIBESAFE_TOOLS env var or common locations
      const envTools = process.env.VIBESAFE_TOOLS;
      if (envTools && fs.existsSync(path.join(envTools, 'audit.sh'))) {
        toolsPath = envTools;
      } else {
        // Bundled: check if vibe-safe repo is a known absolute path
        const commonPaths = [
          '/Volumes/2TB_APFS/projekty/vibe-safe/tools',
          path.join(process.env.HOME || '/tmp', 'vibe-safe', 'tools'),
        ];
        for (const p of commonPaths) {
          if (fs.existsSync(path.join(p, 'audit.sh'))) {
            toolsPath = p;
            break;
          }
        }
      }
    }
  }

  if (!toolsPath || !fs.existsSync(path.join(toolsPath, 'audit.sh'))) {
    throw new Error(
      `VibeSafe audit.sh not found. Set vibesafe.toolsPath in settings or install vibe-safe.\n` +
      `Clone: git clone https://github.com/nerua1/vibe-safe`
    );
  }

  const auditScript = path.join(toolsPath, 'audit.sh');

  return new Promise<AuditResult>((resolve) => {
    outputChannel.appendLine(`[VibeSafe] Running: bash ${auditScript} ${workspaceRoot} ${args.join(' ')}`);
    outputChannel.show(true);

    const child = exec(
      `bash "${auditScript}" "${workspaceRoot}" ${args.join(' ')}`,
      {
        cwd: workspaceRoot,
        maxBuffer: 10 * 1024 * 1024, // 10MB
        env: { ...process.env, VIBESAFE_AGENT: 'vscode' },
      },
      (error, stdout, stderr) => {
        const exitCode = error ? (error as any).code || 1 : 0;
        resolve({
          success: exitCode === 0,
          exitCode,
          stdout: stdout || '',
          stderr: stderr || '',
        });
      }
    );

    child.stdout?.on('data', (data: string) => {
      outputChannel.append(data);
    });
    child.stderr?.on('data', (data: string) => {
      outputChannel.append(data);
    });
  });
}

// ── Parse Output into Diagnostics ──────────────────────────────────────────

function parseAuditOutput(stdout: string, workspaceRoot: string): void {
  clearDiagnostics();

  // Parse lines like "BLOCKED: <reason>" or "CRITICAL: <cve> in <package>"
  const lines = stdout.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    // BLOCKED lines → Error diagnostic
    if (/BLOCKED|CRITICAL/i.test(trimmed)) {
      reportDiagnostic(
        path.join(workspaceRoot, 'stay_safe.md'),
        1,
        `VibeSafe BLOCKED: ${trimmed}`,
        vscode.DiagnosticSeverity.Error
      );
    }
    // WARN / HIGH lines → Warning diagnostic
    else if (/WARN(ING)?|HIGH/i.test(trimmed) && /CVE/i.test(trimmed)) {
      reportDiagnostic(
        path.join(workspaceRoot, 'package.json'),
        1,
        `VibeSafe WARNING: ${trimmed}`,
        vscode.DiagnosticSeverity.Warning
      );
    }
    // MEDIUM lines → Information diagnostic
    else if (/MEDIUM|LOW/i.test(trimmed) && /CVE/i.test(trimmed)) {
      reportDiagnostic(
        path.join(workspaceRoot, 'package.json'),
        1,
        `VibeSafe INFO: ${trimmed}`,
        vscode.DiagnosticSeverity.Information
      );
    }
  }

  // If no problems found, show a clean status
  if (diagnosticCollection.size === 0) {
    reportDiagnostic(
      path.join(workspaceRoot, 'stay_safe.md'),
      1,
      'VibeSafe: All dependencies clean — stay_safe.md certified',
      vscode.DiagnosticSeverity.Information
    );
  }
}

// ── Audit View Certificate ─────────────────────────────────────────────────

async function viewCertificate(workspaceRoot: string): Promise<void> {
  const certPath = path.join(workspaceRoot, 'stay_safe.md');
  if (fs.existsSync(certPath)) {
    const doc = await vscode.workspace.openTextDocument(certPath);
    await vscode.window.showTextDocument(doc, { preview: false });
  } else {
    vscode.window.showWarningMessage(
      'VibeSafe: No stay_safe.md certificate found. Run audit first.'
    );
  }
}

// ── Status Bar Item ────────────────────────────────────────────────────────

let statusBarItem: vscode.StatusBarItem;

function updateStatusBar(success: boolean, exitCode: number): void {
  if (!statusBarItem) {
    statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100
    );
  }

  if (success) {
    statusBarItem.text = '$(shield) VibeSafe: Clean';
    statusBarItem.backgroundColor = undefined;
    statusBarItem.tooltip = 'VibeSafe audit passed — dependencies are clean';
  } else {
    statusBarItem.text = '$(error) VibeSafe: BLOCKED';
    statusBarItem.backgroundColor = new vscode.ThemeColor(
      'statusBarItem.errorBackground'
    );
    statusBarItem.tooltip = `VibeSafe audit failed with exit code ${exitCode}. Open Problems pane for details.`;
  }

  statusBarItem.command = 'vibesafe.audit';
  statusBarItem.show();
}

// ── Extension Activation ───────────────────────────────────────────────────

export function activate(context: vscode.ExtensionContext): void {
  outputChannel.appendLine('[VibeSafe] Extension activated');

  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (!workspaceFolders || workspaceFolders.length === 0) {
    vscode.window.showWarningMessage(
      'VibeSafe: No workspace folder open. Open a project to run security audits.'
    );
    return;
  }

  const workspaceRoot = workspaceFolders[0].uri.fsPath;

  // Register: vibesafe.audit
  const auditCommand = vscode.commands.registerCommand('vibesafe.audit', async () => {
    outputChannel.clear();
    outputChannel.appendLine('[VibeSafe] Starting audit...');
    vscode.window.showInformationMessage('VibeSafe: Running security audit...');

    try {
      const result = await runAudit(workspaceRoot);
      parseAuditOutput(result.stdout, workspaceRoot);
      updateStatusBar(result.success, result.exitCode);

      if (result.success) {
        vscode.window.showInformationMessage(
          'VibeSafe: Audit complete — no critical issues found. stay_safe.md certified.'
        );
      } else {
        vscode.window.showErrorMessage(
          `VibeSafe: Audit BLOCKED (exit code ${result.exitCode}). Check Problems pane for details.`
        );
      }
    } catch (err: any) {
      outputChannel.appendLine(`[VibeSafe] Error: ${err.message}`);
      vscode.window.showErrorMessage(`VibeSafe: Audit error — ${err.message}`);
    }
  });

  // Register: vibesafe.auditJson
  const auditJsonCommand = vscode.commands.registerCommand('vibesafe.auditJson', async () => {
    outputChannel.clear();
    outputChannel.appendLine('[VibeSafe] Starting audit (JSON mode)...');

    try {
      const result = await runAudit(workspaceRoot, ['--json']);
      // Write JSON to a temp file and open it
      const jsonPath = path.join(workspaceRoot, '.vibesafe', 'audit-result.json');
      fs.mkdirSync(path.dirname(jsonPath), { recursive: true });
      fs.writeFileSync(jsonPath, result.stdout);
      const doc = await vscode.workspace.openTextDocument(jsonPath);
      await vscode.window.showTextDocument(doc, { preview: true });
      updateStatusBar(result.success, result.exitCode);
    } catch (err: any) {
      outputChannel.appendLine(`[VibeSafe] Error: ${err.message}`);
      vscode.window.showErrorMessage(`VibeSafe: Audit error — ${err.message}`);
    }
  });

  // Register: vibesafe.fullPreFlight
  const fullPreFlightCommand = vscode.commands.registerCommand('vibesafe.fullPreFlight', async () => {
    outputChannel.clear();
    outputChannel.appendLine('[VibeSafe] Starting Full Pre-Flight...');
    vscode.window.showInformationMessage('VibeSafe: Running Full Pre-Flight (audit + cert)...');

    try {
      const result = await runAudit(workspaceRoot);
      parseAuditOutput(result.stdout, workspaceRoot);
      updateStatusBar(result.success, result.exitCode);

      if (result.success) {
        // Check for stay_safe.md
        const certPath = path.join(workspaceRoot, 'stay_safe.md');
        if (fs.existsSync(certPath)) {
          vscode.window.showInformationMessage(
            'VibeSafe: Full Pre-Flight complete. stay_safe.md certified.'
          );
        } else {
          vscode.window.showWarningMessage(
            'VibeSafe: Audit passed but no certificate generated. Check output.'
          );
        }
      } else {
        vscode.window.showErrorMessage(
          `VibeSafe: Pre-Flight BLOCKED (exit ${result.exitCode}). Fix issues before coding.`
        );
      }
    } catch (err: any) {
      outputChannel.appendLine(`[VibeSafe] Error: ${err.message}`);
      vscode.window.showErrorMessage(`VibeSafe: Pre-Flight error — ${err.message}`);
    }
  });

  // Register: vibesafe.viewCertificate
  const viewCertCommand = vscode.commands.registerCommand('vibesafe.viewCertificate', async () => {
    await viewCertificate(workspaceRoot);
  });

  // Register: run on save (optional)
  let saveListener: vscode.Disposable | undefined;
  const config = vscode.workspace.getConfiguration('vibesafe');
  if (config.get<boolean>('auditOnSave', false)) {
    saveListener = vscode.workspace.onDidSaveTextDocument(async (doc) => {
      const isPackageFile = /(package\.json|requirements\.txt|Pipfile|pyproject\.toml|go\.mod)$/.test(doc.fileName);
      if (isPackageFile) {
        await vscode.commands.executeCommand('vibesafe.audit');
      }
    });
  }

  // Register: config change listener
  const configListener = vscode.workspace.onDidChangeConfiguration((e) => {
    if (e.affectsConfiguration('vibesafe')) {
      outputChannel.appendLine('[VibeSafe] Configuration changed');
    }
  });

  // Push all subscriptions
  context.subscriptions.push(
    auditCommand,
    auditJsonCommand,
    fullPreFlightCommand,
    viewCertCommand,
    diagnosticCollection,
    configListener
  );

  if (saveListener) {
    context.subscriptions.push(saveListener);
  }

  if (statusBarItem) {
    context.subscriptions.push(statusBarItem);
  }

  outputChannel.appendLine('[VibeSafe] All commands registered. Ready.');
}

export function deactivate(): void {
  diagnosticCollection.clear();
  if (statusBarItem) {
    statusBarItem.dispose();
  }
  outputChannel.appendLine('[VibeSafe] Extension deactivated');
}
