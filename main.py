#!/usr/bin/env python3
"""
Green Software Meter - CLI entry point.
Analyzes Python files for energy efficiency using static analysis.
"""

import argparse
import sys
import json
from pathlib import Path
from green_software_meter.vscode_integration import create_vscode_diagnostics

# Allow running as script from repo root or as module
try:
    from green_software_meter import analyze_file, analyze_source
    from green_software_meter.report import ReportGenerator, to_dict
    from green_software_meter.models import IssueCategory
    from green_software_meter.integrations import (
        get_max_cyclomatic_complexity,
        get_pylint_warnings_count,
    )
except ImportError:
    # Run from project root without package install
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from green_software_meter import analyze_file, analyze_source
    from green_software_meter.report import ReportGenerator, to_dict
    from green_software_meter.models import IssueCategory
    from green_software_meter.integrations import (
        get_max_cyclomatic_complexity,
        get_pylint_warnings_count,
    )


def _run_analysis(path: Path, use_radon: bool, use_pylint: bool):
    """Run analyzer and optional integrations, return EnergyReport."""
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return None

    from green_software_meter.analyzer import ASTAnalyzer
    from green_software_meter.scoring import ScoringEngine

    analyzer = ASTAnalyzer()
    engine = ScoringEngine()
    issues, blocks = analyzer.analyze(source, str(path))

    cc = None
    if use_radon:
        cc = get_max_cyclomatic_complexity(source)
        if cc is not None and cc > 10:
            from green_software_meter.models import Issue

            issues.append(
                Issue(
                    category=IssueCategory.CYCLOMATIC_COMPLEXITY,
                    message="High cyclomatic complexity",
                    detail=f"complexity {cc}",
                    severity=2,
                )
            )

    pylint_count = 0
    if use_pylint and path.suffix == ".py":
        cnt = get_pylint_warnings_count(str(path))
        if cnt is not None:
            pylint_count = cnt

    return engine.compute_report(
        issues,
        blocks,
        source_code=source,
        filename=str(path),
        cyclomatic_complexity=cc,
        structural_warnings_count=pylint_count,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Green Software Meter - Energy efficiency static analysis for Python"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="-",
        help="Python file or directory to analyze (default: stdin)",
    )
    parser.add_argument(
        "-o", "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--radon",
        action="store_true",
        help="Include cyclomatic complexity via Radon",
    )
    parser.add_argument(
        "--pylint",
        action="store_true",
        help="Include structural warnings count via Pylint",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Shortcut for -o json",
    )
    args = parser.parse_args()

    if args.output_json:
        args.output_format = "json"

    if args.path == "-":
        source = sys.stdin.read()
        report = analyze_source(source, "<stdin>")
        if args.output_format == "json":
            print(ReportGenerator.json(report))
        else:
            print(ReportGenerator.text(report))
        return 0

    path = Path(args.path)
    if not path.exists():
        print(f"Error: path not found: {path}", file=sys.stderr)
        return 1

    reports = []
    if path.is_file():
        if path.suffix != ".py":
            print("Warning: not a .py file, analysis may be limited.", file=sys.stderr)
        r = _run_analysis(path, use_radon=args.radon, use_pylint=args.pylint)
        if r is not None:
            reports.append(r)
    else:
        for py in path.rglob("*.py"):
            r = _run_analysis(py, use_radon=args.radon, use_pylint=args.pylint)
            if r is not None:
                reports.append(r)

    if not reports:
        return 1

    # FIXED: Changed args.output to args.output_format
    if args.output_format == 'json':
        # Handle multiple reports
        if len(reports) == 1:
            result = to_dict(reports[0])
            
            # Add VS Code diagnostics for single file
            try:
                diagnostics, refactor_target = create_vscode_diagnostics(reports[0])
                result['diagnostics'] = diagnostics
                result['refactor_target'] = refactor_target
            except Exception as e:
                print(f"Warning: {e}", file=sys.stderr)
            
            print(json.dumps(result, indent=2))
        else:
            # Multiple files - return array
            results = []
            for report in reports:
                result = to_dict(report)
                try:
                    diagnostics, refactor_target = create_vscode_diagnostics(report)
                    result['diagnostics'] = diagnostics
                    result['refactor_target'] = refactor_target
                except Exception as e:
                    pass
                results.append(result)
            print(json.dumps(results, indent=2))
    else:
        for report in reports:
            if report.filename:
                print(f"\n--- {report.filename} ---")
            print(ReportGenerator.text(report))

    return 0


if __name__ == "__main__":
    sys.exit(main())