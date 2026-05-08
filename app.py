# app.py - Refactored with Modular Architecture
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from werkzeug.utils import secure_filename
from flask_cors import CORS
from datetime import datetime, timedelta, date
import os
import re
import csv
import numpy as np
import socket
import traceback

from db_handler import get_db_handler
from ai_handler import ask_general_question, ask_with_file_parse
from quick_responses import learn_from_conversation
from context_manager import get_context_manager
from knowledge_base import get_knowledge_base
from session_manager import get_session_manager

import base64
from speaker_recognition.recognizer import recognizer
from speaker_recognition.models import TrainingRequest, VoiceSample, AudioInput, RecognitionRequest

from mcp_activity_client import handle_activity_query_via_mcp
from mcp_attendance_client import handle_attendance_query_via_mcp

from camera import VideoCamera, face_logs
camera = VideoCamera()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST"]}})

CSV_BASE_PATH = "c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/csv_files/"
AUDIO_PATH = "c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/voices_trained/"
TRANSCRIPT_PATH = "c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/speechlogs/"

def get_local_ip():
    """Get local IP address"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"

# @app.route('/hometest')
# def new_index():
#     return render_template('home.html')

@app.route('/')
def index():
    screenshots = []
    with os.scandir('webcam') as d:
        for e in d:
            if e.name[-4:] == '.jpg':
                screenshots.append(f"webcam/{e.name}")
    screenshots.reverse()
    
    known_faces = []
    with os.scandir('known_faces') as f:
        for g in f:
            if g.name[-4:] == '.jpg':
                known_faces.append(f"known_faces/{g.name}")
    
    ip_addr = request.remote_addr
    
    return render_template('index.html', screenshots=screenshots, known_faces=known_faces)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Endpoint for handling file uploads"""
    if 'file' in request.files:
        input_file = request.files['file']
        if '.csv' in input_file.filename:
            filename = secure_filename(input_file.filename)
            input_file.save(os.path.join(CSV_BASE_PATH, filename))
            print("File saved.")
            return jsonify({"success": True}), 200
        else:
            return jsonify({'error': 'Not a csv file'}), 400
    else:
        return jsonify({'error': 'No file part in the request'}), 400

@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """Endpoint for handling csv exports"""
    if os.path.exists(os.path.join(CSV_BASE_PATH, filename)):
        return send_from_directory(CSV_BASE_PATH, filename, as_attachment=True)
    else:
        return jsonify({'error': 'File or path does not exist'}), 404

@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint - routes queries to appropriate handlers"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        fileAttached = data.get('fileAttached', '')
        result = None
        
        if not message and not fileAttached:
            return jsonify({'error': 'Empty message'}), 400
        
        # debug command parser here
        if 'launch camera' in message:
            return jsonify({'redirect': 'webcam', 'msg_type': 'bot', 'message': 'Launching video feed...'}), 302
        
        # Initialize managers
        session_mgr = get_session_manager()
        context_mgr = get_context_manager()
        kb = get_knowledge_base()
        
        # Ensure session exists
        current_session = session_mgr.get_session_object(session_id) # this retrieves the Session Object, or creates one if it doesn't exist

        name_match = re.search(r'my name is (\w+)', message, re.IGNORECASE)
        if name_match:
            current_session.user_name = name_match.group(1)
            print("User name set to: ", name_match.group(1))
            # text = "Nice to meet you, " + name_match.group(1) + "! 👋 How can I assist you today? If you have any questions about attendance records or manufacturing activity, feel free to ask!"
            # result = {'answer': text, 'response_type': 'general'}
        
        # Create user message object
        user_msg = session_mgr.create_message('user', message, session_id)
        
        # Get context and knowledge
        relevant_context = current_session.get_relevant_context(message)

        # synchronous wrapper for unified mcp client
        # wrapper handles routing logic
        # unified client call appropriate server
        # merge ai handler to sync wrapper
        # unified_mcp_client = get_sync_wrapper()
        
        # Route query to appropriate handler
        # result = None
        
        # Priority 1: Activity Monitoring
        if 'debug-act' in message:
            result = handle_activity_query_via_mcp(message)
        
        # Priority 2: Attendance
        elif 'debug-att' in message:
            result = handle_attendance_query_via_mcp(message)

        # Attached file
        if fileAttached or '.csv' in message:
            # either message + file OR message includes filename
            result = ask_with_file_parse(fileAttached, message)
        
        # Process query: Attendance, Activity, Traceability, General
        if not result:
            result = ask_general_question(message, relevant_context, current_session.user_name)
        
        # Create bot message object
        csv_filename = result.get('csv_file', '')
        bot_msg = session_mgr.create_message('bot', result['answer'], session_id, user_msg['id'], 
                                                response_type=result['response_type'], csv = csv_filename, with_chart = result.get('with_chart', False))
        current_session.update_history(message, result['answer'])

        # Update context and learning
        if 'Request timeout' not in result['answer']:
            if 'debug-att' in message or 'debug-act' in message:
                message = message[10:]
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

@app.route('/chart/<path:csv_source>', methods=['GET', 'POST'])
def parseCsv(csv_source):
    """Process the given csv file to chart data"""
    try:
        # with open('./csv_files/Bryan_2026-02-01_2026-02-15.csv') as csvfile:
        with open('./csv_files/' + csv_source) as csvfile:
            reader = csv.DictReader(csvfile)
            records = [row for row in reader]
        
        date_range = csv_source[:-4].split('_')
        sd = date.fromisoformat(date_range[-2])
        ed = date.fromisoformat(date_range[-1])

        tups = {}
        while sd <= ed:
            tups[sd.isoformat()] = [0,0]
            sd += timedelta(days=1)

        for rec in records:
            date_r, time_r = rec['timestamp'].split(maxsplit=1)
            h,m,s = time_r.split(':')
            time_p = float(h) + (float(m)/60)
            if tups[date_r] == [0,0]:
                tups[date_r] = [time_p]
            else:
                tups[date_r].append(time_p)
        labels = list(tups.keys())
        data = list(tups.values())
        name = records[0]['employee_name']
        
        return jsonify({'success': True, 'labels': labels, 'data': data, 'name': name}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/webcam_update', methods=['POST'])
def update_status():
    """Handle webcam inputs"""
    if request.is_json:
        data = request.get_json()
        # print(data)
        img_src = camera.command(data)
        if img_src:
            while not os.path.exists(img_src):
                # makes sure the file already exists
                continue
            return jsonify({"success": True, "img_src": img_src}), 200
        
        return jsonify({"success": True}), 200
    else:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400

def gen(camera: VideoCamera):
    while camera.isOpened():
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        # do NOT put a break here so the feed can continue if stopped

@app.route('/video_feed')
def video_feed():
    return Response(gen(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/screenshots/<path:filename>", methods=['GET'])
def serve_img(filename):
    BASE_PATH = os.getcwd()
    return send_from_directory(BASE_PATH, filename)

@app.route("/webcam/meeting", methods=['POST'])
def log_speech2text():
    if request.is_json:
        data = request.get_json()
        if 'speech2text' in data:
            transcript = data.get('speech2text', '')
            curr_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            full_path = os.path.join(TRANSCRIPT_PATH, f'transcript_{curr_date}.txt')
            with open(full_path, 'w') as txt_file:
                txt_file.write(transcript)
        return jsonify({"success": True}), 200
    
    elif 'audioTrain' in request.files:
        audio_file = request.files['audioTrain']
        # print("To train: ", audio_file)
        filename = secure_filename(audio_file.filename)
        audio_file.save(os.path.join(AUDIO_PATH, filename))

        with open(f"voices_trained/{filename}", "rb") as raw_audio:
            base64_audio = base64.b64encode(raw_audio.read()).decode('utf-8')

        name = filename.split('.webm')
        audio_input = AudioInput(audio_data=base64_audio, sample_rate=16000)
        samples=[VoiceSample(user=name[0], audio=audio_input)]
        trainResult = recognizer.train(TrainingRequest(voice_samples=samples))
        # print(trainResult)
        audio_input = None
        base64_audio = None
        return jsonify({"success": True}), 200
    
    elif 'audioRecog' in request.files:
        audio_file = request.files['audioRecog']
        # print("To recognize: ", audio_file)
        filename = secure_filename(audio_file.filename)
        audio_file.save(os.path.join(AUDIO_PATH, filename))

        with open(f"voices_trained/{filename}", "rb") as raw_audio:
            base64_audio = base64.b64encode(raw_audio.read()).decode('utf-8')
        
        audio_input = AudioInput(audio_data=base64_audio, sample_rate=16000)
        recogResult = recognizer.recognize(RecognitionRequest(audio=audio_input))
        # print(recogResult)
        audio_input = None
        base64_audio = None
        return jsonify({"success": True, "speakerName": recogResult.user_id, "confidence": recogResult.confidence}), 200

    else:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400
    

def print_startup_banner():
    """Print startup banner with server info"""
    local_ip = get_local_ip()
    print(f"""
{'='*70}
🚀 Abigail AI Assistant - Full System
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
    
def load_voice_embeddings():
    recognizer._reference_embeddings = {}
    with os.scandir('./embeddings') as fileIter:
        for file in fileIter:
            user_id = file.name.split('_')[0]
            
            loaded_data = np.load(file.path, allow_pickle=False)
            embedding = np.asarray(loaded_data)
    
            recognizer._reference_embeddings[user_id] = embedding
        recognizer._is_trained = True
    print("Voice embeddings loaded from cache.")

if __name__ == '__main__':
    print_startup_banner()
    load_voice_embeddings()
    app.run(debug=False, host='0.0.0.0', port=8080, threaded=True)