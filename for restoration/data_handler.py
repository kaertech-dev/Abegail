# data_handler.py
# Handles API data fetching and HTML parsing

import requests
import json
import textwrap
from html.parser import HTMLParser
from config import API_URL, MAX_TOKENS_PER_CHUNK, USE_SAMPLE_DATA, SAMPLE_DATA, COMPANY_KEYWORDS


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


def parse_html_to_json(html_content):
    """Converts HTML table data to JSON format"""
    parser = TableParser()
    parser.feed(html_content)
    
    # Convert to list of dictionaries
    json_data = []
    for row in parser.rows:
        if len(row) == len(parser.headers):
            record = {}
            for i, header in enumerate(parser.headers):
                # Clean header names
                clean_header = header.strip().lower().replace(' ', '_')
                record[clean_header] = row[i].strip()
            json_data.append(record)
    
    return json_data


def needs_company_data(question):
    """Check if question requires company data"""
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in COMPANY_KEYWORDS)


def fetch_company_data():
    """Fetches data from company API and converts to JSON"""
    
    if USE_SAMPLE_DATA:
        print("⚠️  WARNING: Using sample data")
        data_str = json.dumps(SAMPLE_DATA, indent=2)
        chunks = textwrap.wrap(data_str, width=MAX_TOKENS_PER_CHUNK*5)
        return chunks, SAMPLE_DATA
    
    try:
        print(f"📡 Fetching data from: {API_URL}")
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '')
        print(f"📄 Content-Type: {content_type}")
        
        json_data = None
        
        # Try to parse as JSON first
        if 'application/json' in content_type:
            try:
                json_data = response.json()
                print(f"✅ Already JSON format - using directly")
            except json.JSONDecodeError:
                pass
        
        # If not JSON, convert HTML to JSON
        if json_data is None:
            print(f"🔄 Converting HTML to JSON (MCP-style)...")
            html_content = response.text
            
            # Parse HTML tables to JSON
            json_data = parse_html_to_json(html_content)
            
            if json_data:
                print(f"✅ Successfully converted HTML to JSON! Found {len(json_data)} records")
            else:
                print(f"❌ Could not extract data from HTML")
                return None, None
        
        # Format JSON for AI
        if isinstance(json_data, list):
            data_str = "Company Activity Data:\n\n"
            data_str += json.dumps(json_data, indent=2)
        elif isinstance(json_data, dict):
            data_str = "Company Activity Data:\n\n"
            data_str += json.dumps(json_data, indent=2)
        else:
            data_str = json.dumps(json_data, indent=2)
        
        chunks = textwrap.wrap(data_str, width=MAX_TOKENS_PER_CHUNK*5)
        return chunks, json_data
        
    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout: API took too long to respond")
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching API data: {e}")
        return None, None