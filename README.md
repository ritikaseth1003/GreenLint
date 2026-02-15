# Green Software Meter

A Python-based **static analysis** tool that estimates the energy efficiency of Python code using Abstract Syntax Tree (AST) analysis. It highlights code patterns that may increase computational cost and carbon footprint—without executing the code.

## Features

- **AST-based analysis** using Python's `ast` module
- **Energy-impacting pattern detection:**
  - Loop nesting depth and nested loops
  - Memory/list/object allocations inside loops
  - Recursion
  - Expensive operations (e.g. I/O, `eval`, regex compile) inside or outside loops
- **Rule-based Energy Score** (0–100) and **Energy Grade** (A–F)
- **Explainable feedback** with line numbers and categories
- **Modular layout:** AST Analyzer, Rule-based Scoring Engine, Report Generator
- **Optional:** Radon (cyclomatic complexity), Pylint (structural warnings)
- **Output:** Human-readable text and **JSON** for IDE/CI integration
- **Design:** Suitable for a future VS Code extension (JSON output, no execution)

## Installation

```bash
cd genesys
pip install -r requirements.txt
```

Optional dependencies:

- `radon` – cyclomatic complexity (recommended)
- `pylint` – structural warnings count

The core tool runs with only the standard library; Radon and Pylint are optional.

## How to check your code

**Terminal:** from the project root run:
```bash
python main.py your_file.py
```
For JSON (e.g. for tools): `python main.py your_file.py -o json`

**VS Code:** use the [Green Software Meter extension](vscode-extension/README.md) in this repo. Open the `genesys` folder in VS Code, install the extension from the `vscode-extension` folder (or package a VSIX), then run **Green Software Meter: Analyze current file** from the Command Palette or click the status bar.

## Usage

### CLI

```bash
# Analyze a file (from project root)
python main.py path/to/file.py

# Text output (default)
python main.py sample_code.py

# JSON output (for IDEs/CI)
python main.py sample_code.py -o json
python main.py sample_code.py --json

# Include Radon (cyclomatic complexity)
python main.py sample_code.py --radon

# Include Pylint (structural warnings count)
python main.py sample_code.py --pylint

# Analyze directory
python main.py path/to/project/

# Stdin
python main.py -
```

### As a library

```python
from green_software_meter import analyze_file, analyze_source

# From file
report = analyze_file("my_script.py")

# From string
report = analyze_source("def f():\n    for x in []:\n        list()")

print(report.score, report.grade.letter)
for issue in report.issues:
    print(issue.message, issue.line)
```

### Report output (example)

```
Energy Score: 42
Energy Grade: C

Issues Detected:
- Nested loops detected (depth 2) [line 7]
- List allocation inside loop [line 6]
- High cyclomatic complexity (complexity 12) [line 2]
```

## Project layout

```
genesys/
├── green_software_meter/
│   ├── __init__.py       # Public API (analyze_file, analyze_source)
│   ├── models.py         # Issue, EnergyReport, EnergyGrade
│   ├── analyzer.py       # AST Analyzer (visitor, patterns)
│   ├── rules.py          # Weights and thresholds (extensible)
│   ├── scoring.py        # Scoring Engine
│   ├── report.py         # Report Generator (text + JSON)
│   └── integrations/
│       ├── radon_integration.py
│       └── pylint_integration.py
├── main.py               # CLI
├── requirements.txt
├── sample_code.py        # Example file for testing
├── vscode-extension/     # VS Code extension (diagnostics + status bar)
└── README.md
```

## Extending the rule engine

Edit `green_software_meter/rules.py`:

- `DEFAULT_WEIGHTS`: penalty per issue category
- `CYCLOMATIC_COMPLEXITY_THRESHOLD`: threshold for “high” complexity
- `USE_SEVERITY_MULTIPLIER`: scale penalty by issue severity

You can pass a custom `weights` dict into `ScoringEngine(weights=...)` for per-run tuning.

## License

Use and modify as needed for your project.
