# activity_filters.py - Data Filtering Functions
from typing import List, Dict
from datetime import datetime, date

def filter_by_employee(data: List[Dict], employee_identifier: str) -> List[Dict]:
    """
    Filter activity data by employee name or ID
    Args:
        data: List of activity records
        employee_identifier: Name or ID to search for
    """
    if not data:
        return []
    
    filtered = []
    search_term = employee_identifier.lower()
    
    for record in data:
        # Check common field names for employee info
        employee_fields = ['employee_name', 'name', 'employee', 'user', 'username', 
                          'employee_id', 'user_id', 'operator', 'operator_name']
        
        for field in employee_fields:
            if field in record and record[field]:
                if search_term in str(record[field]).lower():
                    filtered.append(record)
                    break
    
    return filtered

def filter_by_date(data: List[Dict], target_date: date) -> List[Dict]:
    """
    Filter activity data by date
    Args:
        data: List of activity records
        target_date: Date to filter by
    """
    if not data:
        return []
    
    filtered = []
    
    for record in data:
        # Check common date field names
        date_fields = ['date', 'timestamp', 'datetime', 'created_at', 
                      'activity_date', 'record_date', 'time', 'start_time', 'end_time']
        
        for field in date_fields:
            if field in record and record[field]:
                try:
                    record_date = _parse_date(str(record[field]))
                    if record_date and record_date == target_date:
                        filtered.append(record)
                        break
                except:
                    continue
    
    return filtered

def filter_by_date_range(data: List[Dict], start_date: date, end_date: date) -> List[Dict]:
    """Filter activity data by date range"""
    if not data:
        return []
    
    filtered = []
    
    for record in data:
        date_fields = ['date', 'timestamp', 'datetime', 'created_at', 
                      'activity_date', 'record_date', 'time', 'start_time', 'end_time']
        
        for field in date_fields:
            if field in record and record[field]:
                try:
                    record_date = _parse_date(str(record[field]))
                    if record_date and start_date <= record_date <= end_date:
                        filtered.append(record)
                        break
                except:
                    continue
    
    return filtered

def _parse_date(date_str: str) -> date:
    """Parse date string in various formats"""
    # Try ISO format
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
    except:
        pass
    
    # Try common formats
    for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y', '%d/%m/%Y']:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    
    return None