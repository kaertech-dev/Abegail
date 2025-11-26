"""
MCP Client - Direct connector to your FastMCP server
Fixed to properly pass API base URL to MCP server
"""
import asyncio
import json
from typing import Optional, Dict, Any
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import config to get API URL
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import MCP_SERVER_URL
except ImportError:
    MCP_SERVER_URL = "http://localhost/activity"

# Path to your MCP server script
MCP_SERVER_PATH = r"C:\Users\ai\Documents\project_abegail\mcp-server-demo\mcp.py"

# Global session and context management
_mcp_session: Optional[ClientSession] = None
_mcp_initialized = False
_exit_stack: Optional[AsyncExitStack] = None


async def initialize_mcp():
    """
    Initialize connection to MCP server with proper API URL
    """
    global _mcp_session, _mcp_initialized, _exit_stack
    
    if _mcp_initialized and _mcp_session:
        return True
    
    try:
        # Create exit stack for context management
        _exit_stack = AsyncExitStack()
        
        # Server parameters with environment variable for API URL
        server_params = StdioServerParameters(
            command="python",
            args=[MCP_SERVER_PATH],
            env={
                "API_BASE_URL": MCP_SERVER_URL,  # Pass API URL to MCP server
                **os.environ.copy()  # Keep other env vars
            }
        )
        
        print(f"🔗 Connecting to MCP server...")
        print(f"   Script: {MCP_SERVER_PATH}")
        print(f"   API URL: {MCP_SERVER_URL}")
        
        # Create stdio client using context manager properly
        read, write = await _exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        
        # Create session
        _mcp_session = ClientSession(read, write)
        
        # Initialize session
        await _mcp_session.initialize()
        
        _mcp_initialized = True
        print("✅ MCP Server connected successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to MCP server: {str(e)}")
        import traceback
        traceback.print_exc()
        _mcp_initialized = False
        
        # Clean up on failure
        if _exit_stack:
            await _exit_stack.aclose()
            _exit_stack = None
        
        return False


async def call_mcp_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Call an MCP tool directly through the protocol
    
    Args:
        tool_name: Name of the tool (get_data_from_api, get_download_url, etc.)
        **kwargs: Tool parameters
        
    Returns:
        dict: Tool result with success status and data
    """
    global _mcp_session, _mcp_initialized
    
    # Initialize if needed
    if not _mcp_initialized:
        success = await initialize_mcp()
        if not success:
            return {
                "success": False,
                "error": "Failed to initialize MCP connection. Check if MCP server script exists and API is accessible."
            }
    
    try:
        print(f"🔧 Calling MCP tool: {tool_name}")
        print(f"   Parameters: {kwargs}")
        
        # Call the tool
        result = await _mcp_session.call_tool(tool_name, kwargs)
        
        # Parse result
        if result.content and len(result.content) > 0:
            content = result.content[0]
            
            # Extract text content
            if hasattr(content, 'text'):
                response_text = content.text
                
                # Try to parse as JSON
                try:
                    data = json.loads(response_text)
                    print(f"✅ Tool call successful")
                    return {
                        "success": True,
                        "data": data,
                        "tool": tool_name
                    }
                except json.JSONDecodeError:
                    # Return as plain text
                    print(f"✅ Tool call successful (plain text)")
                    return {
                        "success": True,
                        "data": response_text,
                        "tool": tool_name
                    }
        
        print(f"⚠️ No content in tool response")
        return {
            "success": False,
            "error": "No content in response",
            "tool": tool_name
        }
        
    except Exception as e:
        print(f"❌ MCP Tool Error ({tool_name}): {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Tool call failed: {str(e)}",
            "tool": tool_name
        }


async def list_available_tools() -> Dict[str, Any]:
    """
    List all available tools from MCP server
    """
    global _mcp_session, _mcp_initialized
    
    if not _mcp_initialized:
        success = await initialize_mcp()
        if not success:
            return {
                "success": False,
                "error": "Failed to initialize MCP"
            }
    
    try:
        tools = await _mcp_session.list_tools()
        return {
            "success": True,
            "tools": [
                {
                    "name": tool.name, 
                    "description": tool.description
                } 
                for tool in tools.tools
            ]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def get_production_data(endpoint: str = "/api/operator_today") -> Dict[str, Any]:
    """
    Convenience function to get production data
    Full URL will be: {MCP_SERVER_URL}{endpoint}
    """
    print(f"📊 Fetching production data from: {MCP_SERVER_URL}{endpoint}")
    return await call_mcp_tool("get_data_from_api", endpoint=endpoint)


async def get_download_url(
    format_type: str = "csv",
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to get download URL
    """
    params = {"format": format_type}
    if date:
        params["date"] = date
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    return await call_mcp_tool("get_download_url", **params)


async def query_deepseek(prompt: str, max_tokens: int = 150) -> Dict[str, Any]:
    """
    Query DeepSeek through MCP server
    """
    return await call_mcp_tool("deepseek_query", prompt=prompt, max_tokens=max_tokens)


async def cleanup():
    """
    Clean up MCP connection
    """
    global _mcp_session, _mcp_initialized, _exit_stack
    
    if _exit_stack:
        try:
            await _exit_stack.aclose()
            _mcp_initialized = False
            _mcp_session = None
            _exit_stack = None
            print("✅ MCP connection closed")
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")


# Test function with detailed diagnostics
async def test_mcp_connection():
    """
    Test MCP server connection and tools with diagnostics
    """
    print("🧪 Testing MCP Connection...\n")
    print(f"📍 Configuration:")
    print(f"   API URL: {MCP_SERVER_URL}")
    print(f"   MCP Script: {MCP_SERVER_PATH}")
    print(f"   Script exists: {os.path.exists(MCP_SERVER_PATH)}")
    print()
    
    try:
        # Initialize
        print("1️⃣ Initializing MCP server...")
        success = await initialize_mcp()
        
        if not success:
            print("❌ Failed to initialize MCP server")
            print("   Check:")
            print("   1. Does mcp.py exist at the specified path?")
            print("   2. Is the API server running at http://192.168.0.12:5005?")
            print("   3. Can you ping 192.168.0.12?")
            return
        
        # List tools
        print("\n2️⃣ Listing available tools...")
        tools = await list_available_tools()
        if tools["success"]:
            print(f"✅ Found {len(tools['tools'])} tools:")
            for tool in tools['tools']:
                print(f"   - {tool['name']}: {tool['description'][:80]}...")
        else:
            print(f"❌ Failed to list tools: {tools.get('error')}")
        
        # Test production data (THIS IS THE KEY TEST)
        print("\n3️⃣ Testing production data retrieval...")
        print(f"   Will fetch: {MCP_SERVER_URL}/api/operator_today")
        result = await get_production_data()
        if result["success"]:
            print(f"✅ Production data retrieved successfully")
            print(f"   Data preview: {str(result['data'])[:200]}...")
        else:
            print(f"❌ Failed: {result['error']}")
            print("   This means:")
            print("   - MCP server couldn't reach your API")
            print("   - Check if API is accessible from the machine running this script")
        
        # Test download URL
        print("\n4️⃣ Testing download URL generation...")
        result = await get_download_url(format_type="excel")
        if result["success"]:
            print(f"✅ Download URL generated successfully")
            print(f"   URL: {result['data'].get('download_url', 'N/A')}")
        else:
            print(f"❌ Failed: {result['error']}")
        
        print("\n✅ All tests complete!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always cleanup
        await cleanup()


if __name__ == "__main__":
    asyncio.run(test_mcp_connection())