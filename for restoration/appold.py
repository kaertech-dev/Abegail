from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
import socket

# Import handlers
from data_handler import fetch_company_data
from ai_handler import ask_deepseek, ask_general_question
from mcp_db_handler import (
    query_database_via_mcp, 
    get_table_data_via_mcp,
    search_tables_via_mcp,
    list_databases_via_mcp
)
from email_handler import (
    send_email,
    parse_email_request,
    format_email_confirmation,
    get_email_help
)

# Import new enhanced modules
from quick_responses import check_quick_response
from mcp_db_handler_enhanced import (
    get_enhanced_handler,
    analyze_database,
    smart_search_database,
    get_table_details,
    auto_query_database
)
from query_router_enhanced import (
    parse_query_intent,
    extract_database_name,
    extract_table_name
)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST"]}})

# Session storage
chat_sessions = {}
pending_emails = {}

# Default database name - CHANGE THIS TO YOUR DATABASE
DEFAULT_DATABASE = "operators"  # ← Change to your actual database name

@app.after_request
def add_security_headers(response):
    response.headers.update({
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block'
    })
    return response

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "Unable to determine IP"

def create_message(msg_type, message, session_id, parent_id=None, **kwargs):
    return {
        'type': msg_type,
        'message': message,
        'timestamp': datetime.now().strftime("%H:%M"),
        'id': f"msg_{len(chat_sessions[session_id])}",
        'parent_id': parent_id,
        **kwargs
    }

def handle_database_query(message):
    """Intelligently route database queries to appropriate MCP functions"""
    msg = message.lower()
    
    try:
        # List databases
        if any(phrase in msg for phrase in ['list database', 'show database', 'what databases', 'all databases']):
            result = list_databases_via_mcp()
            if result:
                return {
                    'success': True,
                    'data': f"Available Databases:\n{result}"
                }
        
        # Search across tables
        elif 'search' in msg and ('database' in msg or 'table' in msg):
            words = message.split()
            search_idx = words.index('search') if 'search' in words else -1
            if search_idx >= 0 and search_idx + 1 < len(words):
                search_term = words[search_idx + 1].strip('",\'')
                database = extract_database_name(message)
                if database:
                    result = search_tables_via_mcp(database, search_term)
                    return {
                        'success': True,
                        'data': f"Search Results:\n{result}"
                    }
        
        # Query specific table
        elif 'query' in msg or 'select' in msg or 'from' in msg:
            database = extract_database_name(message)
            
            if 'select' in msg.lower():
                query_start = msg.lower().find('select')
                query = message[query_start:].strip()
                
                if database:
                    result = query_database_via_mcp(database, query)
                    return {
                        'success': True,
                        'data': f"Query Results:\n{result}"
                    }
            else:
                table = extract_table_name(message)
                if database and table:
                    result = get_table_data_via_mcp(database, table)
                    return {
                        'success': True,
                        'data': f"Table Data:\n{result}"
                    }
        
        result = list_databases_via_mcp()
        return {
            'success': True,
            'data': f"I can help with database queries. Available databases:\n{result}\n\nTry: 'query the [table] table in [database]' or 'search for [term] in [database]'"
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

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
        
        chat_sessions.setdefault(session_id, [])
        
        # Add user message
        user_msg = create_message('user', message, session_id)
        chat_sessions[session_id].append(user_msg)
        
        # ═══════════════════════════════════════════════════════════════
        # 1. CHECK FOR EMAIL CONFIRMATION (YES/NO RESPONSES)
        # ═══════════════════════════════════════════════════════════════
        if session_id in pending_emails:
            msg_lower = message.lower().strip()
            if msg_lower in ['yes', 'y', 'yeah', 'yep', 'confirm', 'send it']:
                pending = pending_emails[session_id]
                result = send_email(pending['recipient'], pending['subject'], pending['body'])
                del pending_emails[session_id]
                
                if result['success']:
                    response_msg = f"✅ {result['message']}\n\nYour email has been sent successfully!"
                    response_type = 'email'
                else:
                    response_msg = f"❌ Failed to send email: {result['error']}"
                    response_type = 'error'
                
                bot_msg = create_message('bot', response_msg, session_id, user_msg['id'], 
                                        response_type=response_type)
                chat_sessions[session_id].append(bot_msg)
                return jsonify(bot_msg)
                
            elif msg_lower in ['no', 'n', 'nope', 'cancel', 'dont send', "don't send"]:
                del pending_emails[session_id]
                response_msg = "❌ Email cancelled. Let me know if you'd like to compose a new one!"
                bot_msg = create_message('bot', response_msg, session_id, user_msg['id'], 
                                        response_type='cancelled')
                chat_sessions[session_id].append(bot_msg)
                return jsonify(bot_msg)
        
        # ═══════════════════════════════════════════════════════════════
        # 2. CHECK FOR QUICK RESPONSES (GREETINGS, HELP, ETC.)
        # ═══════════════════════════════════════════════════════════════
        quick_resp = check_quick_response(message)
        if quick_resp:
            bot_msg = create_message('bot', quick_resp, session_id, user_msg['id'], 
                                    response_type='quick')
            chat_sessions[session_id].append(bot_msg)
            return jsonify(bot_msg)
        
        # ═══════════════════════════════════════════════════════════════
        # 3. INTELLIGENT QUERY ROUTING - PARSE USER INTENT
        # ═══════════════════════════════════════════════════════════════
        intent = parse_query_intent(message)
        print(f"🧠 Intent detected: {intent['type']}")
        print(f"   Database: {intent['database']}")
        print(f"   Table: {intent['table']}")
        
        # ═══════════════════════════════════════════════════════════════
        # 4. ROUTE BASED ON INTENT TYPE
        # ═══════════════════════════════════════════════════════════════
        
        # --- SCHEMA INTROSPECTION ---
        if intent['type'] == 'schema_introspection':
            print(f"🔍 Schema introspection requested")
            database = intent['database'] or DEFAULT_DATABASE
            
            if intent['table']:
                print(f"   Analyzing table: {database}.{intent['table']}")
                result = get_table_details(database, intent['table'])
            else:
                print(f"   Analyzing entire database: {database}")
                result = analyze_database(database)
            
            answer = ask_deepseek(message, [result])
            response_type = 'schema'
        
        # --- SMART SEARCH ---
        elif intent['type'] == 'smart_search':
            print(f"🔎 Smart search requested")
            database = intent['database'] or DEFAULT_DATABASE
            search_term = intent['search_term']
            
            if search_term:
                print(f"   Searching for '{search_term}' in {database}")
                result = smart_search_database(database, search_term)
                answer = ask_deepseek(message, [result])
                response_type = 'search'
            else:
                answer = "❌ Please specify what you'd like to search for.\n\nExample: 'Search for KE0152 in production database'"
                response_type = 'error'
        
        # --- AUTO-QUERY ---
        elif intent['type'] == 'auto_query':
            print(f"⚡ Auto-query requested")
            database = intent['database'] or DEFAULT_DATABASE
            print(f"   Generating query for: {database}")
            
            result = auto_query_database(database, message)
            answer = ask_deepseek(message, [result])
            response_type = 'auto_query'
        
        # --- EMAIL ---
        elif intent['type'] == 'email':
            print(f"📧 Email request")
            email_details = parse_email_request(message)
            
            if email_details:
                pending_emails[session_id] = email_details
                answer = format_email_confirmation(
                    email_details['recipient'],
                    email_details['subject'],
                    email_details['body']
                )
                response_type = 'email_confirmation'
            else:
                answer = """❌ I couldn't parse the email request. Please use this format:

`send email to recipient@example.com subject: Your Subject body: Your message`

Or type 'email help' for more examples."""
                response_type = 'error'
        
        # --- DATABASE (Explicit SQL queries) ---
        elif intent['type'] == 'database':
            print(f"💾 Direct database query")
            db_result = handle_database_query(message)
            
            if db_result['success']:
                answer = ask_deepseek(message, [f"Database Query Results:\n{db_result['data']}"])
                response_type = 'database'
            else:
                answer = f"❌ Database Error: {db_result['error']}"
                response_type = 'error'
        
        # --- COMPANY DATA ---
        elif intent['type'] == 'company':
            print(f"📊 Company data query")
            company_data, raw_json = fetch_company_data()
            
            if not company_data:
                answer = "❌ Sorry, I couldn't fetch company data from http://localhost/activity. Please check if the API is running."
                response_type = 'error'
            else:
                print(f"✅ Fetched {len(raw_json) if isinstance(raw_json, list) else 'data'} from API")
                answer = ask_deepseek(message, company_data)
                response_type = 'company'
        
        # --- GENERAL ---
        else:  # general
            print(f"💬 General conversation")
            answer = ask_general_question(message)
            response_type = 'general'
        
        # ═══════════════════════════════════════════════════════════════
        # 5. SEND RESPONSE TO USER
        # ═══════════════════════════════════════════════════════════════
        bot_msg = create_message('bot', answer, session_id, user_msg['id'], 
                                response_type=response_type)
        chat_sessions[session_id].append(bot_msg)
        
        return jsonify(bot_msg)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'type': 'bot',
            'message': f"An error occurred: {str(e)}",
            'timestamp': datetime.now().strftime("%H:%M"),
            'error': True
        }), 500

@app.route('/api/edit', methods=['POST'])
def edit_message():
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        message_id = data.get('message_id')
        new_message = data.get('new_message', '').strip()
        
        if not new_message or not message_id or session_id not in chat_sessions:
            return jsonify({'error': 'Invalid request'}), 400
        
        history = chat_sessions[session_id]
        msg_idx = next((i for i, m in enumerate(history) if m.get('id') == message_id and m['type'] == 'user'), None)
        
        if msg_idx is None:
            return jsonify({'error': 'Message not found'}), 404
        
        history[msg_idx].update({
            'message': new_message, 
            'edited': True, 
            'timestamp': datetime.now().strftime("%H:%M")
        })
        
        if msg_idx + 1 < len(history) and history[msg_idx + 1]['type'] == 'bot':
            history.pop(msg_idx + 1)
        
        # Generate new response using enhanced intent parsing
        quick_resp = check_quick_response(new_message)
        if quick_resp:
            answer = quick_resp
            response_type = 'quick'
        else:
            intent = parse_query_intent(new_message)
            
            if intent['type'] == 'schema_introspection':
                database = intent['database'] or DEFAULT_DATABASE
                if intent['table']:
                    result = get_table_details(database, intent['table'])
                else:
                    result = analyze_database(database)
                answer = ask_deepseek(new_message, [result])
                response_type = 'schema'
            
            elif intent['type'] == 'smart_search':
                database = intent['database'] or DEFAULT_DATABASE
                if intent['search_term']:
                    result = smart_search_database(database, intent['search_term'])
                    answer = ask_deepseek(new_message, [result])
                else:
                    answer = "Please specify what to search for."
                response_type = 'search'
            
            elif intent['type'] == 'auto_query':
                database = intent['database'] or DEFAULT_DATABASE
                result = auto_query_database(database, new_message)
                answer = ask_deepseek(new_message, [result])
                response_type = 'auto_query'
            
            elif intent['type'] == 'email':
                email_details = parse_email_request(new_message)
                if email_details:
                    pending_emails[session_id] = email_details
                    answer = format_email_confirmation(
                        email_details['recipient'],
                        email_details['subject'],
                        email_details['body']
                    )
                    response_type = 'email_confirmation'
                else:
                    answer = "I couldn't parse the email request. Type 'email help' for format."
                    response_type = 'error'
            
            elif intent['type'] == 'database':
                db_result = handle_database_query(new_message)
                if db_result['success']:
                    answer = ask_deepseek(new_message, [f"Database Query Results:\n{db_result['data']}"])
                    response_type = 'database'
                else:
                    answer = f"Database Error: {db_result['error']}"
                    response_type = 'error'
            
            elif intent['type'] == 'company':
                company_data, _ = fetch_company_data()
                if not company_data:
                    return jsonify({'error': True, 'message': "Could not fetch company data"}), 500
                answer = ask_deepseek(new_message, company_data)
                response_type = 'company'
            
            else:
                answer = ask_general_question(new_message)
                response_type = 'general'
        
        bot_response = create_message('bot', answer, session_id, message_id, 
                                     response_type=response_type, regenerated=True)
        history.insert(msg_idx + 1, bot_response)
        
        return jsonify({
            'success': True,
            'user_message': history[msg_idx],
            'bot_response': bot_response
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear', methods=['POST'])
def clear_chat():
    session_id = request.json.get('session_id', 'default')
    chat_sessions[session_id] = []
    if session_id in pending_emails:
        del pending_emails[session_id]
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

@app.route('/api/test-api', methods=['GET'])
def test_api():
    try:
        company_data, raw_json = fetch_company_data()
        if not company_data:
            return jsonify({'success': False, 'error': 'Could not fetch data from API'}), 500
        
        return jsonify({
            'success': True,
            'records': len(raw_json) if isinstance(raw_json, list) else 'N/A',
            'preview': raw_json[:2] if isinstance(raw_json, list) else raw_json,
            'message': 'API is working correctly!'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-database', methods=['GET'])
def test_database():
    try:
        result = list_databases_via_mcp()
        return jsonify({
            'success': True,
            'databases': result,
            'message': 'MCP Database connection is working!'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-email', methods=['POST'])
def test_email():
    try:
        data = request.json
        test_recipient = data.get('recipient', 'test@example.com')
        result = send_email(
            test_recipient,
            'Test Email from Abegail AI',
            'This is a test email to verify the email configuration is working correctly.'
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"""
{'='*70}
🚀 Abegail AI Assistant - Enhanced with Database Introspection
{'='*70}
📡 Access URLs:
   🏠 Local:   http://127.0.0.1:8080
   🌐 Network: http://{local_ip}:8080

✨ Enhanced Features:
   🔍 Schema Introspection - Auto-detect database structure
   🔎 Smart Search - Search across all tables automatically
   ⚡ Auto-Query - Natural language to SQL
   📊 Company Production Data Analysis
   💾 Direct Database Queries (Read-Only)
   📧 Email Sending Capability

📊 Data Source: http://localhost/activity
💾 Database: 192.168.1.38 (via MCP)
🗄️  Default Database: {DEFAULT_DATABASE}
⚙️  AI Model: deepseek-r1:1.5b

💡 Try these new features:
   - "Analyze the {DEFAULT_DATABASE} database"
   - "Show me the structure of operators table"
   - "Search for KE0152 in {DEFAULT_DATABASE}"
   - "Show me all recent data"
   - "List all databases"

{'='*70}
""")
    
    # Test connections
    try:
        print("🔍 Testing API connection...")
        company_data, raw_json = fetch_company_data()
        if company_data:
            record_count = len(raw_json) if isinstance(raw_json, list) else 'N/A'
            print(f"✅ API connection successful! Found {record_count} records")
        else:
            print("⚠️  Warning: Could not fetch data from API")
    except Exception as e:
        print(f"⚠️  Warning: API connection test failed: {e}")
    
    try:
        print("\n🔍 Testing MCP Database connection...")
        result = list_databases_via_mcp()
        print(f"✅ MCP Database connection successful!")
        print(f"   Available databases: {result}")
    except Exception as e:
        print(f"⚠️  Warning: MCP Database connection failed: {e}")
    
    try:
        print("\n🔍 Testing Enhanced Database Features...")
        handler = get_enhanced_handler()
        databases = handler.list_databases_with_details()
        if 'databases' in databases:
            print(f"✅ Enhanced features working!")
            print(f"   Found {databases['count']} databases")
        else:
            print(f"⚠️  Warning: Enhanced features not fully functional")
    except Exception as e:
        print(f"⚠️  Warning: Enhanced features test failed: {e}")
    
    print("="*70 + "\n")
    
    app.run(debug=False, host='0.0.0.0', port=8080, threaded=True)