#!/usr/bin/env python3
"""
Activity MCP Server
Provides activity tracking and querying capabilities via MCP protocol
"""

import asyncio
import json
import csv
import os
import re
import requests
from datetime import datetime, date, time, timedelta
from typing import Any, List, Dict, Optional
from html_parser import parse_html_to_json
import mysql.connector
from mysql.connector import Error

path_name = './csv_files/'

DB_CONFIG = {
    'host': '192.168.1.38',
    'user': 'labeling',
    'password': 'labeling',
    'database': '',
    'autocommit': True,
    'use_unicode': True,
    'charset': 'utf8mb4'
}

def std_name(records: list) -> list:
    for rec in records:
        l_name = rec['Operator'].split(',')
        if len(l_name) > 1:
            rec['Operator'] = l_name[1].strip() + ' ' + l_name[0]
        else:
            pass
    
    return records

def format_entry(entry: dict, filter: str) -> str:
    if filter == 'all':
        text = f"**{entry['Station']}** - {entry['Model']} ({entry['Customer']}) \n\n"
        text += f"   -  **Start Time:** {entry['Start Time']}   **End Time:** {entry['End time']}\n\n"
        text += f"   -  **Cycle Time:** {entry['Cycle Time(s)']}   **Output:** {entry['Output']}\n\n"
        text += f"   -  **Target:** {entry['Target(s)']}   **Status:** {entry['Status']}\n\n"

    elif filter == 'where':
        text = f"**{entry['Station']}** - {entry['Model']} ({entry['Customer']}) \n\n"
        text += f"   -  *Start Time* - {entry['Start Time']}   *End Time* - {entry['End time']}\n\n"
    
    elif filter == 'cycle time' or filter == 'target':
        text = f"**{entry['Station']}** - {entry['Model']} ({entry['Customer']}) \n\n"
        text += f"   -  *Cycle Time* - {entry['Cycle Time(s)']}   *Target* - {entry['Target(s)']} \n\n"
    
    else:
        key = filter.capitalize() if filter == 'end time' else filter.title()
        text = f"**{entry['Station']}** - {entry['Model']} ({entry['Customer']}) \n\n"
        text += f"   -  *{filter.title()}* - {entry[key]} \n\n"
    
    return text

# ==================== API CLASS ====================

ACTIVITY_API_URL = os.getenv('ACTIVITY_API_URL', 'http://192.168.20.200/activity/api/operator_today')
PRODUCTIVITY_API = os.getenv('PRODUCTIVITY_API', 'http://192.168.20.200/productivity/api/operator_today')

class ActivityAPI:
    def __init__(self, api_url: Optional[str] = None):
        if api_url is None:
            api_url = ACTIVITY_API_URL
        
        self.activity_endpoint = api_url
    
    def get_productivity(self, date_suffix: str):
        url = PRODUCTIVITY_API + date_suffix
        try:
            response = requests.get(url, timeout=10, headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
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
                f'API at {self.activity_endpoint} took too long to respond')
        
        except requests.exceptions.ConnectionError:
            return self._build_error('Connection error',
                f'Could not connect to {self.activity_endpoint}. Is the server running?')
        
        except requests.exceptions.HTTPError as e:
            return self._build_error('HTTP error',
                f'API returned error: {e.response.status_code}',
                e.response.text[:500] if hasattr(e.response, 'text') else None)
        
        except Exception as e:
            return self._build_error('Unknown error', str(e))
    
    def get_all_data(self, date_suffix: str, timeout: int = 10) -> Dict:
        """
        Fetch activity data from API
        Returns: Dict with activity data or error info
        """
        api_url = self.activity_endpoint + date_suffix
        try:
            response = requests.get(
                api_url, 
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
            return {
                'success': True,
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'count': len(data) if isinstance(data, list) else 1
            }
        except json.JSONDecodeError as e:
            return None
    
    def _parse_html_response(self, response) -> Dict:
        """Parse HTML response"""
        html_content = response.text
        json_data = parse_html_to_json(html_content)
        
        if json_data:
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

class ActivityDB:
    """Handle attendance database operations"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    def connect(self, schema: str):
        """Create database connection"""
        try:
            self.config['database'] = schema
            return mysql.connector.connect(**self.config)
        except Error as e:
            # raise Exception(f"Database connection error: {e}")
            print(f"Database connection error: {e}")
            return None
    
    def qualified_stations(self, operator_id: List[str], station_list: List[str]):
        conn = self.connect('operators')

        try:
            cursor = conn.cursor(dictionary=True)
            possible_employees = []
            query = " SELECT * FROM `main` "
            ids = []
            for opid in operator_id:
                if KE_num := re.search(r'(?<!\w)KE\d{1,4}\s*', opid, re.IGNORECASE):
                    ids.append(f' `operator_en` LIKE "%{KE_num.group(0)}%" ')
                else:
                    name_parts = opid.lower().replace(',', '').split()
                    terms = [f" `employee_name` LIKE '%{np}%' " for np in name_parts]
                    ids.append('(' + 'AND'.join(terms) + ')')
            id_term = 'OR'.join(ids)
            
            stats = []
            for station in station_list:
                station = station.replace('_', ' ').replace('station', '').strip()
                stats.append(f' `process` LIKE "%{station}%" ')
            stat_term = 'OR'.join(stats)

            if ids and stats:
                query += ' WHERE ' + id_term + ' OR ' + stat_term
            elif ids:
                query += ' WHERE ' + id_term
            elif stats:
                query += ' WHERE ' + stat_term

            cursor.execute(query)
            possible_employees.extend(cursor.fetchall())
            
            # print(possible_employees)
            txt = '## No operator match.'
            if len(possible_employees) > 0:
                txt = '## Process Qualifications \n\n'
                for i, pe in enumerate(possible_employees, 1):
                    txt += f'{i}. **{pe['employee_name']}** ({pe['operator_en']})\n\n{pe['process']}\n\n'
                    pe['stations_allowed'] = pe.pop('process')

            return {'preformat': txt, 'raw_records': possible_employees}
        finally:
            cursor.close()
            conn.close()