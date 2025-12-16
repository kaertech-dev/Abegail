# date_filter.py - Smart Date Filter System
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict

class DateFilter:
    """Parse natural language date queries and generate SQL filters"""
    
    def __init__(self):
        self.today = datetime.now().date()
        self.now = datetime.now()
    
    def parse_date_query(self, message: str) -> Optional[Dict]:
        """
        Parse message for date-related queries
        Returns: {
            'type': 'today'|'yesterday'|'date_range'|'relative'|'custom',
            'start_date': datetime,
            'end_date': datetime,
            'description': str
        }
        """
        msg_lower = message.lower()
        
        # Today
        if any(word in msg_lower for word in ['today', 'today\'s']):
            return {
                'type': 'today',
                'start_date': self.today,
                'end_date': self.today,
                'description': 'today'
            }
        
        # Yesterday
        if 'yesterday' in msg_lower:
            yesterday = self.today - timedelta(days=1)
            return {
                'type': 'yesterday',
                'start_date': yesterday,
                'end_date': yesterday,
                'description': 'yesterday'
            }
        
        # This week
        if 'this week' in msg_lower:
            start = self.today - timedelta(days=self.today.weekday())
            return {
                'type': 'relative',
                'start_date': start,
                'end_date': self.today,
                'description': 'this week'
            }
        
        # Last week
        if 'last week' in msg_lower:
            start = self.today - timedelta(days=self.today.weekday() + 7)
            end = start + timedelta(days=6)
            return {
                'type': 'relative',
                'start_date': start,
                'end_date': end,
                'description': 'last week'
            }
        
        # This month
        if 'this month' in msg_lower:
            start = self.today.replace(day=1)
            return {
                'type': 'relative',
                'start_date': start,
                'end_date': self.today,
                'description': 'this month'
            }
        
        # Last month
        if 'last month' in msg_lower:
            first_this_month = self.today.replace(day=1)
            last_month_end = first_this_month - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            return {
                'type': 'relative',
                'start_date': last_month_start,
                'end_date': last_month_end,
                'description': 'last month'
            }
        
        # Last N days
        last_n_days = re.search(r'last\s+(\d+)\s+days?', msg_lower)
        if last_n_days:
            n = int(last_n_days.group(1))
            start = self.today - timedelta(days=n)
            return {
                'type': 'relative',
                'start_date': start,
                'end_date': self.today,
                'description': f'last {n} days'
            }
        
        # Past N days (same as last N days)
        past_n_days = re.search(r'past\s+(\d+)\s+days?', msg_lower)
        if past_n_days:
            n = int(past_n_days.group(1))
            start = self.today - timedelta(days=n)
            return {
                'type': 'relative',
                'start_date': start,
                'end_date': self.today,
                'description': f'past {n} days'
            }
        
        # Date range: "from YYYY-MM-DD to YYYY-MM-DD"
        date_range = re.search(
            r'from\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})',
            msg_lower
        )
        if date_range:
            try:
                start = datetime.strptime(date_range.group(1), '%Y-%m-%d').date()
                end = datetime.strptime(date_range.group(2), '%Y-%m-%d').date()
                return {
                    'type': 'date_range',
                    'start_date': start,
                    'end_date': end,
                    'description': f'from {start} to {end}'
                }
            except ValueError:
                pass
        
        # Between dates: "between YYYY-MM-DD and YYYY-MM-DD"
        between_dates = re.search(
            r'between\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})',
            msg_lower
        )
        if between_dates:
            try:
                start = datetime.strptime(between_dates.group(1), '%Y-%m-%d').date()
                end = datetime.strptime(between_dates.group(2), '%Y-%m-%d').date()
                return {
                    'type': 'date_range',
                    'start_date': start,
                    'end_date': end,
                    'description': f'between {start} and {end}'
                }
            except ValueError:
                pass
        
        # Specific date: "on YYYY-MM-DD" or "data for YYYY-MM-DD"
        specific_date = re.search(
            r'(?:on|for|date)\s+(\d{4}-\d{2}-\d{2})',
            msg_lower
        )
        if specific_date:
            try:
                date = datetime.strptime(specific_date.group(1), '%Y-%m-%d').date()
                return {
                    'type': 'custom',
                    'start_date': date,
                    'end_date': date,
                    'description': f'on {date}'
                }
            except ValueError:
                pass
        
        # Just a date mentioned: YYYY-MM-DD
        just_date = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', msg_lower)
        if just_date:
            try:
                date = datetime.strptime(just_date.group(1), '%Y-%m-%d').date()
                return {
                    'type': 'custom',
                    'start_date': date,
                    'end_date': date,
                    'description': f'on {date}'
                }
            except ValueError:
                pass
        
        return None
    
    def generate_sql_date_filter(self, date_info: Dict, date_column: str) -> str:
        """
        Generate SQL WHERE clause for date filtering
        Args:
            date_info: Output from parse_date_query()
            date_column: Name of the date/datetime column in the table
        Returns:
            SQL WHERE clause string
        """
        start_date = date_info['start_date']
        end_date = date_info['end_date']
        
        if start_date == end_date:
            # Single day
            return f"`{date_column}` >= '{start_date} 00:00:00' AND `{date_column}` <= '{end_date} 23:59:59'"
        else:
            # Date range
            return f"`{date_column}` >= '{start_date} 00:00:00' AND `{date_column}` <= '{end_date} 23:59:59'"
    
    def detect_date_column(self, columns: list) -> Optional[str]:
        """
        Detect the most likely date/datetime column in a table
        Args:
            columns: List of column dictionaries with 'Field' and 'Type'
        Returns:
            Column name or None
        """
        # Priority order for date column detection
        priority_names = [
            'created_at', 'date', 'timestamp', 'datetime', 'created',
            'updated_at', 'modified', 'time', 'record_date', 'entry_date'
        ]
        
        # First, check for exact matches
        for priority in priority_names:
            for col in columns:
                if col['Field'].lower() == priority:
                    return col['Field']
        
        # Check for columns containing these keywords
        for priority in priority_names:
            for col in columns:
                if priority in col['Field'].lower():
                    return col['Field']
        
        # Check for datetime/date types
        for col in columns:
            col_type = col.get('Type', '').lower()
            if any(dt in col_type for dt in ['datetime', 'timestamp', 'date']):
                return col['Field']
        
        return None

_date_filter = None

def get_date_filter():
    """Get singleton date filter instance"""
    global _date_filter
    if _date_filter is None:
        _date_filter = DateFilter()
    return _date_filter

def parse_date_from_message(message: str) -> Optional[Dict]:
    """Convenience function to parse date from message"""
    return get_date_filter().parse_date_query(message)

def generate_date_sql(date_info: Dict, date_column: str) -> str:
    """Convenience function to generate SQL date filter"""
    return get_date_filter().generate_sql_date_filter(date_info, date_column)

def find_date_column(columns: list) -> Optional[str]:
    """Convenience function to find date column"""
    return get_date_filter().detect_date_column(columns)