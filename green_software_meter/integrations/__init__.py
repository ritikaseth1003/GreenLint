"""
Optional integrations: Radon (cyclomatic complexity), Pylint (structural warnings).
"""

try:
    from green_software_meter.integrations.radon_integration import (
        get_cyclomatic_complexity,
        get_max_cyclomatic_complexity,
    )
except ImportError:
    def get_cyclomatic_complexity(*args, **kwargs):
        return None
    def get_max_cyclomatic_complexity(*args, **kwargs):
        return None

try:
    from green_software_meter.integrations.pylint_integration import get_pylint_warnings_count
except ImportError:
    def get_pylint_warnings_count(*args, **kwargs):
        return None

__all__ = ["get_cyclomatic_complexity", "get_max_cyclomatic_complexity", "get_pylint_warnings_count"]
