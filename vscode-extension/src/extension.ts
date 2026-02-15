import * as path from "path";
import * as vscode from "vscode";
import { execFile, spawn } from "child_process";
import { promisify } from "util";
import * as https from "https";
import { URL } from "url";

const execFileAsync = promisify(execFile);

interface GreenSoftwareMeterIssue {
  category: string;
  message: string;
  line: number | null;
  column: number | null;
  severity: number;
  detail: string | null;
}

interface VSCodeDiagnostic {
  range: {
    start: { line: number; character: number };
    end: { line: number; character: number };
  };
  severity: number;
  source: string;
  message: string;
  code: string;
  relatedInformation?: Array<{
    location: {
      range: {
        start: { line: number; character: number };
        end: { line: number; character: number };
      };
    };
    message: string;
  }>;
  _is_refactor_target?: boolean;
}

interface GreenSoftwareMeterReport {
  filename: string;
  score: number;
  grade: string;
  grade_description: string;
  issues: GreenSoftwareMeterIssue[];
  diagnostics?: VSCodeDiagnostic[];  // New: grouped diagnostics
  refactor_target?: VSCodeDiagnostic;  // New: single refactor target
}

let diagnosticCollection: vscode.DiagnosticCollection;
let statusBarItem: vscode.StatusBarItem;
const debounceTimers = new Map<string, NodeJS.Timeout>();
const REALTIME_DEBOUNCE_MS = 500;
const refactorTargets = new Map<string, VSCodeDiagnostic>();  // Track refactor targets per file

function getConfig() {
  const config = vscode.workspace.getConfiguration("greenSoftwareMeter");
  return {
    pythonPath: config.get<string>("pythonPath") ?? "python",
    analyzerPath: config.get<string>("analyzerPath") ?? "",
    runOnSave: config.get<boolean>("runOnSave") ?? false,
    useRadon: config.get<boolean>("useRadon") ?? true,
    usePylint: config.get<boolean>("usePylint") ?? false,
    realtimeAnalysis: config.get<boolean>("realtimeAnalysis") ?? true,
    llmApiKey: config.get<string>("llmApiKey") ?? "",
    llmEndpoint: config.get<string>("llmEndpoint") ?? "https://api.groq.com/openai/v1/chat/completions",
    llmModel: config.get<string>("llmModel") ?? "llama3-8b-8192",
  };
}

function getAnalyzerPath(): string | null {
  const { analyzerPath } = getConfig();
  if (analyzerPath && analyzerPath.length > 0) {
    return path.isAbsolute(analyzerPath)
      ? analyzerPath
      : path.resolve(vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? "", analyzerPath);
  }
  const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!root) {
    console.error("Green Software Meter: No workspace folder found");
    return null;
  }
  const candidate = path.join(root, "main.py");
  console.log(`Green Software Meter: Using analyzer at ${candidate}`);
  return candidate;
}

function mapSeverity(severityNum: number): vscode.DiagnosticSeverity {
  switch (severityNum) {
    case 1: return vscode.DiagnosticSeverity.Error;
    case 2: return vscode.DiagnosticSeverity.Warning;
    case 3: return vscode.DiagnosticSeverity.Information;
    default: return vscode.DiagnosticSeverity.Hint;
  }
}

function vscodeDiagnosticToNative(
  vsDiag: VSCodeDiagnostic,
  doc: vscode.TextDocument
): vscode.Diagnostic {
  const range = new vscode.Range(
    vsDiag.range.start.line,
    vsDiag.range.start.character,
    vsDiag.range.end.line,
    vsDiag.range.end.character
  );

  const diagnostic = new vscode.Diagnostic(
    range,
    vsDiag.message,
    mapSeverity(vsDiag.severity)
  );

  diagnostic.source = vsDiag.source;
  diagnostic.code = vsDiag.code;

  // Add related information (individual issues within the block)
  if (vsDiag.relatedInformation && vsDiag.relatedInformation.length > 0) {
    diagnostic.relatedInformation = vsDiag.relatedInformation.map(rel => ({
      location: new vscode.Location(
        doc.uri,
        new vscode.Range(
          rel.location.range.start.line,
          rel.location.range.start.character,
          rel.location.range.end.line,
          rel.location.range.end.character
        )
      ),
      message: rel.message
    }));
  }

  return diagnostic;
}

async function runAnalyzer(filePath: string): Promise<GreenSoftwareMeterReport | null> {
  const { pythonPath, useRadon, usePylint } = getConfig();
  const analyzerPath = getAnalyzerPath();
  if (!analyzerPath) {
    vscode.window.showErrorMessage(
      "Green Software Meter: Could not find main.py. Open the genesys project or set greenSoftwareMeter.analyzerPath."
    );
    return null;
  }

  const args = [analyzerPath, filePath, "-o", "json"];
  if (useRadon) args.push("--radon");
  if (usePylint) args.push("--pylint");

  try {
    const { stdout } = await execFileAsync(pythonPath, args, {
      cwd: path.dirname(analyzerPath),
      timeout: 30000,
      maxBuffer: 2 * 1024 * 1024,
    });
    return JSON.parse(stdout) as GreenSoftwareMeterReport;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    vscode.window.showErrorMessage(`Green Software Meter: ${msg}`);
    return null;
  }
}

/** Run analyzer on content via stdin (for real-time, no temp file). */
function runAnalyzerWithContent(
  content: string,
  displayPath: string
): Promise<GreenSoftwareMeterReport | null> {
  return new Promise((resolve) => {
    const analyzerPath = getAnalyzerPath();
    const { pythonPath } = getConfig();
    if (!analyzerPath) {
      resolve(null);
      return;
    }
    const args = [analyzerPath, "-", "-o", "json"];
    const proc = spawn(pythonPath, args, {
      cwd: path.dirname(analyzerPath),
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    proc.stdout.setEncoding("utf8");
    proc.stdout.on("data", (chunk) => (stdout += chunk));
    proc.stderr.on("data", (chunk) => (stderr += chunk));
    proc.on("error", (err) => {
      console.error(`Green Software Meter: spawn error: ${err.message}`);
      resolve(null);
    });
    proc.on("close", (code) => {
      if (code !== 0) {
        console.error(`Green Software Meter: analyzer exited with code ${code}, stderr: ${stderr}`);
        resolve(null);
        return;
      }
      try {
        const report = JSON.parse(stdout) as GreenSoftwareMeterReport;
        report.filename = displayPath;
        console.log(`Green Software Meter: Analysis complete - ${report.issues.length} issues, grade ${report.grade}`);
        resolve(report);
      } catch (e) {
        console.error(`Green Software Meter: JSON parse error: ${e}, stdout: ${stdout.substring(0, 200)}`);
        resolve(null);
      }
    });
    proc.stdin.write(content, "utf8", () => {
      proc.stdin.end();
    });
  });
}

async function analyzeDocument(doc: vscode.TextDocument, useContent = false): Promise<void> {
  if (doc.languageId !== "python") return;

  let report: GreenSoftwareMeterReport | null;
  if (useContent || doc.uri.scheme !== "file") {
    report = await runAnalyzerWithContent(doc.getText(), doc.fileName || "<untitled>");
  } else {
    report = await runAnalyzer(doc.uri.fsPath);
  }
  if (!report) return;

  const diagnostics: vscode.Diagnostic[] = [];
  const docKey = doc.uri.toString();

  // Check if Python backend returned grouped diagnostics (new format)
  if (report.diagnostics && report.diagnostics.length > 0) {
    // NEW: Use grouped diagnostics from Python backend
    console.log(`Green Software Meter: Using ${report.diagnostics.length} grouped diagnostics`);

    for (const vsDiag of report.diagnostics) {
      const diagnostic = vscodeDiagnosticToNative(vsDiag, doc);
      diagnostics.push(diagnostic);
    }

    // Store refactor target (only one per file)
    if (report.refactor_target) {
      refactorTargets.set(docKey, report.refactor_target);
      console.log(`Green Software Meter: Refactor target set for lines ${report.refactor_target.range.start.line + 1}-${report.refactor_target.range.end.line + 1}`);
    } else {
      refactorTargets.delete(docKey);
      console.log('Green Software Meter: No refactor target for this file');
    }
  } else {
    // FALLBACK: Old format - group issues by line (backward compatibility)
    console.log(`Green Software Meter: Using fallback grouping for ${report.issues.length} issues`);

    const byLine = new Map<number, GreenSoftwareMeterIssue[]>();
    for (const issue of report.issues) {
      const lineIndex = Math.max(0, (issue.line ?? 1) - 1);
      if (!byLine.has(lineIndex)) {
        byLine.set(lineIndex, []);
      }
      byLine.get(lineIndex)!.push(issue);
    }

    for (const [lineIndex, issues] of byLine.entries()) {
      const messages = Array.from(
        new Set(
          issues.map((i) =>
            i.detail ? `${i.message} (${i.detail})` : i.message
          )
        )
      );
      const combinedMessage =
        messages.length === 1
          ? messages[0]
          : `Energy issues: ${messages.join("; ")}`;

      const maxSeverity = Math.max(...issues.map((i) => i.severity || 1));
      let range: vscode.Range;
      try {
        const lineText = doc.lineAt(lineIndex).text;
        range = new vscode.Range(lineIndex, 0, lineIndex, lineText.length);
      } catch {
        range = new vscode.Range(lineIndex, 0, lineIndex, 1);
      }

      const diag = new vscode.Diagnostic(
        range,
        combinedMessage,
        maxSeverity >= 2
          ? vscode.DiagnosticSeverity.Warning
          : vscode.DiagnosticSeverity.Information
      );
      diag.source = "Green Software Meter";
      const categories = Array.from(new Set(issues.map((i) => i.category)));
      diag.code = categories.length === 1 ? categories[0] : categories.join(",");
      diagnostics.push(diag);
    }

    // No specific refactor target in old format
    refactorTargets.delete(docKey);
  }

  diagnosticCollection.set(doc.uri, diagnostics);

  if (statusBarItem) {
    statusBarItem.text = `$(zap) Energy: ${report.grade} (${report.score})`;
    statusBarItem.tooltip = `${report.grade_description}\nScore: ${report.score}\n${report.issues.length} issue(s)`;
    statusBarItem.show();
  }
}

function scheduleRealtimeAnalysis(doc: vscode.TextDocument): void {
  if (doc.languageId !== "python") return;
  const key = doc.uri.toString();
  const existing = debounceTimers.get(key);
  if (existing) clearTimeout(existing);
  debounceTimers.set(
    key,
    setTimeout(() => {
      debounceTimers.delete(key);
      analyzeDocument(doc, true);
    }, REALTIME_DEBOUNCE_MS)
  );
}

async function analyzeCurrentFile(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== "python") {
    vscode.window.showInformationMessage("Open a Python file to analyze.");
    return;
  }
  await analyzeDocument(editor.document, false);
}

async function analyzeWorkspace(): Promise<void> {
  const root = vscode.workspace.workspaceFolders?.[0];
  if (!root) {
    vscode.window.showInformationMessage("Open a workspace folder first.");
    return;
  }
  const pyFiles = await vscode.workspace.findFiles("**/*.py", "**/node_modules/**");
  for (const u of pyFiles) {
    const doc = await vscode.workspace.openTextDocument(u);
    await analyzeDocument(doc, false);
  }
  vscode.window.showInformationMessage(`Green Software Meter: Analyzed ${pyFiles.length} Python file(s).`);
}

// --- LLM refactor ---

async function applyLlmRefactor(
  document: vscode.TextDocument,
  range: vscode.Range,
  issueMessage: string,
  issueCategory: string
): Promise<void> {
  const lineNumber = range.start.line + 1;

  // Get the specific code range (hotspot only)
  const hotspotCode = document.getText(range);

  // Also get surrounding context for better refactoring
  const contextStart = Math.max(0, range.start.line - 3);
  const contextEnd = Math.min(document.lineCount - 1, range.end.line + 3);
  const contextRange = new vscode.Range(
    contextStart, 0,
    contextEnd, document.lineAt(contextEnd).text.length
  );
  const contextCode = document.getText(contextRange);

  const refactored = await callLlmRefactorHotspot(
    hotspotCode,
    contextCode,
    issueMessage,
    issueCategory,
    lineNumber
  );

  if (!refactored) return;

  // Replace ONLY the hotspot range, not the entire file
  const edit = new vscode.WorkspaceEdit();
  edit.replace(document.uri, range, refactored);

  const applied = await vscode.workspace.applyEdit(edit);
  if (applied) {
    vscode.window.showInformationMessage(
      `Green Software Meter: Refactored lines ${range.start.line + 1}-${range.end.line + 1}. Re-run analysis to see updated score.`
    );
  }
}

async function callLlmRefactorHotspot(
  hotspotCode: string,
  contextCode: string,
  issueMessage: string,
  issueCategory: string,
  lineNumber: number
): Promise<string | null> {
  const { llmApiKey, llmEndpoint, llmModel } = getConfig();
  if (!llmApiKey.trim()) {
    vscode.window.showErrorMessage(
      "Green Software Meter: Set greenSoftwareMeter.llmApiKey in settings to use AI refactor."
    );
    return null;
  }

  const systemPrompt = `You are an expert in energy-efficient Python. Refactor code to reduce computational cost and carbon footprint.
Rules: Return ONLY the refactored code for the specified section. No markdown, no code fences, no explanation. Preserve behavior and indentation.`;

  const userPrompt = `Refactor this Python code section to fix the energy efficiency issue.

Issue at line ${lineNumber}: ${issueMessage} (category: ${issueCategory})

Context (for reference):
\`\`\`python
${contextCode}
\`\`\`

Code to refactor (ONLY return the refactored version of THIS section):
\`\`\`python
${hotspotCode}
\`\`\`

Return ONLY the refactored code section. Maintain the same indentation level.`;

  async function postJson(
    urlStr: string,
    body: string,
    headers: Record<string, string>
  ): Promise<{ status: number; body: string }> {
    return new Promise((resolve, reject) => {
      try {
        const url = new URL(urlStr);
        const options: https.RequestOptions = {
          method: "POST",
          hostname: url.hostname,
          port: url.port || (url.protocol === "https:" ? 443 : 80),
          path: url.pathname + url.search,
          headers,
        };

        const req = https.request(options, (res) => {
          let data = "";
          res.setEncoding("utf8");
          res.on("data", (chunk) => {
            data += chunk;
          });
          res.on("end", () => {
            resolve({ status: res.statusCode ?? 0, body: data });
          });
        });

        req.on("error", (err) => {
          reject(err);
        });

        req.write(body);
        req.end();
      } catch (err) {
        reject(err);
      }
    });
  }

  try {
    const body = JSON.stringify({
      model: llmModel,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.2,
    });
    const { status, body: responseBody } = await postJson(llmEndpoint, body, {
      "Content-Type": "application/json",
      Authorization: `Bearer ${llmApiKey}`,
    });
    if (status < 200 || status >= 300) {
      throw new Error(`${status}: ${responseBody}`);
    }
    const data = JSON.parse(responseBody) as {
      choices?: { message?: { content?: string } }[];
    };
    const content = data.choices?.[0]?.message?.content?.trim();
    if (!content) return null;

    // Strip markdown code block if present
    const code = content.replace(/^```(?:python)?\s*\n?/i, "").replace(/\n?```\s*$/i, "").trim();
    return code;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    vscode.window.showErrorMessage(`Green Software Meter (LLM): ${msg}`);
    return null;
  }
}

export function activate(context: vscode.ExtensionContext): void {
  diagnosticCollection = vscode.languages.createDiagnosticCollection("greenSoftwareMeter");
  context.subscriptions.push(diagnosticCollection);

  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  context.subscriptions.push(statusBarItem);
  statusBarItem.command = "greenSoftwareMeter.analyzeFile";
  statusBarItem.tooltip = "Run Green Software Meter";

  context.subscriptions.push(
    vscode.commands.registerCommand("greenSoftwareMeter.analyzeFile", analyzeCurrentFile)
  );
  context.subscriptions.push(
    vscode.commands.registerCommand("greenSoftwareMeter.analyzeWorkspace", analyzeWorkspace)
  );
  context.subscriptions.push(
    vscode.commands.registerCommand("greenSoftwareMeter.refactorWithAI", async (args: {
      document: vscode.TextDocument;
      range: vscode.Range;
      message: string;
      code: string;
    }) => {
      if (args?.document && args?.range) {
        await applyLlmRefactor(args.document, args.range, args.message, args.code);
      }
    })
  );

  const { runOnSave, realtimeAnalysis } = getConfig();
  if (runOnSave) {
    context.subscriptions.push(
      vscode.workspace.onDidSaveTextDocument((doc) => analyzeDocument(doc, false))
    );
  }

  if (realtimeAnalysis) {
    context.subscriptions.push(
      vscode.workspace.onDidChangeTextDocument((e) => scheduleRealtimeAnalysis(e.document))
    );
    context.subscriptions.push(
      vscode.workspace.onDidOpenTextDocument((doc) => {
        if (doc.languageId === "python") scheduleRealtimeAnalysis(doc);
      })
    );
  }

  // Code action provider: "Refactor with AI" - ONLY for refactor target
  context.subscriptions.push(
    vscode.languages.registerCodeActionsProvider(
      { language: "python" },
      {
        provideCodeActions(
          document: vscode.TextDocument,
          range: vscode.Range | vscode.Selection,
          context: vscode.CodeActionContext
        ): vscode.CodeAction[] {
          const docKey = document.uri.toString();
          const refactorTarget = refactorTargets.get(docKey);

          // CRITICAL: No refactor target = no actions at all
          if (!refactorTarget) {
            return [];
          }

          // CRITICAL: Only show action if cursor/selection is in the refactor target range
          const targetRange = new vscode.Range(
            refactorTarget.range.start.line,
            refactorTarget.range.start.character,
            refactorTarget.range.end.line,
            refactorTarget.range.end.character
          );

          // Check if the selected range overlaps with refactor target
          const overlaps = range.intersection(targetRange);
          if (!overlaps) {
            return [];  // Not in refactor target - no action
          }

          // CRITICAL: Only show ONE action, don't loop through diagnostics
          const action = new vscode.CodeAction(
            "🔥 Refactor with AI (energy efficiency)",
            vscode.CodeActionKind.QuickFix
          );

          action.isPreferred = true;
          action.command = {
            command: "greenSoftwareMeter.refactorWithAI",
            title: "Refactor with AI",
            arguments: [{
              document,
              range: targetRange,  // Pass the target range directly
              message: refactorTarget.message,
              code: refactorTarget.code
            }],
          };

          // Return array with SINGLE action
          return [action];
        },
      },
      { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }
    )
  );

  const editor = vscode.window.activeTextEditor;
  if (editor?.document.languageId === "python") {
    statusBarItem.show();
    if (realtimeAnalysis) scheduleRealtimeAnalysis(editor.document);
  }
}

export function deactivate(): void {
  for (const t of debounceTimers.values()) clearTimeout(t);
  debounceTimers.clear();
  diagnosticCollection?.dispose();
  statusBarItem?.dispose();
  refactorTargets.clear();
}