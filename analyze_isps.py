import ast
import glob
import os
import statistics
import sys

def count_string_chars(node):
    """Recursively count characters in string literals within an AST node."""
    total = 0
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        total += len(node.value)
    elif isinstance(node, ast.List):
        for elt in node.elts:
            total += count_string_chars(elt)
    elif isinstance(node, ast.JoinedStr):  # f-strings
        for value in node.values:
            total += count_string_chars(value)
    return total


def analyze_file(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception as e:
        return None

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None

    chars_needed = 0
    chars_modified = 0
    found_prompts = False

    for node in ast.walk(tree):
        # Look for assignments (prompts = [...])
        if isinstance(node, ast.Assign):
            # Check if it's a list
            if isinstance(node.value, ast.List):
                # Check if elements are StatePrompt calls
                if node.value.elts and isinstance(node.value.elts[0], ast.Call):
                    func = node.value.elts[0].func
                    if isinstance(func, ast.Name) and func.id == 'StatePrompt':
                        found_prompts = True
                        
                        # Count characters in each StatePrompt
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Call):
                                for keyword in elt.keywords:
                                    # Count all user-defined string content for "chars needed"
                                    if keyword.arg in ['name', 'description', 'triggers', 'actions']:
                                        chars_needed += count_string_chars(keyword.value)
                                    # Count only triggers/actions for "chars modified" (interface-dependent)
                                    if keyword.arg in ['triggers', 'actions']:
                                        chars_modified += count_string_chars(keyword.value)
                        
                        # We verify only the first valid prompts list we find to avoid duplicates 
                        # (though usually there is only one)
                        break

    if found_prompts:
        return {
            'isp': os.path.basename(filepath).replace('.py', ''),
            'chars_needed': chars_needed,
            'chars_modified': chars_modified
        }
    return None

def main():
    files = glob.glob('examples/isps/*.py')
    results = []
    
    print(f"Scanning {len(files)} files...")

    for f in files:
        data = analyze_file(f)
        if data:
            results.append(data)

    if not results:
        print("No valid ISP scripts found.")
        return

    # Sort by ISP name
    results.sort(key=lambda x: x['isp'])

    # Print Table
    print(f"{'ISP':<25} | {'Chars Needed':<12} | {'Chars Modified':<14}")
    print("-" * 57)
    for r in results:
        print(f"{r['isp']:<25} | {r['chars_needed']:<12} | {r['chars_modified']:<14}")

    # Calculate CDFs
    needed_vals = sorted([r['chars_needed'] for r in results])
    modified_vals = sorted([r['chars_modified'] for r in results])
    
    def get_percentile(data, p):
        idx = int(len(data) * p)
        if idx >= len(data): idx = len(data) - 1
        return data[idx]

    print("\nCDF (Cumulative Distribution Function) Estimates:")
    print(f"{'Percentile':<10} | {'Chars Needed':<12} | {'Chars Modified':<14}")
    print("-" * 42)
    for p in [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0]:
        n_val = get_percentile(needed_vals, p)
        m_val = get_percentile(modified_vals, p)
        print(f"{int(p*100):<9}% | {n_val:<12} | {m_val:<14}")

    # Export to CSV
    import csv
    with open('isp_analysis.csv', 'w', newline='') as csvfile:
        fieldnames = ['ISP', 'Chars Needed', 'Chars Modified']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for r in results:
            writer.writerow({'ISP': r['isp'], 'Chars Needed': r['chars_needed'], 'Chars Modified': r['chars_modified']})
    
    print(f"\nCSV exported to 'isp_analysis.csv'")

if __name__ == "__main__":
    main()
