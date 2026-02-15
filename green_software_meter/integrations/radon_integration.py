"""
Radon integration for cyclomatic complexity.
Optional dependency: pip install radon
"""

from typing import Optional

try:
    import radon.complexity as radon_cc
    from radon.visitors import ComplexityVisitor

    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False


def get_cyclomatic_complexity(source_code: str, filename: str = "") -> Optional[int]:
    """
    Return average cyclomatic complexity (CC) for the given source.
    Returns None if Radon is not installed or on parse error.
    """
    if not RADON_AVAILABLE:
        return None
    try:
        visitor = ComplexityVisitor.from_code(source_code)
        blocks = visitor.blocks
        if not blocks:
            return 0
        total = sum(b.complexity for b in blocks)
        return max(0, total)  # average would be total / len(blocks); we use total for scoring
    except Exception:
        return None


def get_max_cyclomatic_complexity(source_code: str) -> Optional[int]:
    """Return the maximum cyclomatic complexity of any single block."""
    if not RADON_AVAILABLE:
        return None
    try:
        visitor = ComplexityVisitor.from_code(source_code)
        if not visitor.blocks:
            return 0
        return max(b.complexity for b in visitor.blocks)
    except Exception:
        return None
