# project_abegail/MCP/chatbot_ai/app.py

"""
Main Flask application - Abegail Chatbot
"""
from flask import Flask, render_template, request, jsonify
import warnings
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

warnings.filterwarnings('ignore')

# Initialize Flask app
app = Flask(__name__)

# Import after Flask app creation to avoid circular imports
import config
from chatbot_service import get_response, is_company_question, initialize_nltk
from utils import async_route

# Initialize NLTK on startup
initialize_nltk()

@app.route('/')
def home():
    """Render the main chat interface"""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
@async_route
async def chat():
    """
    Handle chat messages from the user
    """
    user_message = request.json['message']
    
    # Log the request
    print(f"\n💬 User Message: {user_message}")
    print(f"🔍 Is company question: {is_company_question(user_message)}")
    print(f"🔧 MCP Enabled: {config.MCP_ENABLED}")
    
    # Get response from chatbot service
    result = await get_response(user_message)
    
    # Log the response
    print(f"✅ Response Source: {result.get('source')}")
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    
    return jsonify({
        'response': result['response'],
        'source': result.get('source', 'unknown'),
        'used_mcp': result.get('used_tools', False),
        'error': result.get('error', None)
    })

@app.route('/toggle_mcp', methods=['POST'])
def toggle_mcp():
    """
    Toggle MCP integration on/off
    """
    config.MCP_ENABLED = not config.MCP_ENABLED
    return jsonify({'mcp_enabled': config.MCP_ENABLED})

@app.route('/status')
def status():
    """
    Get current system status
    """
    return jsonify({
        'mcp_enabled': config.MCP_ENABLED,
        'server': 'running',
        'mcp_server': config.MCP_SERVER_URL
    })

if __name__ == '__main__':
    app.run(debug=True, port=5010)