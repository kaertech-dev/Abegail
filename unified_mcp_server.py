#!/usr/bin/env python3
"""
Unified MCP Server with DeepSeek Intelligence
Combines Attendance + Activity Monitoring + AI Analysis
"""

import asyncio
import json
import subprocess
import os
from datetime import datetime, date, time, timedelta
from typing import Any, List, Dict, Optional
import mysql.connector
from mysql.connector import Error
import requests
from html.parser import HTMLParser

# MCP SDK imports
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# ==================== CONFIGURATION ====================

DB_CONFIG = {
    'host': '192.168.1.38',
    'user': 'labeling',
    'password': 'labeling',
    'database': 'attendance',
    'autocommit': True,
    'use_unicode': True,
    'charset': 'utf8mb4'
}

ACTIVITY_API_URL = "http://localhost/activity"
DEEPSEEK_MODEL = "deepseek-r1:14b"  # or "deepseek-r1:1.5b" for faster responses

DEVICE_LOCATIONS = {
    '192.168.1.25': 'Building 6',
    '192.168.1.33': 'Canteen',
    '192.168.1.37': 'Lobby'
}

CHECKIN_TYPES = ['time in', 'check in', 'clock in', 'in', 'Time In', 'Check In']


# ==================== HTML PARSER ====================

class TableParser(HTMLParser):
    """Parse HTML tables to JSON"""
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


def parse_html_to_json(html_content: str) -> List[Dict]:
    """Convert HTML table to JSON"""
    parser = TableParser()
    parser.feed(html_content)
    
    json_data = []
    for row in parser.rows:
        if len(row) == len(parser.headers):
            record = {}
            for i, header in enumerate(parser.headers):
                clean_header = header.strip().lower().replace(' ', '_')
                value = row[i].strip()
                
                if value.isdigit():
                    record[clean_header] = int(value)
                elif _is_float(value):
                    record[clean_header] = float(value)
                else:
                    record[clean_header] = value
            
            json_data.append(record)
    
    return json_data


def _is_float(value: str) -> bool:
    """Check if string is float"""
    try:
        float(value)
        return '.' in value
    except ValueError:
        return False


# ==================== DATABASE HANDLER ====================

class AttendanceDB:
    """Handle attendance database operations"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    def connect(self):
        """Create database connection"""
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            raise Exception(f"Database connection error: {e}")
    
    def get_records_by_date(self, target_date: date, employee_identifier: str = None):
        """Get attendance records for a specific date"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            
            if employee_identifier:
                query = """
                    SELECT * FROM `raw` 
                    WHERE DATE(`timestamp`) = %s 
                    AND (
                        `employee_name` LIKE %s 
                        OR `employee_num` LIKE %s
                    )
                    ORDER BY `timestamp` ASC
                """
                search_pattern = f"%{employee_identifier}%"
                cursor.execute(query, (target_date, search_pattern, search_pattern))
            else:
                query = "SELECT * FROM `raw` WHERE DATE(`timestamp`) = %s ORDER BY `timestamp` ASC"
                cursor.execute(query, (target_date,))
            
            records = cursor.fetchall()
            return self._add_locations(records)
            
        finally:
            cursor.close()
            conn.close()
    
    def get_records_by_range(self, start_date: date, end_date: date, employee_identifier: str = None):
        """Get attendance records for date range"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            
            if employee_identifier:
                query = """
                    SELECT * FROM `raw` 
                    WHERE DATE(`timestamp`) BETWEEN %s AND %s 
                    AND (
                        `employee_name` LIKE %s 
                        OR `employee_num` LIKE %s
                    )
                    ORDER BY `timestamp` ASC
                """
                search_pattern = f"%{employee_identifier}%"
                cursor.execute(query, (start_date, end_date, search_pattern, search_pattern))
            else:
                query = """
                    SELECT * FROM `raw` 
                    WHERE DATE(`timestamp`) BETWEEN %s AND %s 
                    ORDER BY `timestamp` ASC
                """
                cursor.execute(query, (start_date, end_date))
            
            records = cursor.fetchall()
            return self._add_locations(records)
            
        finally:
            cursor.close()
            conn.close()
    
    def get_operators_present(self, target_date: date, start_time: time):
        """Get operators who clocked in after specific time"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT DISTINCT `employee_name`, `employee_num`, MIN(`timestamp`) as first_entry,
                       (SELECT `device_ip` FROM `raw` r2 
                        WHERE r2.`employee_num` = r1.`employee_num` 
                        AND DATE(r2.`timestamp`) = %s
                        AND TIME(r2.`timestamp`) >= %s
                        ORDER BY r2.`timestamp` ASC LIMIT 1) as device_ip
                FROM `raw` r1
                WHERE DATE(`timestamp`) = %s
                AND TIME(`timestamp`) >= %s
                AND `type` IN ({})
                GROUP BY `employee_name`, `employee_num`
                ORDER BY first_entry ASC
            """.format(','.join(['%s'] * len(CHECKIN_TYPES)))
            
            params = (target_date, start_time, target_date, start_time) + tuple(CHECKIN_TYPES)
            cursor.execute(query, params)
            operators = cursor.fetchall()
            return self._add_locations(operators)
            
        finally:
            cursor.close()
            conn.close()
    
    def get_all_employees(self):
        """Get all employees"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT DISTINCT employee_name, employee_num
                FROM `list`
                ORDER BY employee_name
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    
    def get_present_employees(self, target_date: date):
        """Get employees present on date"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT DISTINCT employee_name, employee_num
                FROM `raw`
                WHERE DATE(`timestamp`) = %s
            """, (target_date,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    
    def _add_locations(self, records):
        """Add location info to records"""
        for record in records:
            device_ip = record.get('device_ip', '')
            record['location'] = DEVICE_LOCATIONS.get(device_ip, device_ip)
        return records


# ==================== ACTIVITY API ====================

class ActivityAPI:
    """Handle activity API communication"""
    
    def __init__(self, api_url: str = ACTIVITY_API_URL):
        self.api_url = api_url
    
    def fetch_activities(self, timeout: int = 10) -> Dict:
        """Fetch activity data from API"""
        try:
            response = requests.get(
                self.api_url,
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
                    return {
                        'success': True,
                        'data': data if isinstance(data, list) else [data],
                        'timestamp': datetime.now().isoformat()
                    }
                except json.JSONDecodeError:
                    pass
            
            # Fall back to HTML parsing
            json_data = parse_html_to_json(response.text)
            if json_data:
                return {
                    'success': True,
                    'data': json_data,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'html'
                }
            else:
                return {
                    'success': False,
                    'error': 'No data found',
                    'message': 'Could not parse response'
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }


# ==================== DEEPSEEK AI ====================

class DeepSeekAnalyzer:
    """Use DeepSeek for intelligent query analysis and response generation"""
    
    def __init__(self, model: str = DEEPSEEK_MODEL):
        self.model = model
    
    def analyze_and_respond(self, user_question: str, context_data: Dict) -> str:
        """
        Use DeepSeek to analyze user question and generate intelligent response
        
        Args:
            user_question: The user's natural language question
            context_data: Dict containing relevant data (attendance, activities, etc.)
        """
        prompt = self._build_analysis_prompt(user_question, context_data)
        
        try:
            env = os.environ.copy()
            env['OLLAMA_NUM_GPU'] = '1'
            
            process = subprocess.Popen(
                ["ollama", "run", self.model],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env
            )
            
            timeout = 90 if "14b" in self.model else 60
            stdout, stderr = process.communicate(input=prompt, timeout=timeout)
            
            if process.returncode != 0:
                return "Error: Could not analyze the question."
            
            return self._clean_response(stdout.strip())
            
        except subprocess.TimeoutExpired:
            process.kill()
            return "⏱️ Analysis timeout. The question may be too complex."
        except FileNotFoundError:
            return "❌ DeepSeek (Ollama) is not running. Please start with 'ollama serve'"
        except Exception as e:
            return f"Error during analysis: {str(e)}"
    
    def _build_analysis_prompt(self, question: str, context_data: Dict) -> str:
        """Build comprehensive prompt for DeepSeek"""
        
        prompt = f"""You are an intelligent assistant analyzing employee attendance and activity data.

USER QUESTION: {question}

AVAILABLE DATA CONTEXT:
"""
        
        # Add attendance data if present
        if 'attendance_records' in context_data and context_data['attendance_records']:
            records = context_data['attendance_records']
            prompt += f"\nATTENDANCE RECORDS ({len(records)} total):\n"
            for i, record in enumerate(records[:10], 1):
                ts = record.get('timestamp', '')
                if isinstance(ts, datetime):
                    ts = ts.strftime('%Y-%m-%d %I:%M %p')
                prompt += f"{i}. {record.get('employee_name', 'Unknown')} ({record.get('employee_num', 'N/A')}) - {ts} - {record.get('location', 'Unknown')}\n"
            if len(records) > 10:
                prompt += f"... and {len(records) - 10} more records\n"
        
        # Add activity data if present
        if 'activities' in context_data and context_data['activities']:
            activities = context_data['activities']
            prompt += f"\nACTIVITY RECORDS ({len(activities)} total):\n"
            for i, activity in enumerate(activities[:10], 1):
                emp = activity.get('employee_name') or activity.get('operator') or activity.get('name', 'Unknown')
                prompt += f"{i}. {emp}"
                if 'customer' in activity:
                    prompt += f" - Customer: {activity['customer']}"
                if 'model' in activity:
                    prompt += f" - Model: {activity['model']}"
                if 'status' in activity:
                    prompt += f" - Status: {activity['status']}"
                prompt += "\n"
            if len(activities) > 10:
                prompt += f"... and {len(activities) - 10} more records\n"
        
        # Add summary statistics
        if 'stats' in context_data:
            stats = context_data['stats']
            prompt += f"\nSTATISTICS:\n"
            for key, value in stats.items():
                prompt += f"- {key}: {value}\n"
        
        prompt += """

INSTRUCTIONS:
1. Carefully analyze the user's question to understand their intent
2. Look at the provided data context
3. Answer the question directly and clearly
4. If asking "is [person] present?" answer YES or NO first, then explain
5. Use specific details from the data
6. Format your response in markdown for readability
7. If data is missing or insufficient, say so clearly
8. Be conversational and helpful

Your analysis and answer:"""
        
        return prompt
    
    def _clean_response(self, output: str) -> str:
        """Clean DeepSeek response"""
        clean = output
        
        # Remove thinking markers
        for start, end in [("Thinking...", "...done"), ("<think>", "</think>")]:
            if start in clean and end in clean:
                start_idx = clean.find(start)
                end_idx = clean.find(end) + len(end)
                clean = clean[:start_idx] + clean[end_idx:]
        
        clean = clean.replace("Thinking...", "").replace("<think>", "").replace("</think>", "")
        
        # Clean whitespace
        while "\n\n\n" in clean:
            clean = clean.replace("\n\n\n", "\n\n")
        
        return clean.lstrip(". \n").strip()


# ==================== UTILITY FUNCTIONS ====================

def filter_by_employee(data: List[Dict], employee_identifier: str) -> List[Dict]:
    """Filter by employee"""
    if not data:
        return []
    
    filtered = []
    search_term = employee_identifier.lower()
    
    for record in data:
        employee_fields = ['employee_name', 'name', 'employee', 'user', 'username',
                          'employee_id', 'user_id', 'operator', 'operator_name']
        
        for field in employee_fields:
            if field in record and record[field]:
                if search_term in str(record[field]).lower():
                    filtered.append(record)
                    break
    
    return filtered


def filter_by_date(data: List[Dict], target_date: date) -> List[Dict]:
    """Filter by date"""
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
                    if record_date and record_date == target_date:
                        filtered.append(record)
                        break
                except:
                    continue
    
    return filtered


def _parse_date(date_str: str) -> Optional[date]:
    """Parse date string"""
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
    except:
        pass
    
    for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y', '%d/%m/%Y']:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    
    return None


def calculate_stats(attendance_records: List[Dict], activities: List[Dict]) -> Dict:
    """Calculate summary statistics"""
    stats = {}
    
    if attendance_records:
        stats['total_attendance_records'] = len(attendance_records)
        unique_employees = set(r.get('employee_num') for r in attendance_records if r.get('employee_num'))
        stats['unique_employees_present'] = len(unique_employees)
    
    if activities:
        stats['total_activities'] = len(activities)
    
    return stats


# ==================== MCP SERVER ====================

server = Server("unified-intelligence-server")
attendance_db = AttendanceDB()
activity_api = ActivityAPI()
deepseek = DeepSeekAnalyzer()


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="ask_intelligent_question",
            description="Ask ANY question about attendance or activities. DeepSeek AI will analyze your question and provide intelligent answers. Use this for complex queries, natural language questions, or when you want detailed analysis. Examples: 'Is Ryan present today?', 'Show me who worked overtime this week', 'What are the most common activities?'",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Your question in natural language. Can be simple or complex."
                    },
                    "include_attendance": {
                        "type": "boolean",
                        "description": "Include attendance data in analysis (default: true)",
                        "default": True
                    },
                    "include_activities": {
                        "type": "boolean",
                        "description": "Include activity data in analysis (default: true)",
                        "default": True
                    },
                    "date_filter": {
                        "type": "string",
                        "description": "Optional: Filter data by date (YYYY-MM-DD format). Default: today"
                    },
                    "employee_filter": {
                        "type": "string",
                        "description": "Optional: Filter data by employee name or ID"
                    }
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="check_attendance",
            description="Check attendance records with optional filters. Returns raw attendance data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    },
                    "employee_identifier": {
                        "type": "string",
                        "description": "Optional: Employee name or ID to filter"
                    }
                }
            }
        ),
        Tool(
            name="get_activities",
            description="Get activity monitoring data with optional filters. Returns raw activity data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_identifier": {
                        "type": "string",
                        "description": "Optional: Filter by employee name or ID"
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional: Filter by date (YYYY-MM-DD)"
                    }
                }
            }
        ),
        Tool(
            name="count_present_operators",
            description="Count operators present after a specific time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Time in HH:MM format (default: 07:00)"
                    }
                }
            }
        ),
        Tool(
            name="get_absent_employees",
            description="Get list of employees who are absent on a specific date.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution"""
    
    try:
        if name == "ask_intelligent_question":
            return await handle_intelligent_question(arguments)
        
        elif name == "check_attendance":
            return await handle_check_attendance(arguments)
        
        elif name == "get_activities":
            return await handle_get_activities(arguments)
        
        elif name == "count_present_operators":
            return await handle_count_operators(arguments)
        
        elif name == "get_absent_employees":
            return await handle_absent_employees(arguments)
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_intelligent_question(arguments: dict) -> list[TextContent]:
    """Handle intelligent question with DeepSeek analysis"""
    question = arguments["question"]
    include_attendance = arguments.get("include_attendance", True)
    include_activities = arguments.get("include_activities", True)
    date_filter = arguments.get("date_filter")
    employee_filter = arguments.get("employee_filter")
    
    # Parse date filter
    target_date = date.today()
    if date_filter:
        try:
            target_date = date.fromisoformat(date_filter)
        except:
            pass
    
    # Gather context data
    context_data = {}
    
    # Fetch attendance data
    if include_attendance:
        attendance_records = attendance_db.get_records_by_date(target_date, employee_filter)
        context_data['attendance_records'] = attendance_records
    
    # Fetch activity data
    if include_activities:
        result = activity_api.fetch_activities()
        if result['success']:
            activities = result['data']
            
            # Apply filters
            if employee_filter:
                activities = filter_by_employee(activities, employee_filter)
            if date_filter:
                activities = filter_by_date(activities, target_date)
            
            context_data['activities'] = activities
    
    # Calculate statistics
    context_data['stats'] = calculate_stats(
        context_data.get('attendance_records', []),
        context_data.get('activities', [])
    )
    
    # Use DeepSeek to analyze and respond
    response = deepseek.analyze_and_respond(question, context_data)
    
    return [TextContent(type="text", text=response)]


async def handle_check_attendance(arguments: dict) -> list[TextContent]:
    """Handle attendance check"""
    target_date = date.today()
    if arguments.get("date"):
        target_date = date.fromisoformat(arguments["date"])
    
    employee_id = arguments.get("employee_identifier")
    
    records = attendance_db.get_records_by_date(target_date, employee_id)
    
    if not records:
        text = f"No attendance records found for {target_date}"
        if employee_id:
            text += f" for {employee_id}"
    else:
        text = f"# Attendance Records - {target_date}\n\n"
        text += f"Total records: {len(records)}\n\n"
        
        for i, record in enumerate(records[:50], 1):
            ts = record.get('timestamp', '')
            if isinstance(ts, datetime):
                ts = ts.strftime('%I:%M %p')
            text += f"{i}. **{record.get('employee_name')}** ({record.get('employee_num')})\n"
            text += f"   - Time: {ts}\n"
            text += f"   - Type: {record.get('type')}\n"
            text += f"   - Location: {record.get('location')}\n\n"
        
        if len(records) > 50:
            text += f"\n*Showing first 50 of {len(records)} records*"
    
    return [TextContent(type="text", text=text)]


async def handle_get_activities(arguments: dict) -> list[TextContent]:
    """Handle activity retrieval"""
    result = activity_api.fetch_activities()
    
    if not result['success']:
        text = f"❌ Activity API Error: {result.get('message', 'Unknown error')}"
        return [TextContent(type="text", text=text)]
    
    activities = result['data']
    
    # Apply filters
    if arguments.get("employee_identifier"):
        activities = filter_by_employee(activities, arguments["employee_identifier"])
    
    if arguments.get("date"):
        target_date = date.fromisoformat(arguments["date"])
        activities = filter_by_date(activities, target_date)
    
    if not activities:
        text = "No activities found matching the filters."
    else:
        text = f"# Activity Records\n\n"
        text += f"Total activities: {len(activities)}\n\n"
        
        for i, activity in enumerate(activities[:50], 1):
            emp = activity.get('employee_name') or activity.get('operator') or 'Unknown'
            text += f"{i}. **{emp}**\n"
            
            for key in ['customer', 'model', 'product', 'status', 'station', 'output']:
                if key in activity and activity[key]:
                    text += f"   - {key.title()}: {activity[key]}\n"
            text += "\n"
        
        if len(activities) > 50:
            text += f"\n*Showing first 50 of {len(activities)} activities*"
    
    return [TextContent(type="text", text=text)]


async def handle_count_operators(arguments: dict) -> list[TextContent]:
    """Handle operator counting"""
    target_date = date.today()
    if arguments.get("date"):
        target_date = date.fromisoformat(arguments["date"])
    
    start_time = time(7, 0)
    if arguments.get("start_time"):
        start_time = time.fromisoformat(arguments["start_time"])
    
    operators = attendance_db.get_operators_present(target_date, start_time)
    
    text = f"# Operators Present - {target_date}\n\n"
    text += f"Time threshold: After {start_time.strftime('%H:%M')}\n"
    text += f"**Total operators: {len(operators)}**\n\n"
    
    if operators:
        for i, op in enumerate(operators, 1):
            first_entry = op['first_entry']
            if isinstance(first_entry, datetime):
                first_entry = first_entry.strftime('%I:%M %p')
            text += f"{i}. {op['employee_name']} ({op['employee_num']}) - {first_entry} 📍 {op['location']}\n"
    else:
        text += "No operators clocked in after the specified time."
    
    return [TextContent(type="text", text=text)]


async def handle_absent_employees(arguments: dict) -> list[TextContent]:
    """Handle absent employee listing"""
    target_date = date.today()
    if arguments.get("date"):
        target_date = date.fromisoformat(arguments["date"])
    
    all_employees = attendance_db.get_all_employees()
    present_employees = attendance_db.get_present_employees(target_date)
    
    present_nums = {emp['employee_num'] for emp in present_employees}
    absent = [emp for emp in all_employees if emp['employee_num'] not in present_nums]
    
    text = f"# Absent Employees - {target_date}\n\n"
    text += f"Total employees: {len(all_employees)}\n"
    text += f"Present: {len(present_employees)}\n"
    text += f"**Absent: {len(absent)}**\n\n"
    
    if absent:
        for i, emp in enumerate(absent, 1):
            text += f"{i}. {emp['employee_name']} ({emp['employee_num']})\n"
    else:
        text += "✅ All employees are present!"
    
    return [TextContent(type="text", text=text)]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="unified-intelligence-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())