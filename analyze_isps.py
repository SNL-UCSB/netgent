import ast
import glob
import os
import statistics
import sys

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

    lines_needed = 0
    lines_modified = 0
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
                        
                        # Calculate Lines Needed (Total size of the list or individual items)
                        # We sum the size of each StatePrompt call
                        for elt in node.value.elts:
                            lines_needed += (elt.end_lineno - elt.lineno + 1)
                            
                            # Calculate Lines Modified (triggers and actions)
                            if isinstance(elt, ast.Call):
                                for keyword in elt.keywords:
                                    if keyword.arg in ['triggers', 'actions', 'name', 'description']:
                                        # keyword.value is typically a List
                                        if hasattr(keyword.value, 'end_lineno') and hasattr(keyword.value, 'lineno'):
                                            # We count the lines this list spans
                                            # This is a good proxy for "content" lines
                                            lines_modified += (keyword.value.end_lineno - keyword.value.lineno + 1)
                        
                        # We verify only the first valid prompts list we find to avoid duplicates 
                        # (though usually there is only one)
                        break

    if found_prompts:
        return {
            'isp': os.path.basename(filepath).replace('.py', ''),
            'needed': lines_needed,
            'modified': lines_modified
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
    print(f"{'ISP':<25} | {'Lines Needed':<12} | {'Lines Modified':<14}")
    print("-" * 57)
    for r in results:
        print(f"{r['isp']:<25} | {r['needed']:<12} | {r['modified']:<14}")

    # Calculate CDFs
    needed_vals = sorted([r['needed'] for r in results])
    modified_vals = sorted([r['modified'] for r in results])
    
    def get_percentile(data, p):
        idx = int(len(data) * p)
        if idx >= len(data): idx = len(data) - 1
        return data[idx]

    print("\nCDF (Cumulative Distribution Function) Estimates:")
    print(f"{'Percentile':<10} | {'Lines Needed':<12} | {'Lines Modified':<14}")
    print("-" * 42)
    for p in [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0]:
        n_val = get_percentile(needed_vals, p)
        m_val = get_percentile(modified_vals, p)
        print(f"{int(p*100):<9}% | {n_val:<12} | {m_val:<14}")

    # Export to CSV
    import csv
    with open('isp_analysis.csv', 'w', newline='') as csvfile:
        fieldnames = ['ISP', 'Lines Needed', 'Lines Modified']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for r in results:
            writer.writerow({'ISP': r['isp'], 'Lines Needed': r['needed'], 'Lines Modified': r['modified']})
    
    print(f"\nCSV exported to 'isp_analysis.csv'")

if __name__ == "__main__":
    main()
