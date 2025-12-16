#!/usr/bin/env python3
"""
Enhanced MySQL MCP Server
Provides intelligent database access with schema introspection
"""

import os
import json
import asyncio
import mysql.connector
from mysql.connector import Error
from typing import Any, Sequence, Dict, List, Optional
from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.server.stdio

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '192.168.1.38'),
    'user': os.getenv('DB_USER', 'labeling'),
    'password': os.getenv('DB_PASSWORD', 'labeling'),
    'autocommit': True,
    'use_unicode': True,
    'charset': 'utf8mb4',
    'connection_timeout': 60
}

SYSTEM_DATABASES = ['information_schema', 'mysql', 'performance_schema', 'sys']


class DatabaseMCPServer:
    """Enhanced MCP Server for Database Operations"""
    
    def __init__(self):
        self.server = Server("database-mcp-server")
        self.connection = None
        self.schema_cache = {}
        
        # Register handlers
        self.server.list_resources()(self.list_resources)
        self.server.read_resource()(self.read_resource)
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)
    
    def get_connection(self, database: Optional[str] = None):
        """Create database connection"""
        try:
            config = DB_CONFIG.copy()
            if database:
                config['database'] = database
            return mysql.connector.connect(**config)
        except Error as e:
            raise Exception(f"Database connection error: {str(e)}")
    
    def get_databases(self) -> List[str]:
        """Get all non-system databases"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            databases = [db[0] for db in cursor.fetchall() if db[0] not in SYSTEM_DATABASES]
            cursor.close()
            conn.close()
            return databases
        except Error as e:
            raise Exception(f"Error fetching databases: {str(e)}")
    
    def get_tables(self, database: str) -> List[str]:
        """Get all tables in database"""
        try:
            conn = self.get_connection(database)
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            cursor.close()
            conn.close()
            return tables
        except Error as e:
            raise Exception(f"Error fetching tables: {str(e)}")
    
    def get_table_structure(self, database: str, table: str) -> List[Dict]:
        """Get table column information"""
        try:
            conn = self.get_connection(database)
            cursor = conn.cursor()
            cursor.execute(f"DESCRIBE `{table}`")
            columns = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [{
                "field": col[0],
                "type": col[1],
                "null": col[2],
                "key": col[3],
                "default": col[4],
                "extra": col[5]
            } for col in columns]
        except Error as e:
            raise Exception(f"Error fetching structure: {str(e)}")
    
    def analyze_table(self, database: str, table: str) -> Dict:
        """Deep analysis of table structure"""
        structure = self.get_table_structure(database, table)
        
        analysis = {
            "database": database,
            "table": table,
            "columns": structure,
            "primary_keys": [],
            "key_fields": {},
            "searchable_fields": [],
            "date_fields": [],
            "numeric_fields": []
        }
        
        for col in structure:
            field_name = col['field'].lower()
            field_type = col['type'].lower()
            
            # Identify primary keys
            if col['key'] == 'PRI':
                analysis['primary_keys'].append(col['field'])
            
            # Identify field patterns
            if any(p in field_name for p in ['id', '_id']):
                analysis['key_fields']['id_field'] = col['field']
            
            if any(p in field_name for p in ['name', 'title', 'description']):
                if 'name_fields' not in analysis['key_fields']:
                    analysis['key_fields']['name_fields'] = []
                analysis['key_fields']['name_fields'].append(col['field'])
            
            if any(p in field_name for p in ['date', 'time', 'created', 'updated']):
                analysis['date_fields'].append(col['field'])
            
            if any(p in field_name for p in ['operator', 'user', 'employee', 'worker']):
                analysis['key_fields']['operator_field'] = col['field']
            
            # Identify searchable text fields
            if any(t in field_type for t in ['char', 'text', 'varchar']):
                analysis['searchable_fields'].append(col['field'])
            
            # Identify numeric fields
            if any(t in field_type for t in ['int', 'decimal', 'float', 'double']):
                analysis['numeric_fields'].append(col['field'])
        
        return analysis
    
    def execute_readonly_query(self, database: str, query: str, params: Optional[tuple] = None):
        """Execute read-only query with safety checks"""
        query_upper = query.strip().upper()
        forbidden = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE']
        
        if any(keyword in query_upper for keyword in forbidden):
            raise Exception("Only SELECT queries allowed. This is read-only.")
        
        if not query_upper.startswith(('SELECT', 'SHOW', 'DESCRIBE')):
            raise Exception("Only SELECT, SHOW, and DESCRIBE queries allowed.")
        
        try:
            conn = self.get_connection(database)
            cursor = conn.cursor(dictionary=True)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return results
        except Error as e:
            raise Exception(f"Query error: {str(e)}")
    
    def smart_search(self, database: str, search_term: str, limit: int = 50) -> Dict:
        """Intelligent search across all tables"""
        tables = self.get_tables(database)
        results = {}
        
        for table in tables:
            try:
                analysis = self.analyze_table(database, table)
                searchable = analysis['searchable_fields']
                
                if not searchable:
                    continue
                
                where_clauses = [f"`{col}` LIKE %s" for col in searchable]
                query = f"SELECT * FROM `{table}` WHERE {' OR '.join(where_clauses)} LIMIT {limit}"
                params = tuple([f"%{search_term}%"] * len(searchable))
                
                data = self.execute_readonly_query(database, query, params)
                
                if data:
                    results[table] = {
                        "matches": len(data),
                        "searched_columns": searchable,
                        "data": data
                    }
            except:
                continue
        
        return {
            "database": database,
            "search_term": search_term,
            "tables_searched": len(tables),
            "tables_with_matches": len(results),
            "results": results
        }
    
    async def list_resources(self) -> list[Resource]:
        """List all database resources"""
        resources = []
        
        try:
            databases = self.get_databases()
            
            resources.append(Resource(
                uri="db://overview",
                name="Database Overview",
                mimeType="application/json",
                description="Overview of all databases"
            ))
            
            for db in databases:
                resources.append(Resource(
                    uri=f"db://{db}/schema",
                    name=f"Schema: {db}",
                    mimeType="application/json",
                    description=f"Complete schema of {db}"
                ))
                
                try:
                    tables = self.get_tables(db)
                    for table in tables:
                        resources.append(Resource(
                            uri=f"db://{db}/{table}",
                            name=f"{db}.{table}",
                            mimeType="application/json",
                            description=f"Structure and data from {table}"
                        ))
                except:
                    continue
            
            return resources
        except Exception as e:
            return [Resource(
                uri="db://error",
                name="Error",
                mimeType="text/plain",
                description=f"Error: {str(e)}"
            )]
    
    async def read_resource(self, uri: str) -> str:
        """Read specific database resource"""
        try:
            if uri == "db://overview":
                databases = self.get_databases()
                overview = {}
                
                for db in databases:
                    try:
                        tables = self.get_tables(db)
                        overview[db] = {
                            "table_count": len(tables),
                            "tables": tables
                        }
                    except:
                        overview[db] = {"error": "Could not access"}
                
                return json.dumps(overview, indent=2)
            
            elif uri.startswith("db://"):
                parts = uri.replace("db://", "").split("/")
                
                if len(parts) == 2 and parts[1] == "schema":
                    database = parts[0]
                    tables = self.get_tables(database)
                    
                    schema = {
                        "database": database,
                        "table_count": len(tables),
                        "tables": {}
                    }
                    
                    for table in tables:
                        try:
                            analysis = self.analyze_table(database, table)
                            schema["tables"][table] = analysis
                        except:
                            schema["tables"][table] = {"error": "Could not analyze"}
                    
                    return json.dumps(schema, indent=2)
                
                elif len(parts) == 2:
                    database, table = parts
                    analysis = self.analyze_table(database, table)
                    
                    # Get sample data
                    query = f"SELECT * FROM `{table}` LIMIT 5"
                    sample_data = self.execute_readonly_query(database, query)
                    
                    analysis["sample_data"] = sample_data
                    return json.dumps(analysis, indent=2, default=str)
            
            return json.dumps({"error": "Invalid URI"})
            
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    async def list_tools(self) -> list[Tool]:
        """List available database tools"""
        return [
            Tool(
                name="list_databases",
                description="List all available databases",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="list_tables",
                description="List all tables in a database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {"type": "string", "description": "Database name"}
                    },
                    "required": ["database"]
                }
            ),
            Tool(
                name="analyze_table",
                description="Get detailed analysis of table structure",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {"type": "string", "description": "Database name"},
                        "table": {"type": "string", "description": "Table name"}
                    },
                    "required": ["database", "table"]
                }
            ),
            Tool(
                name="query_table",
                description="Execute SELECT query on a table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {"type": "string", "description": "Database name"},
                        "query": {"type": "string", "description": "SQL SELECT query"},
                        "limit": {"type": "integer", "description": "Row limit", "default": 100}
                    },
                    "required": ["database", "query"]
                }
            ),
            Tool(
                name="smart_search",
                description="Search term across all tables in database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {"type": "string", "description": "Database name"},
                        "search_term": {"type": "string", "description": "Search term"},
                        "limit": {"type": "integer", "description": "Results per table", "default": 50}
                    },
                    "required": ["database", "search_term"]
                }
            ),
            Tool(
                name="get_table_data",
                description="Get data from table with optional filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {"type": "string"},
                        "table": {"type": "string"},
                        "where": {"type": "string", "description": "WHERE clause (optional)"},
                        "order_by": {"type": "string", "description": "ORDER BY clause (optional)"},
                        "limit": {"type": "integer", "default": 100}
                    },
                    "required": ["database", "table"]
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute database tool"""
        try:
            if name == "list_databases":
                databases = self.get_databases()
                return [TextContent(
                    type="text",
                    text=json.dumps({"databases": databases, "count": len(databases)}, indent=2)
                )]
            
            elif name == "list_tables":
                database = arguments["database"]
                tables = self.get_tables(database)
                return [TextContent(
                    type="text",
                    text=json.dumps({"database": database, "tables": tables, "count": len(tables)}, indent=2)
                )]
            
            elif name == "analyze_table":
                database = arguments["database"]
                table = arguments["table"]
                analysis = self.analyze_table(database, table)
                return [TextContent(
                    type="text",
                    text=json.dumps(analysis, indent=2)
                )]
            
            elif name == "query_table":
                database = arguments["database"]
                query = arguments["query"]
                limit = arguments.get("limit", 100)
                
                if "LIMIT" not in query.upper():
                    query = f"{query.rstrip(';')} LIMIT {limit}"
                
                results = self.execute_readonly_query(database, query)
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "database": database,
                        "query": query,
                        "row_count": len(results),
                        "results": results
                    }, indent=2, default=str)
                )]
            
            elif name == "smart_search":
                database = arguments["database"]
                search_term = arguments["search_term"]
                limit = arguments.get("limit", 50)
                
                results = self.smart_search(database, search_term, limit)
                return [TextContent(
                    type="text",
                    text=json.dumps(results, indent=2, default=str)
                )]
            
            elif name == "get_table_data":
                database = arguments["database"]
                table = arguments["table"]
                where = arguments.get("where")
                order_by = arguments.get("order_by")
                limit = arguments.get("limit", 100)
                
                query = f"SELECT * FROM `{table}`"
                if where:
                    query += f" WHERE {where}"
                if order_by:
                    query += f" ORDER BY {order_by}"
                query += f" LIMIT {limit}"
                
                results = self.execute_readonly_query(database, query)
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "database": database,
                        "table": table,
                        "row_count": len(results),
                        "results": results
                    }, indent=2, default=str)
                )]
            
            else:
                raise Exception(f"Unknown tool: {name}")
                
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)})
            )]
    
    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    server = DatabaseMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())