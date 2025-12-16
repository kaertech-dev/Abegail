# query_router_enhanced.py
# Enhanced query routing with intelligent database introspection
from config import COMPANY_KEYWORDS, DATABASE_KEYWORDS
from typing import Dict, Optional, Tuple

def needs_company_data(message: str) -> bool:
    """Check if message is asking about production/operator data from API"""
    msg = message.lower()
    if any(keyword in msg for keyword in DATABASE_KEYWORDS.keys()):
        return False  # Prioritize database keywords
    return any(keyword in msg for keyword in COMPANY_KEYWORDS)

def needs_database_introspection(message: str) -> bool:
    """Check if message requires database schema introspection"""
    msg = message.lower()
    
    introspection_keywords = [
        'analyze database', 'inspect database', 'database structure',
        'show schema', 'describe database', 'table details',
        'what fields', 'what columns', 'column names',
        'field types', 'data types', 'table structure',
        'show tables', 'list tables', 'what tables'
    ]
    
    return any(keyword in msg for keyword in introspection_keywords)

def needs_smart_search(message: str) -> bool:
    """Check if message requires smart search across database"""
    msg = message.lower()
    
    search_patterns = [
        'search for',
        'find in database',
        'look for',
        'search database',
        'find records',
        'search tables',
        'locate',
        'name',
        'database'
    ]
    
    return any(pattern in msg for pattern in search_patterns)

def needs_auto_query(message: str) -> bool:
    """Check if message can be auto-converted to SQL query"""
    msg = message.lower()
    
    auto_query_patterns = [
        'show me all',
        'get all',
        'list all',
        'find all',
        'retrieve all',
        'fetch all',
        'show all',
        'give me all'
    ]
    
    return any(pattern in msg for pattern in auto_query_patterns)

def needs_database_query(message: str) -> bool:
    """
    Check if question requires database access
    Enhanced to detect more patterns
    """
    msg = message.lower()
    
    # Explicit database operations
    explicit_db_keywords = [
        'list database', 'show database', 'what databases', 'all databases',
        'database overview', 'query database', 'sql query', 'run query',
        'execute query', 'query the', 'select from'
    ]
    
    # Also check for introspection and smart features
    if any(keyword in msg for keyword in explicit_db_keywords):
        return True
    
    if needs_database_introspection(message):
        return True
    
    if needs_smart_search(message) and 'database' in msg:
        return True
    
    return False

def needs_email_action(message: str) -> bool:
    """Check if the message is requesting to send an email"""
    msg = message.lower()
    
    email_keywords = [
        'send email',
        'email to',
        'send to',
        'email about',
        'send message to',
        'compose email'
    ]
    
    return any(keyword in msg for keyword in email_keywords)

def extract_database_name(message: str) -> Optional[str]:
    """Extract database name from message with enhanced detection"""
    msg = message.lower()
    
    patterns = [
        ('in database ', ' '),
        ('database ', ' '),
        ('from database ', ' '),
        ('in the ', ' database'),
        ('in ', ' database'),
        ('from ', ' ')
    ]
    
    for start_pattern, end_pattern in patterns:
        if start_pattern in msg:
            start = msg.find(start_pattern) + len(start_pattern)
            rest = message[start:]
            
            # Find end position
            if end_pattern.strip() in rest.lower():
                end = rest.lower().find(end_pattern.strip())
                db_name = rest[:end].strip()
            else:
                db_name = rest.split()[0].strip() if rest.split() else ''
            
            # Clean up
            db_name = db_name.strip('.,!?"\' ')
            if db_name and len(db_name) > 0:
                return db_name
    
    return None

def extract_table_name(message: str) -> Optional[str]:
    """Extract table name from message with enhanced detection"""
    msg = message.lower()
    
    patterns = [
        ('table ', ' '),
        ('from ', ' '),
        ('in table ', ' '),
        ('the ', ' table'),
        ('of ', ' table')
    ]
    
    for start_pattern, end_pattern in patterns:
        if start_pattern in msg:
            start = msg.find(start_pattern) + len(start_pattern)
            rest = message[start:]
            
            # Find end position
            words = rest.split()
            if words and words[0].strip('.,!?"\' ') not in ['database', 'all', 'the']:
                table_name = words[0].strip('.,!?"\' ')
                if len(table_name) > 0:
                    return table_name
    
    return None

def extract_search_term(message: str) -> Optional[str]:
    """Extract search term from message"""
    msg = message.lower()
    
    patterns = [
        'search for ',
        'find ',
        'look for ',
        'locate '
    ]
    
    for pattern in patterns:
        if pattern in msg:
            start = msg.find(pattern) + len(pattern)
            rest = message[start:]
            
            # Extract until 'in' or end of string
            if ' in ' in rest:
                end = rest.find(' in ')
                search_term = rest[:end].strip()
            else:
                # Get first quoted term or first few words
                if '"' in rest or "'" in rest:
                    quote = '"' if '"' in rest else "'"
                    parts = rest.split(quote)
                    if len(parts) >= 2:
                        search_term = parts[1]
                    else:
                        search_term = rest.split()[0] if rest.split() else ''
                else:
                    # Get first word or phrase
                    words = rest.split()
                    search_term = words[0] if words else ''
            
            search_term = search_term.strip('.,!?"\' ')
            if search_term:
                return search_term
    
    return None

def classify_query_type(message: str) -> str:
    """
    Classify the type of query with enhanced detection
    
    Returns:
        str: Query type ('email', 'schema_introspection', 'smart_search', 
             'auto_query', 'database', 'company', 'general')
    """
    # Check in order of specificity
    
    if needs_email_action(message):
        return 'email'
    
    if needs_database_introspection(message):
        return 'schema_introspection'
    
    if needs_smart_search(message):
        return 'smart_search'
    
    if needs_auto_query(message):
        return 'auto_query'
    
    if needs_database_query(message):
        return 'database'
    
    if needs_company_data(message):
        return 'company'
    
    return 'general'

def parse_query_intent(message: str) -> Dict[str, any]:
    """
    Parse message to extract all relevant information
    
    Returns:
        Dict with query intent, database, table, search term, etc.
    """
    intent = {
        'type': classify_query_type(message),
        'database': extract_database_name(message),
        'table': extract_table_name(message),
        'search_term': extract_search_term(message),
        'original_message': message,
        'requires_ai': True
    }
    
    # Determine if AI processing is needed
    if intent['type'] in ['schema_introspection', 'smart_search']:
        intent['requires_ai'] = True  # AI should explain results
    elif intent['type'] == 'auto_query':
        intent['requires_ai'] = True  # AI should format and explain
    
    return intent

def get_query_suggestions(message: str) -> list:
    """
    Suggest possible queries based on message intent
    """
    msg = message.lower()
    suggestions = []
    
    if 'operator' in msg:
        suggestions.extend([
            "Show me all operators in the database",
            "Find operators working today",
            "Search for operator [ID] in database"
        ])
    
    if 'production' in msg or 'output' in msg:
        suggestions.extend([
            "Show production statistics",
            "Get today's production data",
            "Find top performers by output"
        ])
    
    if 'table' in msg:
        suggestions.extend([
            "List all tables in [database]",
            "Describe the structure of [table]",
            "Show sample data from [table]"
        ])
    
    if 'search' in msg:
        suggestions.extend([
            "Search for [term] in [database]",
            "Find records containing [text]",
            "Locate [value] across all tables"
        ])
    
    return suggestions

def format_query_help(query_type: str) -> str:
    """Provide contextual help based on query type"""
    
    help_texts = {
        'schema_introspection': """
**Schema Introspection Examples:**
- "Analyze the production database"
- "Show me the structure of operators table"
- "What fields are in the activity table?"
- "Describe all tables in [database]"
""",
        'smart_search': """
**Smart Search Examples:**
- "Search for 'KE0152' in production database"
- "Find all records containing 'LEDTECH'"
- "Look for operator 'John' in all tables"
""",
        'auto_query': """
**Auto-Query Examples:**
- "Show me all operators"
- "Get the latest production data"
- "List all products in inventory"
- "Find recent activity records"
""",
        'database': """
**Database Query Examples:**
- "List all databases"
- "Show tables in production database"
- "Query the operators table"
- "Execute: SELECT * FROM products LIMIT 10"
"""
    }
    
    return help_texts.get(query_type, "No specific help available for this query type.")


# Quick validation helpers
def is_valid_database_name(name: str) -> bool:
    """Check if database name looks valid"""
    if not name:
        return False
    # Basic validation: alphanumeric and underscore
    return all(c.isalnum() or c == '_' for c in name)


def is_valid_table_name(name: str) -> bool:
    """Check if table name looks valid"""
    if not name:
        return False
    # Basic validation: alphanumeric and underscore
    return all(c.isalnum() or c == '_' for c in name)