import asyncio
import spacy
from typing import List, Dict, Optional
from date_parser import extractDate

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

nlp = spacy.load("en_core_web_md")

server_list = {'attendance-MCP-server': './mcp_attendance_server.py', 
               'activity-MCP-server': './mcp_activity_server.py'}

class GeneralMCPClient:
    """Parent Class for all MCP Clients"""
    
    def __init__(self):
        """
        Initialize MCP client
        
        Args:
            server_script_path: Path to the MCP server script
        """
        # self.server_script_path = server_path
        self.session = None
        self.read_stream = None
        self.write_stream = None
        self._client_context = None
        self.available_tools = []
    
    async def connect(self):
        """Connect to the MCP server"""
        for server_path in server_list.values():
            server_params = StdioServerParameters(
                command="python",
                args=[server_path],
                env=None
            )
            
            self._client_context = stdio_client(server_params)
            self.read_stream, self.write_stream = await self._client_context.__aenter__()
            self.session = ClientSession(self.read_stream, self.write_stream)
            await self.session.__aenter__()
            await self.session.initialize()
            list_tool = await self.session.list_tools()
            self.available_tools.extend({tool.name : tool.description} for tool in list_tool)
        
        print(self.available_tools)
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self._client_context:
            await self._client_context.__aexit__(None, None, None)

class SyncWrapper:
    def __init__(self):
        self._client = None
        self._loop = None

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
            self._client = GeneralMCPClient()
        await self._client.connect()
    
    def cleanup(self):
        """Cleanup resources"""
        if self._client:
            async def _cleanup():
                await self._client.disconnect()
            self._run_async(_cleanup())
            self._client = None
    
    def query_processor(message: str):
        query_type = None
        emp_id = None
        ner_not_person = []

        date_input = extractDate(message.lower())[0]
        processed = nlp(message)
        for ent in processed.ents:
            if ent.label_ == 'PERSON':
                emp_id = ent.text
            elif ent.label_ == 'ORG':
                ner_not_person.append(ent.text)
        
        activity_keywords = [
            'activity', 'activities', 'monitoring', 'where is',
            'what are they doing', 'who is doing', 'doing', 'working',
            'productivity', 'output', 'cycle time', 'target', 'start time', 'end time',
            'station', 'customer', 'model', 'operator'
        ]

        for kw in activity_keywords:
            if kw in message.lower():
                query_type = 'activity'
                break

        attendance_keywords = [
            'attendance', 'present', 'absent', 'time in', 'clock in', 'check in', 
            'who is here', 'who is in', 
            'department', 'headcount', 'employee', 'employees',
            'timeout', 'time out', 'clock out'
        ]

        for kw in attendance_keywords:
            if kw in message.lower():
                query_type = 'attendance'
                break
        
        if query_type is None:
            query_type = 'general'

    def ai_handler():
        pass

# Singleton instance
_client_wrapper = None
def get_sync_wrapper():
    global _client_wrapper
    if _client_wrapper is None:
        _client_wrapper = SyncWrapper()
    return _client_wrapper
    