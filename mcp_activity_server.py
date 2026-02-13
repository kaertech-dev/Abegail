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

path_name = './csv_files/'

def std_name(records: list) -> list:
    for rec in records:
        l_name = rec['Operator'].split(',')
        if len(l_name) > 1:
            rec['Operator'] = l_name[1].strip() + ' ' + l_name[0]
        else:
            pass
    
    return records

def format_entry(entry: dict, filter: str) -> str:
    if filter == 'all':
        text = f"**{entry['Station']}** - {entry['Model']} ({entry['Customer']}) \n\n"
        text += f"   -  **Start Time:** {entry['Start Time']}   **End Time:** {entry['End time']}\n\n"
        text += f"   -  **Cycle Time:** {entry['Cycle Time(s)']}   **Output:** {entry['Output']}\n\n"
        text += f"   -  **Target:** {entry['Target(s)']}   **Status:** {entry['Status']}\n\n"

    elif filter == 'where':
        text = f"**{entry['Station']}** - {entry['Model']} ({entry['Customer']}) \n\n"
        text += f"   -  *Start Time* - {entry['Start Time']}   *End Time* - {entry['End time']}\n\n"
    
    elif filter == 'cycle time' or filter == 'target':
        text = f"**{entry['Station']}** - {entry['Model']} ({entry['Customer']}) \n\n"
        text += f"   -  *Cycle Time* - {entry['Cycle Time(s)']}   *Target* - {entry['Target(s)']} \n\n"
    
    else:
        key = filter.capitalize() if filter == 'end time' else filter.title()
        text = f"**{entry['Station']}** - {entry['Model']} ({entry['Customer']}) \n\n"
        text += f"   -  *{filter.title()}* - {entry[key]} \n\n"
    
    return text

# ==================== API CLASS ====================

ACTIVITY_API_URL = os.getenv('ACTIVITY_API_URL', 'http://localhost/activity/api/operator_today')

class ActivityAPI:
    def __init__(self, api_url: Optional[str] = None):
            if api_url is None:
                api_url = ACTIVITY_API_URL
            
            self.activity_endpoint = api_url
    
    def get_all_data(self, date_suffix: str, timeout: int = 10) -> Dict:
        """
        Fetch activity data from API
        Returns: Dict with activity data or error info
        """
        api_url = self.activity_endpoint + date_suffix
        try:
            response = requests.get(
                api_url, 
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
    start_date = arguments.get('date')
    end_date = arguments.get('end_date')
    customer = arguments.get('customer')
    model = arguments.get('model')
    station = arguments.get('station')

    # prepare csv file for writing
    filename = 'activity_summary_' + start_date + '.csv'
    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csvfile, fieldnames=['Customer', 'Model', 'Station', 'Operator', 'Output', 'Cycle Time(s)', 'Target(s)', 'Start Time', 'End time', 'Status'], extrasaction='ignore')
    writer.writeheader()

    text = ''
    if end_date:
        api_date = f'?start_date={start_date}&end_date={end_date}'
        text = filename + f"# Activity Summary from {start_date} to {end_date}\n\n"
    else:
        api_date = f'?start_date={start_date}&end_date={start_date}'
        text = filename + f"# Activity Summary for {start_date}\n\n"

    success = False
    while not success:
        result = activityServer.get_all_data(api_date)
        success = result['success']

    if not result.get('data'):
        return [TextContent(type="text", text="## No records found.")]
    records = std_name(result['data']['records'])
    # text = str(records)
    # return [TextContent(type="text", text=text)]

    if customer:
        filtered = [r for r in records if r['Customer'].upper()==customer.upper()]
        records = filtered

    if model:
        filtered = [r for r in records if r['Model'].upper()==model.upper()]
        records = filtered
    
    if station:
        filtered = [r for r in records if r['Station'].upper()==station.upper()]
        records = filtered
    
    model_list = {r['Model'] for r in records}
    if len(records) == 0:
        return [TextContent(type="text", text="## No records found.")]
    
    text += f"Total activities: {len(records)}\n\n"
    
    # probably turn into a table???
    for curr_model in model_list:
        text += f"## {curr_model}\n\n"
        ctr = 1
        for e in records:
            if e['Model'] == curr_model:
                text += f"{ctr}. **{e['Operator']}** ({e['operator_code']}) - {e['Station']}\n\n"
                text += f"   -  **Start Time:** {e['Start Time']}   **End Time:** {e['End time']}\n\n"
                text += f"   -  **Cycle Time:** {e['Cycle Time(s)']}s   **Output:** {e['Output']}\n\n"
                text += f"   -  **Target:**  {e['Target(s)']}s   **Status:** {e['Status']}\n\n"
                ctr += 1
                writer.writerow(e)
    
    return [TextContent(type="text", text=text)]

# def get_status(cycle_time: str, target: str) -> str:
#     if cycle_time == '-':
#         return 'ON TARGET'
    
#     if float(cycle_time) <= float(target):
#         return 'ON TARGET'
#     elif float(cycle_time) < float(target)*1.1:
#         return 'ORANGE TARGET'
#     else:
#         return 'BELOW TARGET'

async def handle_operator_data(arguments: dict) -> list[TextContent]:
    start_date = arguments.get('date')
    end_date = arguments.get('end_date')
    emp_id = arguments.get('emp_id')
    stats = arguments.get('stats')
    customer = arguments.get('customer', '')
    model = arguments.get('model', '')
    station = arguments.get('station', '')

    if end_date:
        api_date = f'?start_date={start_date}&end_date={end_date}'
    else:
        api_date = f'?start_date={start_date}&end_date={start_date}'

    success = False
    while not success:
        result = activityServer.get_all_data(api_date)
        success = result['success']
    
    records = std_name(result['data']['records'])

    # filter the records by employee name/number
    emp_records = []
    for r in records:
        if emp_id.lower() in r['Operator'].lower() or emp_id == r['operator_code']:
            emp_records.append(r)
    
    if len(emp_records) == 0:
        err_text = f"## No matches for {emp_id.title()} in the Monitoring System.\n\n"
        return [TextContent(type="text", text=err_text)]
    records = emp_records
    
    # filter the employee records if there was an input customer, model, or station
    if customer:
        filtered = [r for r in records if r['Customer'].upper()==customer.upper()]
        records = filtered

    if model:
        filtered = [r for r in records if r['Model'].upper()==model.upper()]
        records = filtered
    
    if station:
        filtered = [r for r in records if r['Station'].upper()==station.upper()]
        records = filtered
    
    if len(records) == 0:
        err_text = f"## {emp_id.title()} has no such activity reflected in the Monitoring System.\n\n"
        return [TextContent(type="text", text=err_text)]
    
    # set header text
    text = f"# Activity Summary for {emp_id.title()}\n\n"
    if end_date:
        text += f"**Date:** {start_date} to {end_date}\n\n"
    else:
        text += f"**Date:** {start_date}\n\n"
    
    if stats == 'where':
        if start_date == date.today().isoformat():
            text = f"## {emp_id.title()} is currently working at these station/s:\n\n"
        else:
            text = f"## {emp_id.title()} was working at these station/s on {start_date}:\n\n"

    for i, entry in enumerate(records, 1):
        if i == 1 and stats != 'where':
            text += f"**Operator:** {entry['Operator']} ({entry['operator_code']})\n\n"
        text += f"{i}. "
        text += format_entry(entry, stats)

    return [TextContent(type="text", text=text)]

async def handle_aggregate_data(arguments: dict) -> list[TextContent]:
    start_date = arguments.get('date')
    end_date = arguments.get('end_date')
    stats = arguments.get('stats', '')
    customer = arguments.get('customer', '')
    model = arguments.get('model', '')
    station = arguments.get('station', '')
    
    if end_date:
        api_date = f'?start_date={start_date}&end_date={end_date}'
    else:
        api_date = f'?start_date={start_date}&end_date={start_date}'

    success = False
    while not success:
        result = activityServer.get_all_data(api_date)
        success = result['success']
    
    records = std_name(result['data']['records'])

    if customer:
        filtered = [r for r in records if r['Customer'].upper()==customer.upper()]
        records = filtered

    if model:
        filtered = [r for r in records if r['Model'].upper()==model.upper()]
        records = filtered
    
    if station:
        filtered = [r for r in records if r['Station'].upper()==station.upper()]
        records = filtered
        # text = str(records)
        # return [TextContent(type="text", text=text)]
    
    model_list = {r['Model'].upper() for r in records}
    station_list = {r['Station'].upper() for r in records if r['Model'].upper()==model.upper()}

    if model and model.upper() not in model_list:
        # return [TextContent(type="text", text='## No such model in Activity Monitoring.\n\n')]
        return [TextContent(type="text", text=str(model_list))]
    
    if stats == 'list_stn':
        text = f" # List of Stations for {model.upper()}\n\n"
        for i, stn in enumerate(station_list,1):
            text += f"{i}. {stn}\n\n"
        return [TextContent(type="text", text=text)]

    if stats == 'list_ops':
        text = " # List of Operators"
    else:
        text = f" # Showing {stats.title()}s"
    
    if station:
        text += f" at {station.upper()} station"
    if model:
        text += f" on {model.upper()}"
    text += "\n\n"
    if end_date:
        text += f"**Date:** {start_date} to {end_date} "
    else:
        text += f"**Date:** {start_date} "
    text += f"**Count:** {len(records)}\n\n"

    if stats == 'cycle time' or stats == 'target':
        key = stats.title() + '(s)'
    elif stats == 'end time':
        key = stats.capitalize()
    else:
        key = stats.title()

    for i, rec in enumerate(records, 1):
        if stats == 'list_ops':
            text += f"{i}.  **{rec['Operator']}** ({rec['operator_code']}) - {rec['Model']}\n\n"
            text += f"   -  {rec['Station']} - **Output:** {rec['Output']} **Status:** {rec['Status']}\n\n"
        else:
            text += f"{i}.  **{rec['Operator']}** ({rec['operator_code']}) - {rec['Station']}\n\n"
            text += f"   -  **{stats.title()}:** {rec[key]} \n\n"

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