# activity_api.py - API Communication Layer (Fixed Imports)
import requests
import json
import sys
import os
from typing import Optional, Dict
from datetime import datetime

# Add current directory to path to ensure imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import html_parser - try multiple methods
try:
    from .html_parser import parse_html_to_json
    print("✅ Using relative import for html_parser")
except (ImportError, ValueError):
    try:
        from html_parser import parse_html_to_json
        print("✅ Using absolute import for html_parser")
    except ImportError:
        # Last resort - import from file directly
        import importlib.util
        html_parser_path = os.path.join(current_dir, 'html_parser.py')
        if os.path.exists(html_parser_path):
            spec = importlib.util.spec_from_file_location("html_parser", html_parser_path)
            html_parser = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(html_parser)
            parse_html_to_json = html_parser.parse_html_to_json
            print("✅ Using direct file import for html_parser")
        else:
            print(f"❌ Could not find html_parser.py at {html_parser_path}")
            raise

class ActivityAPI:
    """Handle API communication for activity monitoring"""
    
    def __init__(self, api_url: Optional[str] = None):
        if api_url is None:
            from config import ACTIVITY_API_URL
            api_url = ACTIVITY_API_URL
        
        self.activity_endpoint = api_url
        print(f"🔗 Activity API initialized: {self.activity_endpoint}")
    
    def fetch_activity_data(self, timeout: int = 10) -> Dict:
        """
        Fetch activity data from API (supports both JSON and HTML)
        Returns: Dict with activity data or error info
        """
        try:
            print(f"📡 Fetching from: {self.activity_endpoint}")
            
            response = requests.get(
                self.activity_endpoint, 
                timeout=timeout,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            
            # Try JSON first
            if 'application/json' in content_type.lower():
                result = self._parse_json_response(response)
                if result:
                    return result
            
            # Fall back to HTML parsing
            return self._parse_html_response(response)
            
        except requests.exceptions.Timeout:
            return self._build_error('Request timeout', 
                f'API at {self.activity_endpoint} took too long to respond (>{timeout}s)')
        
        except requests.exceptions.ConnectionError:
            return self._build_error('Connection error',
                f'Could not connect to {self.activity_endpoint}. Is the server running?')
        
        except requests.exceptions.HTTPError as e:
            return self._build_error('HTTP error',
                f'API returned error: {e.response.status_code}',
                e.response.text[:500] if hasattr(e.response, 'text') else None)
        
        except Exception as e:
            return self._build_error('Unknown error', str(e))
    
    def _parse_json_response(self, response) -> Optional[Dict]:
        """Parse JSON response"""
        try:
            data = response.json()
            print("✅ Successfully parsed JSON response")
            return {
                'success': True,
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'count': len(data) if isinstance(data, list) else 1
            }
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON decode failed: {e}")
            return None
    
    def _parse_html_response(self, response) -> Dict:
        """Parse HTML response"""
        print("🔄 Attempting HTML table parsing...")
        html_content = response.text
        json_data = parse_html_to_json(html_content)
        
        if json_data:
            print(f"✅ Successfully parsed HTML table ({len(json_data)} records)")
            return {
                'success': True,
                'data': json_data,
                'timestamp': datetime.now().isoformat(),
                'count': len(json_data),
                'source': 'html'
            }
        else:
            return self._build_error('No data found',
                'Could not parse data from HTML table or JSON',
                response.text[:500])
    
    def _build_error(self, error: str, message: str, raw_response: str = None) -> Dict:
        """Build error response"""
        result = {
            'success': False,
            'error': error,
            'message': message,
            'tried_url': self.activity_endpoint
        }
        if raw_response:
            result['raw_response'] = raw_response
        return result