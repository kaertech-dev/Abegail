# activity_formatter.py - Response Formatting Functions
import json
from typing import Dict, List
from collections import defaultdict

def format_error_response(result: Dict) -> str:
    """Format error response"""
    error_msg = f"❌ **Activity API Error**\n\n"
    error_msg += f"**Error:** {result['error']}\n"
    error_msg += f"**Message:** {result['message']}\n"
    error_msg += f"**Tried URL:** {result.get('tried_url', 'Unknown')}\n\n"
    
    if 'raw_response' in result and result['raw_response']:
        error_msg += f"**Debug Info (first 300 chars):**\n```\n{result['raw_response'][:300]}\n```\n\n"
    
    error_msg += f"**Troubleshooting:**\n"
    error_msg += f"1. ✅ Check if Activity Monitoring server is running\n"
    error_msg += f"2. ✅ Verify the URL in config.py is correct\n"
    error_msg += f"3. ✅ Test with: `curl {result.get('tried_url', 'URL')}`\n"
    
    return error_msg

def format_activity_response(result: Dict, query_type: str = 'general', filters: Dict = {}) -> str:
    """Format activity data into readable response"""
    if not result['success']:
        return format_error_response(result)
    
    data = result['data']
    
    # Handle different data structures
    activities = _normalize_activities(data)
    
    if activities is None:
        return f"⚠️ Unexpected data format from API\n\n```json\n{json.dumps(data, indent=2, default=str)}\n```"
    
    # Build response
    output = _build_header(result, filters)
    output += _build_stats(activities, result['timestamp'], filters)
    
    filtered_activities = activities
    # if filters:
    #     try:
    #         # Try relative import first
    #         from .activity_filters import filter_by_employee, filter_by_date, filter_by_date_range
    #     except ImportError:
    #         # Fall back to absolute import
    #         from activity_filters import filter_by_employee, filter_by_date, filter_by_date_range
        
    #     if filters.get('employee_name'):
    #         filtered_activities = filter_by_employee(filtered_activities, filters['employee_name'])
        
    #     if filters.get('date'):
    #         filtered_activities = filter_by_date(filtered_activities, filters['date'])
        
    #     if filters.get('start_date') and filters.get('end_date'):
    #         filtered_activities = filter_by_date_range(
    #             filtered_activities, filters['start_date'], filters['end_date']
    #         )
    
    if not filtered_activities:
        return output + _build_no_results_message(filters)
    
    output += _build_section_header(query_type, filters)
    output += _build_activity_list(filtered_activities)
    # output += _build_footer()
    
    return output

def format_activity_summary(result: Dict) -> str:
    """Format activity summary"""
    if not result['success']:
        return format_error_response(result)
    
    activities = _normalize_activities(result['data'])
    if activities is None:
        return "⚠️ Cannot parse activity data"
    
    output = "# 📊 Activity Summary\n\n"
    output += f"**Total Activities:** {len(activities)}\n"
    output += f"**Last Updated:** {result['timestamp']}\n\n"
    
    by_employee, by_date = _aggregate_activities(activities)
    
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

def _normalize_activities(data) -> List[Dict]:
    """Normalize different data structures to list of activities"""
    if isinstance(data, dict):
        if 'activities' in data:
            return data['activities']
        elif 'data' in data:
            return data['data']
        else:
            return [data]
    elif isinstance(data, list):
        return data
    return None

def _build_header(result: Dict, filters: Dict) -> str:
    """Build response header"""
    source_note = "" if result.get('source') != 'html' else ""
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
    
    return output

def _build_stats(activities: List[Dict], timestamp: str, filters: Dict) -> str:
    """Build statistics section"""
    output = f"**Total Records:** {len(activities)}\n"
    output += f"**Last Updated:** {timestamp}\n\n"
    return output

def _build_no_results_message(filters: Dict) -> str:
    """Build no results message"""
    output = "❌ **No activities found**"
    if filters:
        output += " matching your filters"
    output += ".\n\n💡 Try:\n"
    output += "- \"show all activities\"\n"
    output += "- \"activity for [employee name]\"\n"
    output += "- \"activities today\"\n"
    return output

def _build_section_header(query_type: str, filters: Dict) -> str:
    """Build section header based on query type"""
    if query_type == 'employee' and filters.get('employee_name'):
        return f"## 👤 Activities for {filters['employee_name']}\n\n"
    elif query_type == 'date' and filters.get('date'):
        return f"## 📅 Activities for {filters['date']}\n\n"
    else:
        return "## 📋 Activity Records:\n\n"

def _build_activity_list(activities: List[Dict]) -> str:
    """Build activity list"""
    output = ""
    
    for idx, activity in enumerate(activities[:20], 1):
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
        # important_fields = ['employee_id', 'operator', 'customer', 'model', 'product',
        #                   'station', 'output', 'cycle_time', 'target_time', 'target',
        #                   'status', 'start_time', 'end_time']
        
        # for key in important_fields:
        #     if key in activity and activity[key] is not None:
        #         output += f"   - **{key.replace('_', ' ').title()}:** {activity[key]}\n"
        
        output += f"   - **{activity['station']}** ({activity['customer']}, {activity['model']})\n"
        output += f"   - **Start Time:** {activity['start_time']} **End Time:** {activity['end_time']} **Output:** {activity['output']}\n"
        # output += f"   - {activity['status']} **Cycle Time:** {activity['cycle_time']} ({activity['target_time']})\n"
        
        output += "\n"
    
    if len(activities) > 20:
        output += f"*Showing first 20 of {len(activities)} activities*\n\n"
    
    return output

def _build_footer() -> str:
    """Build response footer"""
    output = "---\n\n"
    output += "## 💡 More Options:\n\n"
    output += "- \"show activities for [employee name]\"\n"
    output += "- \"activities today\"\n"
    output += "- \"activities from last 7 days\"\n"
    output += "- \"activity summary\"\n"
    return output

def _aggregate_activities(activities: List[Dict]) -> tuple:
    """Aggregate activities by employee and date"""
    by_employee = defaultdict(int)
    by_date = defaultdict(int)
    
    for activity in activities:
        # Count by employee
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
                    date_str = str(activity[field]).split('T')[0]
                    by_date[date_str] += 1
                    break
                except:
                    continue
    
    return by_employee, by_date