# db_introspector.py
# Advanced database introspection for automatic schema detection and intelligent querying

import mysql.connector
from mysql.connector import Error
from typing import Dict, List, Optional, Any
import json
from collections import defaultdict


class DatabaseIntrospector:
    """
    Intelligent database introspection system that automatically detects:
    - Primary keys and foreign keys
    - Field names, types, and constraints
    - Common field patterns (id, date, name, etc.)
    - Table relationships
    - Data patterns and statistics
    """
    
    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password
        self.connection = None
        self.schema_cache = {}
        
    def connect(self, database: Optional[str] = None) -> bool:
        """Connect to MySQL server or specific database"""
        try:
            if database:
                self.connection = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=database
                )
            else:
                self.connection = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password
                )
            return self.connection.is_connected()
        except Error as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def get_complete_schema(self, database: str) -> Dict[str, Any]:
        """
        Get complete schema information for a database including:
        - All tables
        - All columns with types and constraints
        - Primary keys
        - Foreign keys
        - Indexes
        - Sample data
        """
        if database in self.schema_cache:
            return self.schema_cache[database]
        
        schema = {
            'database': database,
            'tables': {},
            'relationships': []
        }
        
        if not self.connect(database):
            return schema
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Get all tables
            cursor.execute("SHOW TABLES")
            tables = [list(row.values())[0] for row in cursor.fetchall()]
            
            for table in tables:
                schema['tables'][table] = self._analyze_table(database, table, cursor)
            
            # Detect relationships
            schema['relationships'] = self._detect_relationships(schema['tables'])
            
            cursor.close()
            self.disconnect()
            
            self.schema_cache[database] = schema
            return schema
            
        except Error as e:
            print(f"❌ Schema analysis error: {e}")
            self.disconnect()
            return schema
    
    def _analyze_table(self, database: str, table: str, cursor) -> Dict[str, Any]:
        """Deep analysis of a single table"""
        table_info = {
            'columns': [],
            'primary_keys': [],
            'foreign_keys': [],
            'indexes': [],
            'key_fields': {},
            'sample_data': [],
            'row_count': 0,
            'column_stats': {}
        }
        
        # Get column information
        cursor.execute(f"DESCRIBE {table}")
        columns = cursor.fetchall()
        
        for col in columns:
            column_info = {
                'name': col['Field'],
                'type': col['Type'],
                'nullable': col['Null'] == 'YES',
                'key': col['Key'],
                'default': col['Default'],
                'extra': col['Extra']
            }
            
            table_info['columns'].append(column_info)
            
            # Identify primary keys
            if col['Key'] == 'PRI':
                table_info['primary_keys'].append(col['Field'])
            
            # Classify field types for intelligent querying
            field_name = col['Field'].lower()
            field_type = col['Type'].lower()
            
            # Detect key field patterns
            if any(pattern in field_name for pattern in ['id', '_id']):
                table_info['key_fields']['id_field'] = col['Field']
            
            if any(pattern in field_name for pattern in ['name', 'title', 'description']):
                if 'name_fields' not in table_info['key_fields']:
                    table_info['key_fields']['name_fields'] = []
                table_info['key_fields']['name_fields'].append(col['Field'])
            
            if any(pattern in field_name for pattern in ['date', 'time', 'created', 'updated']):
                if 'date_fields' not in table_info['key_fields']:
                    table_info['key_fields']['date_fields'] = []
                table_info['key_fields']['date_fields'].append(col['Field'])
            
            if any(pattern in field_name for pattern in ['email', 'mail']):
                table_info['key_fields']['email_field'] = col['Field']
            
            if any(pattern in field_name for pattern in ['operator', 'user', 'employee', 'worker']):
                table_info['key_fields']['operator_field'] = col['Field']
        
        # Get foreign key information
        cursor.execute(f"""
            SELECT 
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = '{database}'
                AND TABLE_NAME = '{table}'
                AND REFERENCED_TABLE_NAME IS NOT NULL
        """)
        
        for fk in cursor.fetchall():
            table_info['foreign_keys'].append({
                'column': fk['COLUMN_NAME'],
                'references_table': fk['REFERENCED_TABLE_NAME'],
                'references_column': fk['REFERENCED_COLUMN_NAME']
            })
        
        # Get index information
        cursor.execute(f"SHOW INDEX FROM {table}")
        for idx in cursor.fetchall():
            table_info['indexes'].append({
                'name': idx['Key_name'],
                'column': idx['Column_name'],
                'unique': not idx['Non_unique']
            })
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        table_info['row_count'] = cursor.fetchone()['count']
        
        # Get sample data (first 3 rows)
        cursor.execute(f"SELECT * FROM {table} LIMIT 3")
        table_info['sample_data'] = cursor.fetchall()
        
        # Get column statistics for text fields
        for col in table_info['columns']:
            if 'char' in col['type'].lower() or 'text' in col['type'].lower():
                try:
                    cursor.execute(f"""
                        SELECT 
                            COUNT(DISTINCT {col['name']}) as unique_count,
                            COUNT({col['name']}) as non_null_count
                        FROM {table}
                    """)
                    stats = cursor.fetchone()
                    table_info['column_stats'][col['name']] = stats
                except:
                    pass
        
        return table_info
    
    def _detect_relationships(self, tables: Dict[str, Any]) -> List[Dict[str, str]]:
        """Detect potential relationships between tables"""
        relationships = []
        
        for table_name, table_info in tables.items():
            # Explicit foreign keys
            for fk in table_info.get('foreign_keys', []):
                relationships.append({
                    'from_table': table_name,
                    'from_column': fk['column'],
                    'to_table': fk['references_table'],
                    'to_column': fk['references_column'],
                    'type': 'foreign_key'
                })
            
            # Inferred relationships (columns ending in _id)
            for col in table_info.get('columns', []):
                col_name = col['name'].lower()
                if col_name.endswith('_id') and col_name != 'id':
                    # Try to find matching table
                    potential_table = col_name[:-3]  # Remove '_id'
                    for other_table in tables.keys():
                        if potential_table in other_table.lower():
                            relationships.append({
                                'from_table': table_name,
                                'from_column': col['name'],
                                'to_table': other_table,
                                'to_column': 'id',
                                'type': 'inferred'
                            })
        
        return relationships
    
    def smart_search(self, database: str, search_term: str, limit: int = 50) -> Dict[str, Any]:
        """
        Intelligent search that automatically finds the best fields to search
        """
        schema = self.get_complete_schema(database)
        results = {}
        
        if not self.connect(database):
            return results
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            for table_name, table_info in schema['tables'].items():
                # Identify searchable columns
                searchable_columns = []
                
                for col in table_info['columns']:
                    col_type = col['type'].lower()
                    # Search in text columns
                    if any(t in col_type for t in ['char', 'text', 'varchar']):
                        searchable_columns.append(col['name'])
                
                if not searchable_columns:
                    continue
                
                # Build smart search query
                where_clauses = [f"`{col}` LIKE %s" for col in searchable_columns]
                query = f"""
                    SELECT * FROM `{table_name}` 
                    WHERE {' OR '.join(where_clauses)} 
                    LIMIT {limit}
                """
                
                params = [f"%{search_term}%"] * len(searchable_columns)
                
                try:
                    cursor.execute(query, params)
                    data = cursor.fetchall()
                    
                    if data:
                        results[table_name] = {
                            'matches': len(data),
                            'searched_columns': searchable_columns,
                            'data': data
                        }
                except Error as e:
                    print(f"⚠️ Search error in {table_name}: {e}")
                    continue
            
            cursor.close()
            self.disconnect()
            
        except Error as e:
            print(f"❌ Smart search error: {e}")
            self.disconnect()
        
        return results
    
    def get_field_suggestions(self, database: str, context: str = None) -> Dict[str, List[str]]:
        """
        Get intelligent field suggestions based on context
        """
        schema = self.get_complete_schema(database)
        suggestions = {
            'id_fields': [],
            'name_fields': [],
            'date_fields': [],
            'numeric_fields': [],
            'text_fields': [],
            'operator_fields': []
        }
        
        for table_name, table_info in schema['tables'].items():
            for col in table_info['columns']:
                col_name = col['name']
                col_type = col['type'].lower()
                
                # Categorize fields
                if any(p in col_name.lower() for p in ['id', '_id']):
                    suggestions['id_fields'].append(f"{table_name}.{col_name}")
                
                if any(p in col_name.lower() for p in ['name', 'title', 'description']):
                    suggestions['name_fields'].append(f"{table_name}.{col_name}")
                
                if any(p in col_name.lower() for p in ['date', 'time', 'created', 'updated']):
                    suggestions['date_fields'].append(f"{table_name}.{col_name}")
                
                if any(p in col_name.lower() for p in ['operator', 'user', 'employee', 'worker']):
                    suggestions['operator_fields'].append(f"{table_name}.{col_name}")
                
                if any(t in col_type for t in ['int', 'decimal', 'float', 'double']):
                    suggestions['numeric_fields'].append(f"{table_name}.{col_name}")
                
                if any(t in col_type for t in ['char', 'text', 'varchar']):
                    suggestions['text_fields'].append(f"{table_name}.{col_name}")
        
        return suggestions
    
    def format_schema_summary(self, database: str) -> str:
        """Format schema into readable summary for AI"""
        schema = self.get_complete_schema(database)
        
        summary = f"📊 **Database: {database}**\n\n"
        summary += f"**Total Tables: {len(schema['tables'])}**\n\n"
        
        for table_name, table_info in schema['tables'].items():
            summary += f"### 📋 Table: `{table_name}`\n"
            summary += f"- **Rows:** {table_info['row_count']:,}\n"
            summary += f"- **Columns:** {len(table_info['columns'])}\n"
            
            if table_info['primary_keys']:
                summary += f"- **Primary Key:** {', '.join(table_info['primary_keys'])}\n"
            
            if table_info['key_fields']:
                summary += f"- **Key Fields:**\n"
                for field_type, fields in table_info['key_fields'].items():
                    if isinstance(fields, list):
                        summary += f"  - {field_type}: {', '.join(fields)}\n"
                    else:
                        summary += f"  - {field_type}: {fields}\n"
            
            summary += "\n**Columns:**\n"
            for col in table_info['columns'][:10]:  # Limit to first 10
                summary += f"  - `{col['name']}` ({col['type']})"
                if col['key'] == 'PRI':
                    summary += " 🔑"
                if not col['nullable']:
                    summary += " ⚠️ NOT NULL"
                summary += "\n"
            
            if len(table_info['columns']) > 10:
                summary += f"  ... and {len(table_info['columns']) - 10} more columns\n"
            
            summary += "\n"
        
        if schema['relationships']:
            summary += "\n### 🔗 Relationships:\n"
            for rel in schema['relationships'][:5]:
                summary += f"- `{rel['from_table']}.{rel['from_column']}` → `{rel['to_table']}.{rel['to_column']}` ({rel['type']})\n"
        
        return summary
    
    def build_smart_query(self, database: str, table: str, 
                         filters: Dict[str, Any] = None, 
                         limit: int = 100) -> str:
        """Build optimized query based on table structure"""
        schema = self.get_complete_schema(database)
        
        if table not in schema['tables']:
            return None
        
        table_info = schema['tables'][table]
        
        # Start with all columns
        columns = [col['name'] for col in table_info['columns']]
        query = f"SELECT {', '.join(columns)} FROM `{table}`"
        
        # Add intelligent WHERE clause
        if filters:
            where_parts = []
            for field, value in filters.items():
                # Find column type
                col_info = next((c for c in table_info['columns'] if c['name'] == field), None)
                if col_info:
                    col_type = col_info['type'].lower()
                    if 'char' in col_type or 'text' in col_type:
                        where_parts.append(f"`{field}` LIKE '%{value}%'")
                    else:
                        where_parts.append(f"`{field}` = '{value}'")
            
            if where_parts:
                query += f" WHERE {' AND '.join(where_parts)}"
        
        # Add intelligent ORDER BY
        if table_info['key_fields'].get('date_fields'):
            date_field = table_info['key_fields']['date_fields'][0]
            query += f" ORDER BY `{date_field}` DESC"
        
        query += f" LIMIT {limit}"
        
        return query


def get_introspector(host: str, user: str, password: str) -> DatabaseIntrospector:
    """Factory function to create introspector instance"""
    return DatabaseIntrospector(host, user, password)