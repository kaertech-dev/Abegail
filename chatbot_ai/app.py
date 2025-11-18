from flask import Flask, render_template, request, jsonify
import nltk
import random
import string
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings
import re
warnings.filterwarnings('ignore')

app = Flask(__name__)

# Download NLTK data
nltk.download('punkt', quiet=True)
nltk.download('wordnet', quiet=True)

# Expanded knowledge base - this is what makes your chatbot smart!
knowledge_base = """
Hello! I'm Abegail, your friendly chatbot Ai. I can help you with various topics.
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

# Preprocess the knowledge base
sent_tokens = nltk.sent_tokenize(knowledge_base)

def preprocess_text(text):
    """Normalize and clean text"""
    text = text.lower()
    text = ''.join([char for char in text if char not in string.punctuation])
    return text

def get_response(user_input):
    user_input = user_input.lower().strip()
    
    # Add user input to sentence tokens for learning
    sent_tokens.append(user_input)
    
    # Create TF-IDF vectorizer
    tfidf_vectorizer = TfidfVectorizer(tokenizer=nltk.word_tokenize, stop_words='english')
    
    try:
        # Transform sentences to TF-IDF vectors
        tfidf_matrix = tfidf_vectorizer.fit_transform(sent_tokens)
        
        # Calculate cosine similarity between user input and all sentences
        similarity_scores = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
        
        # Find the most similar sentence
        similar_sentence_idx = similarity_scores.argsort()[0][-1]
        similarity_score = similarity_scores[0][similar_sentence_idx]
        
        # Remove user input from tokens for next iteration
        sent_tokens.pop()
        
        # If similarity score is high enough, return similar sentence
        if similarity_score > 0.1:
            return sent_tokens[similar_sentence_idx]
        else:
            # Fallback responses for low similarity
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
        # Fallback if there's any error in processing
        sent_tokens.pop()
        fallback_responses = [
            "I'm here to chat with you! What would you like to talk about?",
            "Let's have a conversation! Tell me something interesting.",
            "I'm listening! What's on your mind today?",
            "That's nice! What else would you like to discuss?"
        ]
        return random.choice(fallback_responses)

# Simple pattern matching for common questions (as backup)
def get_quick_response(user_input):
    user_input = user_input.lower().strip()
    
    quick_patterns = {
        r'hello|hi|hey|greetings': ["Hello! I'm Abegail! 😊", "Hi there! How can I help you?", "Hey! Nice to meet you!"],
        r'how are you': ["I'm doing great! Thanks for asking! 💫", "I'm wonderful! How about you?", "Pretty good! What's on your mind?"],
        r'your name|who are you': ["I'm Abegail, your friendly chatbot! 🤖", "People call me Abegail! Nice to meet you!"],
        r'what can you do': ["I can chat with you about various topics, answer questions, and learn from our conversation!"],
        r'thank you|thanks': ["You're welcome! 😊", "Happy to help!", "Anytime! 💫"],
        r'bye|goodbye': ["Goodbye! It was nice chatting with you! 👋", "See you later! 😊", "Bye! Come back soon!"]
    }
    
    for pattern, responses in quick_patterns.items():
        if re.search(pattern, user_input):
            return random.choice(responses)
    
    return None

# Enhanced get_response function that tries quick patterns first, then ML approach
def enhanced_get_response(user_input):
    # Try quick pattern matching first
    quick_response = get_quick_response(user_input)
    if quick_response:
        return quick_response
    
    # If no quick pattern matches, use the ML approach
    return get_response(user_input)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    bot_response = enhanced_get_response(user_message)
    return jsonify({'response': bot_response})

if __name__ == '__main__':
    app.run(debug=True)