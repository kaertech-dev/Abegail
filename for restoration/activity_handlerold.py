# activity_handler.py - Activity Monitoring API Handler with HTML Parsing
import requests
import json
from typing import Optional, Dict, List
from datetime import datetime, date
from collections import defaultdict
from html.parser import HTMLParser

class TableParser(HTMLParser):
    """Enhanced parser to convert HTML tables to JSON format"""
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.headers = []
        self.rows = []
        self.current_data = []
        
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
        elif tag == 'tr':
            self.in_row = True
            self.current_row = []
        elif tag in ['td', 'th']:
            self.in_cell = True
            self.current_data = []
            
    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        elif tag == 'tr':
            self.in_row = False
            if self.current_row:
                if not self.headers:
                    self.headers = self.current_row
                else:
                    self.rows.append(self.current_row)
        elif tag in ['td', 'th']:
            self.in_cell = False
            cell_text = ''.join(self.current_data).strip()
            self.current_row.append(cell_text)
            
    def handle_data(self, data):
        if self.in_cell:
            self.current_data.append(data)

class ActivityHandler:
    """Handle activity monitoring API queries with HTML/JSON support"""
    
    def __init__(self, api_url: Optional[str] = None):
        # Import and use config
        if api_url is None:
            from config import ACTIVITY_API_URL
            api_url = ACTIVITY_API_URL
        
        self.activity_endpoint = api_url
        print(f"🔗 Activity API initialized: {self.activity_endpoint}")
    
    def parse_html_to_json(self, html_content: str) -> List[Dict]:
        """Convert HTML table to JSON with enhanced field detection"""
        parser = TableParser()
        parser.feed(html_content)
        
        json_data = []
        for row in parser.rows:
            if len(row) == len(parser.headers):
                record = {}
                for i, header in enumerate(parser.headers):
                    clean_header = header.strip().lower().replace(' ', '_')
                    value = row[i].strip()
                    
                    # Smart type conversion
                    if value.isdigit():
                        record[clean_header] = int(value)
                    elif self._is_float(value):
                        record[clean_header] = float(value)
                    else:
                        record[clean_header] = value
                
                json_data.append(record)
        
        return json_data
    
    def _is_float(self, value: str) -> bool:
        """Check if string is a valid float"""
        try:
            float(value)
            return '.' in value
        except ValueError:
            return False
        
    def fetch_activity_data(self, timeout: int = 10) -> Optional[Dict]:
        """
        Fetch activity data from API (supports both JSON and HTML)
        Returns: Dict with activity data or error info
        """
        try:
            print(f"📡 Fetching from: {self.activity_endpoint}")
            
            response = requests.get(
                self.activity_endpoint, 
                timeout=timeout,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            
            # Try JSON first
            if 'application/json' in content_type.lower():
                try:
                    data = response.json()
                    print("✅ Successfully parsed JSON response")
                    return {
                        'success': True,
                        'data': data,
                        'timestamp': datetime.now().isoformat(),
                        'count': len(data) if isinstance(data, list) else 1
                    }
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode failed, trying HTML parsing: {e}")
                    # Fall through to HTML parsing
            
            # If JSON fails or content is HTML, try parsing HTML
            print("🔄 Attempting HTML table parsing...")
            html_content = response.text
            json_data = self.parse_html_to_json(html_content)
            
            if json_data:
                print(f"✅ Successfully parsed HTML table ({len(json_data)} records)")
                return {
                    'success': True,
                    'data': json_data,
                    'timestamp': datetime.now().isoformat(),
                    'count': len(json_data),
                    'source': 'html'  # Indicate data came from HTML
                }
            else:
                return {
                    'success': False,
                    'error': 'No data found',
                    'message': 'Could not parse data from HTML table or JSON',
                    'raw_response': response.text[:500],
                    'tried_url': self.activity_endpoint
                }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timeout',
                'message': f'API at {self.activity_endpoint} took too long to respond (>{timeout}s)',
                'tried_url': self.activity_endpoint
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Connection error',
                'message': f'Could not connect to {self.activity_endpoint}. Is the server running?',
                'tried_url': self.activity_endpoint
            }
        except requests.exceptions.HTTPError as e:
            return {
                'success': False,
                'error': 'HTTP error',
                'message': f'API returned error: {e.response.status_code}',
                'raw_response': e.response.text[:500] if hasattr(e.response, 'text') else None,
                'tried_url': self.activity_endpoint
            }
        except Exception as e:
            return {
                'success': False,
                'error': 'Unknown error',
                'message': str(e),
                'tried_url': self.activity_endpoint
            }
    
    def filter_by_employee(self, data: List[Dict], employee_identifier: str) -> List[Dict]:
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
    
    def filter_by_date(self, data: List[Dict], target_date: date) -> List[Dict]:
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
                        # Try parsing different date formats
                        record_date = None
                        date_str = str(record[field])
                        
                        # Try ISO format
                        try:
                            record_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                        except:
                            pass
                        
                        # Try common formats
                        if not record_date:
                            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y', '%d/%m/%Y']:
                                try:
                                    record_date = datetime.strptime(date_str, fmt).date()
                                    break
                                except:
                                    continue
                        
                        if record_date and record_date == target_date:
                            filtered.append(record)
                            break
                    except:
                        continue
        
        return filtered
    
    def filter_by_date_range(self, data: List[Dict], start_date: date, end_date: date) -> List[Dict]:
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
                        record_date = None
                        date_str = str(record[field])
                        
                        # Try parsing
                        try:
                            record_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                        except:
                            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y', '%d/%m/%Y']:
                                try:
                                    record_date = datetime.strptime(date_str, fmt).date()
                                    break
                                except:
                                    continue
                        
                        if record_date and start_date <= record_date <= end_date:
                            filtered.append(record)
                            break
                    except:
                        continue
        
        return filtered
    
    def format_activity_response(self, result: Dict, query_type: str = 'general', 
                                 filters: Dict = None) -> str:
        """
        Format activity data into readable response
        Args:
            result: Result from fetch_activity_data
            query_type: Type of query ('general', 'employee', 'date', etc.)
            filters: Applied filters (employee_name, date, etc.)
        """
        if not result['success']:
            error_msg = f"❌ **Activity API Error**\n\n"
            error_msg += f"**Error:** {result['error']}\n"
            error_msg += f"**Message:** {result['message']}\n"
            error_msg += f"**Tried URL:** {result.get('tried_url', 'Unknown')}\n\n"
            
            # Show raw response if available for debugging
            if 'raw_response' in result and result['raw_response']:
                error_msg += f"**Debug Info (first 300 chars):**\n```\n{result['raw_response'][:300]}\n```\n\n"
            
            error_msg += f"**Troubleshooting:**\n"
            error_msg += f"1. ✅ Check if Activity Monitoring server is running\n"
            error_msg += f"2. ✅ Verify the URL in config.py is correct\n"
            error_msg += f"3. ✅ Test with: `curl {result.get('tried_url', 'URL')}`\n"
            
            return error_msg
        
        data = result['data']
        
        # Show if data came from HTML parsing
        source_note = ""
        if result.get('source') == 'html':
            source_note = ""
        
        # Handle different data structures
        if isinstance(data, dict):
            # If API returns object with activities array
            if 'activities' in data:
                activities = data['activities']
            elif 'data' in data:
                activities = data['data']
            else:
                activities = [data]
        elif isinstance(data, list):
            activities = data
        else:
            return f"⚠️ Unexpected data format from API\n\n```json\n{json.dumps(data, indent=2, default=str)}\n```"
        
        # Apply filters if provided
        filtered_activities = activities
        if filters:
            if filters.get('employee_name'):
                filtered_activities = self.filter_by_employee(filtered_activities, filters['employee_name'])
            
            if filters.get('date'):
                filtered_activities = self.filter_by_date(filtered_activities, filters['date'])
            
            if filters.get('start_date') and filters.get('end_date'):
                filtered_activities = self.filter_by_date_range(
                    filtered_activities, 
                    filters['start_date'], 
                    filters['end_date']
                )
        
        # Build response
        output = f"# 📊 Activity Monitoring{source_note}\n\n"
        
        if filters:
            output += "**Filters Applied:**\n"
            if filters.get('employee_name'):
                output += f"- Employee: {filters['employee_name']}\n"
            if filters.get('date'):
                output += f"- Date: {filters['date']}\n"
            if filters.get('start_date') and filters.get('end_date'):
                output += f"- Date Range: {filters['start_date']} to {filters['end_date']}\n"
            output += "\n"
        
        output += f"**Total Records:** {len(activities)}\n"
        
        if filters and filtered_activities != activities:
            output += f"**Matching Records:** {len(filtered_activities)}\n"
        
        output += f"**Last Updated:** {result['timestamp']}\n\n"
        
        if not filtered_activities:
            output += "❌ **No activities found**"
            if filters:
                output += " matching your filters"
            output += ".\n\n💡 Try:\n"
            output += "- \"show all activities\"\n"
            output += "- \"activity for [employee name]\"\n"
            output += "- \"activities today\"\n"
            return output
        
        # Format based on query type
        if query_type == 'employee' and filters.get('employee_name'):
            output += f"## 👤 Activities for {filters['employee_name']}\n\n"
        elif query_type == 'date' and filters.get('date'):
            output += f"## 📅 Activities for {filters['date']}\n\n"
        else:
            output += "## 📋 Activity Records:\n\n"
        
        # Display activities
        for idx, activity in enumerate(filtered_activities[:20], 1):
            output += f"### {idx}. "
            
            # Try to get meaningful title
            if 'employee_name' in activity:
                output += f"**{activity['employee_name']}**"
            elif 'name' in activity:
                output += f"**{activity['name']}**"
            elif 'operator' in activity:
                output += f"**{activity['operator']}**"
            else:
                output += f"Activity {idx}"
            
            output += "\n"
            
            # Show key details
            important_fields = ['employee_id', 'operator', 'customer', 'model', 'product',
                              'station', 'output', 'cycle_time', 'target_time', 'target',
                              'status', 'start_time', 'end_time']
            
            for key in important_fields:
                if key in activity and activity[key] is not None:
                    output += f"   - **{key.replace('_', ' ').title()}:** {activity[key]}\n"
            
            output += "\n"
        
        if len(filtered_activities) > 20:
            output += f"*Showing first 20 of {len(filtered_activities)} activities*\n\n"
        
        output += "---\n\n"
        output += "## 💡 More Options:\n\n"
        output += "- \"show activities for [employee name]\"\n"
        output += "- \"activities today\"\n"
        output += "- \"activities from last 7 days\"\n"
        output += "- \"activity summary\"\n"
        
        return output
    
    def get_activity_summary(self) -> str:
        """Get summary of activity data"""
        result = self.fetch_activity_data()
        
        if not result['success']:
            return self.format_activity_response(result, 'summary')
        
        data = result['data']
        
        # Handle different structures
        if isinstance(data, dict):
            if 'activities' in data:
                activities = data['activities']
            elif 'data' in data:
                activities = data['data']
            else:
                activities = [data]
        elif isinstance(data, list):
            activities = data
        else:
            return "⚠️ Cannot parse activity data"
        
        # Generate summary
        output = "# 📊 Activity Summary\n\n"
        output += f"**Total Activities:** {len(activities)}\n"
        output += f"**Last Updated:** {result['timestamp']}\n\n"
        
        # Group by employee if possible
        by_employee = defaultdict(int)
        by_date = defaultdict(int)
        
        for activity in activities:
            # Count by employee (try multiple field names)
            employee_fields = ['employee_name', 'name', 'employee', 'user', 'operator']
            for field in employee_fields:
                if field in activity and activity[field]:
                    by_employee[activity[field]] += 1
                    break
            
            # Count by date
            date_fields = ['date', 'timestamp', 'datetime', 'created_at', 'start_time']
            for field in date_fields:
                if field in activity and activity[field]:
                    try:
                        date_str = str(activity[field]).split('T')[0]  # Get date part
                        by_date[date_str] += 1
                        break
                    except:
                        continue
        
        if by_employee:
            output += "## 👥 Activities by Employee:\n\n"
            for employee, count in sorted(by_employee.items(), key=lambda x: x[1], reverse=True)[:10]:
                output += f"- **{employee}:** {count} activities\n"
            output += "\n"
        
        if by_date:
            output += "## 📅 Activities by Date:\n\n"
            for date_str, count in sorted(by_date.items(), reverse=True)[:7]:
                output += f"- **{date_str}:** {count} activities\n"
            output += "\n"
        
        output += "---\n\n"
        output += "💡 **Next Steps:**\n"
        output += "- \"show all activities\"\n"
        output += "- \"activities for [employee name]\"\n"
        output += "- \"activities today\"\n"
        
        return output

# Singleton instance
_activity_handler = None

def get_activity_handler():
    """Get singleton activity handler"""
    global _activity_handler
    if _activity_handler is None:
        _activity_handler = ActivityHandler()
    return _activity_handler

# Convenience functions for use in app.py

def get_all_activities() -> str:
    """Get all activities from API"""
    handler = get_activity_handler()
    result = handler.fetch_activity_data()
    return handler.format_activity_response(result, 'general')

def get_activities_for_employee(employee_name: str) -> str:
    """Get activities for specific employee"""
    handler = get_activity_handler()
    result = handler.fetch_activity_data()
    
    if result['success']:
        filters = {'employee_name': employee_name}
        return handler.format_activity_response(result, 'employee', filters)
    else:
        return handler.format_activity_response(result, 'employee')

def get_activities_for_date(target_date: date) -> str:
    """Get activities for specific date"""
    handler = get_activity_handler()
    result = handler.fetch_activity_data()
    
    if result['success']:
        filters = {'date': target_date}
        return handler.format_activity_response(result, 'date', filters)
    else:
        return handler.format_activity_response(result, 'date')

def get_activities_for_range(start_date: date, end_date: date) -> str:
    """Get activities for date range"""
    handler = get_activity_handler()
    result = handler.fetch_activity_data()
    
    if result['success']:
        filters = {'start_date': start_date, 'end_date': end_date}
        return handler.format_activity_response(result, 'range', filters)
    else:
        return handler.format_activity_response(result, 'range')

def get_activity_summary() -> str:
    """Get activity summary"""
    handler = get_activity_handler()
    return handler.get_activity_summary()

def is_activity_query(message: str) -> bool:
    """Check if message is an activity monitoring query"""
    msg_lower = message.lower()
    activity_keywords = [
        'activity', 'activities', 'monitoring',
        'what are they doing', 'what is', 'who is doing',
        'show activity', 'activity log', 'activity report',
        'activity data', 'activity for'
    ]
    return any(keyword in msg_lower for keyword in activity_keywords)