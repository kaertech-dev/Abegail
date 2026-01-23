# quick_responses.py - Streamlined Quick Responses
import json
import os
from datetime import datetime

LEARNING_DATA_FILE = "learning_data.json"

GREETINGS = {
    'hi': "Hello! 👋 How can I help you?",
    'hello': "Hi there! 😊 What can I do for you?",
    'hey': "Hey! How can I assist you?",
    'good morning': "Good morning! ☀️",
    'good afternoon': "Good afternoon!",
    'good evening': "Good evening! 🌙",
}

FAREWELLS = {
    'bye': "Goodbye! 👋",
    'goodbye': "Take care! 😊",
    'see you': "See you! 👋",
}

THANKS = {
    'thanks': "You're welcome! 😊",
    'thank you': "You're very welcome! 💫",
}

HELP_TEXT = """I can help you with:

💾 **Database Operations:**
- List databases
- Query tables
- Search data
- Analyze schemas

💡 **General Questions:**
- Answer questions
- Have conversations

Just ask me anything about databases or data!"""

class LearningSystem:
    def __init__(self):
        self.data = self._load_learning_data()
        self.learned_responses = self.data.get('learned_responses', {})
        
    def _load_learning_data(self):
        if os.path.exists(LEARNING_DATA_FILE):
            try:
                with open(LEARNING_DATA_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'learned_responses': {}, 'last_updated': datetime.now().isoformat()}
    
    def _save_learning_data(self):
        try:
            self.data['last_updated'] = datetime.now().isoformat()
            with open(LEARNING_DATA_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save: {e}")

_learning_system = None

def get_learning_system():
    global _learning_system
    if _learning_system is None:
        _learning_system = LearningSystem()
    return _learning_system

def check_quick_response(message):
    """Check for quick responses"""
    if not message:
        return None
    
    msg = message.lower().strip().rstrip('.,!?;:')
    
    all_responses = {**GREETINGS, **FAREWELLS, **THANKS, 'help': HELP_TEXT}
    all_responses.update(get_learning_system().learned_responses)
    
    for key, response in all_responses.items():
        if msg == key.lower() or msg.startswith(key.lower() + ' '):
            return response
    
    return None

def learn_from_conversation(messages_history):
    """Learn from conversation"""
    try:
        from knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        
        for i in range(len(messages_history) - 1):
            if messages_history[i].get('type') == 'user' and messages_history[i+1].get('type') == 'bot':
                user_msg = messages_history[i].get('message', '')
                bot_msg = messages_history[i+1].get('message', '')
                kb.add_example(user_msg, bot_msg, category=messages_history[i+1].get('response_type', 'general'))
    except Exception as e:
        print(f"⚠️ Learning error: {e}")