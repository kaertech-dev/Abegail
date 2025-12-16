# mcp_db_handler.py
# Handles MCP database operations for Flask app integration

import json
import subprocess
from typing import Optional, Dict, Any

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
    """
    Call an MCP tool via subprocess (this is a simplified version)
    In production, you'd use the actual MCP client library
    """
    try:
        # This is a placeholder - you'll need to implement actual MCP client
        # For now, we'll directly use mysql.connector as fallback
        from db_handler import DatabaseHandler
        db = DatabaseHandler()
        
        if tool_name == "list_databases":
            databases = db.get_all_databases()
            return json.dumps({"databases": databases, "count": len(databases)}, indent=2)
        
        elif tool_name == "list_tables":
            database = arguments.get("database")
            tables = db.get_tables_in_database(database)
            return json.dumps({"database": database, "tables": tables, "count": len(tables)}, indent=2)
        
        elif tool_name == "get_table_data":
            database = arguments["database"]
            table = arguments["table"]
            limit = arguments.get("limit", 100)
            where = arguments.get("where")
            order_by = arguments.get("order_by")
            
            data = db.get_table_data(database, table, limit, where)
            return json.dumps({
                "database": database,
                "table": table,
                "row_count": len(data) if data else 0,
                "results": data
            }, indent=2, default=str)
        
        elif tool_name == "query_database":
            database = arguments["database"]
            query = arguments["query"]
            limit = arguments.get("limit", 100)
            
            # Add LIMIT if not present
            if "LIMIT" not in query.upper():
                query = f"{query.rstrip(';')} LIMIT {limit}"
            
            results = db.execute_query(database, query)
            return json.dumps({
                "database": database,
                "query": query,
                "row_count": len(results) if results else 0,
                "results": results
            }, indent=2, default=str)
        
        elif tool_name == "search_tables":
            database = arguments["database"]
            search_term = arguments["search_term"]
            limit = arguments.get("limit", 50)
            
            results = db.search_across_databases(search_term, limit)
            return json.dumps({
                "database": database,
                "search_term": search_term,
                "results": results
            }, indent=2, default=str)
        
        elif tool_name == "get_table_structure":
            database = arguments["database"]
            table = arguments["table"]
            
            structure = db.get_table_structure(database, table)
            return json.dumps({
                "database": database,
                "table": table,
                "columns": structure,
                "column_count": len(structure)
            }, indent=2)
        
        return None
        
    except Exception as e:
        print(f"❌ Error calling MCP tool {tool_name}: {e}")
        return None


def needs_database_query(question: str) -> bool:
    """
    Check if question requires database access - MUST BE EXPLICIT
    This prevents confusion with company API queries
    """
    question_lower = question.lower()
    
    # ONLY match if explicitly asking about database structure/operations
    explicit_db_keywords = [
        'list database', 'show database', 'what databases', 'all databases',
        'database overview', 'show tables', 'what tables', 'list tables',
        'table structure', 'database schema', 'describe table',
        'query database', 'sql query', 'run query', 'execute query',
        'search database', 'database search', 'query the', 'select from'
    ]
    
    return any(keyword in question_lower for keyword in explicit_db_keywords)


def list_databases_via_mcp() -> str:
    """List all available databases"""
    result = call_mcp_tool("list_databases", {})
    if result:
        data = json.loads(result)
        databases = data.get("databases", [])
        return "\n".join([f"  • {db}" for db in databases])
    return "Could not retrieve databases"


def list_tables_via_mcp(database: str) -> str:
    """List all tables in a database"""
    result = call_mcp_tool("list_tables", {"database": database})
    if result:
        data = json.loads(result)
        tables = data.get("tables", [])
        return f"Tables in {database}:\n" + "\n".join([f"  • {table}" for table in tables])
    return f"Could not retrieve tables from {database}"


def get_table_data_via_mcp(database: str, table: str, limit: int = 100, where: str = None, order_by: str = None) -> str:
    """Get data from a specific table"""
    arguments = {
        "database": database,
        "table": table,
        "limit": limit
    }
    
    if where:
        arguments["where"] = where
    if order_by:
        arguments["order_by"] = order_by
    
    result = call_mcp_tool("get_table_data", arguments)
    if result:
        data = json.loads(result)
        results = data.get("results", [])
        
        if not results:
            return f"No data found in {database}.{table}"
        
        # Format results nicely
        output = f"Data from {database}.{table} ({data.get('row_count', 0)} rows):\n\n"
        output += json.dumps(results, indent=2, default=str)
        return output
    
    return f"Could not retrieve data from {database}.{table}"


def query_database_via_mcp(database: str, query: str, limit: int = 100) -> str:
    """Execute a read-only SQL query"""
    result = call_mcp_tool("query_database", {
        "database": database,
        "query": query,
        "limit": limit
    })
    
    if result:
        data = json.loads(result)
        results = data.get("results", [])
        
        if not results:
            return "Query returned no results"
        
        output = f"Query Results ({data.get('row_count', 0)} rows):\n\n"
        output += json.dumps(results, indent=2, default=str)
        return output
    
    return "Query execution failed"


def search_tables_via_mcp(database: str, search_term: str, limit: int = 50) -> str:
    """Search for a term across all tables in a database"""
    result = call_mcp_tool("search_tables", {
        "database": database,
        "search_term": search_term,
        "limit": limit
    })
    
    if result:
        data = json.loads(result)
        results = data.get("results", {})
        
        if not results:
            return f"No matches found for '{search_term}' in {database}"
        
        output = f"Search results for '{search_term}' in {database}:\n\n"
        
        for table, table_data in results.items():
            output += f"\n📊 Table: {table}\n"
            output += f"   Matches: {table_data.get('match_count', 0)}\n"
            output += json.dumps(table_data.get('results', [])[:3], indent=2, default=str)
            if table_data.get('match_count', 0) > 3:
                output += f"\n   ... and {table_data.get('match_count', 0) - 3} more\n"
        
        return output
    
    return f"Search failed for '{search_term}'"


def get_table_structure_via_mcp(database: str, table: str) -> str:
    """Get table structure/schema"""
    result = call_mcp_tool("get_table_structure", {
        "database": database,
        "table": table
    })
    
    if result:
        data = json.loads(result)
        columns = data.get("columns", [])
        
        output = f"Structure of {database}.{table}:\n\n"
        for col in columns:
            output += f"  • {col.get('field')} ({col.get('type')})"
            if col.get('key'):
                output += f" [{col.get('key')}]"
            output += "\n"
        
        return output
    
    return f"Could not retrieve structure for {database}.{table}"


def format_db_results_for_ai(results_json: str, context: str = "") -> list:
    """
    Format database results into chunks suitable for AI processing
    Returns a list of text chunks
    """
    try:
        data = json.loads(results_json)
        
        formatted = []
        
        if context:
            formatted.append(f"Context: {context}\n")
        
        # Add the data
        formatted.append(json.dumps(data, indent=2, default=str))
        
        return formatted
        
    except Exception as e:
        return [f"Error formatting database results: {str(e)}"]