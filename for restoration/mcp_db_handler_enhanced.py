# mcp_db_handler_enhanced.py
# Enhanced MCP handler with intelligent database introspection

import json
from typing import Optional, Dict, Any, List
from db_introspector import DatabaseIntrospector
from config import DB_HOST, DB_USER, DB_PASSWORD


class EnhancedMCPHandler:
    """Enhanced MCP handler with auto-detection capabilities"""
    
    def __init__(self):
        self.introspector = DatabaseIntrospector(DB_HOST, DB_USER, DB_PASSWORD)
    
    def list_databases_with_details(self) -> Dict[str, Any]:
        """List all databases with metadata"""
        if not self.introspector.connect():
            return {'error': 'Could not connect to database server'}
        
        try:
            cursor = self.introspector.connection.cursor()
            cursor.execute("SHOW DATABASES")
            databases = [db[0] for db in cursor.fetchall()]
            
            # Filter system databases
            system_dbs = ['information_schema', 'mysql', 'performance_schema', 'sys']
            user_databases = [db for db in databases if db not in system_dbs]
            
            result = {
                'databases': user_databases,
                'count': len(user_databases),
                'details': {}
            }
            
            # Get quick stats for each database
            for db in user_databases[:5]:  # Limit to first 5 for performance
                try:
                    cursor.execute(f"USE `{db}`")
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    result['details'][db] = {
                        'table_count': len(tables),
                        'tables': [t[0] for t in tables]
                    }
                except:
                    result['details'][db] = {'error': 'Could not access'}
            
            cursor.close()
            self.introspector.disconnect()
            
            return result
            
        except Exception as e:
            self.introspector.disconnect()
            return {'error': str(e)}
    
    def analyze_database_schema(self, database: str) -> Dict[str, Any]:
        """Get complete schema analysis"""
        schema = self.introspector.get_complete_schema(database)
        return schema
    
    def get_table_intelligence(self, database: str, table: str) -> Dict[str, Any]:
        """Get intelligent analysis of a specific table"""
        schema = self.introspector.get_complete_schema(database)
        
        if table not in schema['tables']:
            return {'error': f'Table {table} not found in {database}'}
        
        table_info = schema['tables'][table]
        
        return {
            'database': database,
            'table': table,
            'analysis': {
                'row_count': table_info['row_count'],
                'columns': len(table_info['columns']),
                'primary_keys': table_info['primary_keys'],
                'foreign_keys': table_info['foreign_keys'],
                'key_fields': table_info['key_fields'],
                'searchable_fields': [
                    col['name'] for col in table_info['columns']
                    if any(t in col['type'].lower() for t in ['char', 'text', 'varchar'])
                ],
                'date_fields': table_info['key_fields'].get('date_fields', []),
                'id_fields': [col['name'] for col in table_info['columns'] 
                             if 'id' in col['name'].lower()],
                'sample_data': table_info['sample_data'][:2]  # Show 2 samples
            },
            'column_details': table_info['columns']
        }
    
    def smart_search(self, database: str, search_term: str, limit: int = 50) -> Dict[str, Any]:
        """Intelligent search across database"""
        results = self.introspector.smart_search(database, search_term, limit)
        
        summary = {
            'database': database,
            'search_term': search_term,
            'tables_searched': len(results),
            'total_matches': sum(r['matches'] for r in results.values()),
            'results': results
        }
        
        return summary
    
    def suggest_queries(self, database: str, intent: str) -> List[str]:
        """Suggest queries based on user intent"""
        schema = self.introspector.get_complete_schema(database)
        suggestions = []
        
        intent_lower = intent.lower()
        
        # Operator queries
        if any(word in intent_lower for word in ['operator', 'worker', 'employee']):
            for table_name, table_info in schema['tables'].items():
                if table_info['key_fields'].get('operator_field'):
                    op_field = table_info['key_fields']['operator_field']
                    suggestions.append(f"SELECT * FROM `{table_name}` ORDER BY `{op_field}` LIMIT 50")
                    suggestions.append(f"SELECT DISTINCT `{op_field}` FROM `{table_name}`")
        
        # Date/time queries
        if any(word in intent_lower for word in ['today', 'recent', 'latest', 'current']):
            for table_name, table_info in schema['tables'].items():
                date_fields = table_info['key_fields'].get('date_fields', [])
                if date_fields:
                    date_field = date_fields[0]
                    suggestions.append(
                        f"SELECT * FROM `{table_name}` ORDER BY `{date_field}` DESC LIMIT 50"
                    )
        
        # Count/statistics queries
        if any(word in intent_lower for word in ['count', 'how many', 'total']):
            for table_name in list(schema['tables'].keys())[:5]:
                suggestions.append(f"SELECT COUNT(*) as total FROM `{table_name}`")
        
        return suggestions
    
    def auto_query(self, database: str, natural_language: str) -> Dict[str, Any]:
        """
        Attempt to automatically generate and execute query from natural language
        """
        schema = self.introspector.get_complete_schema(database)
        nl_lower = natural_language.lower()
        
        # Detect intent
        result = {
            'intent_detected': None,
            'query_generated': None,
            'results': None
        }
        
        # Find table mentioned
        target_table = None
        for table_name in schema['tables'].keys():
            if table_name.lower() in nl_lower:
                target_table = table_name
                break
        
        if not target_table:
            # Try to find most relevant table
            if any(word in nl_lower for word in ['operator', 'worker', 'employee']):
                for table_name, table_info in schema['tables'].items():
                    if 'operator' in table_name.lower() or table_info['key_fields'].get('operator_field'):
                        target_table = table_name
                        break
        
        if not target_table:
            target_table = list(schema['tables'].keys())[0]  # Use first table
        
        table_info = schema['tables'][target_table]
        
        # Build query based on intent
        if 'all' in nl_lower or 'show' in nl_lower or 'list' in nl_lower:
            result['intent_detected'] = 'list_all'
            result['query_generated'] = f"SELECT * FROM `{target_table}` LIMIT 100"
        
        elif 'count' in nl_lower or 'how many' in nl_lower:
            result['intent_detected'] = 'count'
            result['query_generated'] = f"SELECT COUNT(*) as total FROM `{target_table}`"
        
        elif 'recent' in nl_lower or 'latest' in nl_lower:
            date_fields = table_info['key_fields'].get('date_fields', [])
            if date_fields:
                result['intent_detected'] = 'recent_data'
                result['query_generated'] = f"SELECT * FROM `{target_table}` ORDER BY `{date_fields[0]}` DESC LIMIT 50"
        
        # Execute the generated query
        if result['query_generated']:
            try:
                if self.introspector.connect(database):
                    cursor = self.introspector.connection.cursor(dictionary=True)
                    cursor.execute(result['query_generated'])
                    result['results'] = cursor.fetchall()
                    cursor.close()
                    self.introspector.disconnect()
            except Exception as e:
                result['error'] = str(e)
        
        return result
    
    def get_field_map(self, database: str) -> Dict[str, Any]:
        """Get comprehensive field mapping for the entire database"""
        schema = self.introspector.get_complete_schema(database)
        
        field_map = {
            'database': database,
            'all_id_fields': [],
            'all_name_fields': [],
            'all_date_fields': [],
            'all_operator_fields': [],
            'all_numeric_fields': [],
            'tables_with_relationships': [],
            'searchable_tables': {}
        }
        
        for table_name, table_info in schema['tables'].items():
            # Collect all field types
            for col in table_info['columns']:
                col_full = f"{table_name}.{col['name']}"
                col_name_lower = col['name'].lower()
                col_type_lower = col['type'].lower()
                
                if 'id' in col_name_lower or col['key'] == 'PRI':
                    field_map['all_id_fields'].append(col_full)
                
                if any(p in col_name_lower for p in ['name', 'title', 'description']):
                    field_map['all_name_fields'].append(col_full)
                
                if any(p in col_name_lower for p in ['date', 'time', 'created', 'updated']):
                    field_map['all_date_fields'].append(col_full)
                
                if any(p in col_name_lower for p in ['operator', 'user', 'employee', 'worker']):
                    field_map['all_operator_fields'].append(col_full)
                
                if any(t in col_type_lower for t in ['int', 'decimal', 'float', 'double']):
                    field_map['all_numeric_fields'].append(col_full)
            
            # Identify searchable tables
            searchable_cols = [
                col['name'] for col in table_info['columns']
                if any(t in col['type'].lower() for t in ['char', 'text', 'varchar'])
            ]
            if searchable_cols:
                field_map['searchable_tables'][table_name] = searchable_cols
            
            # Tables with relationships
            if table_info['foreign_keys']:
                field_map['tables_with_relationships'].append(table_name)
        
        return field_map


# Global instance
_mcp_handler = None

def get_enhanced_handler() -> EnhancedMCPHandler:
    """Get singleton enhanced MCP handler"""
    global _mcp_handler
    if _mcp_handler is None:
        _mcp_handler = EnhancedMCPHandler()
    return _mcp_handler


# Convenience functions for Flask integration
def analyze_database(database: str) -> str:
    """Analyze database and return formatted summary"""
    handler = get_enhanced_handler()
    schema = handler.analyze_database_schema(database)
    return handler.introspector.format_schema_summary(database)


def smart_search_database(database: str, search_term: str) -> str:
    """Smart search with formatted results"""
    handler = get_enhanced_handler()
    results = handler.smart_search(database, search_term)
    
    output = f"🔍 **Search Results for '{search_term}' in {database}**\n\n"
    output += f"Found {results['total_matches']} matches across {results['tables_searched']} tables\n\n"
    
    for table, data in results['results'].items():
        output += f"### 📋 {table} ({data['matches']} matches)\n"
        output += f"Searched in: {', '.join(data['searched_columns'])}\n\n"
        
        for i, row in enumerate(data['data'][:3], 1):
            output += f"**Result {i}:**\n```json\n{json.dumps(row, indent=2, default=str)}\n```\n\n"
        
        if data['matches'] > 3:
            output += f"... and {data['matches'] - 3} more matches\n\n"
    
    return output


def get_table_details(database: str, table: str) -> str:
    """Get detailed table information"""
    handler = get_enhanced_handler()
    info = handler.get_table_intelligence(database, table)
    
    if 'error' in info:
        return f"❌ {info['error']}"
    
    analysis = info['analysis']
    
    output = f"📊 **Table: {database}.{table}**\n\n"
    output += f"**Statistics:**\n"
    output += f"- Total Rows: {analysis['row_count']:,}\n"
    output += f"- Total Columns: {analysis['columns']}\n\n"
    
    if analysis['primary_keys']:
        output += f"**Primary Keys:** {', '.join(analysis['primary_keys'])}\n\n"
    
    if analysis['key_fields']:
        output += f"**Key Fields Detected:**\n"
        for field_type, fields in analysis['key_fields'].items():
            if isinstance(fields, list):
                output += f"- {field_type}: {', '.join(fields)}\n"
            else:
                output += f"- {field_type}: {fields}\n"
        output += "\n"
    
    if analysis['searchable_fields']:
        output += f"**Searchable Fields:** {', '.join(analysis['searchable_fields'][:5])}\n\n"
    
    if analysis['sample_data']:
        output += f"**Sample Data:**\n```json\n{json.dumps(analysis['sample_data'], indent=2, default=str)}\n```\n"
    
    return output


def auto_query_database(database: str, natural_language: str) -> str:
    """Auto-generate and execute query from natural language"""
    handler = get_enhanced_handler()
    result = handler.auto_query(database, natural_language)
    
    output = f"🤖 **Auto-Query Results**\n\n"
    
    if result['intent_detected']:
        output += f"**Intent Detected:** {result['intent_detected']}\n"
    
    if result['query_generated']:
        output += f"**Query Generated:**\n```sql\n{result['query_generated']}\n```\n\n"
    
    if result.get('results'):
        output += f"**Results:** {len(result['results'])} rows\n\n"
        output += f"```json\n{json.dumps(result['results'][:5], indent=2, default=str)}\n```\n"
        
        if len(result['results']) > 5:
            output += f"\n... and {len(result['results']) - 5} more rows\n"
    
    if result.get('error'):
        output += f"❌ **Error:** {result['error']}\n"
    
    return output