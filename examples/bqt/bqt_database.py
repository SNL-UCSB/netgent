"""
Example usage of the BQT Database.
"""

import sys
import os
import json

# Add the src directory to the python path so we can import bqtdb
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from bqtdb.main import BQTDatabase

def example_usage():
    """Example usage of the BQT Database connection."""
    try:
        # Initialize the database connection
        # Note: Ensure DB_USERNAME and DB_PASSWORD are set in your .env file
        with BQTDatabase() as db:
            print(f"Connected to schema: {db.schema}")
            
            net123_rows = db.query("SELECT * FROM bqtplus.net123_addresses")
            for row in net123_rows:
                print(json.dumps(row, indent=2, default=str))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    example_usage()
