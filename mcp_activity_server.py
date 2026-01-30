#!/usr/bin/env python3
"""
Activity MCP Server
Provides activity tracking and querying capabilities via MCP protocol
"""

import asyncio
import json
import csv
import os
import requests
from datetime import datetime, date, time, timedelta
from typing import Any, List, Dict, Optional
from html_parser import parse_html_to_json
from formatter import format_activity_response

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

ACTIVITY_API_URL = os.getenv('ACTIVITY_API_URL', 'http://localhost/activity/api/operator_today')

class ActivityAPI:
    def __init__(self, api_url: Optional[str] = None):
            if api_url is None:
                api_url = ACTIVITY_API_URL
            
            self.activity_endpoint = api_url
    
    def get_all_data(self, timeout: int = 10) -> Dict:
        """
        Fetch activity data from API
        Returns: Dict with activity data or error info
        """
        try:
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
                result = self._parse_json_response(response)
                if result:
                    return result
            
            # Fall back to HTML parsing
            return self._parse_html_response(response)
            
        except requests.exceptions.Timeout:
            return self._build_error('Request timeout', 
                f'API at {self.activity_endpoint} took too long to respond (>{timeout}s)')
        
        except requests.exceptions.ConnectionError:
            return self._build_error('Connection error',
                f'Could not connect to {self.activity_endpoint}. Is the server running?')
        
        except requests.exceptions.HTTPError as e:
            return self._build_error('HTTP error',
                f'API returned error: {e.response.status_code}',
                e.response.text[:500] if hasattr(e.response, 'text') else None)
        
        except Exception as e:
            return self._build_error('Unknown error', str(e))
    
    def _parse_json_response(self, response) -> Optional[Dict]:
        """Parse JSON response"""
        try:
            data = response.json()
            return {
                'success': True,
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'count': len(data) if isinstance(data, list) else 1
            }
        except json.JSONDecodeError as e:
            return None
    
    def _parse_html_response(self, response) -> Dict:
        """Parse HTML response"""
        html_content = response.text
        json_data = parse_html_to_json(html_content)
        
        if json_data:
            return {
                'success': True,
                'data': json_data,
                'timestamp': datetime.now().isoformat(),
                'count': len(json_data),
                'source': 'html'
            }
        else:
            return self._build_error('No data found',
                'Could not parse data from HTML table or JSON',
                response.text[:500])
    
    def _build_error(self, error: str, message: str, raw_response: str = None) -> Dict:
        """Build error response"""
        result = {
            'success': False,
            'error': error,
            'message': message,
            'tried_url': self.activity_endpoint
        }
        if raw_response:
            result['raw_response'] = raw_response
        return result

# ==================== MCP SERVER ====================

server = Server('activity-server')
activityServer = ActivityAPI()

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available activity tools"""
    return [
        Tool(
            name="fetch_all_activity",
            description="Get all activity records for a specific date.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (None if not date range)"
                    },
                    "customer": {
                        "type": "string",
                        "description": "Name of customer"
                    },
                    "model": {
                        "type": "string",
                        "description": "Name of model"
                    },
                    "station": {
                        "type": "string",
                        "description": "Name of station"
                    }
                }
            }
        ),
        Tool(
            name="fetch_operator_data",
            description="Get activity records for the specified employee on a specific date or date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (None if not date range)"
                    },
                    "employee_id": {
                        "type": "string",
                        "description": "Employee identifer, either a name or employee number"
                    },
                    "stats": {
                        "type": "string",
                        "description": "Operator-specific parameter being queried"
                    },
                    "customer": {
                        "type": "string",
                        "description": "Name of customer"
                    },
                    "model": {
                        "type": "string",
                        "description": "Name of model"
                    },
                    "station": {
                        "type": "string",
                        "description": "Name of station"
                    }
                }
            }
        ),
        Tool(
            name="fetch_aggregate_data",
            description="Get activity records for the given customer, model, or station.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (None if not date range)"
                    },
                    "stats": {
                        "type": "string",
                        "description": "Operator-specific parameter being queried"
                    },
                    "customer": {
                        "type": "string",
                        "description": "Name of customer"
                    },
                    "model": {
                        "type": "string",
                        "description": "Name of model"
                    },
                    "station": {
                        "type": "string",
                        "description": "Name of station"
                    }
                }
            }
        )
    ]


# ==================== TOOL ENDPOINT ====================

@server.call_tool()
async def tool_handler(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == 'fetch_all_activity':
            return await handle_fetch_all(arguments)
        elif name == 'fetch_operator_data':
            return await handle_operator_data(arguments)
        elif name == 'fetch_aggregate_data':
            return await handle_aggregate_data(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
        
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]

async def handle_fetch_all(arguments: dict) -> list[TextContent]:
    # start_date = arguments.get('date')
    # end_date = arguments.get('end_date')
    customer = arguments.get('customer')
    model = arguments.get('model')
    # station = arguments.get('station')

    result = activityServer.get_all_data()
    records = result['data']['records']
    if model:
        model_list = {(r['Model'], r['Customer']) for r in records if r['Model']==model.upper()}
    elif customer:
        model_list = {(r['Model'], r['Customer']) for r in records if r['Customer']==customer.upper()}
    else:
        model_list = {(r['Model'], r['Customer']) for r in records}
    
    # probably make a separate function that takes a dictionary and strings to filter entries
    text = f"# Activity Summary for {date.today()}\n\n"
    for curr_model in model_list:
        text += f"## {curr_model[0]} ({curr_model[1]})\n\n"
        ctr = 1
        for e in records:
            if e['Model'] == curr_model[0]:
                text += f"{ctr}. **{e['Operator']}** ({e['Station']})\n\n"
                text += f"   -  *Start Time:* {e['Start Time']} *End Time:* {e['End time']}\n\n"
                text += f"   -  *Cycle Time:* {e['Cycle Time(s)']} *Output:* {e['Output']}\n\n"
                text += f"   -  *Target:*  {e['Target(s)']} *Status:* {e['Status']}\n\n"
                ctr += 1
    
    return [TextContent(type="text", text=text)]

async def handle_operator_data(arguments: dict) -> list[TextContent]:
    start_date = arguments.get('date')
    end_date = arguments.get('end_date')
    emp_id = arguments.get('emp_id')
    stats = arguments.get('stats')
    customer = arguments.get('customer')
    model = arguments.get('model')
    station = arguments.get('station')

    result = activityServer.get_all_data()
    records = result['data']['records']
    
    text = f"# Activities for {emp_id.title()}\n\n" if emp_id else ''
    for e in records:
        if emp_id in e['Operator'].lower() or emp_id == e['operator_code']:
            if stats == 'all':
                text += f"**{e['Station']}**\n\n"
                text += f"   -  *Start Time:* {e['Start Time']} *End Time:* {e['End time']}\n\n"
                text += f"   -  *Cycle Time:* {e['Cycle Time(s)']} *Output:* {e['Output']}\n\n"
                text += f"   -  *Target:*  {e['Target(s)']} *Status:* {e['Status']}\n\n"

    return [TextContent(type="text", text=text)]

async def handle_aggregate_data(arguments: dict) -> list[TextContent]:
    start_date = arguments.get('date')
    end_date = arguments.get('end_date')
    stats = arguments.get('stats')
    customer = arguments.get('customer')
    model = arguments.get('model')
    station = arguments.get('station')
    
    # result = activityServer.get_all_data()

    # if not result['success']:
    #     text = f"{result['error']}\n {result['message']}\n"
    #     return [TextContent(type="text", text=text)]
    
    text = 'aggregate data  '

    return [TextContent(type="text", text=text)]


# ==================== MAIN ====================

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="activity-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())