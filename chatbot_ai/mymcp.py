"""
MCP Server with File Download Support and DeepSeek Ollama Integration
Supports multiple formats: CSV, Excel, Word, TXT, PowerPoint
Includes DeepSeek R1:8b integration for AI-powered queries
"""

import httpx
import json
import asyncio
import os
from pathlib import Path
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# Global FastMCP server object
mcp = FastMCP("production-api-server")

# Default download directory (can be customized)
DOWNLOAD_DIR = Path.home() / "Downloads" / "ProductionReports"

# Ollama configuration
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEEPSEEK_MODEL = "deepseek-r1:8b"

@mcp.tool()
async def test_ollama_connection() -> str:
    """
    Test connection to Ollama server and check if DeepSeek model is available.
    
    Returns:
        JSON string with connection status and available models
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test if Ollama is running
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            data = response.json()
            
            # Check if DeepSeek model is available
            models = [model.get("name", "") for model in data.get("models", [])]
            deepseek_available = any(DEEPSEEK_MODEL in model for model in models)
            
            return json.dumps({
                "status": "connected",
                "ollama_url": OLLAMA_BASE_URL,
                "deepseek_model": DEEPSEEK_MODEL,
                "deepseek_available": deepseek_available,
                "available_models": models,
                "message": "✓ Ollama is running and accessible" if deepseek_available else "⚠ Ollama is running but DeepSeek R1:8b not found"
            }, indent=2)
    except httpx.ConnectError:
        return json.dumps({
            "status": "error",
            "message": "Cannot connect to Ollama. Make sure Ollama is running on http://127.0.0.1:11434",
            "hint": "Run 'ollama serve' in your terminal to start Ollama"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, indent=2)


@mcp.tool()
async def deepseek_query(prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
    """
    Query the DeepSeek R1:8b model via Ollama.
    
    Args:
        prompt: The query or instruction for DeepSeek
        max_tokens: Maximum tokens to generate (default: 500)
        temperature: Creativity level 0.0-1.0 (default: 0.7)
    
    Returns:
        The AI-generated response as a string
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": DEEPSEEK_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature
        }
    }

    timeout = httpx.Timeout(120.0, connect=5.0)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract the response text
            ai_response = data.get("response", "")
            
            return json.dumps({
                "success": True,
                "model": DEEPSEEK_MODEL,
                "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                "response": ai_response,
                "tokens_generated": data.get("eval_count", 0),
                "generation_time": f"{data.get('total_duration', 0) / 1e9:.2f}s"
            }, indent=2)
            
    except httpx.ConnectError:
        return json.dumps({
            "error": "Cannot connect to Ollama",
            "message": "Make sure Ollama is running: ollama serve",
            "url": url
        })
    except httpx.TimeoutException:
        return json.dumps({
            "error": "Request timed out",
            "message": "DeepSeek took too long to respond. Try a shorter prompt or increase max_tokens.",
            "url": url
        })
    except Exception as e:
        return json.dumps({
            "error": f"Query failed: {str(e)}",
            "url": url
        })


@mcp.tool()
async def deepseek_stream(prompt: str, max_tokens: int = 500) -> str:
    """
    Stream responses from DeepSeek R1:8b model.
    Note: Streaming is collected and returned as complete text in this implementation.
    
    Args:
        prompt: The query or instruction for DeepSeek
        max_tokens: Maximum tokens to generate (default: 500)
    
    Returns:
        The complete AI-generated response
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": DEEPSEEK_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": max_tokens
        }
    }

    collected_response = []
    
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0)) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            chunk_data = json.loads(line)
                            if "response" in chunk_data:
                                collected_response.append(chunk_data["response"])
                        except json.JSONDecodeError:
                            continue
        
        full_response = "".join(collected_response)
        return json.dumps({
            "success": True,
            "model": DEEPSEEK_MODEL,
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "response": full_response,
            "chunks_received": len(collected_response)
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Streaming failed: {str(e)}",
            "url": url
        })


@mcp.tool()
async def analyze_production_with_ai(
    endpoint: str = "/api/operator_today",
    analysis_request: str = "Summarize the key insights from this production data"
) -> str:
    """
    Fetch production data and analyze it using DeepSeek AI.
    
    Args:
        endpoint: API endpoint to fetch data from
        analysis_request: What you want DeepSeek to analyze or explain
    
    Returns:
        JSON with both raw data and AI analysis
    """
    # First, fetch the production data
    data_result = await get_data_from_api(endpoint)
    
    try:
        data = json.loads(data_result)
        
        if "error" in data:
            return json.dumps({
                "error": "Failed to fetch production data",
                "details": data
            }, indent=2)
        
        # Create prompt for DeepSeek
        prompt = f"""You are analyzing production data. Here's the data:

{json.dumps(data, indent=2)}

Analysis request: {analysis_request}

Please provide a clear, concise analysis."""

        # Get AI analysis
        ai_result = await deepseek_query(prompt, max_tokens=800)
        ai_data = json.loads(ai_result)
        
        return json.dumps({
            "success": True,
            "production_data": data,
            "ai_analysis": ai_data.get("response", ""),
            "endpoint": endpoint,
            "analysis_request": analysis_request
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Analysis failed: {str(e)}"
        })


# Tool: Add two numbers
@mcp.tool()
async def add(a: int, b: int) -> str:
    """Add two numbers together."""
    return str(a + b)


# Tool: Fetch data from web API with increased timeout
@mcp.tool()
async def get_data_from_api(endpoint: str = "/api/operator_today", params: dict = None) -> str:
    """
    Fetch data from the production API.
    
    Args:
        endpoint: API endpoint to call (default: /api/operator_today)
        params: Optional query parameters as a dictionary
    
    Returns:
        JSON string of the response data
    """
    base_url = "http://192.168.0.12:5005"
    url = f"{base_url}{endpoint}"

    timeout = httpx.Timeout(30.0, connect=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if params:
                response = await client.get(url, params=params)
            else:
                response = await client.get(url)
            
            response.raise_for_status()
            data = response.json()
            return json.dumps(data, indent=2)
    except httpx.TimeoutException as e:
        return json.dumps({"error": f"Request timed out after 30s: {str(e)}", "url": url})
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})


@mcp.tool()
async def download_report(
    format: str = "csv",
    date: str = None,
    start_date: str = None,
    end_date: str = None,
    save_path: str = None
) -> str:
    """
    Download production report in various formats.
    
    Args:
        format: File format (csv, excel, word, txt, powerpoint)
        date: Specific date (YYYY-MM-DD)
        start_date: Start date for range (YYYY-MM-DD)
        end_date: End date for range (YYYY-MM-DD)
        save_path: Custom save path (optional, defaults to ~/Downloads/ProductionReports)
    
    Returns:
        JSON string with download status and file path
    """
    base_url = "http://192.168.0.12:5005"
    
    format_endpoints = {
        "csv": "/api/download_csv",
        "excel": "/api/download_excel",
        "word": "/api/download_word",
        "txt": "/api/download_txt",
        "powerpoint": "/api/download_powerpoint",
        "ppt": "/api/download_powerpoint"
    }
    
    format_lower = format.lower()
    if format_lower not in format_endpoints:
        return json.dumps({
            "error": f"Unsupported format: {format}",
            "supported_formats": list(format_endpoints.keys())
        })
    
    endpoint = format_endpoints[format_lower]
    
    params = {}
    if date:
        params["date"] = date
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    url = base_url + endpoint
    if params:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query_string}"
    
    if save_path:
        download_path = Path(save_path)
    else:
        download_path = DOWNLOAD_DIR
    
    download_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_info = date or f"{start_date}_to_{end_date}" if start_date and end_date else "today"
    
    extensions = {
        "csv": ".csv",
        "excel": ".xlsx",
        "word": ".docx",
        "txt": ".txt",
        "powerpoint": ".pptx",
        "ppt": ".pptx"
    }
    
    ext = extensions.get(format_lower, ".csv")
    filename = f"production_report_{date_info}_{timestamp}{ext}"
    file_path = download_path / filename
    
    timeout = httpx.Timeout(60.0, connect=5.0)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            with open(file_path, "wb") as f:
                f.write(response.content)
            
            return json.dumps({
                "success": True,
                "format": format_lower,
                "file_path": str(file_path),
                "file_size": len(response.content),
                "filename": filename,
                "download_url": url,
                "message": f"Report downloaded successfully to {file_path}"
            }, indent=2)
            
    except httpx.TimeoutException as e:
        return json.dumps({
            "error": f"Download timed out after 60s: {str(e)}",
            "url": url
        })
    except Exception as e:
        return json.dumps({
            "error": f"Download failed: {str(e)}",
            "url": url,
            "attempted_path": str(file_path)
        })


@mcp.tool()
async def get_download_url(
    format: str = "csv",
    date: str = None,
    start_date: str = None,
    end_date: str = None
) -> str:
    """
    Get a direct download URL for a production report.
    Users can copy this URL and paste it in their browser to download.
    
    Args:
        format: File format (csv, excel, word, txt, powerpoint)
        date: Specific date (YYYY-MM-DD)
        start_date: Start date for range (YYYY-MM-DD)
        end_date: End date for range (YYYY-MM-DD)
    
    Returns:
        JSON string with the download URL
    """
    base_url = "http://192.168.0.12:5005"
    
    format_endpoints = {
        "csv": "/api/download_csv",
        "excel": "/api/download_excel",
        "word": "/api/download_word",
        "txt": "/api/download_txt",
        "powerpoint": "/api/download_powerpoint",
        "ppt": "/api/download_powerpoint"
    }
    
    format_lower = format.lower()
    if format_lower not in format_endpoints:
        return json.dumps({
            "error": f"Unsupported format: {format}",
            "supported_formats": list(format_endpoints.keys())
        })
    
    endpoint = format_endpoints[format_lower]
    
    params = {}
    if date:
        params["date"] = date
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    url = base_url + endpoint
    if params:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query_string}"
    
    return json.dumps({
        "format": format_lower,
        "download_url": url,
        "instructions": "Copy this URL and paste it in your browser to download the file",
        "date_filter": date or f"{start_date} to {end_date}" if start_date and end_date else "today"
    }, indent=2)


@mcp.tool()
async def list_available_formats() -> str:
    """
    List all available download formats and their descriptions.
    
    Returns:
        JSON string with format information
    """
    formats = {
        "csv": {
            "name": "CSV (Comma-Separated Values)",
            "description": "Plain text format, opens in Excel/Google Sheets",
            "best_for": "Data analysis, importing to other systems",
            "extension": ".csv"
        },
        "excel": {
            "name": "Excel Workbook",
            "description": "Microsoft Excel format with formatting",
            "best_for": "Advanced Excel analysis, charts, formulas",
            "extension": ".xlsx"
        },
        "word": {
            "name": "Word Document",
            "description": "Microsoft Word format with formatted report",
            "best_for": "Professional reports, documentation",
            "extension": ".docx"
        },
        "txt": {
            "name": "Text File",
            "description": "Plain text format, universal compatibility",
            "best_for": "Simple viewing, system logs",
            "extension": ".txt"
        },
        "powerpoint": {
            "name": "PowerPoint Presentation",
            "description": "Microsoft PowerPoint format with slides",
            "best_for": "Presentations, visual summaries",
            "extension": ".pptx"
        }
    }
    
    return json.dumps({
        "available_formats": formats,
        "total_formats": len(formats),
        "usage": "Use download_report() or get_download_url() with any of these formats"
    }, indent=2)


# Main entrypoint
if __name__ == "__main__":
    asyncio.run(mcp.run())