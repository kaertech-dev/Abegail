# mcp_client_handler.py
"""
Unified MCP Client Handler
Connects Flask app to both API and Database MCP servers
"""
import subprocess
import json
from typing import Optional, Dict, Any

class MCPClient:
    """Base MCP client for subprocess communication"""
    
    def __init__(self, server_script: str):
        self.server_script = server_script
        self.process = None
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
        """Call MCP tool and return JSON response"""
        try:
            # Start MCP server process
            process = subprocess.Popen(
                ['python3', self.server_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Prepare MCP request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Send request and get response
            stdout, stderr = process.communicate(
                input=json.dumps(request) + "\n",
                timeout=30
            )
            
            if stderr:
                print(f"MCP stderr: {stderr}")
            
            # Parse response
            for line in stdout.split('\n'):
                if line.strip():
                    try:
                        response = json.loads(line)
                        if 'result' in response:
                            # Extract text content from MCP response
                            result = response['result']
                            if isinstance(result, list) and len(result) > 0:
                                if isinstance(result[0], dict) and 'text' in result[0]:
                                    return json.loads(result[0]['text'])
                            return result
                    except json.JSONDecodeError:
                        continue
            
            return None
            
        except subprocess.TimeoutExpired:
            if process:
                process.kill()
            return {"error": "MCP request timeout"}
        except Exception as e:
            return {"error": str(e)}

class APIClient(MCPClient):
    """Client for Company API MCP Server"""
    
    def __init__(self):
        super().__init__('mcp_api_server.py')
    
    def fetch_production_data(self, format_type: str = "raw") -> Optional[Dict]:
        """Fetch production data from API"""
        return self.call_tool("fetch_production_data", {"format": format_type})
    
    def get_operator_stats(self, operator_id: Optional[str] = None) -> Optional[Dict]:
        """Get operator statistics"""
        args = {}
        if operator_id:
            args["operator_id"] = operator_id
        return self.call_tool("get_operator_stats", args)
    
    def filter_by_customer(self, customer: str) -> Optional[Dict]:
        """Filter data by customer"""
        return self.call_tool("filter_by_customer", {"customer": customer})
    
    def filter_by_product(self, product: str) -> Optional[Dict]:
        """Filter data by product"""
        return self.call_tool("filter_by_product", {"product": product})
    
    def get_top_performers(self, limit: int = 5) -> Optional[Dict]:
        """Get top performing operators"""
        return self.call_tool("get_top_performers", {"limit": limit})

class DatabaseClient(MCPClient):
    """Client for Database MCP Server"""
    
    def __init__(self):
        super().__init__('mcp_db_server.py')
    
    def list_databases(self) -> Optional[Dict]:
        """List all databases"""
        return self.call_tool("list_databases", {})
    
    def list_tables(self, database: str) -> Optional[Dict]:
        """List tables in database"""
        return self.call_tool("list_tables", {"database": database})
    
    def analyze_table(self, database: str, table: str) -> Optional[Dict]:
        """Analyze table structure"""
        return self.call_tool("analyze_table", {
            "database": database,
            "table": table
        })
    
    def query_table(self, database: str, query: str, limit: int = 100) -> Optional[Dict]:
        """Execute SELECT query"""
        return self.call_tool("query_table", {
            "database": database,
            "query": query,
            "limit": limit
        })
    
    def smart_search(self, database: str, search_term: str, limit: int = 50) -> Optional[Dict]:
        """Smart search across database"""
        return self.call_tool("smart_search", {
            "database": database,
            "search_term": search_term,
            "limit": limit
        })
    
    def get_table_data(self, database: str, table: str, 
                      where: Optional[str] = None,
                      order_by: Optional[str] = None,
                      limit: int = 100) -> Optional[Dict]:
        """Get table data with filters"""
        args = {
            "database": database,
            "table": table,
            "limit": limit
        }
        if where:
            args["where"] = where
        if order_by:
            args["order_by"] = order_by
        
        return self.call_tool("get_table_data", args)

# Global client instances
_api_client = None
_db_client = None

def get_api_client() -> APIClient:
    """Get singleton API client"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client

def get_db_client() -> DatabaseClient:
    """Get singleton Database client"""
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client

# Convenience functions for Flask integration

def fetch_company_data_mcp():
    """Fetch company data via MCP"""
    client = get_api_client()
    result = client.fetch_production_data()
    
    if result and not result.get('error'):
        data = result.get('data', [])
        # Format for AI consumption
        formatted = json.dumps(data, indent=2, default=str)
        return [formatted], data
    
    return None, None

def list_databases_mcp() -> str:
    """List databases via MCP"""
    client = get_db_client()
    result = client.list_databases()
    
    if result and not result.get('error'):
        databases = result.get('databases', [])
        return "\n".join([f"  • {db}" for db in databases])
    
    return "Could not retrieve databases"

def analyze_database_mcp(database: str) -> str:
    """Analyze database schema via MCP"""
    client = get_db_client()
    result = client.list_tables(database)
    
    if result and not result.get('error'):
        tables = result.get('tables', [])
        output = f"📊 **Database: {database}**\n\n"
        output += f"**Total Tables: {len(tables)}**\n\n"
        
        for table in tables[:10]:  # Limit to first 10
            analysis = client.analyze_table(database, table)
            if analysis and not analysis.get('error'):
                output += f"### 📋 Table: `{table}`\n"
                output += f"- Columns: {len(analysis.get('columns', []))}\n"
                if analysis.get('primary_keys'):
                    output += f"- Primary Keys: {', '.join(analysis['primary_keys'])}\n"
                output += "\n"
        
        return output
    
    return f"Could not analyze database: {database}"

def smart_search_mcp(database: str, search_term: str) -> str:
    """Smart search via MCP"""
    client = get_db_client()
    result = client.smart_search(database, search_term)
    
    if result and not result.get('error'):
        output = f"🔍 **Search Results for '{search_term}' in {database}**\n\n"
        output += f"Tables searched: {result.get('tables_searched', 0)}\n"
        output += f"Tables with matches: {result.get('tables_with_matches', 0)}\n\n"
        
        for table, data in result.get('results', {}).items():
            output += f"### 📋 {table} ({data['matches']} matches)\n"
            output += f"```json\n{json.dumps(data['data'][:2], indent=2, default=str)}\n```\n\n"
        
        return output
    
    return f"Search failed for '{search_term}'"

def query_database_mcp(database: str, query: str) -> str:
    """Query database via MCP"""
    client = get_db_client()
    result = client.query_table(database, query)
    
    if result and not result.get('error'):
        output = f"**Query Results ({result.get('row_count', 0)} rows)**\n\n"
        output += f"```json\n{json.dumps(result.get('results', [])[:5], indent=2, default=str)}\n```"
        return output
    
    return f"Query failed: {result.get('error', 'Unknown error')}"