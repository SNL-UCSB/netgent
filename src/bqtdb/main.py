import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

class BQTDatabase:
    """Helper class to manage connection to the BQT Database with type-safe models."""
    
    def __init__(
        self,
        host: str = "pinot.cs.ucsb.edu",
        port: int = 5432,
        database: str = "bqtDB",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username or os.getenv("DB_USERNAME")
        self.password = password or os.getenv("DB_PASSWORD")
        self.connection = None
        self.schema = "bqtplus"
        
        if not self.username:
            raise ValueError("Username must be provided either as parameter or DB_USERNAME env var")
        if not self.password:
            raise ValueError("Password must be provided either as parameter or DB_PASSWORD env var")
    
    def connect(self):
        """Establish connection to the database."""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
            )
            print(f"Successfully connected to {self.database} at {self.host}:{self.port}")
            return self.connection
        except psycopg2.Error as e:
            print(f"Error connecting to database: {e}")
            raise
    
    def disconnect(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            print("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def execute_query(self, query: str, params: Optional[tuple] = None, fetch: bool = True) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as dictionaries.
        
        Args:
            query: SQL query string
            params: Optional tuple of parameters for parameterized queries
            fetch: Whether to fetch results (True) or just execute (False)
        
        Returns:
            List of query results as dictionaries
        """
        if not self.connection:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch:
                    results = cursor.fetchall()
                    # Convert RealDictRow to regular dict for easier use
                    return [dict(row) for row in results]
                else:
                    self.connection.commit()
                    return []
        except psycopg2.Error as e:
            self.connection.rollback()
            print(f"Error executing query: {e}")
            raise
    
    # Pure SQL methods with type-safe returns
    def list_tables(self, schema: str = None) -> List[str]:
        """List all tables in the specified schema."""
        schema = schema or self.schema
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s
            ORDER BY table_name;
        """
        results = self.execute_query(query, (schema,))
        return [row['table_name'] for row in results]
    
    def get_table_columns(self, table_name: str, schema: str = None) -> List[Dict[str, Any]]:
        """Get column information for a specific table."""
        schema = schema or self.schema
        query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position;
        """
        return self.execute_query(query, (schema, table_name))
    
    def get_isp_tables(self) -> Dict[str, List[str]]:
        """
        Get all ISP-specific tables (addresses and results tables).
        
        Returns:
            Dictionary mapping ISP names to their table types
        """
        tables = self.list_tables()
        isp_tables = {}
        for table in tables:
            if table.endswith('_addresses') or table.endswith('_results'):
                isp_name = table.rsplit('_', 1)[0]
                table_type = table.rsplit('_', 1)[1]
                if isp_name not in isp_tables:
                    isp_tables[isp_name] = []
                isp_tables[isp_name].append(table_type)
        return isp_tables
    
    # Type-safe convenience methods
    def get_claims(self, limit: int = 100, isp: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get claims with optional filtering. Returns list of dictionaries."""
        query = f"SELECT * FROM {self.schema}.claims WHERE 1=1"
        params = []
        
        if isp:
            query += " AND isp = %s"
            params.append(isp)
        
        query += " ORDER BY claimed_at DESC LIMIT %s"
        params.append(limit)
        
        return self.execute_query(query, tuple(params) if params else None)
    
    
    
    
    def get_isp_config(self, isp: str) -> Optional[Dict[str, Any]]:
        """Get ISP configuration for a specific ISP. Returns dictionary or None."""
        query = f"SELECT * FROM {self.schema}.isp_config WHERE isp = %s LIMIT 1;"
        results = self.execute_query(query, (isp,))
        return results[0] if results else None
    
    def get_proxy_info(self) -> List[Dict[str, Any]]:
        """Get all proxy information. Returns list of dictionaries."""
        query = f"SELECT * FROM {self.schema}.proxy_info;"
        return self.execute_query(query)
    
    def get_isp_addresses(self, isp: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get addresses for a specific ISP. Returns raw dicts since schema may vary by ISP."""
        table_name = f"{isp}_addresses"
        query = f'SELECT * FROM {self.schema}."{table_name}" LIMIT %s;'
        return self.execute_query(query, (limit,))
    
    def get_isp_results(self, isp: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get results for a specific ISP. Returns raw dicts since schema may vary by ISP."""
        table_name = f"{isp}_results"
        query = f'SELECT * FROM {self.schema}."{table_name}" LIMIT %s;'
        return self.execute_query(query, (limit,))
    
    # Flexible method for complex queries
    def query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a custom SQL query.
        
        Args:
            sql: SQL query string
            params: Optional parameters for parameterized queries
        
        Returns:
            List of results as dictionaries
        """
        return self.execute_query(sql, params)
