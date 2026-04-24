# mcp_attendance_client.py - Client to interact with MCP Server from Flask
"""
This module provides a client interface to interact with the Attendance MCP Server
from your Flask application. It allows your chatroom to query attendance data.
"""

import asyncio
import re
import time
# import dateparser
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from contextlib import asynccontextmanager
from date_parser import extractDate

# MCP Client imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class AttendanceMCPClient():
    """Client to interact with Attendance MCP Server"""
    
    def __init__(self, server_script_path: str = "./mcp_attendance_server.py"):
        """
        Initialize MCP client
        
        Args:
            server_script_path: Path to the MCP server script
        """
        self.server_script_path = server_script_path
        self.session = None
        self.read_stream = None
        self.write_stream = None
        self._client_context = None
    
    async def connect(self):
        """Connect to the MCP server"""
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script_path],
            env=None
        )
        
        self._client_context = stdio_client(server_params)
        self.read_stream, self.write_stream = await self._client_context.__aenter__()
        self.session = ClientSession(self.read_stream, self.write_stream)
        await self.session.__aenter__()
        await self.session.initialize()
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self._client_context:
            await self._client_context.__aexit__(None, None, None)
    
    async def check_attendance(self, date_str: str, 
                              employee_identifier: Optional[str] = None) -> str:
        """
        Check attendance records for a specific date
        
        Args:
            date_str: Date in YYYY-MM-DD format (default: today)
            employee_identifier: Optional employee name or ID to filter
            
        Returns:
            Formatted attendance report
        """
        arguments = {"date": date_str}
        # if date_str:
        #     arguments["date"] = date_str
        if employee_identifier:
            arguments["employee_identifier"] = employee_identifier
        
        result = await self.session.call_tool("check_attendance", arguments)
        return result.content[0].text if result.content else "No response"
    
    async def check_presence(self, employee_identifier: str, 
                            date_str: Optional[str] = None) -> str:
        """
        Check if a specific employee is present
        
        Args:
            employee_identifier: Employee name or ID
            date_str: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            YES/NO answer with timeline
        """
        arguments = {"employee_identifier": employee_identifier}
        if date_str:
            arguments["date"] = date_str
        
        result = await self.session.call_tool("check_presence", arguments)
        return result.content[0].text if result.content else "No response"
    
    async def get_attendance_range(self, start_date: str, end_date: str,
                                  employee_identifier: Optional[str] = None) -> str:
        """
        Get attendance for a date range
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            employee_identifier: Optional employee filter
            
        Returns:
            Attendance report for the date range
        """
        arguments = {
            "start_date": start_date,
            "end_date": end_date
        }
        if employee_identifier:
            arguments["employee_identifier"] = employee_identifier
        
        result = await self.session.call_tool("get_attendance_range", arguments)
        return result.content[0].text if result.content else "No response"
    
    async def count_present_operators(self, date_str: Optional[str] = None,
                                     start_time: str = "07:00") -> str:
        """
        Count operators present after a specific time
        
        Args:
            date_str: Date in YYYY-MM-DD format (default: today)
            start_time: Time in HH:MM format (default: 07:00)
            
        Returns:
            Operator count with details
        """
        arguments = {"start_time": start_time}
        if date_str:
            arguments["date"] = date_str
        
        result = await self.session.call_tool("count_present_operators", arguments)
        return result.content[0].text if result.content else "No response"

    async def department_headcount(self, dept_str: str, date_str: str = None,
                                     start_time: str = '') -> str:
        """
        Count present employees in the given department after a specific time
        
        Args:
            department: Department name
            date_str: Date in YYYY-MM-DD format (default: today)
            start_time: Time in HH:MM format (default: 07:00)
            
        Returns:
            Employee count with details
        """
        arguments = {"department": dept_str, "start_time": start_time}
        if date_str:
            arguments["date"] = date_str
        
        result = await self.session.call_tool("department_headcount", arguments)
        return result.content[0].text if result.content else "No response"
    
    async def get_absent_employees(self, date_str: Optional[str] = None) -> str:
        """
        Get list of absent employees
        
        Args:
            date_str: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            List of absent employees
        """
        arguments = {}
        if date_str:
            arguments["date"] = date_str
        
        result = await self.session.call_tool("get_absent_employees", arguments)
        return result.content[0].text if result.content else "No response"
    
    async def get_latest_entries(self, start_time: Optional[str], end_time: Optional[str], where: str = 'last', limit: int = 10) -> str:
        """
        Get latest attendance entries
        
        Args:
            limit: Number of entries to retrieve
            
        Returns:
            Latest attendance entries
        """
        arguments = {"where": where, "limit": limit}
        if start_time:
            arguments["start_time"] = start_time
            arguments["end_time"] = end_time
        result = await self.session.call_tool("get_latest_entries", arguments)
        return result.content[0].text if result.content else "No response"


# Synchronous wrapper for Flask integration
class AttendanceService:
    """Synchronous service wrapper for Flask"""
    
    def __init__(self, server_script_path: str = "c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/mcp_attendance_server.py"):
        self.server_script_path = server_script_path
        self._loop = None
        self._client = None
    
    def _get_event_loop(self):
        """Get or create event loop"""
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def _run_async(self, coro):
        """Run async coroutine in sync context"""
        loop = self._get_event_loop()
        return loop.run_until_complete(coro)
    
    async def _ensure_connected(self):
        """Ensure client is connected"""
        if self._client is None:
            self._client = AttendanceMCPClient(self.server_script_path)
            await self._client.connect()
    
    # combine these three functions into one
    def check_attendance(self, date_str: Optional[str] = None, 
                        employee_identifier: Optional[str] = None) -> str:
        """Check attendance (sync)"""
        async def _check():
            await self._ensure_connected()
            return await self._client.check_attendance(date_str, employee_identifier)
        return self._run_async(_check())
    
    def check_presence(self, employee_identifier: str, 
                      date_str: Optional[str] = None) -> str:
        """Check presence (sync)"""
        async def _check():
            await self._ensure_connected()
            return await self._client.check_presence(employee_identifier, date_str)
        return self._run_async(_check())
    
    def get_attendance_range(self, start_date: str, end_date: str,
                            employee_identifier: Optional[str] = None) -> str:
        """Get attendance range (sync)"""
        async def _get():
            await self._ensure_connected()
            return await self._client.get_attendance_range(start_date, end_date, employee_identifier)
        return self._run_async(_get())
    
    # also combine these three functions
    def count_present_operators(self, date_str: Optional[str] = None,
                               start_time: str = "07:00") -> str:
        """Count operators (sync)"""
        async def _count():
            await self._ensure_connected()
            return await self._client.count_present_operators(date_str, start_time)
        return self._run_async(_count())
    
    def department_headcount(self, dept_str: str, date_str: str = None,
                               start_time: str = None) -> str:
        """Count operators (sync)"""
        async def _count():
            await self._ensure_connected()
            return await self._client.department_headcount(dept_str, date_str, start_time)
        return self._run_async(_count())
    
    def get_absent_employees(self, date_str: Optional[str] = None) -> str:
        """Get absent employees (sync)"""
        async def _get():
            await self._ensure_connected()
            return await self._client.get_absent_employees(date_str)
        return self._run_async(_get())
    
    # add tag to allow for different date, as well as earliest or within a time range
    def get_latest_entries(self, start_time: Optional[str], end_time: Optional[str], where: str = 'last', limit: int = 10) -> str:
        """Get latest entries (sync)"""
        async def _get():
            await self._ensure_connected()
            return await self._client.get_latest_entries(start_time, end_time, where, limit)
        return self._run_async(_get())
    
    def cleanup(self):
        """Cleanup resources"""
        if self._client:
            async def _cleanup():
                await self._client.disconnect()
            self._run_async(_cleanup())
            self._client = None


# Singleton instance
_attendance_service = None

def get_attendance_service(server_script_path: str = "c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/mcp_attendance_server.py") -> AttendanceService:
    """Get singleton attendance service"""
    global _attendance_service
    if _attendance_service is None:
        _attendance_service = AttendanceService(server_script_path)
    return _attendance_service

def get_name(raw_name: str) -> str:
    l_name = raw_name.split(',')
    if len(l_name) > 1:
        new_name = l_name[1] + ' ' + l_name[0]
        return new_name.strip()
    else:
        return raw_name.strip()

# Query router to detect attendance queries
def detect_attendance_query(message: str) -> Optional[Dict]:
    """
    Detect if message is an attendance query and extract parameters
    
    Returns:
        Dict with query type and parameters, or None if not an attendance query
    """
    
    msg_lower = message.lower()
    
    # Check for attendance keywords
    attendance_keywords = [
        'attendance', 'present', 'absent', 'time in', 'clock in', 'check in', 
        'who is here', 'who is in', 
        'department', 'headcount', 'employee', 'employees',
        'timeout', 'time out', 'clock out',
        'your_custom_keyword'
    ]

    departments = ['Top Management',
                   'Manufacturing', 'Quality Regulatory Affairs & EHS',
                   'Business Development', 'HR & Admin',
                   'Supply Chain Management', 'Facilities & Maintenance',
                   'Information Technology', 'Research & Development',
                   'Accounting', 'Finance & Administration']
    
    if not any(keyword in msg_lower for keyword in attendance_keywords+departments):
        return None
    
    # Detect query type and extract parameters
    query_info = {'type': None, 'params': {}}
    
    # 1. Presence check: "is [name] present"
    presence_patterns = [
        r'is\s+([A-Za-z,\s]+)\s+present',
        r'is\s+([A-Za-z,\s]+)\s+here',
        r'is\s+(KE\d{4})\s+present',
        r'check\s+([A-Za-z,\s]+)\s+attendance',
        r'([A-Za-z,\s]+)\s+attendance',
        r'attendance\s*(?:of)?\s*([A-Za-z,\s]+)(?=(for|from|on))',
        r'([A-Za-z,\s]+)\s*time\s*out\s*\w*',
        r'([A-Za-z,\s]+) clock out'
    ]
    
    for pattern in presence_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            query_info['type'] = 'presence_check'
            query_info['params']['employee_identifier'] = get_name(match.group(1))
            break
    
    # 2. Operator count: "how many operators"
    if re.search(r'how many.*(?:operator|employee|people)', msg_lower):
        query_info['type'] = 'count_operators'
    
    for dept in departments:
        if dept.lower() in msg_lower:
            query_info['type'] = 'dep_headcount'
            query_info['params']['department'] = dept
            break
    
    # 3. Absent employees: "who is absent"
    if 'absent' in msg_lower or 'not present' in msg_lower:
        if not query_info['type']:  # Don't override presence check
            query_info['type'] = 'absent_list'
    
    # 4. Latest entries: "latest attendance" or "recent attendance"
    if 'latest' in msg_lower or 'recent' in msg_lower:
        query_info['type'] = 'latest_entries'
        query_info['params']['where'] = 'last'
    
    if 'earliest' in msg_lower or 'first entries' in msg_lower:
        query_info['type'] = 'latest_entries'
        query_info['params']['where'] = 'first'
    
    if 'entries between' in msg_lower:
        query_info['type'] = 'latest_entries'
        query_info['params']['where'] = 'middle'
        time_regex = r'(\d{2}:\d{2})\s+(to|and)\s+(\d{2}:\d{2})'
        time_match = re.search(time_regex, msg_lower)
        query_info['params']['start_time'] = time_match.group(1)
        query_info['params']['end_time'] = time_match.group(3)
    
    # 5. General attendance query with date
    if not query_info['type']:
        query_info['type'] = 'general_attendance'
    
    # Extract date information
    date_results = extractDate(msg_lower)
    if len(date_results) == 1:
        # only one date was given, explicitly or implicitly
        query_info['params']['date'] = date_results[0]
    elif len(date_results) > 1:
        # two dates were given, i.e. a range
        query_info['params']['start_date'] = date_results[0]
        query_info['params']['end_date'] = date_results[1]
        query_info['type'] = 'attendance_range'
    
    # Extract employee name/ID if not already found
    if 'employee_identifier' not in query_info['params']:
        # Look for employee ID pattern
        id_match = re.search(r'\b(KE\d{4})\b', message, re.IGNORECASE)
        if id_match:
            query_info['params']['employee_identifier'] = id_match.group(1).upper()
        else:
            # Look for common names
            name_patterns = [
                r'for\s+(\w+)',
                r'of\s+(\w+)',
                r'attendance\s+(\w+)',
                r'(\w+)\s+attendance',
                r'(\w+)\s+record',
                r'record of (\w+)'
            ]
            for pattern in name_patterns:
                match = re.search(pattern, msg_lower)
                if match and match.group(1) not in ['today', 'yesterday', 'the', 'all']:
                    query_info['params']['employee_identifier'] = match.group(1).title()
                    break
    
    return query_info if query_info['type'] else None


def handle_attendance_query_via_mcp(message: str) -> None | dict[str, str]:
    """
    Handle attendance query through MCP server
    
    Args:
        message: User's message
        
    Returns:
        Response string, or None if not an attendance query
    """
    message = message.replace('debug-att', '')
    query_info = detect_attendance_query(message)
    
    if not query_info:
        return None
    
    try:
        service = get_attendance_service()
        query_type = query_info['type']
        params = query_info['params']
        
        if query_type == 'presence_check':
            answer = service.check_presence(
                params['employee_identifier'],
                params.get('date')
            )
        
        elif query_type == 'dep_headcount':
            curr_time = str(datetime.now().time())
            print("Current time", curr_time)
            answer = service.department_headcount(
                params.get('department'),
                params.get('date'),
                params.get('start_time', curr_time[:5])
            )
        
        elif query_type == 'count_operators':
            curr_time = str(datetime.now().time())
            answer = service.count_present_operators(
                params.get('date'),
                params.get('start_time', curr_time[:5])
            )
        
        elif query_type == 'absent_list':
            answer = service.get_absent_employees(params.get('date'))
        
        elif query_type == 'latest_entries':
            answer = service.get_latest_entries(
                params.get('start_time'),
                params.get('end_time'),
                params['where'],
                params.get('limit', 10)
            )
        
        elif query_type == 'attendance_range':
            answer = service.get_attendance_range(
                params['start_date'],
                params['end_date'],
                params.get('employee_identifier')
            )
        
        elif query_type == 'general_attendance':
            answer = service.check_attendance(
                params.get('date'),
                params.get('employee_identifier')
            )
        
        else:
            return None
        
        idx = answer.find('.csv') + 4
        if idx > 3:
            filename = answer[:idx]
            return {'answer': answer[idx:], 'csv_file': filename, 'response_type': 'attendance'}
        else:
            return {'answer': answer, 'response_type': 'attendance'}
    
    except Exception as e:
        return {'answer': f"❌ **Attendance Query Error:** {str(e)}\n\nPlease check if the MCP server is running.", 'response_type': 'error'}


# Example usage in Flask route
"""
# Add to your app.py:

from mcp_attendance_client import handle_attendance_query_via_mcp

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '').strip()
        
        # ... existing code ...
        
        # Try attendance query first
        attendance_response = handle_attendance_query_via_mcp(message)
        if attendance_response:
            bot_msg = session_mgr.create_message(
                'bot', 
                attendance_response, 
                session_id,
                user_msg['id'], 
                response_type='attendance'
            )
            session_mgr.add_message(session_id, bot_msg)
            return jsonify(bot_msg)
        
        # ... rest of your existing routing logic ...
        
    except Exception as e:
        # ... error handling ...
"""