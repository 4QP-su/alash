import os
import json
from flask import Blueprint, request, jsonify, session, render_template
from werkzeug.utils import secure_filename
import google.generativeai as genai
from dotenv import load_dotenv
import tempfile
import uuid

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create blueprint
gemini_bp = Blueprint('gemini', __name__, url_prefix='/gemini')

# Store chat sessions (in production, use Redis or database)
chat_sessions = {}

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {'webm', 'wav', 'mp3', 'ogg', 'flac'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@gemini_bp.route('/chat', methods=['POST'])
def voice_chat():
    """Handle voice chat requests with audio transcription and text messages"""
    try:
        # Check if it's a text message (for hints)
        if request.is_json:
            data = request.get_json()
            message = data.get('message', '')
            message_type = data.get('type', 'text')
            
            if not message:
                return jsonify({'error': 'No message provided'}), 400
            
            # Get or create user session
            user_id = session.get('user_id', str(uuid.uuid4()))
            session['user_id'] = user_id
            
            if user_id not in chat_sessions:
                chat_sessions[user_id] = []
            
            # Initialize Gemini model
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            
            # Prepare chat history
            chat_history = chat_sessions[user_id]
            
            # Create chat session with history
            chat = model.start_chat(history=chat_history)
            
            # Get user language preference
            user_lang = session.get('lang', 'ru')
            
            # Send message with system instruction for hints
            if message_type == 'hint':
                if user_lang == 'ru':
                    system_instruction = "You are a cybersecurity assistant helping with SQL injection levels. Provide helpful hints without giving away complete solutions. Focus on techniques and concepts. Respond in Russian language."
                elif user_lang == 'kz':
                    system_instruction = "You are a cybersecurity assistant helping with SQL injection levels. Provide helpful hints without giving away complete solutions. Focus on techniques and concepts. Respond in Kazakh language."
                else:
                    system_instruction = "You are a cybersecurity assistant helping with SQL injection levels. Provide helpful hints without giving away complete solutions. Focus on techniques and concepts."
                response = chat.send_message([system_instruction, message])
            else:
                if user_lang == 'ru':
                    system_instruction = "You are a text assistant. Respond to the user's message in Russian language."
                elif user_lang == 'kz':
                    system_instruction = "You are a text assistant. Respond to the user's message in Kazakh language."
                else:
                    system_instruction = "You are a text assistant. Respond to the user's message."
                response = chat.send_message([system_instruction, message])
            
            # Update chat history
            chat_sessions[user_id].append(
                {"role": "user", "parts": [{"text": message}]}
            )
            chat_sessions[user_id].append(
                {"role": "model", "parts": [{"text": response.text}]}
            )
            
            # Keep only last 10 messages to avoid token limits
            if len(chat_sessions[user_id]) > 20:
                chat_sessions[user_id] = chat_sessions[user_id][-20:]
            
            return jsonify({
                'transcription': message,
                'response': response.text,
                'session_id': user_id
            })
        
        # Handle audio file
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Get or create user session
        user_id = session.get('user_id', str(uuid.uuid4()))
        session['user_id'] = user_id
        
        if user_id not in chat_sessions:
            chat_sessions[user_id] = []
        
        # Save audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
            file.save(temp_file.name)
            audio_path = temp_file.name
        
        try:
            # Initialize Gemini model
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            
            # Upload audio file to Gemini
            audio_file = genai.upload_file(audio_path)
            
            # Wait for file to be processed
            import time
            while audio_file.state.name == 'PROCESSING':
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
            
            if audio_file.state.name != 'ACTIVE':
                # Fallback to text message if audio processing fails
                return jsonify({
                    'error': 'Audio processing failed. Please try again or use text input.',
                    'fallback_text': True
                }), 400
            
            # System instruction
            system_instruction = "Transcribe the audio and respond to it."
            
            # Prepare chat history
            chat_history = chat_sessions[user_id]
            
            # Create chat session with history
            chat = model.start_chat(history=chat_history)
            
            # Send audio with system instruction
            response = chat.send_message([
                system_instruction,
                audio_file
            ])
            
            # Extract transcription and response
            response_text = response.text
            
            # Parse response (assuming format: "Transcription: [text]\nResponse: [text]")
            if "Transcription:" in response_text and "Response:" in response_text:
                parts = response_text.split("Response:")
                transcription = parts[0].replace("Transcription:", "").strip()
                bot_response = parts[1].strip()
            else:
                # Fallback: treat entire response as both transcription and response
                transcription = "Audio processed"
                bot_response = response_text
            
            # Update chat history
            chat_sessions[user_id].append(
                {"role": "user", "parts": [{"audio_file": audio_file.name}]}
            )
            chat_sessions[user_id].append(
                {"role": "model", "parts": [{"text": response_text}]}
            )
            
            # Keep only last 10 messages to avoid token limits
            if len(chat_sessions[user_id]) > 20:
                chat_sessions[user_id] = chat_sessions[user_id][-20:]
            
            return jsonify({
                'transcription': transcription,
                'response': bot_response,
                'session_id': user_id
            })
            
        finally:
            # Clean up temporary file
            if os.path.exists(audio_path):
                os.unlink(audio_path)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gemini_bp.route('/chat/history', methods=['GET'])
def get_chat_history():
    """Get chat history for current session"""
    user_id = session.get('user_id')
    if not user_id or user_id not in chat_sessions:
        return jsonify({'history': []})
    
    return jsonify({'history': chat_sessions[user_id]})

@gemini_bp.route('/chat/clear', methods=['POST'])
def clear_chat_history():
    """Clear chat history for current session"""
    user_id = session.get('user_id')
    if user_id and user_id in chat_sessions:
        chat_sessions[user_id] = []
    
    return jsonify({'message': 'Chat history cleared'})

@gemini_bp.route('/', methods=['GET'])
def voice_chat_page():
    """Render voice chat page"""
    return render_template('voice_chat.html')

@gemini_bp.route('/test', methods=['GET'])
def voice_test_page():
    """Render voice assistant test page"""
    return render_template('voice_test.html')

@gemini_bp.route('/health', methods=['GET'])
def health_check():
    """Check if Gemini API is configured"""
    if not os.getenv("GEMINI_API_KEY"):
        return jsonify({'error': 'Gemini API key not configured'}), 500
    
    return jsonify({'status': 'healthy', 'api_configured': True})
