import os
import json
from flask import Blueprint, request, jsonify, session, render_template
from werkzeug.utils import secure_filename
import google.generativeai as genai
from dotenv import load_dotenv
import tempfile
import uuid
import requests
from langdetect import detect, LangDetectException

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Create blueprint
gemini_bp = Blueprint('gemini', __name__, url_prefix='/gemini')

# Store chat sessions (in production, use Redis or database)
chat_sessions = {}

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {'webm', 'wav', 'mp3', 'ogg', 'flac'}

def detect_language(text):
    """Detect language from text"""
    try:
        detected = detect(text)
        # Map detected languages to our supported languages
        lang_map = {'ru': 'ru', 'kk': 'kz', 'ky': 'kz', 'en': 'en'}
        return lang_map.get(detected, 'en')
    except LangDetectException:
        return 'en'  # Default to English if detection fails

def load_theory_data(language='ru'):
    """Load theory data for the specified language"""
    try:
        theory_file = f"/app/levels_{language}.json"
        with open(theory_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}  # Return empty dict if file doesn't exist

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
            category = data.get('category', 'sql')  # Category: sql, xss, csrf, path, auth
            
            if not message:
                return jsonify({'error': 'No message provided'}), 400
            
            # Get user's language from session
            user_lang = session.get('lang', 'ru')
            
            # Detect language from message
            detected_lang = detect_language(message)
            
            # Use detected language if it differs from session language
            if detected_lang != user_lang:
                user_lang = detected_lang
            
            # Load theory data as context
            theory_data = load_theory_data(user_lang)
            print(f"Loaded theory data length: {len(theory_data)}, language: {user_lang}")
            
            # Category names for system instructions
            category_names = {
                'sql': {'ru': 'SQL инъекциям', 'kz': 'SQL инъекциялары', 'en': 'SQL injection'},
                'xss': {'ru': 'XSS атакам', 'kz': 'XSS шабуылдары', 'en': 'XSS attacks'},
                'csrf': {'ru': 'CSRF атакам', 'kz': 'CSRF шабуылдары', 'en': 'CSRF attacks'},
                'path': {'ru': 'Path Traversal атакам', 'kz': 'Path Traversal шабуылдары', 'en': 'Path Traversal attacks'},
                'auth': {'ru': 'Auth Bypass атакам', 'kz': 'Auth Bypass шабуылдары', 'en': 'Auth Bypass attacks'}
            }
            
            cat_name = category_names.get(category, category_names['sql'])
            
            # Prepare system instruction with strict boundaries
            if message_type == 'hint':
                if user_lang == 'ru':
                    system_instruction = f"""You are a cybersecurity assistant helping with {cat_name['en']} levels. 

STRICT RULES:
1. ONLY answer questions about cybersecurity, {cat_name['en']}, web vulnerabilities, and related technical topics.
2. If asked about unrelated topics (physics, biology, general knowledge, etc.), politely refuse: "Извините, я могу отвечать только на вопросы по кибербезопасности и {cat_name['ru']}."
3. Provide helpful hints without giving away complete solutions.
4. Keep answers short (1-3 sentences).
5. Respond ONLY in Russian language."""
                elif user_lang == 'kz':
                    system_instruction = f"""You are a cybersecurity assistant helping with {cat_name['en']} levels.

STRICT RULES:
1. ONLY answer questions about cybersecurity, {cat_name['en']}, web vulnerabilities, and related technical topics.
2. If asked about unrelated topics (physics, biology, general knowledge, etc.), politely refuse: "Кешіріңіз, мен тек киберқауіпсіздік және {cat_name['kz']} бойынша сұрақтарға жауап бере аламын."
3. Provide helpful hints without giving away complete solutions.
4. Keep answers short (1-3 sentences).
5. Respond ONLY in Kazakh language."""
                else:
                    system_instruction = f"""You are a cybersecurity assistant helping with {cat_name['en']} levels.

STRICT RULES:
1. ONLY answer questions about cybersecurity, {cat_name['en']}, web vulnerabilities, and related technical topics.
2. If asked about unrelated topics (physics, biology, general knowledge, etc.), politely refuse: "Sorry, I can only answer questions about cybersecurity and {cat_name['en']}."
3. Provide helpful hints without giving away complete solutions.
4. Keep answers short (1-3 sentences)."""
            else:
                if user_lang == 'ru':
                    system_instruction = f"""You are a cybersecurity assistant for {cat_name['en']} training.

STRICT RULES:
1. ONLY answer questions about cybersecurity, {cat_name['en']}, web vulnerabilities, and related technical topics.
2. If asked about unrelated topics (physics, biology, general knowledge, etc.), politely refuse: "Извините, я могу отвечать только на вопросы по кибербезопасности и {cat_name['ru']}."
3. Answer in the same language as the user's question.
4. Keep answers short and focused on cybersecurity concepts.
5. Respond ONLY in Russian language."""
                elif user_lang == 'kz':
                    system_instruction = f"""You are a cybersecurity assistant for {cat_name['en']} training.

STRICT RULES:
1. ONLY answer questions about cybersecurity, {cat_name['en']}, web vulnerabilities, and related technical topics.
2. If asked about unrelated topics (physics, biology, general knowledge, etc.), politely refuse: "Кешіріңіз, мен тек киберқауіпсіздік және {cat_name['kz']} бойынша сұрақтарға жауап бере аламын."
3. Answer in the same language as the user's question.
4. Keep answers short and focused on cybersecurity concepts.
5. Respond ONLY in Kazakh language."""
                else:
                    system_instruction = f"""You are a cybersecurity assistant for {cat_name['en']} training.

STRICT RULES:
1. ONLY answer questions about cybersecurity, {cat_name['en']}, web vulnerabilities, and related technical topics.
2. If asked about unrelated topics (physics, biology, general knowledge, etc.), politely refuse: "Sorry, I can only answer questions about cybersecurity and {cat_name['en']}."
3. Answer in the same language as the user's question.
4. Keep answers short and focused on cybersecurity concepts."""
            
            # Call OpenRouter API
            try:
                auth_header = f"Bearer {OPENROUTER_API_KEY}"
                headers = {
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5001",
                    "X-Title": "SQL Exploit Trainer"
                }
                
                # Prepare messages in standard Chat Completion format
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": message}
                ]
                
                payload = {
                    "model": "openai/gpt-4o-mini",  # Cheap and fast model
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500
                }
                
                response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
                
                if response.status_code != 200:
                    print(f"OpenRouter API Error: {response.text}")
                    return jsonify({'error': f"API Error: {response.status_code}"}), response.status_code
                
                result = response.json()
                response_text = result['choices'][0]['message']['content']
            except Exception as e:
                print(f"OpenRouter API error: {e}")
                response_text = f"Error: {str(e)}"
            
            # Ensure response is valid for JSON
            result = {
                'transcription': message,
                'response': response_text
            }
            return jsonify(result)
        
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
            # OpenRouter does not support direct audio processing
            # Return error suggesting text input
            return jsonify({
                'error': 'Audio processing not supported with OpenRouter API. Please use text input.',
                'fallback_text': True
            }), 400
            
        finally:
            # Clean up temporary file
            if os.path.exists(audio_path):
                os.unlink(audio_path)
                
    except Exception as e:
        print(f"Error in voice_chat: {e}")
        import traceback
        traceback.print_exc()
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
    """Check if OpenRouter API is configured"""
    if not OPENROUTER_API_KEY:
        return jsonify({'error': 'OpenRouter API key not configured'}), 500
    
    return jsonify({'status': 'healthy', 'api_configured': True})
