import asyncio
from contextlib import AsyncExitStack

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_list = {'attendance-MCP-server': './mcp_attendance_server.py', 
               'activity-MCP-server': './mcp_activity_server.py'}

class UnifiedMCPClient:
    def __init__(self):
        """Initialize MCP client"""
        self.exit_stack = AsyncExitStack()
        self.sessions = {}
        self.read_stream = None
        self.write_stream = None
        self._client_context = None
        self.available_tools = []

    async def connect(self, server_path):
        """Connect to MCP servers"""
        for server_name, server_path in server_list.items():
            server_params = StdioServerParameters(
                command="python",
                args=[server_path],
                env=None
            )
            
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params))
            self.read_stream, self.write_stream = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(self.read_stream, self.write_stream))
            await session.initialize()

            response = await session.list_tools()
            for tool in response.tools:
                self.sessions[tool.name] = session
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })

    async def disconnect(self):
        """Clean up resources and close all connections."""
        await self.exit_stack.aclose()
    
    async def execute_tool(self, tool_name, args):
        """Execute an MCP tool directly with given arguments."""
        session = self.sessions.get(tool_name)
        if not session:
            # print(f"Tool '{tool_name}' not found.")
            return
        
        try:
            result = await session.call_tool(tool_name, arguments=args)
            # print(f"\nTool '{tool_name}' result:")
            # print(result.content)
        except Exception as e:
            print(f"Error executing tool: {e}")
            # traceback.print_exc()

# async def main():
#     """Main entry point for the MCP ChatBot application."""
#     chatbot = UnifiedMCPClient()
#     try:
#         await chatbot.connect_to_servers()
#         # await chatbot.chat_loop()
#     finally:
#         await chatbot.cleanup()


# if __name__ == "__main__":
#     asyncio.run(main())

class SyncWrapper:
    def __init__(self):
        self._client = UnifiedMCPClient()
        self._client.connect()
        self._loop = ()

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
        await self._client.connect()
    
    def cleanup(self):
        """Cleanup resources"""
        if self._client:
            async def _cleanup():
                await self._client.disconnect()
            self._run_async(_cleanup())
            self._client = None
    
    def query_processor():
        pass

    def ai_handler():
        pass

# Singleton instance
_client_wrapper = None
def get_sync_wrapper():
    global _client_wrapper
    if _client_wrapper is None:
        _client_wrapper = SyncWrapper()
    return _client_wrapper
    