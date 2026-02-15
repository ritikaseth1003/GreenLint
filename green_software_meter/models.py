"""
Data models for Green Software Meter.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple


class IssueCategory(str, Enum):
    """Categories of energy-impacting code patterns."""

    NESTED_LOOPS = "nested_loops"
    LOOP_DEPTH = "loop_depth"
    ALLOCATION_IN_LOOP = "allocation_in_loop"
    LIST_CREATION_IN_LOOP = "list_creation_in_loop"
    OBJECT_CREATION_IN_LOOP = "object_creation_in_loop"
    RECURSION = "recursion"
    EXPENSIVE_OPERATION = "expensive_operation"
    CYCLOMATIC_COMPLEXITY = "cyclomatic_complexity"
    STRUCTURAL_WARNING = "structural_warning"


@dataclass
class BlockMetrics:
    """Energy metrics for a code block (function, loop, conditional)."""
    
    block_type: str  # 'function', 'loop', 'conditional', 'module'
    start_line: int
    end_line: int
    base_energy: float
    depth: int = 1
    operation_penalties: float = 0.0
    total_energy: float = 0.0
    energy_per_line: float = 0.0
    
    def calculate(self, depth_sensitivity: float = 0.3) -> 'BlockMetrics':
        """
        Calculate total energy with depth multiplier:
        AdjustedBlockEnergy = BaseEnergy × (1 + Depth × k) + OperationPenalties
        """
        # Apply depth multiplier to base energy
        depth_multiplier = 1 + (self.depth - 1) * depth_sensitivity
        adjusted_base = self.base_energy * depth_multiplier
        
        # Add operation penalties
        self.total_energy = adjusted_base + self.operation_penalties
        
        # Calculate energy per line
        lines = max(1, self.end_line - self.start_line + 1)
        self.energy_per_line = self.total_energy / lines
        
        return self


@dataclass
class Issue:
    """A single detected energy-impacting issue."""

    category: IssueCategory
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    severity: int = 1  # 1-3, used for weighting
    detail: Optional[str] = None
    estimated_impact: Optional[float] = None

    def __str__(self) -> str:
        loc = f" (line {self.line})" if self.line else ""
        return f"{self.message}{loc}"


@dataclass
class EnergyGrade:
    """Energy grade (A-F) with score bounds."""

    letter: str
    score_min: int
    score_max: int
    description: str
    icon: str

    @classmethod
    def from_score(cls, score: int) -> "EnergyGrade":
        """
        Map a numeric score to a grade.
        Score range: 0-100 where 100 = best efficiency, 0 = worst efficiency
        
        Grade boundaries designed to be achievable:
        - A: 90-100 (Excellent - minimal issues)
        - B: 75-89 (Good - few minor issues)
        - C: 60-74 (Moderate - some optimization opportunities)
        - D: 45-59 (Needs work - notable inefficiencies)
        - E: 30-44 (Poor - significant problems)
        - F: 0-29 (Critical - severe issues)
        """
        # Clamp score to valid range
        score = max(0, min(100, score))
        
        # Define grades from best to worst
        grades = [
            EnergyGrade("A", 90, 100, "Excellent efficiency", "🌟"),
            EnergyGrade("B", 75, 89, "Good efficiency", "👍"),
            EnergyGrade("C", 60, 74, "Moderate inefficiencies", "⚠️"),
            EnergyGrade("D", 45, 59, "Needs optimization", "🔋"),
            EnergyGrade("E", 30, 44, "Poor efficiency", "🔥"),
            EnergyGrade("F", 0, 29, "Critical inefficiencies", "💀"),
        ]
        
        # Find matching grade
        for g in grades:
            if g.score_min <= score <= g.score_max:
                return g
        
        # Fallback (should never reach here)
        return grades[-1]


@dataclass
class EnergyReport:
    """Full energy analysis report."""

    score: int
    grade: EnergyGrade
    issues: List[Issue] = field(default_factory=list)
    block_metrics: List[BlockMetrics] = field(default_factory=list)
    hotspot: Optional[BlockMetrics] = None
    filename: str = ""
    source_lines: int = 0
    raw_penalty: float = 0.0
    components: Dict[str, float] = field(default_factory=dict)

    def get_issues_by_category(self) -> Dict[str, List[Issue]]:
        """Group issues by category for reporting."""
        result = {}
        for issue in self.issues:
            key = issue.category.value
            if key not in result:
                result[key] = []
            result[key].append(issue)
        return result
    
    def get_hotspot_region(self) -> Optional[Tuple[int, int]]:
        """Get line range of the hottest block for targeted refactoring."""
        if self.hotspot:
            return (self.hotspot.start_line, self.hotspot.end_line)
        return None
    
    @property
    def efficiency_percentage(self) -> int:
        """Return efficiency as percentage (same as score)."""
        return self.score