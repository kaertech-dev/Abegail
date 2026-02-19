# app.py - Refactored with Modular Architecture
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import re
import csv
import socket
import traceback

from db_handler import get_db_handler
from ai_handler import ask_general_question, query_processor_LLM
from quick_responses import check_quick_response, learn_from_conversation
from context_manager import get_context_manager
from knowledge_base import get_knowledge_base
from query_router import extract_database_name
from session_manager import get_session_manager
from unified_mcp_client import get_sync_wrapper
from activity_routes import handle_activity_query
from attendance_routes import handle_attendance_query
from database_routes import handle_database_query

from mcp_activity_client import handle_activity_query_via_mcp
from mcp_attendance_client import handle_attendance_query_via_mcp


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST"]}})

DEFAULT_DATABASE = "operators"

def get_local_ip():
    """Get local IP address"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    # method to export to csv
    base_path = "c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/csv_files/"
    return send_from_directory(base_path, filename, as_attachment=True)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint - routes queries to appropriate handlers"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not message:
            return jsonify({'error': 'Empty message'}), 400
        
        # Initialize managers
        session_mgr = get_session_manager()
        context_mgr = get_context_manager()
        kb = get_knowledge_base()
        
        # Ensure session exists
        session_mgr.ensure_session_exists(session_id)
        
        actual_message = message
        if 'debug123' in message or 'debug456' in message:
            actual_message = message[9:]
        
        # Create and add user message
        user_msg = session_mgr.create_message('user', actual_message, session_id)
        session_mgr.add_message(session_id, user_msg)
        
        # Check for quick responses first
        # quick_resp = check_quick_response(message)
        # if quick_resp:
        #     bot_msg = session_mgr.create_message('bot', quick_resp, session_id, 
        #                                          user_msg['id'], response_type='quick')
        #     session_mgr.add_message(session_id, bot_msg)
        #     context_mgr.add_message(session_id, message, 'user')
        #     context_mgr.add_message(session_id, quick_resp, 'bot')
        #     learn_from_conversation(session_mgr.get_session(session_id))
        #     return jsonify(bot_msg)
        
        name_pattern = r'name is (\w+)'
        name_match = re.search(name_pattern, message)
        if name_match:
            context_mgr.add_fact(session_id, {'User name': name_match.group(1).title()})
        
        # message = message.replace('my', context_mgr.fill_name(session_id))
        # print("New message: ", message)
        
        # Add to context
        # context_mgr.add_message(session_id, actual_message, 'user')
        
        # Get context and knowledge
        conversation_context = context_mgr.get_relevant_context(session_id, actual_message, max_messages=5)
        relevant_facts = kb.search_facts(message, limit=3)
        relevant_facts_text = [f['fact'] for f in relevant_facts]

        # synchronous wrapper for unified mcp client
        # wrapper handles routing logic
        # unified client call appropriate server
        # merge ai handler to sync wrapper
        # unified_mcp_client = get_sync_wrapper()
        
        # Extract database name
        database = extract_database_name(message) or DEFAULT_DATABASE
        
        # Route query to appropriate handler
        result = None
        
        # Priority 1: Activity Monitoring
        if 'debug123' in message:
            result = handle_activity_query_via_mcp(message)
        
        # Priority 2: Attendance
        elif 'debug456' in message:
            result = handle_attendance_query_via_mcp(message)
        
        # Priority 3: Database queries
        # if not handler_response:
        #     handler_response = handle_database_query(message, database, conversation_context, relevant_facts_text)
        #     result = handler_response
        
        # Default: General AI response
        if not result:
            result = ask_general_question(message, conversation_context)
        
        # Create and add bot message
        csv_filename = result.get('csv_file')
        bot_msg = session_mgr.create_message('bot', result['answer'], session_id, user_msg['id'], 
                                            response_type=result['response_type'], csv = csv_filename)
        session_mgr.add_message(session_id, bot_msg)

        # Update context and learning
        if 'Request timeout' not in result['answer']:
            if 'debug123' in message or 'debug456' in message:
                message = message[9:]
            # context_mgr.add_message(session_id, result, 'bot')
            context_mgr.update_history(session_id, message, result['answer'])
            learn_from_conversation(session_mgr.get_session(session_id))
        
            # Store in knowledge base
            _update_knowledge_base(kb, message, result['answer'], result['response_type'])
        
        return jsonify(bot_msg)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'type': 'bot',
            'message': f"An error occurred: {str(e)}",
            'timestamp': datetime.now().strftime("%H:%M"),
            'error': True
        }), 500

def _update_knowledge_base(kb, message: str, answer: str, response_type: str):
    """Update knowledge base with query results"""
    tracked_types = [
        'database', 'search', 'global_search', 'custom_query', 'table_details',
        'attendance', 'attendance_presence', 'attendance_count',
        'activity_general', 'activity_employee', 'activity_date', 'activity_summary'
    ]
    
    if response_type in tracked_types:
        entities = kb.extract_entities_from_text(message + " " + answer)
        for db in entities.get('databases', []):
            kb.add_fact(f"Database {db} queried", category="databases", confidence=0.7)
    
    kb.add_example(message, answer, category=response_type)

@app.route('/api/clear', methods=['POST'])
def clear_chat():
    """Clear chat session"""
    session_id = request.json.get('session_id', 'default')
    get_session_manager().clear_session(session_id)
    get_context_manager().clear_session(session_id)
    return jsonify({'success': True})

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get chat history"""
    session_id = request.args.get('session_id', 'default')
    return jsonify({'history': get_session_manager().get_session(session_id)})

@app.route('/api/server-info', methods=['GET'])
def server_info():
    """Get server information"""
    local_ip = get_local_ip()
    return jsonify({
        'success': True,
        'local_ip': local_ip,
        'port': 8080,
        'access_url': f'http://{local_ip}:8080'
    })

@app.route('/api/test-database', methods=['GET'])
def test_database():
    """Test database connection"""
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

@app.route('/chart')
def homepage():
    with open('./csv_files/Bryan_2026-02-01_2026-02-15.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        records = [row for row in reader]

    tups = {}
    for rec in records:
        date_r, time_r = rec['timestamp'].split()
        h,m,s = time_r.split(':')
        time_p = float(h) + (float(m)/60)
        if date_r not in tups:
            tups[date_r] = [time_p]
        else:
            tups[date_r].append(time_p)
    labels = list(tups.keys())
    data = list(tups.values())
    name = records[0]['employee_name']
    
    return render_template('chartjs-example.html', labels=labels, data=data, name=name)

def print_startup_banner():
    """Print startup banner with server info"""
    local_ip = get_local_ip()
    print(f"""
{'='*70}
🚀 Abegail AI Assistant - Full System
{'='*70}
📡 Access URLs:
   🏠 Local:   http://127.0.0.1:8080
   🌐 Network: http://{local_ip}:8080

✨ Features:
   💾 Full Database Exploration
   🎯 Active Database Detection
   🔍 Global Search Across Active Databases
   
   👤 Advanced Attendance Tracking:
      • Check employee presence
      • View attendance by date/range
      • Count operators present
      • Smart name matching
   
   📊 Activity Monitoring:
      • Real-time activity tracking
      • Employee activity queries
      • Activity summaries
      • Date-filtered activities
   
   💬 AI Chat with Context
   🧠 Learning System
   📚 Knowledge Base

💡 Try These Activity Queries:
   📊 General Activity:
      - "show all activities"
      - "activity summary"
      - "what activities are there"
   
   👤 Employee Activity:
      - "show activities for Ryan"
      - "what is KE0152 doing?"
      - "activity for Maria"
   
   📅 Date-based Activity:
      - "show activities today"
      - "activities yesterday"
      - "activities from last 7 days"

💡 Attendance Queries:
   ✅ Presence Check:
      - "is Ryan present today?"
      - "is KE0152 here today?"
   
   📅 Date-based:
      - "show attendance today"
      - "attendance from last 7 days"
   
   🔢 Count:
      - "how many operators are present today?"

💡 Database Queries:
   - "show active databases"
   - "show tables in ledtech"
   - "search all for KE0152"
{'='*70}
""")

if __name__ == '__main__':
    print_startup_banner()
    app.run(debug=False, host='0.0.0.0', port=8080, threaded=True)