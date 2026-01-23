# query_processor.py - Query Processing Logic
import re
from datetime import date, time
from typing import Dict, Optional, Tuple
from config import DATABASE_KEYWORDS, EMPLOYEE_ID_PATTERN

def extract_employee_name(message: str) -> Optional[str]:
    """Extract employee name from attendance/activity query"""
    msg = message.lower()
    
    # Pattern for employee IDs like KE0008
    employee_id_match = re.search(EMPLOYEE_ID_PATTERN, message, re.IGNORECASE)
    if employee_id_match:
        return employee_id_match.group(1).upper()
    
    # Patterns for employee names
    patterns = [
        r'(?:is|was|were)\s+([A-Za-z0-9\s]+?)\s+(?:present|absent|here|in|out|doing)',
        r'(?:attendance|activity)\s+(?:for|of)\s+([A-Za-z\s]+?)(?:\s+(?:today|yesterday|from|last|on)|\s*$)',
        r'([A-Za-z\s]+?)\'s\s+(?:attendance|activity)',
        r'show\s+([A-Za-z\s]+?)\s+(?:attendance|activity)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, msg)
        if match:
            name = match.group(1).strip()
            # Filter out common words
            if name.lower() not in ['all', 'the', 'data', 'for', 'from', 'show', 'today', 'yesterday', 'there', 'anyone', 'someone']:
                return name
    
    return None

def extract_table_name(message: str, database: str) -> Optional[str]:
    """Extract table name from message"""
    msg = message.lower()
    
    patterns = [
        r'table\s+(\w+)',
        r'details\s+of\s+(\w+)',
        r'info\s+on\s+(\w+)',
        r'about\s+(\w+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, msg)
        if match:
            return match.group(1)
    
    return None

def is_attendance_query(message: str) -> bool:
    """Check if message is an attendance query"""
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in DATABASE_KEYWORDS['attendance'])

def is_operator_count_query(message: str) -> bool:
    """Check if query is asking for operator count"""
    msg_lower = message.lower()
    count_patterns = [
        r'how many.*(?:operator|employee|people|worker).*present',
        r'count.*(?:operator|employee|people|worker).*present',
        r'total.*(?:operator|employee|people|worker).*present',
        r'number of.*(?:operator|employee|people|worker).*present',
        r'how many.*clocked in',
        r'how many.*time in'
    ]
    
    return any(re.search(pattern, msg_lower) for pattern in count_patterns)

def extract_search_term(message: str) -> Optional[str]:
    """Extract search term from message"""
    words = message.split()
    search_idx = next((i for i, w in enumerate(words) if w.lower() in ['search', 'find']), -1)
    if search_idx >= 0 and search_idx + 1 < len(words):
        return words[search_idx + 1].strip('"\'.,')
    return None

def extract_sql_query(message: str) -> Optional[str]:
    """Extract SQL query from message"""
    query_start = message.lower().find('select')
    if query_start >= 0:
        return message[query_start:].strip()
    return None

def extract_table_from_show_all(message: str) -> Optional[str]:
    """Extract table name from 'show all data' queries"""
    msg_lower = message.lower()
    table_match = re.search(r'(?:in|from)\s+(\w+)', msg_lower)
    if table_match:
        return table_match.group(1)
    return None

def extract_table_for_date_filter(message: str) -> Optional[Tuple[str, str]]:
    """Extract database and table name for date-filtered queries"""
    msg_lower = message.lower()
    
    table_patterns = [
        r'show\s+(\w+)\s+(?:data\s+)?(?:from|for)',
        r'(\w+)\s+(?:data|table)\s+(?:from|for|today|yesterday)',
        r'(?:from|in)\s+(\w+)\.(\w+)',
        r'table\s+(\w+)',
    ]
    
    for pattern in table_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            if match.lastindex and match.lastindex > 1:
                return match.group(1), match.group(2)
            return None, match.group(1)
    
    return None, None