# api_handler.py
"""
Company API Handler (Simplified)
Handles all company production API operations
"""
import requests
import json
from typing import Optional, Dict, Any, List, Tuple
from html.parser import HTMLParser

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

class APIHandler:
    """Handler for Company Production API"""
    
    def __init__(self, api_url: str = "http://localhost/activity", timeout: int = 10):
        self.api_url = api_url
        self.timeout = timeout
    
    def parse_html_to_json(self, html_content: str) -> List[Dict]:
        """Convert HTML table to JSON"""
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
    
    def fetch_raw_data(self) -> Optional[List[Dict]]:
        """Fetch and parse data from API"""
        try:
            response = requests.get(self.api_url, timeout=self.timeout)
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
            print(f"❌ API Error: {e}")
            return None
    
    def fetch_production_data(self, format_type: str = "raw") -> Dict[str, Any]:
        """Fetch production data with optional formatting"""
        data = self.fetch_raw_data()
        
        if not data:
            return {"error": "Could not fetch data from API"}
        
        if format_type == "summary" and isinstance(data, list):
            return {
                "total_records": len(data),
                "unique_operators": len(set(r.get('operator', '') for r in data)),
                "unique_customers": len(set(r.get('customer', '') for r in data)),
                "unique_products": len(set(r.get('product', '') for r in data)),
                "total_output": sum(int(r.get('output', 0)) for r in data if str(r.get('output', '')).isdigit()),
                "data": data
            }
        
        return {"data": data, "count": len(data)}
    
    def get_operator_stats(self, operator_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for specific operator or all operators"""
        data = self.fetch_raw_data()
        
        if not data:
            return {"error": "No data available"}
        
        if not isinstance(data, list):
            return {"error": "Invalid data format"}
        
        if operator_id:
            # Filter for specific operator
            filtered = [r for r in data if r.get('operator', '') == operator_id]
            return {
                "operator_id": operator_id,
                "records": len(filtered),
                "data": filtered
            }
        else:
            # Stats for all operators
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
                output = record.get('output', '0')
                operators[op_id]["total_output"] += int(output) if output.isdigit() else 0
                operators[op_id]["data"].append(record)
            
            return {
                "operator_count": len(operators),
                "operators": operators
            }
    
    def filter_by_customer(self, customer: str) -> Dict[str, Any]:
        """Filter data by customer name"""
        data = self.fetch_raw_data()
        
        if not data or not isinstance(data, list):
            return {"error": "No data available"}
        
        filtered = [r for r in data if customer.lower() in r.get('customer', '').lower()]
        
        return {
            "customer": customer,
            "matches": len(filtered),
            "data": filtered
        }
    
    def filter_by_product(self, product: str) -> Dict[str, Any]:
        """Filter data by product name"""
        data = self.fetch_raw_data()
        
        if not data or not isinstance(data, list):
            return {"error": "No data available"}
        
        filtered = [r for r in data if product.lower() in r.get('product', '').lower()]
        
        return {
            "product": product,
            "matches": len(filtered),
            "data": filtered
        }
    
    def get_top_performers(self, limit: int = 5) -> Dict[str, Any]:
        """Get top performing operators by output"""
        data = self.fetch_raw_data()
        
        if not data or not isinstance(data, list):
            return {"error": "No data available"}
        
        # Aggregate by operator
        operators = {}
        for record in data:
            op_id = record.get('operator', 'unknown')
            output = record.get('output', '0')
            output_val = int(output) if output.isdigit() else 0
            
            if op_id not in operators:
                operators[op_id] = {"total_output": 0, "records": []}
            
            operators[op_id]["total_output"] += output_val
            operators[op_id]["records"].append(record)
        
        # Sort by total output
        sorted_ops = sorted(operators.items(), key=lambda x: x[1]["total_output"], reverse=True)
        top_performers = dict(sorted_ops[:limit])
        
        return {
            "limit": limit,
            "top_performers": top_performers
        }

# Global handler instance
_api_handler = None

def get_api_handler() -> APIHandler:
    """Get singleton API handler"""
    global _api_handler
    if _api_handler is None:
        _api_handler = APIHandler()
    return _api_handler

# Convenience functions for Flask integration
def fetch_company_data() -> Tuple[Optional[List[str]], Optional[List[Dict]]]:
    """Fetch company data (compatible with existing code)"""
    handler = get_api_handler()
    result = handler.fetch_production_data()
    
    if result.get('error'):
        return None, None
    
    data = result.get('data', [])
    
    # Format for AI consumption
    formatted = json.dumps(data, indent=2, default=str)
    return [formatted], data

def needs_company_data(message: str) -> bool:
    """Enhanced: Check if message requires company API data"""
    msg = message.lower().strip()
    
    # Pattern 1: "send [company-related word]" - means show/display, not email
    send_patterns = [
        'send the activity', 'send activity', 'send all activity',
        'send all working', 'send working', 'send all operators',
        'send operators', 'send operator', 'send all operator',
        'send production', 'send output', 'send stats',
        'send statistics', 'send performance', 'send today',
        'send current', 'send latest', 'send recent'
    ]
    
    # Check for "send" + company keywords pattern (but not email)
    if 'send' in msg and 'email' not in msg and 'mail' not in msg:
        after_send = msg[msg.find('send') + 4:].strip()
        company_keywords = ['activity', 'operators', 'working', 'production', 'output', 'stats', 'statistics', 'performance']
        if any(keyword in after_send for keyword in company_keywords):
            return True
        if any(pattern in msg for pattern in send_patterns):
            return True
    
    company_keywords = [
        'operator', 'operators', 'working', 'production', 'output',
        'performance', 'cycle', 'time', 'statistics', 'stats',
        'today', 'current', 'latest', 'recent',
        'show', 'list', 'who', 'which', 'what',
        'top', 'best', 'highest', 'fastest', 'activity'
    ]
    
    # Pattern 2: Direct company keyword matches
    if any(keyword in msg for keyword in company_keywords):
        return True
    
    # Pattern 3: Common company query patterns
    company_query_patterns = [
        'who is working', 'who are working', 'who working',
        'all working', 'all operators', 'all operator',
        'activity today', 'activity now', 'activity current',
        'working today', 'working now', 'working current',
        'operators today', 'operators now', 'operators current'
    ]
    
    return any(pattern in msg for pattern in company_query_patterns)