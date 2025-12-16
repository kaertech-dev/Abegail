# app.py - Enhanced with Better Database Navigation
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
import socket
import re

from db_handler import (
    get_db_handler, 
    list_databases, 
    list_active_databases,
    analyze_database, 
    smart_search,
    search_all_active_databases,
    execute_query,
    show_table_details,
    show_filtered_data
)
from ai_handler import ask_deepseek, ask_general_question
from quick_responses import check_quick_response, learn_from_conversation
from context_manager import get_context_manager
from knowledge_base import get_knowledge_base
from query_router import classify_query_type, extract_database_name
from date_filter import parse_date_from_message

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST"]}})

chat_sessions = {}
DEFAULT_DATABASE = "operators"

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"

def create_message(msg_type, message, session_id, parent_id=None, **kwargs):
    return {
        'type': msg_type,
        'message': message,
        'timestamp': datetime.now().strftime("%H:%M"),
        'id': f"msg_{len(chat_sessions.get(session_id, []))}",
        'parent_id': parent_id,
        **kwargs
    }

def extract_table_name(message: str, database: str) -> str:
    """Extract table name from message"""
    msg = message.lower()
    
    # Patterns: "show table X", "table X in database", "details of X"
    patterns = [
        r'table\s+(\w+)',
        r'details\s+of\s+(\w+)',
        r'info\s+on\s+(\w+)',
        r'about\s+(\w+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, msg)
        if match:
            return match.group(1)
    
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not message:
            return jsonify({'error': 'Empty message'}), 400
        
        context_mgr = get_context_manager()
        kb = get_knowledge_base()
        
        chat_sessions.setdefault(session_id, [])
        user_msg = create_message('user', message, session_id)
        chat_sessions[session_id].append(user_msg)
        
        # Quick responses first
        quick_resp = check_quick_response(message)
        if quick_resp:
            bot_msg = create_message('bot', quick_resp, session_id, user_msg['id'], response_type='quick')
            chat_sessions[session_id].append(bot_msg)
            context_mgr.add_message(session_id, message, 'user')
            context_mgr.add_message(session_id, quick_resp, 'bot')
            learn_from_conversation(chat_sessions[session_id])
            return jsonify(bot_msg)
        
        context_mgr.add_message(session_id, message, 'user')
        
        # Get context
        conversation_context = context_mgr.get_relevant_context(session_id, message, max_messages=5)
        relevant_facts = kb.search_facts(message, limit=3)
        relevant_facts_text = [f['fact'] for f in relevant_facts]
        
        # Route query
        msg_lower = message.lower()
        database = extract_database_name(message) or DEFAULT_DATABASE
        
        # Check for date filtering first
        date_info = parse_date_from_message(message)
        
        # Extract table name for date-filtered queries
        table_name = None
        if date_info:
            # Patterns: "show activity from today", "activity data today", "ledtech.activity today"
            table_patterns = [
                r'show\s+(\w+)\s+(?:data\s+)?(?:from|for)',
                r'(\w+)\s+(?:data|table)\s+(?:from|for|today|yesterday)',
                r'(?:from|in)\s+(\w+)\.(\w+)',
                r'table\s+(\w+)',
            ]
            
            for pattern in table_patterns:
                match = re.search(pattern, msg_lower)
                if match:
                    table_name = match.group(1)
                    # Check if it's database.table format
                    if match.lastindex and match.lastindex > 1:
                        database = match.group(1)
                        table_name = match.group(2)
                    break
        
        # Check for date-filtered data query
        if date_info and table_name:
            result = show_filtered_data(database, table_name, date_info, limit=100)
            answer = result
            response_type = 'date_filtered'
        
        # Check for table details query
        if any(phrase in msg_lower for phrase in ['show table', 'table details', 'table info', 'about table']):
            table_name = extract_table_name(message, database)
            if table_name:
                result = show_table_details(database, table_name)
                answer = result
                response_type = 'table_details'
            else:
                answer = "Please specify the table name. Example: \"show table activity in operators\""
                response_type = 'error'
        
        # Check for "show all data" queries
        elif 'show all data' in msg_lower or 'show all in' in msg_lower or 'all data in' in msg_lower:
            # Extract table name
            table_match = re.search(r'(?:in|from)\s+(\w+)', msg_lower)
            if table_match:
                table_name = table_match.group(1)
                query = f"SELECT * FROM {database}.{table_name} LIMIT 50"
                result = execute_query(database, query)
                answer = f"## 📊 All Data from **{table_name}**\n\n{result}"
                response_type = 'custom_query'
            else:
                answer = "Please specify the table name. Example: \"show all data in activity\""
                response_type = 'error'
        
        # Check for active databases query
        elif 'active database' in msg_lower or 'active db' in msg_lower or 'show active' in msg_lower:
            result = list_active_databases()
            answer = result
            response_type = 'database'
        
        # Check for global search across all active databases
        elif 'search all' in msg_lower or 'search everywhere' in msg_lower or 'global search' in msg_lower:
            words = message.split()
            search_idx = next((i for i, w in enumerate(words) if w.lower() in ['search', 'find']), -1)
            if search_idx >= 0 and search_idx + 1 < len(words):
                search_term = words[search_idx + 1].strip('"\'.,')
                result = search_all_active_databases(search_term)
                answer = result
                response_type = 'global_search'
            else:
                answer = "Please specify what to search for."
                response_type = 'error'
        
        # Check for custom SQL query
        elif 'query' in msg_lower and ('select' in msg_lower or 'SELECT' in message):
            query_start = message.lower().find('select')
            if query_start >= 0:
                sql_query = message[query_start:].strip()
                result = execute_query(database, sql_query)
                answer = result
                response_type = 'custom_query'
            else:
                answer = "Could not find SELECT query in your message."
                response_type = 'error'
        
        # Check for database listing
        elif any(phrase in msg_lower for phrase in ['list database', 'show database', 'what databases', 'all databases']):
            result = list_databases()
            answer = f"**All Databases:**\n{result}\n\n💡 Tip: Ask for 'active databases' to see only active ones."
            response_type = 'database'
        
        # Check for "show tables in X" queries
        elif any(phrase in msg_lower for phrase in ['show tables', 'list tables', 'tables in', 'what tables']):
            handler = get_db_handler()
            tables = handler.get_tables(database)
            
            if not tables:
                answer = f"❌ Could not access database '{database}'"
                response_type = 'error'
            else:
                # Use the enhanced analyze_database function
                answer = analyze_database(database)
                response_type = 'database'
        
        # Search queries
        elif 'search' in msg_lower:
            words = message.split()
            search_idx = next((i for i, w in enumerate(words) if w.lower() in ['search', 'find']), -1)
            if search_idx >= 0 and search_idx + 1 < len(words):
                search_term = words[search_idx + 1].strip('"\'.,')
                result = smart_search(database, search_term)
                answer = ask_deepseek(message, [result], conversation_context, relevant_facts_text)
                response_type = 'search'
            else:
                answer = "Please specify what to search for."
                response_type = 'error'
        
        # Database analysis
        elif any(kw in msg_lower for kw in ['analyze', 'structure', 'schema']):
            result = analyze_database(database)
            answer = ask_deepseek(message, [result], conversation_context, relevant_facts_text)
            response_type = 'database'
        
        # General questions
        else:
            answer = ask_general_question(message, conversation_context, relevant_facts_text)
            response_type = 'general'
        
        bot_msg = create_message('bot', answer, session_id, user_msg['id'], response_type=response_type)
        chat_sessions[session_id].append(bot_msg)
        
        context_mgr.add_message(session_id, answer, 'bot')
        learn_from_conversation(chat_sessions[session_id])
        
        # Store in knowledge base
        if response_type in ['database', 'search', 'global_search', 'custom_query', 'table_details']:
            entities = kb.extract_entities_from_text(message + " " + answer)
            for db in entities.get('databases', []):
                kb.add_fact(f"Database {db} queried", category="databases", confidence=0.7)
        
        kb.add_example(message, answer, category=response_type)
        
        return jsonify(bot_msg)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'type': 'bot',
            'message': f"An error occurred: {str(e)}",
            'timestamp': datetime.now().strftime("%H:%M"),
            'error': True
        }), 500

@app.route('/api/clear', methods=['POST'])
def clear_chat():
    session_id = request.json.get('session_id', 'default')
    chat_sessions[session_id] = []
    get_context_manager().clear_session(session_id)
    return jsonify({'success': True})

@app.route('/api/history', methods=['GET'])
def get_history():
    session_id = request.args.get('session_id', 'default')
    return jsonify({'history': chat_sessions.get(session_id, [])})

@app.route('/api/server-info', methods=['GET'])
def server_info():
    local_ip = get_local_ip()
    return jsonify({
        'success': True,
        'local_ip': local_ip,
        'port': 8080,
        'access_url': f'http://{local_ip}:8080'
    })

@app.route('/api/test-database', methods=['GET'])
def test_database():
    try:
        databases = get_db_handler().get_databases()
        active_dbs = get_db_handler().get_active_databases()
        return jsonify({
            'success': True,
            'message': 'Database connected!',
            'total_databases': len(databases),
            'active_databases': len(active_dbs),
            'databases': databases[:10]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"""
{'='*70}
🚀 Abegail AI Assistant - Enhanced Database Edition
{'='*70}
📡 Access URLs:
   🏠 Local:   http://127.0.0.1:8080
   🌐 Network: http://{local_ip}:8080

✨ Features:
   💾 Full Database Exploration
   🎯 Active Database Detection
   🔍 Global Search Across Active Databases
   💬 AI Chat with Context
   🧠 Learning System
   📚 Knowledge Base
   📝 Custom SQL Queries
   📋 Detailed Table Information

💡 Try:
   - "show active databases"
   - "show tables in ledtech"
   - "show table activity in operators"
   - "show all data in activity"
   - "show activity from today"
   - "show activity from yesterday"
   - "show activity from last 7 days"
   - "show activity from 2024-01-01 to 2024-01-31"
   - "search for KE0152 in ledtech"
   - "search all for KE0152"
   - "query: SELECT * FROM operators.activity LIMIT 10"
{'='*70}
""")
    app.run(debug=False, host='0.0.0.0', port=8080, threaded=True)