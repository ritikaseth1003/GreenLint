"""
Report Generator - Text and JSON output with hotspot detection and LLM prompts.
"""

import json
from typing import Any, Dict, List, Optional

from green_software_meter.models import EnergyReport, Issue, BlockMetrics


def _issue_to_dict(issue: Issue) -> Dict[str, Any]:
    """Convert Issue to dictionary."""
    return {
        "category": issue.category.value,
        "message": issue.message,
        "line": issue.line,
        "column": issue.column,
        "severity": issue.severity,
        "detail": issue.detail,
        "estimated_impact": issue.estimated_impact,
    }


def _block_to_dict(block: BlockMetrics) -> Dict[str, Any]:
    """Convert BlockMetrics to dictionary."""
    return {
        "block_type": block.block_type,
        "start_line": block.start_line,
        "end_line": block.end_line,
        "base_energy": block.base_energy,
        "depth": block.depth,
        "operation_penalties": block.operation_penalties,
        "total_energy": block.total_energy,
        "energy_per_line": block.energy_per_line,
    }


def _dedupe_issues(issues: List[Issue]) -> List[Issue]:
    """Deduplicate issues for display."""
    seen = set()
    result = []
    for issue in issues:
        key = (issue.category.value, issue.line, issue.message)
        if key not in seen:
            seen.add(key)
            result.append(issue)
    return result


def format_text(report: EnergyReport) -> str:
    """Produce human-readable text report."""
    lines = [
        "=" * 60,
        "GREEN SOFTWARE METER - ENERGY ANALYSIS REPORT",
        "=" * 60,
        f"File: {report.filename or '<string>'}",
        f"Lines: {report.source_lines}",
        f"Energy Score: {report.score}/100",
        f"Energy Grade: {report.grade.letter} - {report.grade.description} {report.grade.icon}",
        "=" * 60,
        "",
    ]
    
    # Component breakdown
    if report.components:
        lines.append("Score Components:")
        lines.append(f"  • Raw Penalty: {report.components.get('total_penalty', 0)}")
        if 'energy_component' in report.components:
            lines.append(f"  • Energy Component: {report.components.get('energy_component', 0)}")
        if 'issue_component' in report.components:
            lines.append(f"  • Issue Component: {report.components.get('issue_component', 0)}")
        if 'complexity_component' in report.components:
            lines.append(f"  • Complexity Component: {report.components.get('complexity_component', 0)}")
        lines.append(f"  • Scaling Factor (S): {report.components.get('scaling_constant', 150)}")
        lines.append(f"  • Formula: {report.components.get('formula', 'N/A')}")
        lines.append("")
    
    # Hotspot
    if report.hotspot:
        h = report.hotspot
        lines.append("🔥 HOTSPOT DETECTED - Most Inefficient Region:")
        lines.append(f"  • Type: {h.block_type}")
        lines.append(f"  • Lines: {h.start_line}-{h.end_line}")
        lines.append(f"  • Energy Impact: {h.total_energy:.2f}")
        lines.append(f"  • Energy/Line: {h.energy_per_line:.2f}")
        lines.append("")
        lines.append("💡 TARGET THIS REGION FOR REFACTORING")
        lines.append("")
    
    # Issues
    if report.issues:
        by_category = report.get_issues_by_category()
        
        lines.append(f"Issues Detected ({len(report.issues)} total):")
        lines.append("-" * 40)
        
        for category, cat_issues in by_category.items():
            lines.append(f"\n[{category}]")
            for issue in cat_issues[:5]:
                line = f"  • Line {issue.line}: {issue.message}"
                if issue.detail:
                    line += f" ({issue.detail})"
                if issue.estimated_impact:
                    line += f" [impact: {issue.estimated_impact:.1f}]"
                lines.append(line)
            if len(cat_issues) > 5:
                lines.append(f"  ... and {len(cat_issues) - 5} more")
    else:
        lines.append("✅ No energy inefficiency issues detected!")
    
    return "\n".join(lines)


def format_text_clean(report: EnergyReport) -> str:
    """Produce human-readable text report with deduplicated issues."""
    issues = _dedupe_issues(report.issues)
    
    lines = [
        "=" * 60,
        "GREEN SOFTWARE METER - ENERGY ANALYSIS REPORT",
        "=" * 60,
        f"File: {report.filename or '<string>'}",
        f"Lines: {report.source_lines}",
        f"Energy Score: {report.score}/100",
        f"Energy Grade: {report.grade.letter} - {report.grade.description} {report.grade.icon}",
        "=" * 60,
        "",
    ]
    
    # Component breakdown
    if report.components:
        lines.append("Score Components:")
        lines.append(f"  • Raw Penalty: {report.components.get('total_penalty', 0)}")
        if 'energy_component' in report.components:
            lines.append(f"  • Energy Component: {report.components.get('energy_component', 0)}")
        if 'issue_component' in report.components:
            lines.append(f"  • Issue Component: {report.components.get('issue_component', 0)}")
        if 'complexity_component' in report.components:
            lines.append(f"  • Complexity Component: {report.components.get('complexity_component', 0)}")
        lines.append(f"  • Scaling Factor (S): {report.components.get('scaling_constant', 150)}")
        lines.append(f"  • Formula: {report.components.get('formula', 'N/A')}")
        lines.append("")
    
    # Hotspot
    if report.hotspot:
        h = report.hotspot
        lines.append("🔥 HOTSPOT DETECTED - Most Inefficient Region:")
        lines.append(f"  • Type: {h.block_type}")
        lines.append(f"  • Lines: {h.start_line}-{h.end_line}")
        lines.append(f"  • Energy Impact: {h.total_energy:.2f}")
        lines.append(f"  • Energy/Line: {h.energy_per_line:.2f}")
        lines.append("")
        lines.append("💡 TARGET THIS REGION FOR REFACTORING")
        lines.append("")
    
    if issues:
        lines.append(f"Issues Detected ({len(issues)} unique):")
        for issue in issues:
            line = f"  • Line {issue.line}: {issue.message}"
            if issue.detail:
                line += f" ({issue.detail})"
            if issue.estimated_impact:
                line += f" [impact: {issue.estimated_impact:.1f}]"
            lines.append(line)
    else:
        lines.append("✅ No energy inefficiency issues detected!")
    
    return "\n".join(lines)


def to_dict(report: EnergyReport) -> Dict[str, Any]:
    """Serialize report to a dict for JSON / IDE integration."""
    issues = _dedupe_issues(report.issues)
    
    result = {
        "filename": report.filename,
        "score": report.score,
        "grade": report.grade.letter,
        "grade_description": report.grade.description,
        "grade_icon": report.grade.icon,
        "source_lines": report.source_lines,
        "issues": [_issue_to_dict(i) for i in issues],
        "issues_count": len(issues),
        "components": report.components,
    }
    
    if report.block_metrics:
        result["blocks"] = [_block_to_dict(b) for b in report.block_metrics]
        result["blocks_count"] = len(report.block_metrics)
    
    if report.hotspot:
        result["hotspot"] = _block_to_dict(report.hotspot)
        result["hotspot_range"] = [report.hotspot.start_line, report.hotspot.end_line]
    
    return result


def format_json(report: EnergyReport, indent: int = 2) -> str:
    """Produce JSON string for IDE/CI integration."""
    return json.dumps(to_dict(report), indent=indent)

# get the refactor prompt

def get_refactor_prompt(report: EnergyReport, original_code: str = "") -> str:
    """Generate a targeted LLM refactoring prompt that REPLACES the code."""
    if not report.hotspot:
        return "No hotspot detected for refactoring."
    
    h = report.hotspot
    issues_in_hotspot = [
        i for i in report.issues
        if i.line and h.start_line <= i.line <= h.end_line
    ]
    
    # Extract the specific code lines if original_code is provided
    specific_code = ""
    if original_code:
        lines = original_code.splitlines()
        if h.start_line <= len(lines):
            specific_code = "\n".join(lines[h.start_line-1:h.end_line])
    
    # Build the prompt
    prompt = f"""You are a code refactoring assistant. Your task is to REPLACE the code at lines {h.start_line}-{h.end_line} with an optimized version.

## ORIGINAL CODE TO REPLACE (lines {h.start_line}-{h.end_line}):
```python
{specific_code or '[Code not provided]'}
```

## ISSUES TO FIX IN THIS REGION:
"""
    
    for issue in issues_in_hotspot:
        prompt += f"- Line {issue.line}: {issue.message}"
        if issue.detail:
            prompt += f" ({issue.detail})"
        if issue.estimated_impact:
            prompt += f" [Impact: {issue.estimated_impact:.1f}]"
        prompt += "\n"
    
    prompt += f"""
## REFACTORING REQUIREMENTS:
1. **KEEP THE SAME FUNCTION NAME AND SIGNATURE** - Do not rename the function
2. **REPLACE** - Return only the code that should go in lines {h.start_line}-{h.end_line}
3. **NO NEW FUNCTIONS** - Do not create additional functions or keep the original code
4. **SAME INDENTATION LEVEL** - Maintain proper indentation for the replacement code
5. **PRESERVE FUNCTIONALITY** - The code should do the same thing, just more efficiently

## OPTIMIZATION GUIDELINES:
- Reduce computational complexity (avoid nested loops, use early breaks)
- Minimize memory allocations (pre-allocate, use generators)
- Avoid expensive operations inside loops (move them outside)
- Replace recursion with iteration where possible
- Use appropriate data structures (sets for lookups, etc.)

## OUTPUT FORMAT:
Return ONLY the refactored code for lines {h.start_line}-{h.end_line}.
No explanations, no markdown formatting, no backticks, just the raw Python code.
Do not include the original function name if it's already in the code - just the inner code.
"""
    
    return prompt


class ReportGenerator:
    """
    Generates reports in text or JSON format with hotspot detection.
    """

    @staticmethod
    def text(report: EnergyReport, dedupe: bool = True) -> str:
        """Generate text report."""
        return format_text_clean(report) if dedupe else format_text(report)

    @staticmethod
    def json(report: EnergyReport, indent: int = 2) -> str:
        """Generate JSON report."""
        return format_json(report, indent=indent)

    @staticmethod
    def to_dict(report: EnergyReport) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return to_dict(report)
    
    @staticmethod
    def refactor_prompt(report: EnergyReport, original_code: str = "") -> str:
        """Generate a prompt that tells the AI to REPLACE the code."""
        return get_refactor_prompt(report, original_code)
