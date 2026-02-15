"""
Rule-based Scoring Engine.
Computes Energy Score using hybrid model with exponential normalization.
"""

import math
from typing import List, Optional, Dict, Any

from green_software_meter.models import (
    EnergyGrade,
    EnergyReport,
    Issue,
    IssueCategory,
    BlockMetrics,
)
from green_software_meter import rules


class ScoringEngine:
    """
    Applies hybrid energy scoring:
    - Block-level energy with depth multiplier
    - Issue penalties with severity weighting
    - Cyclomatic complexity penalty
    - Exponential normalization: Score = 100 × e^(-RawPenalty / S)
    
    Final Score: 0-100 where 100 = best efficiency, 0 = worst efficiency
    """

    def __init__(
        self,
        weights: Optional[dict] = None,
        use_severity: bool = True,
        cc_threshold: int = rules.CYCLOMATIC_COMPLEXITY_THRESHOLD,
        # Hybrid model parameters
        alpha: float = 0.6,  # Energy component weight (increased)
        beta: float = 0.6,   # Issue component weight (increased)
        gamma: float = 0.2,  # Complexity component weight
        depth_sensitivity: float = 0.3,
        scaling_constant: float = 50.0,  # Reduced from 80 - stricter scoring
    ):
        self.weights = weights or rules.DEFAULT_WEIGHTS
        self.use_severity = use_severity
        self.cc_threshold = cc_threshold
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.depth_sensitivity = depth_sensitivity
        self.scaling_constant = scaling_constant

    def _calculate_energy_component(self, block_metrics: List[BlockMetrics]) -> float:
        """Calculate total energy from blocks: Σ AdjustedBlockEnergy"""
        if not block_metrics:
            return 0.0
        
        total_energy = sum(block.total_energy for block in block_metrics)
        
        # Apply gentle normalization (don't divide by lines completely)
        # This prevents tiny files from getting perfect scores
        total_lines = sum(max(1, block.end_line - block.start_line + 1) 
                         for block in block_metrics)
        
        if total_lines > 0:
            # Normalize but keep meaningful scale
            normalized = total_energy / max(1, total_lines / 20)
            return normalized
        return total_energy

    def _calculate_issue_component(self, issues: List[Issue]) -> float:
        """Calculate total issue penalties: Σ (Weight × Severity)"""
        if not issues:
            return 0.0
            
        total = 0.0
        for issue in issues:
            weight = self.weights.get(issue.category, 3)
            
            if issue.estimated_impact:
                # Use estimated impact if available
                total += issue.estimated_impact
            else:
                # Otherwise use weight × severity
                if self.use_severity:
                    total += weight * issue.severity
                else:
                    total += weight
        
        # Minimal dampening - use power of 0.95 instead of 0.85
        # This makes penalties more impactful
        if total > 0:
            return (total ** 0.95) * 2.0
        return 0.0

    def _calculate_complexity_component(self, cyclomatic_complexity: Optional[int] = None) -> float:
        """Calculate cyclomatic complexity penalty: max(0, CC - Threshold) × Weight"""
        if cyclomatic_complexity is None or cyclomatic_complexity <= self.cc_threshold:
            return 0.0
            
        excess = cyclomatic_complexity - self.cc_threshold
        weight = self.weights.get(IssueCategory.CYCLOMATIC_COMPLEXITY, 4)
        
        # Use logarithmic scaling to avoid extreme penalties
        return math.log(1 + excess) * weight

    def _total_penalty(
        self,
        issues: List[Issue],
        block_metrics: List[BlockMetrics],
        cyclomatic_complexity: Optional[int] = None,
    ) -> float:
        """
        Calculate total penalty using hybrid model:
        RawScore = α × TotalEnergy + β × IssuePenalty + γ × CCPenalty
        """
        energy = self._calculate_energy_component(block_metrics)
        issue = self._calculate_issue_component(issues)
        complexity = self._calculate_complexity_component(cyclomatic_complexity)
        
        total = self.alpha * energy + self.beta * issue + self.gamma * complexity
        
        # Small minimum threshold for non-trivial code
        return max(0.1, total)

    def _calculate_efficiency_score(self, total_penalty: float) -> int:
        """
        Convert total penalty to efficiency score using exponential decay:
        Score = 100 × e^(-TotalPenalty / S)
        
        Small penalties → score near 100 (excellent)
        Large penalties → score approaches 0 (critical)
        """
        if total_penalty <= 0:
            return 100
        
        # Apply exponential decay with adjusted scaling
        score = 100 * math.exp(-total_penalty / self.scaling_constant)
        
        # Ensure score is in valid range
        score = max(0, min(100, score))
        
        # Round to nearest integer
        return int(round(score))

    def _find_hotspot(self, block_metrics: List[BlockMetrics]) -> Optional[BlockMetrics]:
        """Find the most energy-inefficient region."""
        if not block_metrics:
            return None
        
        # Filter out module-level blocks for hotspot detection
        non_module_blocks = [b for b in block_metrics if b.block_type != "module"]
        
        if not non_module_blocks:
            return None
        
        def hotspot_score(block: BlockMetrics) -> float:
            """Calculate hotspot score based on total energy and energy density."""
            lines = max(1, block.end_line - block.start_line + 1)
            
            # For large blocks, prioritize total energy
            if lines > 10:
                return block.total_energy * 0.7 + block.energy_per_line * lines * 0.3
            # For small blocks, prioritize energy density
            return block.total_energy * 0.4 + block.energy_per_line * lines * 0.6
        
        return max(non_module_blocks, key=hotspot_score)

    def compute_report(
        self,
        issues: List[Issue],
        block_metrics: List[BlockMetrics],
        source_code: str = "",
        filename: str = "",
        cyclomatic_complexity: Optional[int] = None,
        structural_warnings_count: int = 0,
    ) -> EnergyReport:
        """
        Build an EnergyReport using hybrid scoring model.
        Returns score where 100 = best efficiency, 0 = worst efficiency.
        """
        # Add structural warnings as issues
        if structural_warnings_count > 0:
            from green_software_meter.models import Issue as IssueModel
            
            for _ in range(structural_warnings_count):
                issues.append(
                    IssueModel(
                        category=IssueCategory.STRUCTURAL_WARNING,
                        message="Structural warning (Pylint)",
                        severity=1,
                        estimated_impact=2.0,
                    )
                )
        
        # Calculate total penalty and score
        total_penalty = self._total_penalty(issues, block_metrics, cyclomatic_complexity)
        score = self._calculate_efficiency_score(total_penalty)
        
        # Get grade based on score
        grade = EnergyGrade.from_score(score)
        
        # Find hotspot
        hotspot = self._find_hotspot(block_metrics)
        
        # Count source lines
        source_lines = len(source_code.splitlines()) if source_code else 0
        
        # Build component breakdown
        energy_component = self._calculate_energy_component(block_metrics)
        issue_component = self._calculate_issue_component(issues)
        complexity_component = self._calculate_complexity_component(cyclomatic_complexity)
        
        components = {
            "total_penalty": round(total_penalty, 2),
            "energy_component": round(energy_component, 2),
            "issue_component": round(issue_component, 2),
            "complexity_component": round(complexity_component, 2),
            "score": score,
            "scaling_constant": self.scaling_constant,
            "alpha": self.alpha,
            "beta": self.beta,
            "gamma": self.gamma,
            "formula": "Score = 100 × e^(-Penalty / S)",
        }
        
        return EnergyReport(
            score=score,
            grade=grade,
            issues=issues,
            block_metrics=block_metrics,
            hotspot=hotspot,
            filename=filename,
            source_lines=source_lines,
            raw_penalty=total_penalty,
            components=components,
        )