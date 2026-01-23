# html_parser.py - HTML Table Parser
from html.parser import HTMLParser
from typing import List, Dict

class TableParser(HTMLParser):
    """Enhanced parser to convert HTML tables to JSON format"""
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

def parse_html_to_json(html_content: str) -> List[Dict]:
    """Convert HTML table to JSON with enhanced field detection"""
    parser = TableParser()
    parser.feed(html_content)
    
    json_data = []
    for row in parser.rows:
        if len(row) == len(parser.headers):
            record = {}
            for i, header in enumerate(parser.headers):
                clean_header = header.strip().lower().replace(' ', '_')
                value = row[i].strip()
                
                # Smart type conversion
                if value.isdigit():
                    record[clean_header] = int(value)
                elif _is_float(value):
                    record[clean_header] = float(value)
                else:
                    record[clean_header] = value
            
            json_data.append(record)
    
    return json_data

def _is_float(value: str) -> bool:
    """Check if string is a valid float"""
    try:
        float(value)
        return '.' in value
    except ValueError:
        return False