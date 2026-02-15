"""
Rule-based scoring weights for energy impact.
Extensible: add or override rules to tune the Energy Score.
"""

from typing import Dict

from green_software_meter.models import IssueCategory

# Base penalty per occurrence. Score is 0-100 (higher = worse).
# These can be overridden or extended.
DEFAULT_WEIGHTS: Dict[IssueCategory, int] = {
    IssueCategory.NESTED_LOOPS: 8,
    IssueCategory.LOOP_DEPTH: 5,
    IssueCategory.ALLOCATION_IN_LOOP: 6,
    IssueCategory.LIST_CREATION_IN_LOOP: 5,
    IssueCategory.OBJECT_CREATION_IN_LOOP: 6,
    IssueCategory.RECURSION: 7,
    IssueCategory.EXPENSIVE_OPERATION: 6,
    IssueCategory.CYCLOMATIC_COMPLEXITY: 4,  # per point over threshold
    IssueCategory.STRUCTURAL_WARNING: 2,
}

# Severity multiplier: penalty *= severity (1, 2, or 3)
USE_SEVERITY_MULTIPLIER = True

# Cyclomatic complexity threshold (from Radon). Score adds (complexity - threshold) * weight.
CYCLOMATIC_COMPLEXITY_THRESHOLD = 10

# Cap the raw score before grading (so grade stays in A-F range).
SCORE_CAP = 100
SCORE_FLOOR = 0


def get_weight(category: IssueCategory) -> int:
    """Return the penalty weight for a category. Override for custom rules."""
    return DEFAULT_WEIGHTS.get(category, 3)
