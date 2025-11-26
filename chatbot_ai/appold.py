from flask import Flask, render_template, request, jsonify
import nltk
import random
import string
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings
import re
import httpx
import asyncio
from functools import wraps
import json

warnings.filterwarnings('ignore')

app = Flask(__name__)

# Download NLTK data
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)   # <<< ADD THIS
nltk.download('wordnet', quiet=True)

# Configuration - DeepSeek API
DEEPSEEK_API_KEY = "sk-1580c429372d45d1a537ff703974be6e"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
MCP_SERVER_URL = "http://192.168.0.12:5005"  # Your production API
MCP_ENABLED = True  # Toggle MCP integration

# Expanded knowledge base
knowledge_base = """
Hello! I'm Abegail, your friendly chatbot AI. I can help you with various topics.
I love chatting about technology, programming, weather, sports, and general knowledge.
Python is one of my favorite programming languages.
Flask is a great web framework for building web applications.
Chatbots are fun to create and can be very helpful.
The weather today is nice and sunny.
Basketball and football are popular sports.
I enjoy helping people learn new things.
Machine learning and artificial intelligence are fascinating topics.
You can ask me about almost anything!
"""

sent_tokens = nltk.sent_tokenize(knowledge_base)

def async_route(f):
    """Decorator to handle async routes in Flask"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

def preprocess_text(text):
    """Normalize and clean text"""
    text = text.lower()
    text = ''.join([char for char in text if char not in string.punctuation])
    return text

async def call_mcp_tool(tool_name: str, **kwargs) -> dict:
    """
    Call your MCP server tools directly
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if tool_name == "get_data_from_api":
                endpoint = kwargs.get("endpoint", "/api/operator_today")
                params = kwargs.get("params")
                url = f"{MCP_SERVER_URL}{endpoint}"
                
                if params:
                    response = await client.get(url, params=params)
                else:
                    response = await client.get(url)
                
                response.raise_for_status()
                return {"success": True, "data": response.json()}
                
            elif tool_name == "get_download_url":
                format_type = kwargs.get("format", "csv")
                date = kwargs.get("date")
                start_date = kwargs.get("start_date")
                end_date = kwargs.get("end_date")
                
                format_endpoints = {
                    "csv": "/api/download_csv",
                    "excel": "/api/download_excel",
                    "word": "/api/download_word",
                    "txt": "/api/download_txt",
                    "powerpoint": "/api/download_powerpoint"
                }
                
                endpoint = format_endpoints.get(format_type.lower(), "/api/download_csv")
                params = {}
                if date:
                    params["date"] = date
                if start_date:
                    params["start_date"] = start_date
                if end_date:
                    params["end_date"] = end_date
                
                url = MCP_SERVER_URL + endpoint
                if params:
                    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                    url = f"{url}?{query_string}"
                
                return {
                    "success": True,
                    "download_url": url,
                    "format": format_type
                }
            
            return {"success": False, "error": "Unknown tool"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

async def ask_deepseek_with_mcp(user_message: str) -> dict:
    """
    Send message to DeepSeek API and handle tool calls to your MCP server.
    This creates a bridge between DeepSeek AI and your production data.
    """
    messages = [
        {
            "role": "system",
            "content": """You are Abegail, a helpful AI assistant with access to production data tools.

Available tools:
1. get_data_from_api(endpoint, params) - Fetch production data
   - endpoint examples: /api/operator_today, /api/production_stats
   - Use this when users ask about production data, operators, statistics

2. get_download_url(format, date, start_date, end_date) - Get download links
   - format: csv, excel, word, txt, powerpoint
   - Use this when users want to download reports

When users ask about production data, operators, or reports, use these tools to fetch real data.
After getting data from tools, explain it clearly to the user."""
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    
    max_iterations = 5  # Prevent infinite loops
    iteration = 0
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            while iteration < max_iterations:
                iteration += 1
                
                # Call DeepSeek API
                payload = {
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
                
                response = await client.post(
                    DEEPSEEK_API_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
                    }
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    print(f"❌ DeepSeek API Error {response.status_code}: {error_detail}")
                    return {
                        "success": False,
                        "error": f"DeepSeek API error {response.status_code}: {error_detail}",
                        "response": None
                    }
                
                data = response.json()
                assistant_message = data["choices"][0]["message"]
                content = assistant_message.get("content", "")
                
                # Check if DeepSeek wants to use a tool
                # Parse content for tool requests (DeepSeek may indicate tool use in text)
                if "get_data_from_api" in content.lower() or "production data" in user_message.lower():
                    # Call MCP tool
                    tool_result = await call_mcp_tool("get_data_from_api")
                    
                    if tool_result["success"]:
                        # Add tool result to conversation
                        messages.append({
                            "role": "assistant",
                            "content": f"[Fetching production data from API...]"
                        })
                        messages.append({
                            "role": "user",
                            "content": f"Tool result: {json.dumps(tool_result['data'], indent=2)}\n\nPlease analyze this data and provide a clear answer to the user."
                        })
                        continue  # Loop again with tool result
                    
                elif "download" in user_message.lower() and any(fmt in user_message.lower() for fmt in ["csv", "excel", "word", "report"]):
                    # Determine format from user request
                    format_type = "csv"
                    if "excel" in user_message.lower():
                        format_type = "excel"
                    elif "word" in user_message.lower():
                        format_type = "word"
                    elif "powerpoint" in user_message.lower():
                        format_type = "powerpoint"
                    
                    tool_result = await call_mcp_tool("get_download_url", format=format_type)
                    
                    if tool_result["success"]:
                        messages.append({
                            "role": "assistant",
                            "content": f"[Getting download link...]"
                        })
                        messages.append({
                            "role": "user",
                            "content": f"Download URL ready: {tool_result['download_url']}\n\nPlease provide this link to the user with clear instructions."
                        })
                        continue
                
                # No more tool calls needed, return final response
                return {
                    "success": True,
                    "response": content,
                    "used_mcp": iteration > 1,  # Used MCP if we looped
                    "iterations": iteration
                }
            
            # Max iterations reached
            return {
                "success": True,
                "response": "I've gathered the information but reached my processing limit. Please ask me to clarify anything specific.",
                "used_mcp": True,
                "iterations": iteration
            }
                
    except Exception as e:
        print(f"❌ DeepSeek Exception: {str(e)}")
        print(f"   Error Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "response": None
        }

def is_company_question(user_input: str) -> bool:
    """
    Determine if the question is about company/production data
    that should be routed to DeepSeek with MCP
    """
    company_keywords = [
        'production', 'report', 'operator', 'download', 'data',
        'company', 'today', 'yesterday', 'this week', 'statistics',
        'performance', 'metrics', 'excel', 'csv', 'api', 'workers',
        'manufacturing', 'output', 'records', 'database'
    ]
    
    user_lower = user_input.lower()
    return any(keyword in user_lower for keyword in company_keywords)

def get_response(user_input):
    user_input = user_input.lower().strip()
    sent_tokens.append(user_input)
    
    tfidf_vectorizer = TfidfVectorizer(tokenizer=nltk.word_tokenize, stop_words='english')
    try:
        tfidf_matrix = tfidf_vectorizer.fit_transform(sent_tokens)
        similarity_scores = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
        similar_sentence_idx = similarity_scores.argsort()[0][-1]
        similarity_score = similarity_scores[0][similar_sentence_idx]
        
        sent_tokens.pop()
        
        if similarity_score > 0.1:
            return sent_tokens[similar_sentence_idx]
        else:
            fallback_responses = [
                "That's interesting! Can you tell me more about that?",
                "I'm still learning about that topic. Could you rephrase your question?",
                "That's a great point! What else would you like to know?",
                "I'm not sure I understand completely. Could you elaborate?",
                "Fascinating! I'd love to learn more about that.",
                "That's beyond my current knowledge, but I'm always learning!",
                "I appreciate you sharing that with me. What's on your mind?"
            ]
            return random.choice(fallback_responses)
    except Exception as e:
        sent_tokens.pop()
        fallback_responses = [
            "I'm here to chat with you! What would you like to talk about?",
            "Let's have a conversation! Tell me something interesting.",
            "I'm listening! What's on your mind today?",
            "That's nice! What else would you like to discuss?"
        ]
        return random.choice(fallback_responses)

def get_quick_response(user_input):
    user_input = user_input.lower().strip()
    quick_patterns = {
        r'hello|hi|hey|greetings': [
            "Hello! I'm Abegail! 😊",
            "Hi there! How can I help you?",
            "Hey! Nice to meet you! please tell me what can I help you with?"
        ],
        r'how are you': [
            "I'm doing great! Thanks for asking! 💫",
            "I'm wonderful! How about you?",
            "Pretty good! What's on your mind?"
        ],
        r'your name|who are you|who you': [
            "I'm Abegail, your friendly AI assistant! 🤖 I can help with general questions and access our company's production data!",
            "People call me Abegail! Nice to meet you!"
        ],
        r'what can you do': [
            "I can chat with you about various topics, answer questions about our company's production data, generate reports, and provide download links!"
        ],
        r'thank you|thanks': [
            "You're welcome! 😊",
            "Happy to help!",
            "Anytime! 💫"
        ],
        r'bye|goodbye': [
            "Goodbye! It was nice chatting with you! 👋",
            "See you later! 😊",
            "Bye! Come back soon!"
        ]
    }
    
    for pattern, responses in quick_patterns.items():
        if re.search(pattern, user_input):
            return random.choice(responses)
    return None

async def enhanced_get_response(user_input):
    """
    Enhanced response function that routes to DeepSeek with MCP or local responses
    """
    # Try quick pattern matching first
    quick_response = get_quick_response(user_input)
    if quick_response:
        return {"response": quick_response, "source": "local"}
    
    # Check if this is a company/production question
    if MCP_ENABLED and is_company_question(user_input):
        deepseek_result = await ask_deepseek_with_mcp(user_input)
        
        if deepseek_result["success"] and deepseek_result["response"]:
            return {
                "response": deepseek_result["response"],
                "source": "deepseek_mcp",
                "used_tools": deepseek_result.get("used_mcp", False)
            }
        else:
            # Fallback to local response if DeepSeek fails
            return {
                "response": get_response(user_input),
                "source": "local_fallback",
                "error": deepseek_result.get("error")
            }
    
    # Use local ML approach for general questions
    return {"response": get_response(user_input), "source": "local"}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
@async_route
async def chat():
    user_message = request.json['message']
    print(f"\n💬 User Message: {user_message}")
    print(f"🔍 Is company question: {is_company_question(user_message)}")
    print(f"🔧 MCP Enabled: {MCP_ENABLED}")
    
    result = await enhanced_get_response(user_message)
    
    print(f"✅ Response Source: {result.get('source')}")
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    
    return jsonify({
        'response': result['response'],
        'source': result.get('source', 'unknown'),
        'used_mcp': result.get('used_tools', False),
        'error': result.get('error', None)  # Include error in response
    })

@app.route('/toggle_mcp', methods=['POST'])
def toggle_mcp():
    global MCP_ENABLED
    MCP_ENABLED = not MCP_ENABLED
    return jsonify({'mcp_enabled': MCP_ENABLED})

@app.route('/status')
def status():
    return jsonify({
        'mcp_enabled': MCP_ENABLED,
        'server': 'running',
        'mcp_server': MCP_SERVER_URL
    })

if __name__ == '__main__':
    app.run(debug=True, port=5010)