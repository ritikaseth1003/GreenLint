"""Sample Python file with energy-impacting patterns for testing Green Software Meter."""

def process_data(items):
    result = []
    for i in items:
        row = []  # list allocation inside loop
        for j in range(10):  # nested loop
            row.append(i * j)
        result.append(row)
    return result


def recursive_factorial(n):
    if n <= 1:
        return 1
    return n * recursive_factorial(n - 1)  # recursion


def expensive_loop(paths):
    output = []
    for p in paths:
        with open(p) as f:  # I/O inside loop
            output.append(f.read())
    return output
