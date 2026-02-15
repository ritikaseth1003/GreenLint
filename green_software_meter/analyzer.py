"""
AST Analyzer - Detects energy-impacting patterns in Python source code.
Uses static analysis with block-level energy tracking.
"""

import ast
from typing import List, Optional, Set, Tuple

from green_software_meter.models import Issue, IssueCategory, BlockMetrics


# Base energy costs for different constructs - calibrated for realistic penalties
BASE_ENERGY_COSTS = {
    "statement": 0.8,
    "arithmetic": 1.2,
    "conditional": 2.0,
    "loop": 4.0,
    "function_call": 2.5,
    "comprehension": 3.0,
    "allocation": 2.0,
}

# AST node types that represent loops
LOOP_NODES = (ast.For, ast.While)

# Nodes that allocate memory
ALLOCATION_NODES = (
    ast.List, ast.Dict, ast.Set,
    ast.ListComp, ast.DictComp, ast.SetComp,
    ast.GeneratorExp,
)

# Expensive operations
EXPENSIVE_NAMES = frozenset({
    "eval", "exec", "compile", "open",
    "re.compile", "sorted", "glob.glob",
    "os.walk", "os.listdir", "subprocess",
    "pickle.loads", "pickle.dumps",
    "json.loads", "json.dumps",
})


class EnergyASTVisitor(ast.NodeVisitor):
    """
    Visits AST nodes and collects energy-related issues and block metrics.
    Tracks loop depth and detects patterns inside loops.
    """

    def __init__(self, filename: str = ""):
        self.issues: List[Issue] = []
        self.block_metrics: List[BlockMetrics] = []
        self.filename = filename
        self._loop_stack: List[int] = []
        self._function_stack: List[str] = []
        self._current_block: Optional[BlockMetrics] = None
        self._block_stack: List[BlockMetrics] = []
        self._depth_sensitivity = 0.3

    def _get_line(self, node: ast.AST) -> Optional[int]:
        return getattr(node, "lineno", None)

    def _get_end_line(self, node: ast.AST) -> Optional[int]:
        return getattr(node, "end_lineno", None)

    def _get_col(self, node: ast.AST) -> Optional[int]:
        return getattr(node, "col_offset", None)

    def _depth(self) -> int:
        return len(self._loop_stack)

    def _add_issue(
        self,
        category: IssueCategory,
        message: str,
        node: Optional[ast.AST] = None,
        detail: Optional[str] = None,
        severity: int = 1,
        estimated_impact: Optional[float] = None,
    ) -> None:
        line = self._get_line(node) if node else None
        col = self._get_col(node) if node else None
        
        # Calculate estimated impact based on depth if not provided
        if estimated_impact is None:
            base_impact = float(severity)
            if self._depth() > 0:
                # Increase impact for nested contexts
                estimated_impact = base_impact * (1 + self._depth() * 0.3)
            else:
                estimated_impact = base_impact
            
        self.issues.append(
            Issue(
                category=category,
                message=message,
                line=line,
                column=col,
                severity=severity,
                detail=detail,
                estimated_impact=estimated_impact,
            )
        )

    def _start_block(self, block_type: str, node: ast.AST, base_energy: float):
        """Start tracking a new code block."""
        start_line = self._get_line(node) or 0
        end_line = self._get_end_line(node) or start_line
        
        # Depth is current loop depth + 1 (for the block itself)
        block = BlockMetrics(
            block_type=block_type,
            start_line=start_line,
            end_line=end_line,
            base_energy=base_energy,
            depth=self._depth() + 1,
            operation_penalties=0.0,
        )
        
        self._block_stack.append(block)
        self._current_block = block

    def _end_block(self):
        """End tracking current block and add to metrics."""
        if self._block_stack:
            block = self._block_stack.pop()
            block.calculate(self._depth_sensitivity)
            self.block_metrics.append(block)
            self._current_block = self._block_stack[-1] if self._block_stack else None

    def _add_operation_penalty(self, penalty: float):
        """Add operation penalty to current block."""
        if self._current_block:
            self._current_block.operation_penalties += penalty

    def visit_Module(self, node: ast.Module):
        self._start_block("module", node, BASE_ENERGY_COSTS["statement"])
        self.generic_visit(node)
        self._end_block()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._function_stack.append(node.name)
        self._start_block("function", node, BASE_ENERGY_COSTS["function_call"])
        self._check_recursion(node, node.name)
        self.generic_visit(node)
        self._end_block()
        self._function_stack.pop()

    def visit_For(self, node: ast.For) -> None:
        self._loop_stack.append(self._get_line(node) or 0)
        self._start_block("loop", node, BASE_ENERGY_COSTS["loop"])
        
        # Detect nested loops (depth >= 2)
        if self._depth() >= 2:
            impact = 6.0 * (1 + self._depth() * 0.4)
            self._add_issue(
                IssueCategory.NESTED_LOOPS,
                "Nested loops detected",
                node,
                detail=f"depth {self._depth()}",
                severity=2,
                estimated_impact=impact,
            )
            self._add_operation_penalty(impact)
        
        # Detect deep nesting (depth > 2)
        if self._depth() > 2:
            impact = 8.0 * self._depth()
            self._add_issue(
                IssueCategory.LOOP_DEPTH,
                "High loop nesting depth",
                node,
                detail=f"depth {self._depth()}",
                severity=min(3, self._depth()),
                estimated_impact=impact,
            )
            self._add_operation_penalty(impact)
        
        self.generic_visit(node)
        self._end_block()
        self._loop_stack.pop()

    def visit_While(self, node: ast.While) -> None:
        self._loop_stack.append(self._get_line(node) or 0)
        self._start_block("loop", node, BASE_ENERGY_COSTS["loop"])
        
        # Detect nested loops (depth >= 2)
        if self._depth() >= 2:
            impact = 6.0 * (1 + self._depth() * 0.4)
            self._add_issue(
                IssueCategory.NESTED_LOOPS,
                "Nested loops detected",
                node,
                detail=f"depth {self._depth()}",
                severity=2,
                estimated_impact=impact,
            )
            self._add_operation_penalty(impact)
        
        # Detect deep nesting (depth > 2)
        if self._depth() > 2:
            impact = 8.0 * self._depth()
            self._add_issue(
                IssueCategory.LOOP_DEPTH,
                "High loop nesting depth",
                node,
                detail=f"depth {self._depth()}",
                severity=min(3, self._depth()),
                estimated_impact=impact,
            )
            self._add_operation_penalty(impact)
        
        self.generic_visit(node)
        self._end_block()
        self._loop_stack.pop()

    def visit_If(self, node: ast.If):
        self._start_block("conditional", node, BASE_ENERGY_COSTS["conditional"])
        self.generic_visit(node)
        self._end_block()

    def _visit_allocations_in_loop(self, node: ast.AST, kind: str) -> None:
        """Detect memory allocations inside loops."""
        if self._depth() < 1:
            return
        
        # Calculate impact based on allocation type and depth
        impact = BASE_ENERGY_COSTS["allocation"] * (1 + self._depth() * 0.6)
        self._add_operation_penalty(impact)
        
        # Create appropriate issue
        if "object" in kind.lower() or kind[0].isupper():
            self._add_issue(
                IssueCategory.OBJECT_CREATION_IN_LOOP,
                "Object creation inside loop",
                node,
                severity=2,
                estimated_impact=impact,
            )
        else:
            self._add_issue(
                IssueCategory.ALLOCATION_IN_LOOP,
                f"{kind.capitalize()} allocation inside loop",
                node,
                detail=kind,
                severity=2,
                estimated_impact=impact,
            )

    def visit_List(self, node: ast.List) -> None:
        if self._depth() >= 1:
            self._visit_allocations_in_loop(node, "list")
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        if self._depth() >= 1:
            self._visit_allocations_in_loop(node, "dict")
        self.generic_visit(node)

    def visit_Set(self, node: ast.Set) -> None:
        if self._depth() >= 1:
            self._visit_allocations_in_loop(node, "set")
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._start_block("comprehension", node, BASE_ENERGY_COSTS["comprehension"])
        if self._depth() >= 1:
            impact = BASE_ENERGY_COSTS["comprehension"] * (1 + self._depth() * 0.3)
            self._add_issue(
                IssueCategory.LIST_CREATION_IN_LOOP,
                "List comprehension inside loop (consider pre-allocating)",
                node,
                severity=1,
                estimated_impact=impact,
            )
            self._add_operation_penalty(impact)
        self.generic_visit(node)
        self._end_block()

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._start_block("comprehension", node, BASE_ENERGY_COSTS["comprehension"])
        if self._depth() >= 1:
            self._visit_allocations_in_loop(node, "dict comprehension")
        self.generic_visit(node)
        self._end_block()

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._start_block("comprehension", node, BASE_ENERGY_COSTS["comprehension"])
        if self._depth() >= 1:
            self._visit_allocations_in_loop(node, "set comprehension")
        self.generic_visit(node)
        self._end_block()

    def visit_Call(self, node: ast.Call) -> None:
        """Detect function calls and expensive operations."""
        impact = BASE_ENERGY_COSTS["function_call"]
        
        # Check for expensive operations
        expensive = False
        full_name = ""
        
        if isinstance(node.func, ast.Name):
            name = node.func.id
            
            # Handle built-in type constructors inside loops
            if name in ("list", "dict", "set", "tuple"):
                if self._depth() >= 1:
                    self._visit_allocations_in_loop(node, name)
                return
            
            # Handle class constructors (capitalized names)
            elif name and name[0].isupper():
                if self._depth() >= 1:
                    impact *= (1 + self._depth() * 0.3)
                    self._add_issue(
                        IssueCategory.OBJECT_CREATION_IN_LOOP,
                        f"Object creation inside loop: {name}",
                        node,
                        detail=name,
                        severity=2,
                        estimated_impact=impact,
                    )
                    self._add_operation_penalty(impact)
                return
            
            # Check for expensive function names
            elif name in EXPENSIVE_NAMES:
                expensive = True
                full_name = name
        
        elif isinstance(node.func, ast.Attribute):
            full_name = _qualified_name(node.func)
            if full_name in EXPENSIVE_NAMES or any(full_name.startswith(p) for p in ["re.", "os.", "glob."]):
                expensive = True
        
        # Handle expensive operations
        if expensive:
            if self._depth() >= 1:
                impact *= (1.5 + self._depth() * 0.4)
                self._add_issue(
                    IssueCategory.EXPENSIVE_OPERATION,
                    f"Expensive operation inside loop: {full_name}",
                    node,
                    detail=full_name,
                    severity=2,
                    estimated_impact=impact,
                )
                self._add_operation_penalty(impact)
            else:
                self._add_issue(
                    IssueCategory.EXPENSIVE_OPERATION,
                    f"Expensive operation: {full_name}",
                    node,
                    detail=full_name,
                    severity=1,
                    estimated_impact=impact,
                )
        
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        """Track arithmetic operations."""
        if self._current_block:
            # Add small penalty for arithmetic ops
            self._current_block.operation_penalties += BASE_ENERGY_COSTS["arithmetic"] * 0.05
        self.generic_visit(node)

    def _check_recursion(self, node: ast.FunctionDef, name: str) -> None:
        """Detect if function calls itself (recursion)."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Direct recursion: function calls itself by name
                if isinstance(child.func, ast.Name) and child.func.id == name:
                    impact = 12.0
                    self._add_issue(
                        IssueCategory.RECURSION,
                        "Recursion detected",
                        child,
                        detail=name,
                        severity=2,
                        estimated_impact=impact,
                    )
                    self._add_operation_penalty(impact)
                    return
                
                # Method recursion: self.method_name()
                if isinstance(child.func, ast.Attribute):
                    if (isinstance(child.func.value, ast.Name) and 
                        child.func.value.id == "self" and 
                        child.func.attr == name):
                        impact = 12.0
                        self._add_issue(
                            IssueCategory.RECURSION,
                            "Recursive method call detected",
                            child,
                            detail=child.func.attr,
                            severity=2,
                            estimated_impact=impact,
                        )
                        self._add_operation_penalty(impact)
                        return


def _qualified_name(node: ast.Attribute) -> str:
    """Build a string like 'os.path.join' from Attribute node."""
    if isinstance(node.value, ast.Name):
        return f"{node.value.id}.{node.attr}"
    if isinstance(node.value, ast.Attribute):
        return f"{_qualified_name(node.value)}.{node.attr}"
    return node.attr


class ASTAnalyzer:
    """
    Parses Python source and runs the energy-focused AST visitor.
    Returns issues and block metrics.
    """

    def analyze(self, source_code: str, filename: str = "") -> Tuple[List[Issue], List[BlockMetrics]]:
        """
        Parse source and collect all energy-related issues and block metrics.
        """
        try:
            tree = ast.parse(source_code, filename=filename or "<string>")
            visitor = EnergyASTVisitor(filename=filename)
            visitor.visit(tree)
            return visitor.issues, visitor.block_metrics
        except SyntaxError as e:
            # Return empty results for invalid syntax
            return [], []

    def analyze_block(self, code_block: str, block_type: str = "module", start_line: int = 1) -> List[Issue]:
        """
        Analyze a single code block for live editing feedback.
        """
        # Wrap block to make it parseable
        if block_type == "loop":
            wrapper = f"for _ in range(1):\n    {code_block}"
        elif block_type == "function":
            wrapper = f"def _wrapper():\n    {code_block}"
        else:
            wrapper = code_block
        
        try:
            tree = ast.parse(wrapper)
            visitor = EnergyASTVisitor()
            
            # Find and visit the actual block
            for node in ast.walk(tree):
                if block_type == "loop" and isinstance(node, (ast.For, ast.While)):
                    visitor.visit(node)
                    break
                elif block_type == "function" and isinstance(node, ast.FunctionDef):
                    visitor.visit(node)
                    break
                elif block_type == "module":
                    visitor.visit(tree)
                    break
            
            # Adjust line numbers
            for issue in visitor.issues:
                if issue.line:
                    issue.line += start_line - 1
            
            return visitor.issues
        except SyntaxError:
            return []