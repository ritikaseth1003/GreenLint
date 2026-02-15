from green_software_meter.analyzer import ASTAnalyzer
from green_software_meter.scoring import ScoringEngine

# Read code from test.py file
with open('test.py', 'r') as f:
    code = f.read()

print("=" * 50)
print("DEBUG: Energy Analysis for test.py")
print("=" * 50)

analyzer = ASTAnalyzer()
result = analyzer.analyze(code)

# Handle different return types
if isinstance(result, tuple) and len(result) == 2:
    issues, blocks = result
    print(f"\n✅ Analyzer returned tuple with {len(issues)} issues and {len(blocks)} blocks")
elif isinstance(result, list):
    issues = result
    blocks = []
    print(f"\n✅ Analyzer returned list with {len(issues)} issues (no blocks)")
else:
    print(f"\n❌ Unexpected return type: {type(result)}")
    issues = []
    blocks = []

print(f"\n1. ISSUES DETECTED: {len(issues)}")
for issue in issues:
    print(f"   • {issue.message}")
    print(f"     Category: {issue.category.value}")
    print(f"     Severity: {issue.severity}")
    print(f"     Impact: {issue.estimated_impact}")
    print(f"     Line: {issue.line}")

print(f"\n2. BLOCKS DETECTED: {len(blocks)}")
total_energy = 0
for block in blocks:
    print(f"   • {block.block_type} (lines {block.start_line}-{block.end_line})")
    print(f"     Base Energy: {block.base_energy}")
    print(f"     Depth: {block.depth}")
    print(f"     Operation Penalties: {block.operation_penalties}")
    print(f"     Total Energy: {block.total_energy}")
    print(f"     Energy/Line: {block.energy_per_line}")
    total_energy += block.total_energy

print(f"\n3. TOTAL ENERGY SUM: {total_energy}")

engine = ScoringEngine()
print(f"\n4. SCORING ENGINE PARAMETERS:")
print(f"   • alpha (Energy weight): {engine.alpha}")
print(f"   • beta (Issue weight): {engine.beta}")
print(f"   • gamma (Complexity weight): {engine.gamma}")
print(f"   • scaling_constant (S): {engine.scaling_constant}")

# Calculate components manually
energy_component = engine._calculate_energy_component(blocks) if blocks else 0
issue_component = engine._calculate_issue_component(issues)
complexity_component = engine._calculate_complexity_component(None)

print(f"\n5. COMPONENTS:")
print(f"   • Energy Component: {energy_component}")
print(f"   • Issue Component: {issue_component}")
print(f"   • Complexity Component: {complexity_component}")

raw_penalty = engine._total_penalty(issues, blocks, None)
print(f"\n6. RAW PENALTY = {raw_penalty}")

score = engine._calculate_efficiency_score(raw_penalty)
print(f"\n7. FINAL SCORE = {score}")

# Only create report if we have the right data
if hasattr(engine, 'compute_report'):
    try:
        report = engine.compute_report(issues, blocks, code)
        print(f"\n8. REPORT:")
        print(f"   • Score: {report.score}")
        print(f"   • Grade: {report.grade.letter}({report.score})")
        print(f"   • Raw Penalty: {report.raw_penalty}")
    except Exception as e:
        print(f"\n❌ Error creating report: {e}")
else:
    print("\n8. REPORT: compute_report method not available")