# project_abegail/MCP/chatbot_ai/chatbot_services.py
"""
Chatbot service for handling local responses and routing
"""
import nltk
import random
import string
import re
import sys
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import config first
try:
    from config import (
        KNOWLEDGE_BASE, COMPANY_KEYWORDS, QUICK_RESPONSE_PATTERNS,
        FALLBACK_RESPONSES, GENERAL_FALLBACK_RESPONSES, MCP_ENABLED
    )
except ImportError:
    # Fallback values if config not found
    KNOWLEDGE_BASE = "Hello! I'm Abegail."
    COMPANY_KEYWORDS = ['production', 'report', 'operator']
    QUICK_RESPONSE_PATTERNS = {}
    FALLBACK_RESPONSES = ["I'm not sure about that."]
    GENERAL_FALLBACK_RESPONSES = ["Let's chat!"]
    MCP_ENABLED = True

# Now import deepseek_service
from deepseek_service import ask_deepseek_with_mcp

# Initialize NLTK
def initialize_nltk():
    """Download required NLTK data"""
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    nltk.download('wordnet', quiet=True)

# Tokenize knowledge base
sent_tokens = nltk.sent_tokenize(KNOWLEDGE_BASE)

def preprocess_text(text: str) -> str:
    """
    Normalize and clean text
    """
    text = text.lower()
    text = ''.join([char for char in text if char not in string.punctuation])
    return text

def is_company_question(user_input: str) -> bool:
    """
    Determine if the question is about company/production data
    """
    user_lower = user_input.lower()
    return any(keyword in user_lower for keyword in COMPANY_KEYWORDS)

def get_quick_response(user_input: str) -> str:
    """
    Check for quick pattern-based responses
    """
    user_input = user_input.lower().strip()
    
    for pattern, responses in QUICK_RESPONSE_PATTERNS.items():
        if re.search(pattern, user_input):
            return random.choice(responses)
    
    return None

def get_local_response(user_input: str) -> str:
    """
    Get response using local TF-IDF similarity matching
    """
    user_input = user_input.lower().strip()
    sent_tokens.append(user_input)
    
    tfidf_vectorizer = TfidfVectorizer(
        tokenizer=nltk.word_tokenize, 
        stop_words='english'
    )
    
    try:
        tfidf_matrix = tfidf_vectorizer.fit_transform(sent_tokens)
        similarity_scores = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
        similar_sentence_idx = similarity_scores.argsort()[0][-1]
        similarity_score = similarity_scores[0][similar_sentence_idx]
        
        sent_tokens.pop()
        
        if similarity_score > 0.1:
            return sent_tokens[similar_sentence_idx]
        else:
            return random.choice(FALLBACK_RESPONSES)
            
    except Exception as e:
        sent_tokens.pop()
        return random.choice(GENERAL_FALLBACK_RESPONSES)


async def get_response(user_input: str) -> dict:
    """
    Main response function that routes to appropriate handler
    
    Returns:
        dict: Response with metadata
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
                "response": get_local_response(user_input),
                "source": "local_fallback",
                "error": deepseek_result.get("error")
            }
    
    # Use local ML approach for general questions
    return {
        "response": get_local_response(user_input), 
        "source": "local"
    }