import csv
import json
import os

def extract_isps(input_csv, output_csv):
    unique_isps = set()
    
    try:
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    metadata_str = row.get('metadata')
                    if metadata_str:
                        # Metadata is a JSON string
                        metadata = json.loads(metadata_str)
                        session = metadata.get('session')
                        if session:
                            unique_isps.add(session)
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse metadata for row: {row}")
                except Exception as e:
                    print(f"Error processing row: {e}")

        # Sort extracted ISPs
        sorted_isps = sorted(list(unique_isps))
        
        # Write to output CSV
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['isp'])  # Header
            for isp in sorted_isps:
                writer.writerow([isp])
                
        print(f"Successfully extracted {len(sorted_isps)} unique ISPs to {output_csv}")
        print("ISPs found:")
        for isp in sorted_isps:
            print(f"- {isp}")

    except FileNotFoundError:
        print(f"Error: Input file '{input_csv}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Use the latest trace file identified
    latest_trace = "queries/traces_export_20260126_092307.csv"
    output_file = "extracted_isps.csv"
    extract_isps(latest_trace, output_file)
