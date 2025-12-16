# query_router.py - Enhanced Query Router with Active DB Support
import re

def classify_query_type(message):
    """Classify query type"""
    msg = message.lower()
    
    # Active databases query
    if 'active database' in msg or 'active db' in msg:
        return 'active_databases'
    
    # Global search
    if 'search all' in msg or 'search everywhere' in msg or 'global search' in msg:
        return 'global_search'
    
    # Custom SQL query
    if 'query' in msg and ('select' in msg or 'SELECT' in message):
        return 'custom_query'
    
    # List databases
    if any(p in msg for p in ['list database', 'show database', 'what databases', 'all databases']):
        return 'database_listing'
    
    # Query specific database
    specific_patterns = ['show all in', 'list all in', 'show tables', 'list tables']
    if any(p in msg for p in specific_patterns):
        return 'database_query'
    
    # General database operations
    db_keywords = ['analyze', 'structure', 'schema', 'search', 'query', 'table', 'data']
    if any(kw in msg for kw in db_keywords):
        return 'database'
    
    return 'general'

def extract_database_name(message):
    """Extract database name from message"""
    msg = message.lower()
    
    # Pattern: "in [database]"
    patterns = [
        r'\bin\s+(\w+)',
        r'database\s+(\w+)',
        r'from\s+(\w+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, msg)
        if match:
            candidate = match.group(1)
            if candidate not in ['the', 'a', 'an', 'all', 'any', 'active', 'every']:
                # Return with original case
                start = msg.find(candidate)
                if start != -1:
                    return message[start:start + len(candidate)]
    
    return None