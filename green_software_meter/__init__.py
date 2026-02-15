"""
Green Software Meter - Static analysis for Python code energy efficiency.
"""

__version__ = "1.0.0"

from green_software_meter.models import (
    EnergyReport, 
    EnergyGrade, 
    Issue, 
    IssueCategory,
    BlockMetrics
)
from green_software_meter.analyzer import ASTAnalyzer
from green_software_meter.scoring import ScoringEngine
from green_software_meter.report import ReportGenerator

__all__ = [
    "EnergyReport",
    "EnergyGrade",
    "Issue",
    "IssueCategory",
    "BlockMetrics",
    "ASTAnalyzer",
    "ScoringEngine",
    "ReportGenerator",
    "analyze_file",
    "analyze_source",
]


def analyze_source(source_code: str, filename: str = "<string>") -> "EnergyReport":
    """Analyze Python source code and return an energy report."""
    analyzer = ASTAnalyzer()
    scoring_engine = ScoringEngine()
    
    # Get both issues and block metrics
    issues, block_metrics = analyzer.analyze(source_code, filename)
    
    # Compute report with block metrics
    return scoring_engine.compute_report(
        issues=issues,
        block_metrics=block_metrics,
        source_code=source_code,
        filename=filename
    )


def analyze_file(filepath: str) -> "EnergyReport":
    """Analyze a Python file and return an energy report."""
    with open(filepath, encoding="utf-8") as f:
        source_code = f.read()
    return analyze_source(source_code, filepath)


def analyze_block(code_block: str, block_type: str = "module", start_line: int = 1) -> list:
    """
    Analyze a single code block for live editing feedback.
    
    Args:
        code_block: The code block to analyze
        block_type: 'loop', 'function', or 'module'
        start_line: The starting line number in the original file
    
    Returns:
        List of issues found in the block
    """
    analyzer = ASTAnalyzer()
    return analyzer.analyze_block(code_block, block_type, start_line)