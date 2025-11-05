
"""
Example usage of the BQT Database.

This demonstrates connecting to the BQT+ PostgreSQL database and querying data.
"""

from bqtdb import BQTDatabase


def example_usage():
    """Example usage of the BQT Database connection."""
    try:
        with BQTDatabase() as db:
            # Query information_schema.tables to get table information
            query = """
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_schema = %s
                ORDER BY table_name;
            """
            tables = db.execute_query(query, (db.schema,))
            
            print(f"\nTables in schema '{db.schema}':")
            print("-" * 60)
            for table in tables:
                print(f"Schema: {table['table_schema']}, Table: {table['table_name']}, Type: {table['table_type']}")
            
            return tables
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    example_usage()
