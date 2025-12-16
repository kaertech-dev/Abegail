#!/usr/bin/env python3
"""
MySQL Read-Only MCP Server
A Model Context Protocol server providing read-only access to MySQL databases
"""

import os
import json
import asyncio
import mysql.connector
from mysql.connector import Error
from typing import Any, Sequence
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
    'connection_timeout': 60,
    'sql_mode': 'TRADITIONAL'
}

# System databases to exclude
SYSTEM_DATABASES = ['information_schema', 'mysql', 'performance_schema', 'sys']

class MySQLReadOnlyServer:
    def __init__(self):
        self.server = Server("mysql-readonly-server")
        self.connection = None
        
        # Register handlers
        self.server.list_resources()(self.list_resources)
        self.server.read_resource()(self.read_resource)
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)
        
    def get_connection(self, database=None):
        """Create a new database connection"""
        try:
            config = DB_CONFIG.copy()
            if database:
                config['database'] = database
            return mysql.connector.connect(**config)
        except Error as e:
            raise Exception(f"Database connection error: {str(e)}")
    
    def get_databases(self):
        """Get list of all non-system databases"""
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
    
    def get_tables(self, database):
        """Get all tables in a database"""
        try:
            conn = self.get_connection(database)
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            cursor.close()
            conn.close()
            return tables
        except Error as e:
            raise Exception(f"Error fetching tables from {database}: {str(e)}")
    
    def get_table_structure(self, database, table):
        """Get column information for a table"""
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
            raise Exception(f"Error fetching structure for {database}.{table}: {str(e)}")
    
    def execute_readonly_query(self, database, query, params=None):
        """Execute a read-only query"""
        # Security check: ensure query is read-only
        query_upper = query.strip().upper()
        forbidden_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'REPLACE']
        
        if any(keyword in query_upper for keyword in forbidden_keywords):
            raise Exception("Only SELECT queries are allowed. This is a read-only server.")
        
        if not query_upper.startswith('SELECT') and not query_upper.startswith('SHOW') and not query_upper.startswith('DESCRIBE'):
            raise Exception("Only SELECT, SHOW, and DESCRIBE queries are allowed.")
        
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
            raise Exception(f"Query execution error: {str(e)}")
    
    async def list_resources(self) -> list[Resource]:
        """List all available database resources"""
        resources = []
        
        try:
            databases = self.get_databases()
            
            # Add database overview resource
            resources.append(Resource(
                uri="mysql://databases/overview",
                name="Database Overview",
                mimeType="application/json",
                description="Overview of all available databases and their tables"
            ))
            
            # Add individual database resources
            for db in databases:
                resources.append(Resource(
                    uri=f"mysql://database/{db}",
                    name=f"Database: {db}",
                    mimeType="application/json",
                    description=f"Tables and structure of {db} database"
                ))
                
                # Add table resources
                try:
                    tables = self.get_tables(db)
                    for table in tables:
                        resources.append(Resource(
                            uri=f"mysql://database/{db}/table/{table}",
                            name=f"{db}.{table}",
                            mimeType="application/json",
                            description=f"Structure and sample data from {db}.{table}"
                        ))
                except:
                    continue
            
            return resources
        except Exception as e:
            return [Resource(
                uri="mysql://error",
                name="Error",
                mimeType="text/plain",
                description=f"Error listing resources: {str(e)}"
            )]
    
    async def read_resource(self, uri: str) -> str:
        """Read a specific database resource"""
        try:
            if uri == "mysql://databases/overview":
                # Return overview of all databases
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
                        overview[db] = {"error": "Could not access database"}
                
                return json.dumps(overview, indent=2)
            
            elif uri.startswith("mysql://database/"):
                parts = uri.replace("mysql://database/", "").split("/table/")
                
                if len(parts) == 1:
                    # Database overview
                    database = parts[0]
                    tables = self.get_tables(database)
                    
                    db_info = {
                        "database": database,
                        "table_count": len(tables),
                        "tables": {}
                    }
                    
                    for table in tables:
                        try:
                            structure = self.get_table_structure(database, table)
                            db_info["tables"][table] = {
                                "columns": structure,
                                "column_count": len(structure)
                            }
                        except:
                            db_info["tables"][table] = {"error": "Could not read structure"}
                    
                    return json.dumps(db_info, indent=2)
                
                elif len(parts) == 2:
                    # Specific table
                    database, table = parts
                    structure = self.get_table_structure(database, table)
                    
                    # Get sample data (first 10 rows)
                    query = f"SELECT * FROM `{table}` LIMIT 10"
                    sample_data = self.execute_readonly_query(database, query)
                    
                    table_info = {
                        "database": database,
                        "table": table,
                        "structure": structure,
                        "sample_data": sample_data,
                        "sample_count": len(sample_data)
                    }
                    
                    return json.dumps(table_info, indent=2, default=str)
            
            return json.dumps({"error": "Invalid resource URI"})
            
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    async def list_tools(self) -> list[Tool]:
        """List available database tools"""
        return [
            Tool(
                name="query_database",
                description="Execute a read-only SELECT query on any database. Only SELECT, SHOW, and DESCRIBE queries are allowed.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": "Name of the database to query"
                        },
                        "query": {
                            "type": "string",
                            "description": "SQL SELECT query to execute (read-only)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of rows to return (default: 100)",
                            "default": 100
                        }
                    },
                    "required": ["database", "query"]
                }
            ),
            Tool(
                name="get_table_data",
                description="Get data from a specific table with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": "Name of the database"
                        },
                        "table": {
                            "type": "string",
                            "description": "Name of the table"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of rows to return (default: 100)",
                            "default": 100
                        },
                        "where": {
                            "type": "string",
                            "description": "Optional WHERE clause (without the WHERE keyword)"
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Optional ORDER BY clause (without ORDER BY keyword)"
                        }
                    },
                    "required": ["database", "table"]
                }
            ),
            Tool(
                name="search_tables",
                description="Search for data across multiple tables in a database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": "Name of the database to search"
                        },
                        "search_term": {
                            "type": "string",
                            "description": "Term to search for"
                        },
                        "tables": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of specific tables to search (searches all if not provided)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results per table (default: 50)",
                            "default": 50
                        }
                    },
                    "required": ["database", "search_term"]
                }
            ),
            Tool(
                name="get_table_structure",
                description="Get detailed structure/schema information for a table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": "Name of the database"
                        },
                        "table": {
                            "type": "string",
                            "description": "Name of the table"
                        }
                    },
                    "required": ["database", "table"]
                }
            ),
            Tool(
                name="list_databases",
                description="List all available databases (excluding system databases)",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="list_tables",
                description="List all tables in a specific database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": "Name of the database"
                        }
                    },
                    "required": ["database"]
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute a tool"""
        try:
            if name == "query_database":
                database = arguments["database"]
                query = arguments["query"]
                limit = arguments.get("limit", 100)
                
                # Add LIMIT if not present
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
            
            elif name == "get_table_data":
                database = arguments["database"]
                table = arguments["table"]
                limit = arguments.get("limit", 100)
                where = arguments.get("where")
                order_by = arguments.get("order_by")
                
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
            
            elif name == "search_tables":
                database = arguments["database"]
                search_term = arguments["search_term"]
                tables = arguments.get("tables")
                limit = arguments.get("limit", 50)
                
                if not tables:
                    tables = self.get_tables(database)
                
                search_results = {}
                
                for table in tables:
                    try:
                        structure = self.get_table_structure(database, table)
                        text_columns = [col['field'] for col in structure 
                                      if 'char' in col['type'].lower() or 'text' in col['type'].lower()]
                        
                        if text_columns:
                            where_clauses = [f"`{col}` LIKE %s" for col in text_columns]
                            query = f"SELECT * FROM `{table}` WHERE {' OR '.join(where_clauses)} LIMIT {limit}"
                            params = [f"%{search_term}%"] * len(text_columns)
                            
                            results = self.execute_readonly_query(database, query, params)
                            
                            if results:
                                search_results[table] = {
                                    "match_count": len(results),
                                    "results": results
                                }
                    except:
                        continue
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "database": database,
                        "search_term": search_term,
                        "tables_searched": len(tables),
                        "tables_with_matches": len(search_results),
                        "results": search_results
                    }, indent=2, default=str)
                )]
            
            elif name == "get_table_structure":
                database = arguments["database"]
                table = arguments["table"]
                
                structure = self.get_table_structure(database, table)
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "database": database,
                        "table": table,
                        "columns": structure,
                        "column_count": len(structure)
                    }, indent=2)
                )]
            
            elif name == "list_databases":
                databases = self.get_databases()
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "databases": databases,
                        "count": len(databases)
                    }, indent=2)
                )]
            
            elif name == "list_tables":
                database = arguments["database"]
                tables = self.get_tables(database)
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "database": database,
                        "tables": tables,
                        "count": len(tables)
                    }, indent=2)
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
    server = MySQLReadOnlyServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())