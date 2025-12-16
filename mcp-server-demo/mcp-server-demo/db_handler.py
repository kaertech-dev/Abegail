# db_handler.py - Fixed Active Database Detection
import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, List, Tuple
import json

class DatabaseHandler:
    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password
        self.system_databases = ['information_schema', 'mysql', 'performance_schema', 'sys']
        self._active_databases_cache = None
    
    def connect(self, database: Optional[str] = None):
        """Connect to MySQL"""
        try:
            config = {
                'host': self.host,
                'user': self.user,
                'password': self.password,
                'autocommit': True,
                'use_unicode': True,
                'charset': 'utf8mb4'
            }
            if database:
                config['database'] = database
            
            return mysql.connector.connect(**config)
        except Error as e:
            print(f"❌ Connection error: {e}")
            return None
    
    def get_table_columns(self, database: str, table: str) -> List[Dict]:
        """Get column information for a table"""
        conn = self.connect(database)
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"DESCRIBE `{table}`")
            columns = cursor.fetchall()
            cursor.close()
            conn.close()
            return columns
        except Error as e:
            print(f"❌ Error getting columns: {e}")
            return []
    
    def get_active_databases(self) -> List[Dict]:
        """Get active databases from projectsdb.projects"""
        conn = self.connect('projectsdb')
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # First, get column names to debug
            cursor.execute("DESCRIBE projects")
            columns = cursor.fetchall()
            column_names = [col['Field'] for col in columns]
            print(f"📋 Available columns in projectsdb.projects: {column_names}")
            
            # Query for active projects
            cursor.execute("SELECT * FROM projects WHERE status = 'active'")
            active_projects = cursor.fetchall()
            
            # Debug: print first project to see structure
            if active_projects:
                print(f"🔍 Sample project data: {active_projects[0]}")
            
            cursor.close()
            conn.close()
            
            # Cache the results
            self._active_databases_cache = active_projects
            return active_projects
        except Error as e:
            print(f"❌ Error getting active databases: {e}")
            return []
    
    def get_databases(self) -> List[str]:
        """Get all databases"""
        conn = self.connect()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            databases = [db[0] for db in cursor.fetchall() if db[0] not in self.system_databases]
            cursor.close()
            conn.close()
            return databases
        except Error as e:
            print(f"❌ Error: {e}")
            return []
    
    def get_tables(self, database: str) -> List[str]:
        """Get tables in database"""
        conn = self.connect(database)
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            cursor.close()
            conn.close()
            return tables
        except Error as e:
            print(f"❌ Error: {e}")
            return []
    
    def get_table_data(self, database: str, table: str, limit: int = 100, 
                       date_filter: Optional[str] = None) -> Optional[List[Dict]]:
        """Get table data with optional date filtering"""
        conn = self.connect(database)
        if not conn:
            return None
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Build query with optional date filter
            query = f"SELECT * FROM `{table}`"
            if date_filter:
                query += f" WHERE {date_filter}"
            query += f" LIMIT {limit}"
            
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Error as e:
            print(f"❌ Error: {e}")
            return None
    
    def execute_custom_query(self, database: str, query: str, params: Optional[Tuple] = None) -> Optional[List[Dict]]:
        """Execute custom SELECT query"""
        # Safety check - only allow SELECT queries
        query_upper = query.strip().upper()
        if not query_upper.startswith('SELECT'):
            print("❌ Only SELECT queries allowed")
            return None
        
        conn = self.connect(database)
        if not conn:
            return None
        
        try:
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
            print(f"❌ Query error: {e}")
            return None
    
    def smart_search(self, database: str, search_term: str, limit: int = 50) -> Dict:
        """Search across all tables"""
        tables = self.get_tables(database)
        results = {}
        
        for table in tables:
            conn = self.connect(database)
            if not conn:
                continue
            
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(f"DESCRIBE `{table}`")
                columns = cursor.fetchall()
                
                # Get searchable text columns
                searchable = [col['Field'] for col in columns 
                            if any(t in col['Type'].lower() for t in ['char', 'text', 'varchar'])]
                
                if searchable:
                    where_clauses = [f"`{col}` LIKE %s" for col in searchable]
                    query = f"SELECT * FROM `{table}` WHERE {' OR '.join(where_clauses)} LIMIT {limit}"
                    params = tuple([f"%{search_term}%"] * len(searchable))
                    
                    cursor.execute(query, params)
                    data = cursor.fetchall()
                    
                    if data:
                        results[table] = {
                            "matches": len(data),
                            "data": data
                        }
                
                cursor.close()
                conn.close()
            except:
                continue
        
        return {
            "database": database,
            "search_term": search_term,
            "tables_searched": len(tables),
            "tables_with_matches": len(results),
            "results": results
        }
    
    def search_across_active_databases(self, search_term: str, limit: int = 20) -> Dict:
        """Search across all active databases"""
        active_dbs = self.get_active_databases()
        all_results = {}
        
        if not active_dbs:
            return {
                "search_term": search_term,
                "databases_searched": 0,
                "databases_with_matches": 0,
                "results": {},
                "error": "No active databases found"
            }
        
        # Use 'schemadb' as the primary column
        possible_db_columns = ['schemadb', 'database_name', 'db_name', 'name', 'project_name', 
                               'project', 'db', 'database', 'project_db']
        
        for project in active_dbs:
            # Try to find database name in any of the possible columns
            db_name = None
            for col in possible_db_columns:
                if col in project and project[col]:
                    db_name = project[col]
                    break
            
            # If still no database name found, use the first string value
            if not db_name:
                for key, value in project.items():
                    if isinstance(value, str) and key.lower() != 'status' and len(value) > 2:
                        db_name = value
                        break
            
            if not db_name:
                continue
            
            try:
                result = self.smart_search(db_name, search_term, limit)
                if result.get('tables_with_matches', 0) > 0:
                    all_results[db_name] = result
            except:
                continue
        
        return {
            "search_term": search_term,
            "databases_searched": len(active_dbs),
            "databases_with_matches": len(all_results),
            "results": all_results
        }

_db_handler = None

def get_db_handler():
    global _db_handler
    if _db_handler is None:
        from config import DB_HOST, DB_USER, DB_PASSWORD
        _db_handler = DatabaseHandler(DB_HOST, DB_USER, DB_PASSWORD)
    return _db_handler

def list_databases() -> str:
    """List all databases"""
    databases = get_db_handler().get_databases()
    return "\n".join([f"  • {db}" for db in databases]) if databases else "No databases found"

def list_active_databases() -> str:
    """List active databases from projectsdb.projects"""
    handler = get_db_handler()
    active_dbs = handler.get_active_databases()
    
    if not active_dbs:
        return "No active databases found in projectsdb.projects"
    
    # Now we know the column is 'schemadb'
    possible_db_columns = ['schemadb', 'database_name', 'db_name', 'name', 'project_name', 
                           'project', 'db', 'database', 'project_db']
    
    output = f"**Active Databases ({len(active_dbs)}):**\n\n"
    
    for idx, project in enumerate(active_dbs, 1):
        # Try to find database name
        db_name = None
        for col in possible_db_columns:
            if col in project and project[col]:
                db_name = project[col]
                break
        
        if db_name:
            status = project.get('status', 'N/A')
            output += f"{idx}. **{db_name}** (Status: {status})\n"
        else:
            # Fallback: show all fields
            output += f"{idx}. **Project Entry:**\n"
            for key, value in project.items():
                if value and str(value).strip():
                    output += f"   - {key}: {value}\n"
    
    output += f"\n\n💡 **Next steps:** Type \"show tables in [database]\" to explore any database\n"
    output += f"Example: \"show tables in ledtech\""
    
    return output

def analyze_database(database: str) -> str:
    """Analyze database with full details"""
    handler = get_db_handler()
    tables = handler.get_tables(database)
    
    if not tables:
        return f"❌ Could not access database: **{database}**\n\nMake sure the database name is correct and you have access."
    
    output = f"# 📊 Database: **{database}**\n\n"
    output += f"**Total Tables:** {len(tables)}\n\n"
    output += "---\n\n"
    
    output += "## 📋 All Tables:\n\n"
    
    for idx, table in enumerate(tables, 1):
        conn = handler.connect(database)
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                
                # Get column info
                cursor.execute(f"DESCRIBE `{table}`")
                columns = cursor.fetchall()
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) as count FROM `{table}`")
                row_count = cursor.fetchone()['count']
                
                output += f"### {idx}. `{table}`\n"
                output += f"   - **Columns:** {len(columns)}\n"
                output += f"   - **Rows:** {row_count:,}\n"
                
                # Show column details
                output += f"   - **Schema:**\n"
                for col in columns[:5]:  # Show first 5 columns
                    col_type = col['Type']
                    col_null = "NULL" if col['Null'] == 'YES' else "NOT NULL"
                    col_key = f" [{col['Key']}]" if col['Key'] else ""
                    output += f"      - `{col['Field']}` - {col_type} {col_null}{col_key}\n"
                
                if len(columns) > 5:
                    output += f"      - ... and {len(columns) - 5} more columns\n"
                
                output += "\n"
                
                cursor.close()
                conn.close()
            except Exception as e:
                output += f"### {idx}. `{table}`\n"
                output += f"   - ⚠️ Could not access table details\n\n"
    
    output += "\n---\n\n"
    output += "## 💡 Next Steps:\n\n"
    output += f"- **View data:** \"show all data in {tables[0] if tables else 'table_name'}\"\n"
    output += f"- **Search:** \"search for [term] in {database}\"\n"
    output += f"- **Custom query:** \"query: SELECT * FROM {database}.{tables[0] if tables else 'table_name'} LIMIT 10\"\n"
    output += f"- **Table details:** \"show table {tables[0] if tables else 'table_name'} in {database}\"\n"
    
    return output

def smart_search(database: str, search_term: str) -> str:
    """Smart search"""
    results = get_db_handler().smart_search(database, search_term)
    
    output = f"🔍 **Search: '{search_term}' in {database}**\n\n"
    output += f"Tables searched: {results.get('tables_searched', 0)}\n"
    output += f"Matches: {results.get('tables_with_matches', 0)}\n\n"
    
    for table, data in results.get('results', {}).items():
        output += f"### 📋 {table} ({data['matches']} matches)\n"
        output += f"```json\n{json.dumps(data['data'][:2], indent=2, default=str)}\n```\n\n"
    
    return output

def search_all_active_databases(search_term: str) -> str:
    """Search across all active databases"""
    results = get_db_handler().search_across_active_databases(search_term)
    
    if 'error' in results:
        return f"❌ {results['error']}"
    
    output = f"🔍 **Global Search: '{search_term}' across active databases**\n\n"
    output += f"Databases searched: {results.get('databases_searched', 0)}\n"
    output += f"Databases with matches: {results.get('databases_with_matches', 0)}\n\n"
    
    for db_name, db_results in results.get('results', {}).items():
        output += f"## 💾 Database: {db_name}\n"
        output += f"Tables with matches: {db_results.get('tables_with_matches', 0)}\n\n"
        
        for table, data in db_results.get('results', {}).items():
            output += f"### 📋 {table} ({data['matches']} matches)\n"
            output += f"```json\n{json.dumps(data['data'][:1], indent=2, default=str)}\n```\n\n"
    
    return output

def execute_query(database: str, query: str) -> str:
    """Execute custom query"""
    handler = get_db_handler()
    results = handler.execute_custom_query(database, query)
    
    if results is None:
        return "❌ Query failed or not allowed"
    
    output = f"**Query Results ({len(results)} rows)**\n\n"
    output += f"```json\n{json.dumps(results[:5], indent=2, default=str)}\n```"
    
    return output

def show_table_details(database: str, table: str) -> str:
    """Show detailed table information"""
    handler = get_db_handler()
    conn = handler.connect(database)
    
    if not conn:
        return f"❌ Could not connect to database: {database}"
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get table structure
        cursor.execute(f"DESCRIBE `{table}`")
        columns = cursor.fetchall()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) as count FROM `{table}`")
        row_count = cursor.fetchone()['count']
        
        # Get sample data
        cursor.execute(f"SELECT * FROM `{table}` LIMIT 5")
        sample_data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        output = f"# 📋 Table: **{database}.{table}**\n\n"
        output += f"**Total Rows:** {row_count:,}\n\n"
        output += "---\n\n"
        
        output += "## 🏗️ Schema:\n\n"
        output += "| Column | Type | Null | Key | Default |\n"
        output += "|--------|------|------|-----|--------|\n"
        
        for col in columns:
            col_name = col['Field']
            col_type = col['Type']
            col_null = "✓" if col['Null'] == 'YES' else "✗"
            col_key = col['Key'] or '-'
            col_default = str(col['Default']) if col['Default'] else '-'
            output += f"| `{col_name}` | {col_type} | {col_null} | {col_key} | {col_default} |\n"
        
        output += "\n## 📊 Sample Data:\n\n"
        output += f"```json\n{json.dumps(sample_data, indent=2, default=str)}\n```\n\n"
        
        output += "---\n\n"
        output += "## 💡 Next Steps:\n\n"
        output += f"- **View all:** \"show all data in {table}\"\n"
        output += f"- **Today's data:** \"show {table} data from today\"\n"
        output += f"- **Yesterday's data:** \"show {table} data from yesterday\"\n"
        output += f"- **Last 7 days:** \"show {table} data from last 7 days\"\n"
        output += f"- **Search:** \"search for [term] in {database}\"\n"
        output += f"- **Custom query:** \"query: SELECT * FROM {database}.{table} WHERE ...\"\n"
        
        return output
        
    except Error as e:
        return f"❌ Error accessing table: {str(e)}"

def show_filtered_data(database: str, table: str, date_info: Dict, limit: int = 100) -> str:
    """Show table data filtered by date"""
    handler = get_db_handler()
    conn = handler.connect(database)
    
    if not conn:
        return f"❌ Could not connect to database: {database}"
    
    try:
        from date_filter import generate_date_sql, find_date_column
        
        cursor = conn.cursor(dictionary=True)
        
        # Get table structure to find date column
        cursor.execute(f"DESCRIBE `{table}`")
        columns = cursor.fetchall()
        
        # Detect date column
        date_column = find_date_column(columns)
        
        if not date_column:
            cursor.close()
            conn.close()
            return f"❌ Could not find a date/timestamp column in table **{table}**.\n\nAvailable columns: {', '.join([c['Field'] for c in columns])}"
        
        # Generate SQL filter
        sql_filter = generate_date_sql(date_info, date_column)
        
        # Build and execute query
        query = f"SELECT * FROM `{table}` WHERE {sql_filter} ORDER BY `{date_column}` DESC LIMIT {limit}"
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Get count
        count_query = f"SELECT COUNT(*) as count FROM `{table}` WHERE {sql_filter}"
        cursor.execute(count_query)
        total_count = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        output = f"# 📅 {table} - Data from {date_info['description']}\n\n"
        output += f"**Database:** {database}\n"
        output += f"**Date Column:** `{date_column}`\n"
        output += f"**Total Matching Rows:** {total_count:,}\n"
        output += f"**Showing:** {min(len(results), limit)} rows\n\n"
        
        if not results:
            output += "❌ **No data found for this date range.**\n\n"
            output += "💡 Try:\n"
            output += f"- \"show {table} data from yesterday\"\n"
            output += f"- \"show {table} data from last 7 days\"\n"
            output += f"- \"show all data in {table}\" (no filter)\n"
        else:
            output += "## 📊 Data:\n\n"
            output += f"```json\n{json.dumps(results[:10], indent=2, default=str)}\n```\n\n"
            
            if len(results) > 10:
                output += f"*Showing first 10 of {len(results)} results*\n\n"
            
            output += "---\n\n"
            output += "## 💡 Try Other Filters:\n\n"
            output += f"- \"show {table} from yesterday\"\n"
            output += f"- \"show {table} from last 7 days\"\n"
            output += f"- \"show {table} from 2024-01-01 to 2024-01-31\"\n"
        
        return output
        
    except Error as e:
        return f"❌ Query error: {str(e)}"