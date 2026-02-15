"""
Pylint integration for structural warnings.
Optional dependency: pip install pylint
Runs Pylint in programmatic mode and counts messages.
"""

from typing import List, Optional

try:
    from pylint.lint import Run as PylintRun
    from pylint.reporters import CollectingReporter

    PYLINT_AVAILABLE = True
except ImportError:
    PYLINT_AVAILABLE = False


def get_pylint_warnings_count(
    filepath: str, extra_args: Optional[List[str]] = None
) -> Optional[int]:
    """
    Run Pylint on the file and return the number of messages.
    Returns None if Pylint is not installed or on error.
    """
    if not PYLINT_AVAILABLE:
        return None
    try:
        reporter = CollectingReporter()
        args = [filepath, "--reports=no"]
        if extra_args:
            args.extend(extra_args)
        PylintRun(args, reporter=reporter, do_exit=False)
        return len(reporter.messages)
    except Exception:
        return None
