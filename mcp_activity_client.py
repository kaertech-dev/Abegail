import asyncio
import json
import re
from datetime import date, timedelta
from typing import Dict, Optional, List
from contextlib import asynccontextmanager
from date_parser import extractDate

from ai_handler import ask_general_question

# MCP Client imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class ActivityMCPClient:
    """Client to interact with Activity MCP Server"""
    
    def __init__(self, server_script_path: str = "c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/mcp_activity_server.py"):
        """
        Initialize MCP client
        
        Args:
            server_script_path: Path to the MCP server script
        """
        self.server_script_path = server_script_path
        # self.api = ActivityAPI(api_url)
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

    async def get_activity_summary(self, params: Dict):
        result = await self.session.call_tool('fetch_all_activity', params)
        return result.content[0].text if result.content else "No response"
    
    async def get_operator_data(self, params: Dict):
        result = await self.session.call_tool('fetch_operator_data', params)
        return result.content[0].text if result.content else "No response"
    
    async def get_aggregate_data(self, params: Dict):
        result = await self.session.call_tool('fetch_aggregate_data', params)
        return result.content[0].text if result.content else "No response"

class ActivityService:
    """Synchronous service wrapper for Flask"""
    
    def __init__(self, server_script_path: str = "c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/mcp_activity_server.py"):
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
            self._client = ActivityMCPClient(self.server_script_path)
            await self._client.connect()
    
    def get_activity_summary(self, params: Dict) -> str:
        async def _check():
            await self._ensure_connected()
            return await self._client.get_activity_summary(params)
        return self._run_async(_check())
    
    def get_operator_data(self, params: Dict) -> str:
        async def _check():
            await self._ensure_connected()
            return await self._client.get_operator_data(params)
        return self._run_async(_check())
    
    def get_aggregate_data(self, params: Dict) -> str:
        async def _check():
            await self._ensure_connected()
            return await self._client.get_aggregate_data(params)
        return self._run_async(_check())
    
    def cleanup(self):
        """Cleanup resources"""
        if self._client:
            async def _cleanup():
                await self._client.disconnect()
            self._run_async(_cleanup())
            self._client = None

# Singleton instance
_activity_service = None

def get_activity_service(server_script_path: str = "c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/mcp_activity_server.py") -> ActivityService:
    """Get singleton activity service"""
    global _activity_service
    if _activity_service is None:
        _activity_service = ActivityService(server_script_path)
    return _activity_service

def detect_activity_query(message: str) -> Optional[Dict]:
    """
    Detect if message is an activity query and extract parameters
    
    Returns:
        Dict with query type and parameters, or None if not an activity query
    """
    msg_lower = message.lower()

    activity_keywords = [
        'activity', 'activities', 'monitoring', 'where is',
        'what are they doing', 'who is doing', 'doing', 'working',
        'productivity', 'output', 'cycle time', 'target',
        'station', 'customer', 'model', 'operator'
    ]

    if not any(keyword in msg_lower for keyword in activity_keywords):
        return None
    
    query_info = {'type': None, 'params': {}}

    # 1. check for employee name and operator-specific parameter
    ops_patterns = {
        'average cycle time': r'(what is)?\s*([A-Za-z]+)\s+average cycle time',
        'total output': r'(what is)?\s*([A-Za-z]+)\s+total output',
        'cycle time': r'(what is)?\s*([A-Za-z]+)\s+cycle time',
        'start time': r'(what is)?\s*([A-Za-z]+)\s+start',
        'end time': r'(what is)?\s*([A-Za-z]+)\s+end',
        'output': r'(what is)?\s*([A-Za-z]+)\s+output',
        'status': r'(what is)?\s*([A-Za-z]+)\s+status',
        'where': r'(where is)\s*([A-Za-z]+)\s*',
        'station': r'(what station is)\s*([A-Za-z]+)\s*'
    }
    for kw, pattern in ops_patterns.items():
        if kw in msg_lower:
            name_match = re.search(pattern, msg_lower)
            if name_match:
                # query has name and operator stat
                query_info['params']['emp_id'] = name_match.group(2)
                query_info['params']['stats'] = kw
                query_info['type'] = 'operator_data'
            else:
                # query has operator stat but no name
                query_info['params']['stats'] = kw
                query_info['type'] = 'aggregate_data'
            break
    
    empnum_pattern = r'\s*(KE\d{4})\s*'
    empnum_match = re.search(empnum_pattern, message)
    if empnum_match:
        query_info['params']['emp_id'] = empnum_match.group(1)

    # 2. check for general parameters: customer, model, or station
    customer_find = r'customer ([A-Za-z]+)'
    model_find = r'model ([A-Za-z0-9]+)'
    station_find = r'([A-Za-z0-9]+) station'

    c_match = re.search(customer_find, msg_lower)
    if c_match:
        query_info['params']['customer'] = c_match.group(1)

    m_match = re.search(model_find, msg_lower)
    if m_match:
        query_info['params']['model'] = m_match.group(1)

    s_match = re.search(station_find, msg_lower)
    if s_match:
        query_info['params']['station'] = s_match.group(1)
    
    agg_keywords = [
        'who is at',
        'who is working',
        'who are working',
        'list operator',
        'list of operator'
    ]

    if not query_info['type'] and any([c_match, m_match, s_match]):
        # query has general parameter, but no name or operator-specific parameter
        if any(kw in msg_lower for kw in agg_keywords):
            query_info['type'] = 'aggregate_data'

    # 3. check for summary keywords
    summary_patterns = [
        r'\s*([A-Za-z]+)\s+activity',
        r'activity for\s+([A-Za-z]+)',
        r'is\s+([A-Za-z]+)\s+doing',
        r'is\s+([A-Za-z]+)\s+working on'
    ]

    for sp in summary_patterns:
        summary_match = re.search(sp, msg_lower)
        if summary_match:
            # query is looking for operator-specific summary
            query_info['params']['emp_id'] = summary_match.group(1)
            query_info['params']['stats'] = 'all'
            query_info['type'] = 'operator_data' 
            break

    summary_keywords = [
        'show all',
        'summary',
        'ongoing'
    ]
    
    if not query_info['type'] and any(kw in msg_lower for kw in summary_keywords):
        # query is looking for overall summary
        query_info['type'] = 'all_data'
    
    # 4. check for date/s
    today = date.today()
    date_results = extractDate(msg_lower)
    if len(date_results) == 1:
        query_info['params']['date'] = date_results[0]
    elif len(date_results) > 1:
        query_info['params']['date'] = date_results[0]
        query_info['params']['end_date'] = date_results[1]
    else:
        # no explicit date was given, assume today
        query_info['params']['date'] = today.isoformat()
    
    return query_info if query_info['type'] else None

def handle_activity_query_via_mcp(message: str) -> Optional[str]:
    """
    Handle activity query through MCP server
    
    Args:
        message: User's message
        
    Returns:
        Response string, or None if not an activity query
    """
    query_info = detect_activity_query(message)
    
    if not query_info:
        return None
    
    # analysis = {'primary_intent': 'activity', 
    #             'question_type': 'quantitative', 
    #             'temporal_context': {'has_time_reference': 1, 'specific_date': '2026-01-28'},
    #             'entities': {}}
    # deepsought = ask_general_question(question=message, query_analysis=analysis)
    # print(deepsought)
    
    try:
        service = get_activity_service()
        query_type = query_info['type']
        params = query_info['params']

        match query_type:
            case 'all_data':
                handler_response = service.get_activity_summary(params)
            case 'operator_data':
                handler_response = service.get_operator_data(params)
            case 'aggregate_data':
                handler_response = service.get_aggregate_data(params)
            case _:
                err = 'Cannot parse the input. Please refine your query or be more specific.'
                return {'answer': err, 'response_type': 'activity'}
        
        return {'answer': handler_response, 'response_type': 'activity'}
    
    except Exception as e:
        return f"❌ **Activity Query Error:** {str(e)}\n\nPlease check if the MCP server is running."