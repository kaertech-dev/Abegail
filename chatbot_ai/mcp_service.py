"""
MCP Client - Direct connector to your FastMCP server
This replaces the HTTP-based mcp_service.py with direct MCP protocol calls
"""
import asyncio
import json
from typing import Optional, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Path to your MCP server
MCP_SERVER_PATH = r"C:\Users\ai\Documents\project_abegail\mcp-server-demo\mcp.py"

# Global session
_mcp_session: Optional[ClientSession] = None
_mcp_initialized = False


async def initialize_mcp():
    """
    Initialize connection to MCP server
    """
    global _mcp_session, _mcp_initialized
    
    if _mcp_initialized and _mcp_session:
        return True
    
    try:
        # Server parameters
        server_params = StdioServerParameters(
            command="python",
            args=[MCP_SERVER_PATH],
            env=None
        )
        
        # Create stdio client
        stdio_transport = await stdio_client(server_params)
        _mcp_session = ClientSession(stdio_transport[0], stdio_transport[1])
        
        # Initialize session
        await _mcp_session.initialize()
        
        _mcp_initialized = True
        print("✅ MCP Server connected successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to MCP server: {str(e)}")
        _mcp_initialized = False
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
                "error": "Failed to initialize MCP connection"
            }
    
    try:
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
                    return {
                        "success": True,
                        "data": data,
                        "tool": tool_name
                    }
                except json.JSONDecodeError:
                    # Return as plain text
                    return {
                        "success": True,
                        "data": response_text,
                        "tool": tool_name
                    }
        
        return {
            "success": False,
            "error": "No content in response",
            "tool": tool_name
        }
        
    except Exception as e:
        print(f"❌ MCP Tool Error ({tool_name}): {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "tool": tool_name
        }


async def list_available_tools() -> Dict[str, Any]:
    """
    List all available tools from MCP server
    """
    global _mcp_session, _mcp_initialized
    
    if not _mcp_initialized:
        await initialize_mcp()
    
    try:
        tools = await _mcp_session.list_tools()
        return {
            "success": True,
            "tools": [{"name": tool.name, "description": tool.description} for tool in tools.tools]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def get_production_data(endpoint: str = "/api/operator_today") -> Dict[str, Any]:
    """
    Convenience function to get production data
    """
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
    global _mcp_session, _mcp_initialized
    
    if _mcp_session:
        try:
            # Close session if needed
            _mcp_initialized = False
            print("✅ MCP connection closed")
        except:
            pass


# Test function
async def test_mcp_connection():
    """
    Test MCP server connection and tools
    """
    print("🧪 Testing MCP Connection...\n")
    
    # Initialize
    print("1. Initializing MCP server...")
    success = await initialize_mcp()
    
    if not success:
        print("❌ Failed to initialize MCP server")
        return
    
    # List tools
    print("\n2. Listing available tools...")
    tools = await list_available_tools()
    if tools["success"]:
        print(f"✅ Found {len(tools['tools'])} tools:")
        for tool in tools['tools']:
            print(f"   - {tool['name']}: {tool['description'][:80]}...")
    
    # Test production data
    print("\n3. Testing production data retrieval...")
    result = await get_production_data()
    if result["success"]:
        print(f"✅ Production data retrieved successfully")
        print(f"   Data preview: {str(result['data'])[:200]}...")
    else:
        print(f"❌ Failed: {result['error']}")
    
    # Test download URL
    print("\n4. Testing download URL generation...")
    result = await get_download_url(format_type="excel")
    if result["success"]:
        print(f"✅ Download URL generated successfully")
        print(f"   URL: {result['data'].get('download_url', 'N/A')}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    # Test DeepSeek query
    print("\n5. Testing DeepSeek query through MCP...")
    result = await query_deepseek("What is 2+2?")
    if result["success"]:
        print(f"✅ DeepSeek query successful")
        print(f"   Response: {result['data'][:200]}...")
    else:
        print(f"❌ Failed: {result['error']}")
    
    # Cleanup
    await cleanup()
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    asyncio.run(test_mcp_connection())