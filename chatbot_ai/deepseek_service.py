"""
DeepSeek AI Service with MCP integration - Using Ollama Local Instance
Connected to your MCP server for production data tools
"""
import httpx
import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ollama Configuration (Local) - Using your 70b model
OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "deepseek-r1:8b"  # Changed to 70b

# Import MCP client (replaces old mcp_service)
from mcp_client import call_mcp_tool, initialize_mcp


SYSTEM_PROMPT = """You are Abegail, a helpful AI assistant with access to production data tools through MCP.

Available MCP Tools:
1. get_data_from_api(endpoint, params) - Fetch production data from API
   - Examples: /api/operator_today, /api/production_stats
   - Use when users ask about production data, operators, statistics

2. get_download_url(format, date, start_date, end_date) - Get download links
   - Formats: csv, excel, word, txt, powerpoint
   - Use when users want to download reports

3. deepseek_query(prompt, max_tokens) - Query yourself recursively (use sparingly)

4. add(a, b) - Simple addition tool for testing

When users ask about production data or reports, automatically use the appropriate MCP tool.
Explain results clearly and provide actionable information."""


async def ask_deepseek_with_mcp(user_message: str) -> dict:
    """
    Send message to Ollama DeepSeek-R1 70b and handle MCP tool calls.
    
    Args:
        user_message: The user's message
        
    Returns:
        dict: Response from DeepSeek with success status
    """
    # Initialize MCP connection
    await initialize_mcp()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]
    
    max_iterations = 5
    iteration = 0
    
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:  # 3 min timeout for 70b
            while iteration < max_iterations:
                iteration += 1
                print(f"🔄 Iteration {iteration}/{max_iterations}")
                
                # Call Ollama API
                response = await _call_ollama_api(client, messages)
                
                if not response["success"]:
                    return response
                
                content = response["content"]
                print(f"💬 DeepSeek response preview: {content[:150]}...")
                
                # Check for tool usage
                tool_used = await _handle_tool_requests(user_message, content, messages, iteration)
                
                if tool_used:
                    print(f"🛠️  Tool executed, continuing conversation...")
                    continue  # Loop again with tool result
                
                # No more tool calls needed
                return {
                    "success": True,
                    "response": content,
                    "used_mcp": iteration > 1,
                    "iterations": iteration,
                    "model": MODEL_NAME
                }
            
            # Max iterations reached
            return {
                "success": True,
                "response": "I've gathered the information but reached my processing limit. Here's what I found: " + content,
                "used_mcp": True,
                "iterations": iteration,
                "model": MODEL_NAME
            }
                
    except Exception as e:
        print(f"❌ Ollama DeepSeek Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "response": None}


async def _call_ollama_api(client: httpx.AsyncClient, messages: list) -> dict:
    """
    Make API call to Ollama (local DeepSeek-R1 70b)
    """
    # Convert messages to Ollama format
    ollama_messages = []
    for msg in messages:
        ollama_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    payload = {
        "model": MODEL_NAME,
        "messages": ollama_messages,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 2000,
            "num_ctx": 4096  # Context window for 70b
        }
    }
    
    try:
        print(f"📤 Sending request to Ollama ({MODEL_NAME})...")
        response = await client.post(
            OLLAMA_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            error_detail = response.text
            print(f"❌ Ollama API Error {response.status_code}: {error_detail}")
            return {
                "success": False,
                "error": f"Ollama API error {response.status_code}: {error_detail}"
            }
        
        data = response.json()
        content = data.get("message", {}).get("content", "")
        print(f"✅ Received response from Ollama")
        
        return {"success": True, "content": content}
        
    except httpx.ConnectError:
        return {
            "success": False,
            "error": "Cannot connect to Ollama. Make sure Ollama is running with: ollama serve"
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Ollama request timed out. The 70b model might be too slow, consider using 8b model."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Ollama error: {str(e)}"
        }


async def _handle_tool_requests(user_message: str, content: str, messages: list, iteration: str) -> bool:
    """
    Check if MCP tools need to be called and handle them
    
    Returns:
        bool: True if a tool was used
    """
    user_lower = user_message.lower()
    content_lower = content.lower()
    
    # Check for production data request
    if any(keyword in user_lower for keyword in ['production', 'operator', 'data', 'stats', 'today']):
        if 'get_data_from_api' in content_lower or iteration == 1:
            print("🔧 Calling MCP tool: get_data_from_api")
            tool_result = await call_mcp_tool("get_data_from_api", endpoint="/api/operator_today")
            
            if tool_result["success"]:
                messages.append({
                    "role": "assistant",
                    "content": "[Fetching production data from API via MCP...]"
                })
                messages.append({
                    "role": "user",
                    "content": f"Here's the production data from the API:\n\n{json.dumps(tool_result['data'], indent=2)}\n\nPlease analyze this data and provide a clear, helpful answer to the user's question: '{user_message}'"
                })
                return True
            else:
                print(f"⚠️ MCP tool failed: {tool_result.get('error')}")
    
    # Check for download request
    if any(keyword in user_lower for keyword in ['download', 'export', 'report', 'file']):
        format_type = _determine_format(user_message)
        print(f"🔧 Calling MCP tool: get_download_url (format={format_type})")
        
        tool_result = await call_mcp_tool("get_download_url", format=format_type)
        
        if tool_result["success"]:
            messages.append({
                "role": "assistant",
                "content": "[Getting download link via MCP...]"
            })
            messages.append({
                "role": "user",
                "content": f"Download URL is ready:\n\n{json.dumps(tool_result['data'], indent=2)}\n\nPlease provide this link to the user with clear instructions on how to download the {format_type} file."
            })
            return True
        else:
            print(f"⚠️ MCP tool failed: {tool_result.get('error')}")
    
    return False


def _determine_format(user_message: str) -> str:
    """
    Determine file format from user message
    """
    user_lower = user_message.lower()
    
    if "excel" in user_lower or "xlsx" in user_lower:
        return "excel"
    elif "word" in user_lower or "docx" in user_lower:
        return "word"
    elif "powerpoint" in user_lower or "ppt" in user_lower:
        return "powerpoint"
    elif "txt" in user_lower or "text" in user_lower:
        return "txt"
    else:
        return "csv"


# Test function
async def test_full_stack():
    """
    Test the complete integration: Ollama + MCP
    """
    print(f"🧪 Testing Full Stack Integration")
    print(f"   Model: {MODEL_NAME}")
    print(f"   MCP: Enabled\n")
    
    # Test 1: Simple query
    print("1️⃣ Testing simple query...")
    result = await ask_deepseek_with_mcp("Hello, who are you?")
    if result["success"]:
        print(f"✅ Success!")
        print(f"   Response: {result['response'][:150]}...")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    # Test 2: Production data query (uses MCP)
    print("\n2️⃣ Testing production data query (should trigger MCP)...")
    result = await ask_deepseek_with_mcp("Show me today's production data")
    if result["success"]:
        print(f"✅ Success! Used MCP: {result.get('used_mcp', False)}")
        print(f"   Iterations: {result.get('iterations', 0)}")
        print(f"   Response: {result['response'][:200]}...")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_full_stack())