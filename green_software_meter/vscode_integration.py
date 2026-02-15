"""
VS Code Extension Integration Helper
Provides grouped diagnostics and single refactor action for best UX
"""

from typing import List, Dict, Optional, Tuple, Any


def create_vscode_diagnostics(report) -> Tuple[List[Dict], Optional[Dict]]:
    """
    Main entry point for VS Code extension.
    
    Takes an EnergyReport object and returns:
        - List of diagnostics (one per block, grouped issues)
        - Single refactor target (the hotspot) or None
    
    Args:
        report: EnergyReport object with issues, block_metrics, and hotspot
        
    Returns:
        Tuple of (diagnostics list, refactor_target dict or None)
    """
    # Build a map of line ranges to blocks
    block_map = {}
    for block in report.block_metrics:
        if block.block_type != "module":  # Skip module-level
            key = (block.start_line, block.end_line)
            block_map[key] = block
    
    # Group issues by their containing block
    grouped = {}
    
    for issue in report.issues:
        if not issue.line:
            continue
        
        # Find the smallest block containing this issue
        containing_block = None
        min_size = float('inf')
        
        for (start, end), block in block_map.items():
            if start <= issue.line <= end:
                size = end - start
                if size < min_size:
                    min_size = size
                    containing_block = (start, end)
        
        # If no block found, create a single-line range
        if containing_block is None:
            containing_block = (issue.line, issue.line)
        
        if containing_block not in grouped:
            grouped[containing_block] = []
        grouped[containing_block].append(issue)
    
    # Create diagnostic groups
    diagnostics = []
    for (start, end), block_issues in grouped.items():
        # Calculate severity based on worst issue
        max_severity = max(issue.severity for issue in block_issues)
        severity = _map_severity_to_lsp(max_severity)
        
        # Create summary message
        issue_count = len(block_issues)
        if issue_count == 1:
            message = block_issues[0].message
        else:
            categories = list(set(issue.category.value for issue in block_issues))
            message = f"{issue_count} energy issues detected ({', '.join(categories[:2])})"
        
        # Build related information (individual issues)
        related_info = []
        for issue in block_issues[:5]:  # Limit to 5 related issues
            if issue.line:
                related_info.append({
                    "location": {
                        "range": {
                            "start": {"line": issue.line - 1, "character": issue.column or 0},
                            "end": {"line": issue.line - 1, "character": (issue.column or 0) + 1}
                        }
                    },
                    "message": issue.message
                })
        
        diagnostic = {
            "range": {
                "start": {"line": start - 1, "character": 0},
                "end": {"line": end, "character": 0}
            },
            "severity": severity,
            "source": "green-software-meter",
            "message": message,
            "code": "energy-inefficiency",
            "relatedInformation": related_info
        }
        
        diagnostics.append(diagnostic)
    
    # Sort by severity and line number
    diagnostics.sort(key=lambda d: (
        -d['severity'],
        d['range']['start']['line']
    ))
    
    # Get single refactor target (the hotspot)
    refactor_target = None
    if report.hotspot:
        # Get issues in the hotspot range
        hotspot_issues = [
            issue for issue in report.issues
            if issue.line and report.hotspot.start_line <= issue.line <= report.hotspot.end_line
        ]
        
        if not hotspot_issues:
            # Create a generic issue for the hotspot
            severity = 2
        else:
            severity = max(issue.severity for issue in hotspot_issues)
        
        severity_lsp = _map_severity_to_lsp(severity)
        
        # Build related information for hotspot
        related_info = []
        for issue in hotspot_issues[:5]:
            if issue.line:
                related_info.append({
                    "location": {
                        "range": {
                            "start": {"line": issue.line - 1, "character": issue.column or 0},
                            "end": {"line": issue.line - 1, "character": (issue.column or 0) + 1}
                        }
                    },
                    "message": issue.message
                })
        
        refactor_target = {
            "range": {
                "start": {"line": report.hotspot.start_line - 1, "character": 0},
                "end": {"line": report.hotspot.end_line, "character": 0}
            },
            "severity": severity_lsp,
            "source": "green-software-meter",
            "message": f"🔥 Energy hotspot - {len(hotspot_issues)} issues (refactor recommended)",
            "code": "energy-hotspot",
            "relatedInformation": related_info,
            "_is_refactor_target": True
        }
    
    return diagnostics, refactor_target


def _map_severity_to_lsp(severity: int) -> int:
    """
    Convert severity number to LSP diagnostic severity.
    
    Args:
        severity: Issue severity (1-3)
        
    Returns:
        LSP severity number (1=Error, 2=Warning, 3=Info, 4=Hint)
    """
    if severity >= 3:
        return 1  # Error
    elif severity >= 2:
        return 2  # Warning
    else:
        return 3  # Information