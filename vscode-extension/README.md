# Green Software Meter – VS Code Extension

**Grammarly-style energy efficiency** for Python: real-time suggestions as you type (static analysis only), plus **Refactor with AI** to apply fixes via an LLM.

## How to run the analyzer (check your code)

**From the terminal (anywhere):**

```bash
cd c:\Users\ASUS\Desktop\genesys
pip install -r requirements.txt
python main.py path\to\your\file.py
python main.py path\to\your\file.py -o json
```

**From VS Code (with this extension):**

1. Open the **genesys** folder in VS Code (so `main.py` is in the workspace root).
2. Install the extension (see below).
3. Open a Python file. Energy issues and the grade update **as you type** (real-time). You can also run **Green Software Meter: Analyze current file** from the Command Palette or click the status bar **Energy: …**.
4. To **refactor with AI**: click the lightbulb on a squiggle and choose **Refactor with AI (energy efficiency)**. Set `greenSoftwareMeter.llmApiKey` in settings first.

## Installing the extension

### Option A: Run from source (development)

1. Open the **genesys** folder in VS Code (the folder that contains `main.py` and `vscode-extension`).
2. In a terminal:
   ```bash
   cd vscode-extension
   npm install
   npm run compile
   ```
3. Press `F5` to launch a new “Extension Development Host” window. In that window, open the same genesys folder and open a `.py` file. Use the command **Green Software Meter: Analyze current file** or the status bar.

### Option B: Install the VSIX (packaged extension)

1. In `vscode-extension` folder:
   ```bash
   npm install
   npm run compile
   npx vsce package
   ```
2. In VS Code: **Extensions** → **...** → **Install from VSIX…** → choose the generated `.vsix` file.
3. Open your project. Ensure the folder that contains `main.py` is in your workspace (or set `greenSoftwareMeter.analyzerPath` to the full path to `main.py`).

## Requirements

- **Python** on your PATH (or set `greenSoftwareMeter.pythonPath`).
- **Green Software Meter** script: `main.py` in the workspace root, or set `greenSoftwareMeter.analyzerPath` to its path.
- Optional: `radon` and `pylint` (`pip install -r requirements.txt` in the genesys folder).

## Settings

| Setting | Description |
|--------|-------------|
| `greenSoftwareMeter.pythonPath` | Python interpreter (default: `python`). |
| `greenSoftwareMeter.analyzerPath` | Full path to `main.py`. Empty = use `main.py` in workspace root. |
| `greenSoftwareMeter.realtimeAnalysis` | Run analysis as you type, Grammarly-style (default: `true`). |
| `greenSoftwareMeter.runOnSave` | Run analysis when a Python file is saved. |
| `greenSoftwareMeter.useRadon` | Include cyclomatic complexity. |
| `greenSoftwareMeter.usePylint` | Include Pylint warning count. |
| `greenSoftwareMeter.llmApiKey` | API key for **Refactor with AI** (OpenAI or compatible). Leave empty to disable. |
| `greenSoftwareMeter.llmEndpoint` | LLM endpoint (default: OpenAI chat completions). |
| `greenSoftwareMeter.llmModel` | Model name (e.g. `gpt-4o-mini`, `gpt-4o`). |

## Commands

- **Green Software Meter: Analyze current file** – analyze the active Python file and show diagnostics + status bar grade.
- **Green Software Meter: Analyze workspace Python files** – analyze all `.py` files in the workspace.
- **Refactor with AI** – available as a Quick Fix on energy diagnostics (lightbulb) when `llmApiKey` is set.
