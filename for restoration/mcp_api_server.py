#!/usr/bin/env python3
"""
Company API MCP Server
Provides access to company production data via MCP protocol
"""

import os
import json
import asyncio
import requests
from typing import Any, Sequence
from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.server.stdio
from html.parser import HTMLParser

# API Configuration
API_URL = os.getenv('API_URL', 'http://localhost/activity')
API_TIMEOUT = int(os.getenv('API_TIMEOUT', '10'))

class TableParser(HTMLParser):
    """Parser to convert HTML tables to JSON format"""
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


class CompanyAPIServer:
    """MCP Server for Company Production API"""
    
    def __init__(self):
        self.server = Server("company-api-server")
        
        # Register handlers
        self.server.list_resources()(self.list_resources)
        self.server.read_resource()(self.read_resource)
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)
    
    def parse_html_to_json(self, html_content):
        """Converts HTML table data to JSON format"""
        parser = TableParser()
        parser.feed(html_content)
        
        json_data = []
        for row in parser.rows:
            if len(row) == len(parser.headers):
                record = {}
                for i, header in enumerate(parser.headers):
                    clean_header = header.strip().lower().replace(' ', '_')
                    record[clean_header] = row[i].strip()
                json_data.append(record)
        
        return json_data
    
    def fetch_api_data(self):
        """Fetch data from company API"""
        try:
            response = requests.get(API_URL, timeout=API_TIMEOUT)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            
            # Try JSON first
            if 'application/json' in content_type:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    pass
            
            # Convert HTML to JSON
            html_content = response.text
            json_data = self.parse_html_to_json(html_content)
            
            return json_data if json_data else None
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request error: {str(e)}")
    
    async def list_resources(self) -> list[Resource]:
        """List available API resources"""
        return [
            Resource(
                uri="company://production/current",
                name="Current Production Data",
                mimeType="application/json",
                description="Current production activity data from company API"
            ),
            Resource(
                uri="company://production/summary",
                name="Production Summary",
                mimeType="application/json",
                description="Summary statistics of production data"
            ),
            Resource(
                uri="company://operators/active",
                name="Active Operators",
                mimeType="application/json",
                description="List of currently active operators"
            )
        ]
    
    async def read_resource(self, uri: str) -> str:
        """Read a specific resource"""
        try:
            data = self.fetch_api_data()
            
            if not data:
                return json.dumps({"error": "No data available from API"})
            
            if uri == "company://production/current":
                return json.dumps({
                    "source": "company_api",
                    "url": API_URL,
                    "record_count": len(data) if isinstance(data, list) else 1,
                    "data": data
                }, indent=2, default=str)
            
            elif uri == "company://production/summary":
                if isinstance(data, list):
                    summary = {
                        "total_records": len(data),
                        "operators": list(set(r.get('operator', '') for r in data)),
                        "customers": list(set(r.get('customer', '') for r in data)),
                        "products": list(set(r.get('product', '') for r in data))
                    }
                    return json.dumps(summary, indent=2)
                return json.dumps({"error": "Data format not suitable for summary"})
            
            elif uri == "company://operators/active":
                if isinstance(data, list):
                    operators = {}
                    for record in data:
                        op_id = record.get('operator', 'unknown')
                        if op_id not in operators:
                            operators[op_id] = []
                        operators[op_id].append(record)
                    
                    return json.dumps({
                        "operator_count": len(operators),
                        "operators": operators
                    }, indent=2, default=str)
                return json.dumps({"error": "Cannot extract operators from data"})
            
            return json.dumps({"error": "Unknown resource URI"})
            
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    async def list_tools(self) -> list[Tool]:
        """List available API tools"""
        return [
            Tool(
                name="fetch_production_data",
                description="Fetch current production data from company API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "enum": ["raw", "summary"],
                            "description": "Data format to return (default: raw)",
                            "default": "raw"
                        }
                    }
                }
            ),
            Tool(
                name="get_operator_stats",
                description="Get statistics for a specific operator or all operators",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "operator_id": {
                            "type": "string",
                            "description": "Operator ID to filter (optional - returns all if not specified)"
                        }
                    }
                }
            ),
            Tool(
                name="filter_by_customer",
                description="Filter production data by customer name",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer": {
                            "type": "string",
                            "description": "Customer name to filter by"
                        }
                    },
                    "required": ["customer"]
                }
            ),
            Tool(
                name="filter_by_product",
                description="Filter production data by product name",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product": {
                            "type": "string",
                            "description": "Product name to filter by"
                        }
                    },
                    "required": ["product"]
                }
            ),
            Tool(
                name="get_top_performers",
                description="Get top performing operators by output",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of top performers to return (default: 5)",
                            "default": 5
                        }
                    }
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute a tool"""
        try:
            data = self.fetch_api_data()
            
            if not data:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "No data available from API"})
                )]
            
            if name == "fetch_production_data":
                format_type = arguments.get("format", "raw")
                
                if format_type == "summary" and isinstance(data, list):
                    summary = {
                        "total_records": len(data),
                        "unique_operators": len(set(r.get('operator', '') for r in data)),
                        "unique_customers": len(set(r.get('customer', '') for r in data)),
                        "unique_products": len(set(r.get('product', '') for r in data)),
                        "total_output": sum(int(r.get('output', 0)) for r in data if r.get('output', '').isdigit())
                    }
                    result = summary
                else:
                    result = data
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, default=str)
                )]
            
            elif name == "get_operator_stats":
                operator_id = arguments.get("operator_id")
                
                if not isinstance(data, list):
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": "Data format not suitable for operator stats"})
                    )]
                
                if operator_id:
                    filtered = [r for r in data if r.get('operator', '') == operator_id]
                    result = {
                        "operator_id": operator_id,
                        "records": len(filtered),
                        "data": filtered
                    }
                else:
                    operators = {}
                    for record in data:
                        op_id = record.get('operator', 'unknown')
                        if op_id not in operators:
                            operators[op_id] = {
                                "records": 0,
                                "total_output": 0,
                                "data": []
                            }
                        operators[op_id]["records"] += 1
                        operators[op_id]["total_output"] += int(record.get('output', 0)) if record.get('output', '').isdigit() else 0
                        operators[op_id]["data"].append(record)
                    
                    result = {
                        "operator_count": len(operators),
                        "operators": operators
                    }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, default=str)
                )]
            
            elif name == "filter_by_customer":
                customer = arguments["customer"]
                
                if not isinstance(data, list):
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": "Data format not suitable for filtering"})
                    )]
                
                filtered = [r for r in data if customer.lower() in r.get('customer', '').lower()]
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "customer": customer,
                        "matches": len(filtered),
                        "data": filtered
                    }, indent=2, default=str)
                )]
            
            elif name == "filter_by_product":
                product = arguments["product"]
                
                if not isinstance(data, list):
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": "Data format not suitable for filtering"})
                    )]
                
                filtered = [r for r in data if product.lower() in r.get('product', '').lower()]
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "product": product,
                        "matches": len(filtered),
                        "data": filtered
                    }, indent=2, default=str)
                )]
            
            elif name == "get_top_performers":
                limit = arguments.get("limit", 5)
                
                if not isinstance(data, list):
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": "Data format not suitable for ranking"})
                    )]
                
                # Aggregate by operator
                operators = {}
                for record in data:
                    op_id = record.get('operator', 'unknown')
                    output = int(record.get('output', 0)) if record.get('output', '').isdigit() else 0
                    
                    if op_id not in operators:
                        operators[op_id] = {"total_output": 0, "records": []}
                    
                    operators[op_id]["total_output"] += output
                    operators[op_id]["records"].append(record)
                
                # Sort by total output
                sorted_ops = sorted(operators.items(), key=lambda x: x[1]["total_output"], reverse=True)
                top_performers = dict(sorted_ops[:limit])
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "limit": limit,
                        "top_performers": top_performers
                    }, indent=2, default=str)
                )]
            
            else:
                raise Exception(f"Unknown tool: {name}")
                
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)})
            )]
    
    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

async def main():
    server = CompanyAPIServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())