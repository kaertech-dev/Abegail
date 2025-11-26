# project_abegail/MCP/chatbot_ai/config.py
"""
Configuration settings for the chatbot application
"""

# DeepSeek API Configuration
DEEPSEEK_API_KEY = "sk-1580c429372d45d1a537ff703974be6e"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# MCP Server Configuration
MCP_SERVER_URL = "http://localhost/activity"
MCP_ENABLED = True

# Knowledge Base
KNOWLEDGE_BASE = """
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

# Company Keywords for Routing
COMPANY_KEYWORDS = [
    'production', 'report', 'operator', 'download', 'data',
    'company', 'today', 'yesterday', 'this week', 'statistics',
    'performance', 'metrics', 'excel', 'csv', 'api', 'workers',
    'manufacturing', 'output', 'records', 'database','EK', 'KE', 'LL'
]

# Quick Response Patterns
QUICK_RESPONSE_PATTERNS = {
    r'Good Morning!|goodmorning|morning|greetings': [
        "Hello, good morning! what can I help? 😊",
        "Hi there! How can I help you?",
        "Hey! Nice to meet you! please tell me what can I help you with?"
    ],
    r'Good Afternoon!|good afternoon|afternoon|greetings': [
        "Hello, good afternoon! what can I help? 😊",
        "Hi there! How can I help you?",
        "Hey! Nice to meet you! please tell me what can I help you with?"
    ],
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
    ],
    r'nice to meet you': [
        "nice to meet you too! I'm Abegail your AI assistance, what task you work on?"
    ]
}

# Fallback Responses
FALLBACK_RESPONSES = [
    "That's interesting! Can you tell me more about that?",
    "I'm still learning about that topic. Could you rephrase your question?",
    "That's a great point! What else would you like to know?",
    "I'm not sure I understand completely. Could you elaborate?",
    "Fascinating! I'd love to learn more about that.",
    "That's beyond my current knowledge, but I'm always learning!",
    "I appreciate you sharing that with me. What's on your mind?"
]

GENERAL_FALLBACK_RESPONSES = [
    "I'm here to chat with you! What would you like to talk about?",
    "Let's have a conversation! Tell me something interesting.",
    "I'm listening! What's on your mind today?",
    "That's nice! What else would you like to discuss?"
]