# database_routes.py - Database Query Handler
from typing import Dict, Optional
from db_handler import (
    get_db_handler,
    list_databases,
    list_active_databases,
    analyze_database,
    smart_search,
    search_all_active_databases,
    execute_query,
    show_table_details,
    show_filtered_data
)
from query_processor import (
    extract_table_name,
    extract_search_term,
    extract_sql_query,
    extract_table_from_show_all,
    extract_table_for_date_filter
)
from date_filter import parse_date_from_message
from ai_handler import ask_deepseek, ask_general_question

def handle_database_query(message: str, database: str, conversation_context: list, 
                          relevant_facts: list) -> Optional[Dict[str, str]]:
    """
    Handle database-related queries
    Returns: dict with 'answer' and 'response_type', or None if not a database query
    """
    msg_lower = message.lower()
    
    # Check for date filtering
    date_info = parse_date_from_message(message)
    
    # Date-filtered data query
    if date_info:
        db_name, table_name = extract_table_for_date_filter(message)
        if table_name:
            if db_name:
                database = db_name
            
            return {
                'answer': show_filtered_data(database, table_name, date_info, limit=100),
                'response_type': 'date_filtered'
            }
    
    # Table details query
    if any(phrase in msg_lower for phrase in ['show table', 'table details', 'table info', 'about table']):
        table_name = extract_table_name(message, database)
        if table_name:
            return {
                'answer': show_table_details(database, table_name),
                'response_type': 'table_details'
            }
        else:
            return {
                'answer': "Please specify the table name. Example: \"show table activity in operators\"",
                'response_type': 'error'
            }
    
    # Show all data query
    if 'show all data' in msg_lower or 'show all in' in msg_lower or 'all data in' in msg_lower:
        table_name = extract_table_from_show_all(message)
        if table_name:
            query = f"SELECT * FROM {database}.{table_name} LIMIT 50"
            return {
                'answer': f"## 📊 All Data from **{table_name}**\n\n{execute_query(database, query)}",
                'response_type': 'custom_query'
            }
        else:
            return {
                'answer': "Please specify the table name. Example: \"show all data in activity\"",
                'response_type': 'error'
            }
    
    # Active databases query
    if 'active database' in msg_lower or 'active db' in msg_lower or 'show active' in msg_lower:
        return {
            'answer': list_active_databases(),
            'response_type': 'database'
        }
    
    # Global search query
    if 'search all' in msg_lower or 'search everywhere' in msg_lower or 'global search' in msg_lower:
        search_term = extract_search_term(message)
        if search_term:
            return {
                'answer': search_all_active_databases(search_term),
                'response_type': 'global_search'
            }
        else:
            return {
                'answer': "Please specify what to search for.",
                'response_type': 'error'
            }
    
    # Custom SQL query
    if 'query' in msg_lower and ('select' in msg_lower or 'SELECT' in message):
        sql_query = extract_sql_query(message)
        if sql_query:
            return {
                'answer': execute_query(database, sql_query),
                'response_type': 'custom_query'
            }
        else:
            return {
                'answer': "Could not find SELECT query in your message.",
                'response_type': 'error'
            }
    
    # Database listing query
    if any(phrase in msg_lower for phrase in ['list database', 'show database', 'what databases', 'all databases']):
        return {
            'answer': f"**All Databases:**\n{list_databases()}\n\n💡 Tip: Ask for 'active databases' to see only active ones.",
            'response_type': 'database'
        }
    
    # Show tables query
    if any(phrase in msg_lower for phrase in ['show tables', 'list tables', 'tables in', 'what tables']):
        handler = get_db_handler()
        tables = handler.get_tables(database)
        
        if not tables:
            return {
                'answer': f"❌ Could not access database '{database}'",
                'response_type': 'error'
            }
        else:
            return {
                'answer': analyze_database(database),
                'response_type': 'database'
            }
    
    # Search queries
    if 'search' in msg_lower:
        search_term = extract_search_term(message)
        if search_term:
            result = smart_search(database, search_term)
            return {
                'answer': ask_deepseek(message, [result], conversation_context, relevant_facts),
                'response_type': 'search'
            }
        else:
            return {
                'answer': "Please specify what to search for.",
                'response_type': 'error'
            }
    
    # Database analysis
    if any(kw in msg_lower for kw in ['analyze', 'structure', 'schema']):
        result = analyze_database(database)
        return {
            'answer': ask_deepseek(message, [result], conversation_context, relevant_facts),
            'response_type': 'database'
        }
    
    return None